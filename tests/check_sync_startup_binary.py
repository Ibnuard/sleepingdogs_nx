"""Replay the linked ARM64 syscall dispatcher and real get_cpu_area.

TEB/TLS, syscall returns, locks and clock are fixtures. The v4 regression must
fault at address 2 inside the actual Wine get_cpu_area; v5 must return the
original syscall status without entering that function until CPU TLS exists.
The collector is observed at its boundary and has separate ASan/UBSan tests.
This is not a hardware run or a reproduction of the game loading freeze.
"""
from pathlib import Path
import argparse
import io
import json
import struct
from elftools.elf.elffile import ELFFile
from unicorn import UcError, UC_HOOK_MEM_INVALID
from unicorn import arm64_const as arm
from check_low_window_binary import Machine, ROOT
from port_common import sha, write_json

V4_SHA = 'e9519a8cfdabcad70c5a5f16c5054eb64bad0146759f695a7ae006c965070df6'


class Startup(Machine):
    def __init__(self, elf, cpu='missing', debug=True, handler='NtClose', status=0, wow=True):
        super().__init__(elf_path=elf)
        self.handler = handler
        self.status = status
        self.calls = self.cpu_calls = 0
        self.notes = []
        self.faults = []
        self.lock_depth = 0
        binary = ELFFile(io.BytesIO(elf.read_bytes()))
        self.tls_offsets = {s.name: s['st_value'] + 16
                            for s in binary.get_section_by_name('.symtab').iter_symbols()
                            if s['st_info']['type'] == 'STT_TLS'}
        self.cpu_range = next((self.symbols[s.name], self.symbols[s.name] + s['st_size'])
                              for s in binary.get_section_by_name('.symtab').iter_symbols()
                              if s.name == 'get_cpu_area')
        for name in ('NtCurrentTeb', 'pthread_getspecific', '__aarch64_read_tp',
                     'pthread_mutex_lock', 'pthread_mutex_unlock', 'get_cpu_area',
                     'sd_sync_note', handler):
            self.hooks[self.symbols[name]] = name
        self.invalid_hook = self.vm.hook_add(UC_HOOK_MEM_INVALID, self.invalid)
        self.q(self.back + 0x48, 4)  # TEB64.ClientId.UniqueThread
        self.q(self.back + 0x1488, 0 if cpu == 'missing' else self.back + 0x3000)
        self.vm.mem_write(self.back + 0x3000, struct.pack('<HH', 0, 0x14c if cpu == 'ready' else 0xaa64))
        self.regs = tuple(range(0x12340000, 0x12340009))
        for value, offset in zip(self.regs, (0xb0, 0xa4, 0xac, 0xa8, 0xa0, 0x9c, 0xb4, 0xc4, 0xb8)):
            self.vm.mem_write(self.back + 0x3004 + offset, struct.pack('<I', value))
        self.q(self.symbols['wow_peb'], self.back + 0x4000 if wow else 0)
        self.vm.mem_write(self.symbols['f1_startup_watch_enabled'], struct.pack('<I', int(debug)))
        self.vm.mem_write(self.symbols['wine_nx_runtime_verbose'], bytes(4))
        self.q(self.back + 0x5000, self.symbols[handler])
        self.vm.mem_write(self.symbols['KeServiceDescriptorTable'],
                          struct.pack('<4Q', self.back + 0x5000, 0, 1, 0))

    def invalid(self, vm, access, address, size, value, data):
        self.faults.append({'address': address, 'pc': vm.reg_read(arm.UC_ARM64_REG_PC), 'size': size})
        return False

    def hook(self, vm, pc, size, data):
        name = self.hooks.get(pc)
        if name in ('NtCurrentTeb', 'pthread_getspecific'):
            self.ret(self.back)
        elif name == '__aarch64_read_tp':
            self.ret(self.tls)
        elif name == 'pthread_mutex_lock':
            self.lock_depth += 1
            assert self.lock_depth == 1
            self.ret()
        elif name == 'pthread_mutex_unlock':
            assert self.lock_depth == 1
            self.lock_depth -= 1
            self.ret()
        elif name == 'get_cpu_area':
            self.cpu_calls += 1  # Observe entry; execute the real function.
        elif name == self.handler:
            self.calls += 1
            if name in ('NtCreateSemaphore', 'NtOpenSemaphore') and not self.status:
                # Model the scalar captured at the successful native return.
                self.q(self.tls + self.tls_offsets['sd_sync_create_serial'], self.calls)
                self.q(self.tls + self.tls_offsets['sd_sync_last_created'], 0x804)
            self.ret(self.status)
        elif name == 'sd_sync_note':
            self.notes.append({'kind': self.x(0), 'tid': self.x(1), 'handle': self.x(2),
                               'status': self.x(3), 'initial': self.x(4), 'maximum': self.x(5),
                               'registers': struct.unpack('<9I', vm.mem_read(self.x(7), 36))})
            self.ret()
        else:
            super().hook(vm, pc, size, data)

    def dispatch(self):
        # wine_nx_do_syscall has ten AAPCS64 arguments, two on the stack.
        self.q(self.stack + 0xf000, 0)
        self.q(self.stack + 0xf008, 0)
        return self.call('wine_nx_do_syscall', 0, 0x6d4ffff0, 0, 0, 7, 1000, 0, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-elf', type=Path, default=ROOT / 'local/symbols/sleepingdogs-low-window-v4.elf')
    parser.add_argument('--elf', type=Path, default=ROOT / 'local/symbols/sleepingdogs-low-window-v5.elf')
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/low-window-v5-sync-startup-binary.json')
    parser.add_argument('--negative-only', action='store_true')
    args = parser.parse_args()
    assert sha(args.old_elf) == V4_SHA
    cases = []
    evidence = []
    for handler in ('NtClose', 'NtCreateSemaphore', 'NtOpenSemaphore'):
        m = Startup(args.old_elf, handler=handler)
        try:
            m.dispatch()
        except UcError:
            assert len(m.faults) == 1 and m.faults[0]['address'] == 2
            assert m.cpu_range[0] <= m.faults[0]['pc'] < m.cpu_range[1]
            assert m.calls == m.cpu_calls == 1
            evidence.append(dict(handler=handler, **m.faults[0]))
        else:
            raise AssertionError('The pinned v4 regression was not reproduced')
        m.close()
        cases.append('v4 '+handler+' with missing CPU area faults at address 2')
    for debug, wow in ((False, True), (True, False)):
        m = Startup(args.old_elf, debug=debug, wow=wow)
        assert m.dispatch() == 0 and not m.faults and m.calls == 1
        m.close()
        cases.append(f'v4 control debug={debug} wow_peb={wow} returns normally')
    if not args.negative_only:
        for handler, status in (('NtClose', 0), ('NtClose', 0xc0000008),
                                ('NtCreateSemaphore', 0), ('NtOpenSemaphore', 0),
                                ('NtWaitForSingleObject', 0xc0000008)):
            for cpu in ('missing', 'wrong_machine', 'ready'):
                m = Startup(args.elf, cpu=cpu, handler=handler, status=status)
                assert m.dispatch() == status and not m.faults and m.calls == 1 and not m.lock_depth
                assert m.cpu_calls == (cpu != 'missing')
                assert len(m.notes) == (cpu == 'ready')
                if m.notes:
                    note = m.notes[0]
                    assert note['registers'] == m.regs and note['tid'] == 4 and note['status'] == status
                    assert note['handle'] == (0x804 if handler in ('NtCreateSemaphore', 'NtOpenSemaphore') else 0x6d4ffff0)
                    if handler == 'NtCreateSemaphore':
                        assert note['initial'] == 7 and note['maximum'] == 1000
                m.close()
                cases.append(f'v5 {handler} status={status:08x} CPU={cpu}')
        m = Startup(args.elf, debug=False)
        assert m.dispatch() == 0 and not m.faults and not m.cpu_calls and not m.notes
        m.close()
        cases.append('v5 GUI/debug-off does not request a CPU area')
    for case in cases:
        print('PASS', case, flush=True)
    if not args.negative_only:
        write_json(args.report, {'status': 'PASS', 'scope': __doc__, 'hardware_tested': False,
            'old_elf_sha256': V4_SHA, 'elf_sha256': sha(args.elf), 'cases': cases,
            'old_faults': evidence, 'sources': {str(p.relative_to(ROOT)): sha(p) for p in
            (Path(__file__), ROOT / 'tests/check_low_window_binary.py')}})


if __name__ == '__main__':
    main()
