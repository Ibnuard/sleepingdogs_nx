"""Execute real x86 DXVK deferred Map instructions with allocation/log boundaries.

Original shipped DLL must reproduce the recorded read at NULL+0x28. Candidate
must return OOM with no new command/map entry, while successful calls still
record the real command and retain the real allocation reference.
"""
from pathlib import Path
import json
import struct
import sys
import pefile
from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_INVALID
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP
from check_wow64_context_binary import symbols
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json


class MapReplay:
    def __init__(self,path):
        self.path=path;self.pe=pefile.PE(str(path));self.syms=symbols(self.pe)
        self.vm=Uc(UC_ARCH_X86,UC_MODE_32);vm=self.vm
        base=self.pe.OPTIONAL_HEADER.ImageBase
        vm.mem_map(base,(self.pe.OPTIONAL_HEADER.SizeOfImage+4095)&-4096)
        vm.mem_write(base,self.pe.get_memory_mapped_image())
        vm.mem_map(0x20000000,0x1000000);vm.mem_map(0x22000000,0x10000);vm.mem_map(0x23000000,0x1000)
        self.ctx=0x20000000;self.buffer=0x20010000;self.dxbuf=0x20011000
        self.output=0x20012000;self.allocation=0x20013000;self.allocator=0x20014000
        self.queue=0x20020000;self.entries=0x20025000;self.storage=0x20100000
        self.entry=self.symbol('D3D11DeferredContext9MapBuffer')
        self.update=self.symbol('D3D11DeferredContext18UpdateMappedBuffer')
        self.allocate=self.symbol('DxvkMemoryAllocator20createBufferResource')
        self.logger=self.symbol('4dxvk6Logger3errE')
        self.formats={v for n,v in self.syms.items() if '4dxvk3str6formatIJA56_cj' in n}
        self.ctors={v for n,v in self.syms.items() if 'basic_stringIc' in n and 'EC2B9' in n and n.endswith('EPKc')}
        self.fail=True;self.calls=0;self.logs=0;self.faults=[]
        self.d(self.buffer+0x60,1);self.d(self.buffer+0x64,self.dxbuf)
        self.d(self.buffer+0x68,0x12345678);self.d(self.dxbuf+4,self.allocator)
        self.d(self.dxbuf+8,1);self.d(self.dxbuf+0x2c,7);self.d(self.dxbuf+0x48,0x200c3)
        self.d(self.allocation,1);self.d(self.allocation+0x28,self.storage)
        self.d(self.ctx+0x3458,self.queue);self.d(self.queue+0xc,self.queue+8)
        self.d(self.ctx+0x34bc,self.entries);self.d(self.ctx+0x34c0,self.entries);self.d(self.ctx+0x34c4,self.entries+1024)
        vm.hook_add(UC_HOOK_CODE,self.hook)
        vm.hook_add(UC_HOOK_MEM_INVALID,self.invalid)
    def symbol(self,fragment):
        hits=[v for n,v in self.syms.items() if fragment in n and n.startswith('__ZN') and '$_' not in n]
        assert len(hits)==1,(fragment,hits)
        return hits[0]
    def d(self,p,v):self.vm.mem_write(p,struct.pack('<I',v&0xffffffff))
    def u(self,p):return struct.unpack('<I',self.vm.mem_read(p,4))[0]
    def q(self,p):return struct.unpack('<Q',self.vm.mem_read(p,8))[0]
    def ret(self,value=0,pop=0):
        sp=self.vm.reg_read(UC_X86_REG_ESP)
        self.vm.reg_write(UC_X86_REG_EAX,value)
        self.vm.reg_write(UC_X86_REG_ESP,sp+4+pop)
        self.vm.reg_write(UC_X86_REG_EIP,self.u(sp))
    def invalid(self,vm,access,address,size,value,user):
        self.faults.append({'pc':hex(vm.reg_read(UC_X86_REG_EIP)),'address':hex(address),'bytes':size})
        return False
    def hook(self,vm,pc,size,user):
        sp=vm.reg_read(UC_X86_REG_ESP)
        if pc==self.allocate:
            assert self.u(sp+4)==self.allocator
            info=self.u(sp+8)
            assert self.q(info+16)==self.u(self.buffer+0x1c)
            self.d(vm.reg_read(UC_X86_REG_ECX),0 if self.fail else self.allocation)
            self.calls+=1;self.ret(pop=16)
        elif pc==self.logger:self.logs+=1;self.ret()
        elif pc in self.formats:
            # Only diagnostic string construction is modeled, not the branch.
            assert self.u(self.u(sp+12))==self.u(self.buffer+0x1c)
            vm.mem_write(self.u(sp+4),bytes(12));self.ret()
        elif pc in self.ctors:
            vm.mem_write(vm.reg_read(UC_X86_REG_ECX),bytes(12));self.ret(pop=4)
    def call(self,need=5242880,update=False):
        vm=self.vm;self.d(self.buffer+0x1c,need);self.d(self.dxbuf+0x40,need)
        self.d(self.output,0xcafebabe);self.d(self.output+4,0x1234);self.d(self.output+8,0x5678)
        args=[self.buffer,16,8,self.storage,0] if update else [self.buffer,self.output]
        sp=0x2200f000
        vm.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x23000000,*args))
        vm.reg_write(UC_X86_REG_ESP,sp);vm.reg_write(UC_X86_REG_ECX,self.ctx)
        vm.emu_start(self.update if update else self.entry,0x23000000,count=30000)
        assert vm.reg_read(UC_X86_REG_EIP)==0x23000000
        assert vm.reg_read(UC_X86_REG_ESP)==sp+4+4*len(args)
        return vm.reg_read(UC_X86_REG_EAX)
    def state(self):
        return (bytes(self.vm.mem_read(self.ctx,0x3500)),bytes(self.vm.mem_read(self.queue,0x5000)),
                bytes(self.vm.mem_read(self.entries,1024)))


