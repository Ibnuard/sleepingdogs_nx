"""Replay shipped ARM64 topology queries and original x86 game initialization.

Native allocation, pthread_once, logging and PEB values are fixtures. Wine's
linked topology builder and NtQuerySystemInformation(/Ex) execute unchanged.
The x86 test executes HKShip's CPU probe, queue initialization and index read,
plus the real kernelbase GetLogicalProcessorInformation. The WoW64 structure
conversion is a model of dlls/wow64/system.c; no game file is modified.
"""
from pathlib import Path
import argparse
import json
import struct
import sys
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn import arm64_const as arm, x86_const as x86
from check_low_window_binary import Machine, ROOT
from port_common import sha, write_json

V5_SHA = '1e933b326bdffa9144b9158498083c21c60b81023665d313470c7b93a9652f59'
GAME = ROOT.parent / 'Sleeping Dogs/HKShip.exe'
KERNELBASE = ROOT.parent / 'pes13-nx/local/production-input-fix/approved/switch/pes13-fex/drive_c/windows/syswow64/kernelbase.dll'
NOT_IMPLEMENTED, LENGTH_MISMATCH, ACCESS_VIOLATION = 0xc0000002, 0xc0000004, 0xc0000005


class Topology(Machine):
    def __init__(self, elf, count=4, fail_allocation=0):
        super().__init__(elf_path=elf)
        self.count = count
        self.once_calls = self.alloc_calls = 0
        self.fail_allocation = fail_allocation
        self.allocations = {}
        self.heap = 0x1300000000
        self.vm.mem_map(self.heap, 0x200000)
        self.heap_next = self.heap
        self.q(self.symbols['peb'], self.back)
        self.put(self.back + 0xb8, count)
        for name in ('pthread_once', 'realloc', 'malloc', 'calloc', 'memcpy', 'memset',
                     'free', '__wine_dbg_get_channel_flags', '__wine_dbg_header', '__wine_dbg_output'):
            if name in self.symbols:
                self.hooks[self.symbols[name]] = name

    def put(self, at, value): self.vm.mem_write(at, struct.pack('<I', value))
    def u32(self, at): return struct.unpack('<I', self.vm.mem_read(at, 4))[0]

    def hook(self, vm, pc, size, data):
        name = self.hooks.get(pc)
        if name == 'pthread_once':
            if self.u32(self.x(0)):
                self.ret()
            else:
                self.once_calls += 1
                self.put(self.x(0), 1)
                # Execute the real initializer and return to pthread_once's caller.
                vm.reg_write(arm.UC_ARM64_REG_PC, self.x(1))
        elif name in ('realloc', 'malloc', 'calloc'):
            self.alloc_calls += 1
            old = self.x(0) if name == 'realloc' else 0
            length = self.x(1) if name == 'realloc' else self.x(0)
            if name == 'calloc': length *= self.x(1)
            if self.alloc_calls == self.fail_allocation:
                self.ret(0)
                return
            ptr = self.heap_next
            self.heap_next += (length + 63) & ~63
            assert self.heap_next < self.heap + 0x200000
            vm.mem_write(ptr, bytes(length))
            if old:
                vm.mem_write(ptr, bytes(vm.mem_read(old, min(length, self.allocations.pop(old)))))
            self.allocations[ptr] = length
            self.ret(ptr)
        elif name == 'free':
            if self.x(0): self.allocations.pop(self.x(0))
            self.ret()
        elif name == 'memcpy':
            vm.mem_write(self.x(0), bytes(vm.mem_read(self.x(1), self.x(2))))
            self.ret(self.x(0))
        elif name == 'memset':
            vm.mem_write(self.x(0), bytes([self.x(1) & 255]) * self.x(2))
            self.ret(self.x(0))
        elif name and name.startswith('__wine_dbg_'):
            self.ret(0)
        else:
            super().hook(vm, pc, size, data)

    def query(self, length=0, null=False, relation=None):
        output, retlen, query = self.back + 0x1000, self.back + 0x100, self.back + 0x108
        self.vm.mem_write(output, b'\xa5' * 0x8000)
        self.put(retlen, 0xdeadbeef)
        if relation is None:
            status = self.call('NtQuerySystemInformation', 73, 0 if null else output, length, retlen)
        else:
            self.put(query, relation)
            status = self.call('NtQuerySystemInformationEx', 107, query, 4,
                               0 if null else output, length, retlen)
        needed = self.u32(retlen)
        assert needed < 0x8000
        payload = bytes(self.vm.mem_read(output, needed)) if not status else b''
        assert bytes(self.vm.mem_read(output + max(length, needed), 16)) == b'\xa5' * 16
        return status & 0xffffffff, needed, payload

    def wow64_query(self, length):
        # Model the existing WoW64 conversion, consuming real native API output.
        status, needed, payload = self.query(length * 2)
        if status not in (0, LENGTH_MISMATCH): return status, None, b''
        count = needed // 32
        if not status and length >= count * 24:
            converted = b''.join(struct.pack('<II', struct.unpack_from('<Q', payload, i*32)[0] & 0xffffffff,
                                             struct.unpack_from('<I', payload, i*32+8)[0]) + payload[i*32+16:i*32+32]
                                 for i in range(count))
        else:
            status, converted = LENGTH_MISMATCH, b''
        return status, count * 24, converted


