"""Exercise the new linked ARM64 admission helper and its real low-VA probes.

The native-stack allocator and 1000-MiB arena boundary are modeled here; the
separate arena test executes its real protection/alias operations on Linux.
"""
from pathlib import Path
import argparse
import json
import struct
import sys

from check_low_window_binary import Machine, ROOT
from port_common import sha, write_json

ELF = ROOT / 'local/symbols/sleepingdogs-low-window-v2.elf'


class Admission(Machine):
    def __init__(self, mode, elf=ELF):
        super().__init__('good' if mode == 'arena_fail' else mode, elf)
        self.arena_fail = mode == 'arena_fail'
        self.order = []
        self.arena_allocations = 0
        for name in ('wine_nx_f1_native_stacks_init', 'sd_low_window_init', 'sd_guest_arena_init'):
            self.hooks[self.symbols[name]] = name

    def hook(self, vm, pc, size, data):
        name = self.hooks.get(pc)
        if name == 'wine_nx_f1_native_stacks_init':
            self.order.append('stacks')
            self.ret()
        elif name == 'sd_low_window_init':
            self.order.append('probe')  # Observe, do not replace the real probe.
        elif name == 'sd_guest_arena_init':
            assert struct.unpack('<I', vm.mem_read(self.symbols['sd_low_ready'], 4))[0] == 1
            self.order.append('arena')
            if not self.arena_fail and not self.uq(self.symbols['sd_arena_base']):
                self.q(self.symbols['sd_arena_base'], 0x30000000)
                self.arena_allocations += 1
            self.ret()
        else:
            super().hook(vm, pc, size, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, default=ELF)
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/low-window-admission-binary.json')
    args = parser.parse_args()
    cases = []
    for mode in ('good', 'stock39', 'old32', 'quota2g', 'wrong_title', 'low_heap',
                 'no_handle', 'occupied', 'map_fail', 'process_perm_fail', 'unmap_fail', 'arena_fail'):
        m = Admission(mode, args.elf)
        result = m.call('sd_launch_memory_prepare', m.stack + 0x1000, 192)
        assert bool(result) == (mode == 'good'), (mode, result)
        assert m.order == (['stacks', 'probe', 'arena'] if mode in ('good', 'arena_fail') else ['stacks', 'probe'])
        if mode == 'good':
            assert m.executed == 1 and m.maps == 2 and m.arena_allocations == 1
            assert m.call('sd_launch_memory_prepare', m.stack + 0x1000, 192) == 1
            assert m.executed == 1 and m.maps == 2 and m.arena_allocations == 1
        else:
            assert m.arena_allocations == 0
        assert m.depth == 0
        cases.append(mode)
        m.close()
    report = {'status': 'PASS', 'scope': __doc__, 'hardware_tested': False,
              'elf_sha256': sha(args.elf), 'cases': cases, 'test_sha256': sha(Path(__file__)),
              'harness_sha256': sha(ROOT / 'tests/check_low_window_binary.py')}
    write_json(args.report, report)
    print('PASS 12 linked ARM64 admission cases, including probe execution and retry')


if __name__ == '__main__':
    main()