def main():
    original=ROOT/'local/compiler-memory-validate-dg3y8pil/switch/sleepingdogs-fex/launcher/renderers/dxvk-3.1.1/d3d11.dll'
    candidate=ROOT/'dist/dxvk-memory-fix/x32/d3d11.dll'
    assert sha(original)=='598c56dce50a04adb9c2d6f134d380697b6ef1c5c3dcbf65a6de29e636710be7'
    old=MapReplay(original)
    try:old.call()
    except UcError:pass
    else:raise AssertionError('Old DLL unexpectedly survived null allocation')
    assert old.faults==[{'pc':'0x10073556','address':'0x28','bytes':4}],old.faults
    results=[]
    for need in (1,65536,5242880,9437184):
        new=MapReplay(candidate);before=new.state()
        assert new.call(need)==0x8007000e
        assert bytes(new.vm.mem_read(new.output,12))==bytes(12)
        assert new.state()==before and new.calls==new.logs==1 and not new.faults
        new.call(need,update=True)
        assert new.state()==before and new.calls==new.logs==2 and not new.faults
        results.append({'bytes':need,'oom_hresult':'0x8007000e','failed_update_no_copy':True})
    new=MapReplay(candidate);new.fail=False
    assert new.call()==0
    assert (new.u(new.output),new.u(new.output+4),new.u(new.output+8))==(new.storage,5242880,5242880)
    assert new.u(new.queue+4)==16 and new.u(new.ctx+0x34c0)==new.entries+24
    assert new.u(new.queue+0x48)==new.dxbuf and new.u(new.queue+0x4c)==new.allocation
    assert new.q(new.dxbuf+8)==2 and new.u(new.allocation)==1
    assert new.u(new.entries)==0x12345678 and new.u(new.entries+8)==new.storage
    before=new.state();new.fail=True
    assert new.call()==0x8007000e and new.state()==before
    new.d(new.buffer+0x60,0);calls=new.calls
    assert new.call()==0x80070057 and new.calls==calls and not new.u(new.output)
    report={'status':'PASS','dll_sha256':sha(candidate),'baseline_sha256':sha(original),
        'baseline_fault':old.faults,'oom_cases':results,'success_command_ownership':True,
        'failed_remap_preserves_previous_commands':True,'invalid_mode':'PASS',
        'sources':{'tests/check_dxvk_map_binary.py':sha(Path(__file__))},
        'limits':'Real DLL instructions; Vulkan resource creation and diagnostics modeled. No complete game/GPU execution.'}
    write_json(ROOT/'reports/dxvk-map-binary-check.json',report)
    print(json.dumps(report))


if __name__=='__main__':main()