class Guest:
    def __init__(self, topology):
        self.native = topology
        self.vm = Uc(UC_ARCH_X86, UC_MODE_32)
        for path in (GAME, KERNELBASE):
            pe = pefile.PE(str(path))
            self.vm.mem_map(pe.OPTIONAL_HEADER.ImageBase, (pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
            self.vm.mem_write(pe.OPTIONAL_HEADER.ImageBase, pe.get_memory_mapped_image())
        self.stack, self.data, self.api, self.stop = 0x1600000, 0x30000000, 0x2000000, 0x2000f00
        for address, length in ((0, 0x1000), (self.stack, 0x10000), (self.data, 0x10000), (self.api, 0x1000)):
            self.vm.mem_map(address, length)
        self.put(0x18, self.data)  # TEB fixture for kernelbase SetLastError.
        self.queue = self.data + 0x2000
        self.tls_index = 0
        self.queries = []
        self.hooks = {}
        for slot, (iat, name) in enumerate(((0x10e12b8, 'GetSystemInfo'),
                (0x10e11dc, 'LoadLibraryA'), (0x10e11a8, 'GetProcAddress'),
                (0x10e12f0, 'FreeLibrary'), (0x7b09424c, 'NtQuerySystemInformation'),
                (0x7b094558, 'RtlNtStatusToDosError'), (0x10e11f0, 'TlsGetValue'))):
            address = self.api + 16 * slot
            self.put(iat, address)
            self.hooks[address] = name
        # Queue storage allocation and lock release are outside this test's scope.
        self.hooks[0xbb82f0] = 'queue_storage'
        self.hooks[0xbb6fe0] = 'unlock'
        self.put(0x14c17a8, 10)
        self.put(0x14c17a4, 11)
        self.vm.hook_add(UC_HOOK_CODE, self.hook)

    def put(self, at, value): self.vm.mem_write(at, struct.pack('<I', value & 0xffffffff))
    def u32(self, at): return struct.unpack('<I', self.vm.mem_read(at, 4))[0]
    def reg(self, name, value=None):
        register = getattr(x86, 'UC_X86_REG_' + name)
        if value is None: return self.vm.reg_read(register)
        self.vm.reg_write(register, value)
    def ret(self, result, nargs):
        sp = self.reg('ESP')
        self.reg('EAX', result)
        self.reg('EIP', self.u32(sp))
        self.reg('ESP', sp + 4 + 4*nargs)
    def args(self, count):
        return [self.u32(self.reg('ESP') + 4 + i*4) for i in range(count)]

    def hook(self, vm, pc, size, data):
        name = self.hooks.get(pc)
        if pc == self.stop:
            vm.emu_stop()
        elif name == 'GetSystemInfo':
            self.put(self.args(1)[0] + 20, self.native.count)
            self.ret(0, 1)
        elif name in ('LoadLibraryA', 'FreeLibrary'):
            self.ret(1, 1)
        elif name == 'GetProcAddress':
            assert bytes(vm.mem_read(self.args(2)[1], 31)) == b'GetLogicalProcessorInformation\0'
            self.ret(0x7b03a240, 2)
        elif name == 'NtQuerySystemInformation':
            klass, out, length, retlen = self.args(4)
            assert klass == 73
            status, needed, payload = self.native.wow64_query(length)
            self.queries.append({'input_length': length, 'status': hex(status), 'returned_length': needed})
            if needed is not None: self.put(retlen, needed)
            if payload: vm.mem_write(out, payload)
            self.ret(status, 4)
        elif name == 'RtlNtStatusToDosError':
            status = self.args(1)[0]
            self.ret(122 if status == 0xc0000023 else 120, 1)
        elif name == 'TlsGetValue':
            index = self.args(1)[0]
            assert index in (10, 11)
            self.ret(self.tls_index if index == 10 else self.data + 0x8000, 1)
        elif name == 'queue_storage': self.ret(0, 1)
        elif name == 'unlock': self.ret(0, 1)

    def run(self, start, end=None, ecx=None):
        self.reg('ESP', self.stack + 0xe000)
        self.reg('EBP', self.stack + 0xf000)
        self.put(self.reg('ESP'), self.stop)
        if ecx is not None: self.reg('ECX', ecx)
        self.vm.emu_start(start, end or self.stop, count=100000)
        assert self.reg('EIP') == (end or self.stop), hex(self.reg('EIP'))

    def initialize(self):
        q = self.queue
        self.vm.mem_write(q, b'\xde' * 0x400)
        # Actual configuration default constructor calls HKShip's actual CPU
        # probe (GetSystemInfo + GetLogicalProcessorInformation) into this+0xc.
        self.run(0xbb8030, ecx=q+0x58)
        count = self.u32(q+0x64)
        for offset, value in ((0x18,self.data+0x1000),(0x24,22),(0x28,0),(0x2c,1),
                             (0x30,1),(0x34,23),(0x74,0),(0x294,0),(0x298,0)):
            self.put(q+offset,value)
        self.run(0xbb7300, end=0xbb759c, ecx=q)
        indices = []
        for self.tls_index in range(max(1, count)):
            self.reg('ESI', q)
            self.reg('EBX', self.data+0x1000)
            self.run(0xbb86de, end=0xbb8730)
            indices.append(self.reg('EDI'))
        return {'worker_count':count,'queue_default_index':self.u32(q+0x54),
                'indices':indices,'queries':self.queries,
                'table':bytes(self.vm.mem_read(q+0x121,12)).hex()}


def parse_legacy(payload):
    return [{'mask':struct.unpack_from('<Q',payload,i)[0],
             'relation':struct.unpack_from('<I',payload,i+8)[0],
             'body':payload[i+16:i+32].hex()} for i in range(0,len(payload),32)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf',type=Path,default=ROOT/'local/symbols/sleepingdogs-low-window-v6.elf')
    parser.add_argument('--old-elf',type=Path,default=ROOT/'local/symbols/sleepingdogs-low-window-v5.elf')
    parser.add_argument('--report',type=Path,default=ROOT/'reports/low-window-v6-cpu-topology.json')
    args=parser.parse_args()
    assert sha(args.old_elf)==V5_SHA
    assert sha(GAME)=='3c2eaa260ee29dfb464a0321aa9c7dc74e343894b663fac4fdd11d40fab0bacc'
    assert sha(KERNELBASE)=='972a55bf3fc8e7f7f6fa9ac62c9c8ec44cb5463bb891f71a0358f2eb03c60a9f'
    old=Topology(args.old_elf)
    assert old.query()[0]==NOT_IMPLEMENTED
    old_guest=Guest(old).initialize()
    assert old_guest['worker_count']==0 and old_guest['indices']==[0xffffffde],old_guest
    old.close()
    print('PASS: original v5 API -> original game CPU count 0 -> queue index -34',flush=True)
    cases=[]
    for count in (1,3,4,64):
        m=Topology(args.elf,count)
        status,needed,_=m.query(null=True)
        assert status==LENGTH_MISMATCH and needed==(count+2)*32,(status,needed)
        assert m.query(needed-1)[0]==LENGTH_MISMATCH
        assert m.query(needed,null=True)[0]==ACCESS_VIOLATION
        status,length,payload=m.query(needed)
        assert status==0 and length==needed
        records=parse_legacy(payload)
        assert [r['mask'] for r in records if r['relation']==0]==[1<<i for i in range(count)]
        assert [r['mask'] for r in records if r['relation']==3]==[(1<<count)-1]
        assert [r['mask'] for r in records if r['relation']==1]==[(1<<count)-1]
        for relation,n in ((0,count),(1,1),(2,0),(3,1),(4,1),(0xffff,count+3)):
            status,needed,_=m.query(relation=relation)
            assert status==(LENGTH_MISMATCH if n else 0)
            status,length,payload=m.query(needed,relation=relation)
            assert status==0 and length==needed
            pos=0; ex=[]
            while pos<len(payload):
                rel,size=struct.unpack_from('<II',payload,pos);assert size>=8
                ex.append((rel,size))
                if rel in (0,3):
                    assert struct.unpack_from('<H',payload,pos+30)[0]==1
                    if rel==0:assert payload[pos+8]==0  # no SMT
                pos+=size
            assert pos==len(payload) and len(ex)==n
        assert m.once_calls==1
        if count==4:
            new_guest=Guest(m).initialize()
            assert new_guest['worker_count']==4 and new_guest['indices']==[1,0,0,0],new_guest
            assert new_guest['queue_default_index']==0
        cases.append({'count':count,'legacy_records':records,'status':'PASS'})
        m.close()
    for count in (0,65):
        m=Topology(args.elf,count)
        assert m.query()[0]==NOT_IMPLEMENTED
        assert not m.allocations
        cases.append({'count':count,'invalid_count_rejected':True})
        m.close()
    # Fail the first legacy/extended allocation and a later growth, checking
    # the existing Wine initializer discards partial topology on failure.
    for fail in (1,2,3,5):
        m=Topology(args.elf,fail_allocation=fail)
        assert m.query()[0]==NOT_IMPLEMENTED
        assert not m.allocations,m.allocations
        cases.append({'fail_allocation':fail,'partial_topology_discarded':True})
        m.close()
    report={'status':'PASS','scope':__doc__,'hardware_tested':False,'game_modified':False,
            'elf_sha256':sha(args.elf),'old_elf_sha256':sha(args.old_elf),
            'game_sha256':sha(GAME),'kernelbase_sha256':sha(KERNELBASE),
            'old_game':old_guest,'new_game':new_guest,'cases':cases,
            'sources':{n:sha(ROOT/n) for n in ('tests/check_cpu_topology_binary.py',
                'tests/check_low_window_binary.py','src/low_window/sd_cpu_topology.inc')}}
    write_json(args.report,report)
    print(json.dumps({k:report[k] for k in ('status','elf_sha256','hardware_tested','old_game','new_game')},indent=2))
    print('PASS:',len(cases),'topology/error-path groups; report:',args.report)


if __name__=='__main__':main()
