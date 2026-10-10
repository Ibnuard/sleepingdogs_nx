"""Execute the linked v17 scheduler with modeled Horizon and mutex boundaries.

The real AArch64 registry, exclusion, retry, mask, and failure branches execute.
Kernel placement and FPS are not simulated. Struct offsets come from a separate
unlinked probe compiled with this exact candidate's recorded compiler command.
"""
from pathlib import Path
import argparse
import io
import json
import struct

from elftools.elf.elffile import ELFFile
from check_low_window_binary import Machine, ROOT
from port_common import sha, write_json


class SchedulerMachine(Machine):
    def __init__(self, elf, layout):
        super().__init__(elf_path=elf)
        self.layout = layout
        self.lock_depth = 0
        self.process_mask = 15
        self.process_failure = False
        self.fail_query = set()
        self.fail_set = set()
        self.masks = {}
        self.queries = []
        self.sets = []
        self.follows = []
        for name in ('svcGetThreadCoreMask', 'svcSetThreadCoreMask',
                     'pthread_mutex_lock', 'pthread_mutex_unlock',
                     'horizon_follow_thread_cores'):
            self.hooks[self.symbols[name]] = name

    def w32(self, address, value):
        self.vm.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def u32(self, address):
        return struct.unpack('<I', self.vm.mem_read(address, 4))[0]

    @staticmethod
    def signed(value):
        return struct.unpack('<i', struct.pack('<I', value & 0xffffffff))[0]

    def hook(self, vm, pc, size, unused):
        name = self.hooks.get(pc)
        if name == 'pthread_mutex_lock':
            self.lock_depth += 1
            assert self.lock_depth == 1
            self.ret()
        elif name == 'pthread_mutex_unlock':
            assert self.lock_depth == 1
            self.lock_depth -= 1
            self.ret()
        elif name == 'svcGetInfo':
            if self.x(1) == 0:  # InfoType_CoreMask, from the SDK.
                if self.process_failure:
                    self.ret(1)
                else:
                    self.q(self.x(0), self.process_mask)
                    self.ret()
            else:  # OFF-path thread tick query; no time elapsed in fixture.
                self.q(self.x(0), 0)
                self.ret()
        elif name == 'svcGetThreadCoreMask':
            assert self.lock_depth == 1
            handle = self.x(2)
            self.queries.append(handle)
            if handle in self.fail_query:
                self.ret(2)
            else:
                core, mask = self.masks[handle]
                self.w32(self.x(0), core)
                self.q(self.x(1), mask)
                self.ret()
        elif name == 'svcSetThreadCoreMask':
            assert self.lock_depth == 1
            handle, core, mask = self.x(0), self.signed(self.x(1)), self.x(2)
            self.sets.append((handle, core, mask))
            if handle in self.fail_set:
                self.ret(3)
            else:
                assert mask and (core == -1 or 0 <= core < 64 and mask & (1 << core))
                self.masks[handle] = (core, mask)
                self.ret()
        elif name == 'horizon_follow_thread_cores':
            assert self.lock_depth == 1
            self.follows.append((self.x(0), self.x(1)))
            self.ret()
        else:
            super().hook(vm, pc, size, unused)

    def reset(self):
        assert self.lock_depth == 0
        for name, size in (('registry', self.layout['registry_size']),
                           ('fex_dxvk_slots', self.layout['dxvk_size']),
                           ('sd_shader_slots', self.layout['shader_size'])):
            self.vm.mem_write(self.symbols[name], bytes(size * self.layout['max_threads']))
        self.vm.mem_write(self.symbols['sd_scheduler_counts'], bytes(48))
        for name, value in (('wine_nx_sd_auto_affinity', 1), ('wine_nx_balance_enabled', 1)):
            self.w32(self.symbols[name], value)
        self.process_mask = 15
        self.process_failure = False
        self.fail_query.clear()
        self.fail_set.clear()
        self.masks.clear()
        self.queries.clear()
        self.sets.clear()
        self.follows.clear()

    def thread(self, index=0, handle=41, kind='w', core=0, actual_core=None,
               mask=1, fixed=0, teb=None, dxvk_active=0, shader_mode=0,
               shader_core=2, shader_mask=4):
        layout, symbols = self.layout, self.symbols
        if teb is None:
            teb = self.back + 4096 + index * 256
        address = symbols['registry'] + index * layout['registry_size']
        for field, value in (('handle', handle), ('tid', 4 + 4 * index),
                             ('core', core), ('fixed', fixed)):
            self.w32(address + layout['registry_' + field], value)
        self.vm.mem_write(address + layout['registry_kind'], kind.encode())
        self.q(address + layout['registry_teb'], teb)
        dxvk = symbols['fex_dxvk_slots'] + index * layout['dxvk_size']
        self.w32(dxvk + layout['dxvk_active'], dxvk_active)
        shader = symbols['sd_shader_slots'] + index * layout['shader_size']
        self.w32(shader + layout['shader_mode'], shader_mode)
        self.w32(shader + layout['shader_core'], shader_core)
        self.q(shader + layout['shader_mask'], shader_mask)
        self.masks[handle] = (core if actual_core is None else actual_core, mask)
        return teb, shader

    def run(self):
        self.call('wine_nx_thread_balance')
        assert self.lock_depth == 0
        return list(struct.unpack('<6Q', self.vm.mem_read(self.symbols['sd_scheduler_counts'], 48)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, default=ROOT / 'local/symbols/sleepingdogs-scheduler-v17.elf')
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/scheduler-v17-binary.json')
    args = parser.parse_args()
    receipt = json.loads((ROOT / 'local/scheduler-v17/native.json').read_text())
    layout_meta = json.loads((ROOT / 'local/scheduler-v17/scheduler-layout.json').read_text())
    obj_path = ROOT / 'local/scheduler-v17/scheduler-layout.o'
    assert sha(args.elf) == receipt['elf_sha256'] == layout_meta['build_elf_sha256']
    assert sha(obj_path) == layout_meta['object_sha256']
    obj = ELFFile(io.BytesIO(obj_path.read_bytes()))
    raw = obj.get_section_by_name('.sd_v17_layout').data()
    assert len(raw) == len(layout_meta['fields']) * 8
    layout = dict(zip(layout_meta['fields'], struct.unpack('<' + 'Q' * len(layout_meta['fields']), raw)))
    machine = SchedulerMachine(args.elf, layout)
    cases = []

    def record(name, expected_counts, expected_sets, expected_follows, queries):
        counts = machine.run()
        assert counts == expected_counts, (name, counts, expected_counts)
        assert machine.sets == expected_sets, (name, machine.sets, expected_sets)
        assert machine.follows == expected_follows, (name, machine.follows, expected_follows)
        assert machine.queries == queries, (name, machine.queries, queries)
        cases.append(dict(name=name, counts=counts, set_calls=machine.sets.copy(),
                          follow_calls=machine.follows.copy(), queried=machine.queries.copy()))

    try:
        # Runtime startup loads the default-ON config; the ELF's BSS is zero
        # before startup. Each fixture explicitly selects the tested mode.
        for name, process, actual_core, registered, current, wanted in (
            ('broad-mask-preserves-preferred', 15, 2, 0, 4, 2),
            ('sparse-process-mask', 13, 2, 0, 4, 2),
            ('invalid-preferred-uses-registered', 15, -1, 1, 1, 1),
            ('invalid-both-use-lowest', 15, -1, -1, 4, 0),
            ('core3-preferred-falls-back', 15, 3, 2, 8, 2),
            ('single-allowed-core', 2, 2, 0, 4, 1),
            ('removed-process-grant', 3, 2, 1, 7, 1),
        ):
            machine.reset()
            machine.process_mask = process
            teb, _ = machine.thread(core=registered, actual_core=actual_core, mask=current)
            allowed = process & 7
            record(name, [1, 0, 0, 0, 0, 0], [(41, wanted, allowed)], [(teb, allowed)], [41])
        for name, actual_core, teb_value in (
            ('already-correct-confirms-follow', 1, None),
            ('already-correct-no-preference', -1, None),
            ('already-correct-without-teb', 1, 0),
        ):
            machine.reset()
            teb, _ = machine.thread(mask=7, actual_core=actual_core, teb=teb_value)
            record(name, [0, 1, 0, 0, 0, 0], [], [(teb, 7)] if teb else [], [41])
        for name, parameters in (
            ('fixed-single-mask', {'fixed': 1}),
            ('fixed-multiple-mask', {'fixed': 1, 'mask': 5}),
            ('server-thread-excluded', {'kind': 's'}),
            ('empty-registry-slot', {'handle': 0}),
            ('core3-helper-excluded', {'dxvk_active': 1}),
            ('shader-worker-excluded', {'shader_mode': layout['shader_worker']}),
            ('shader-pipeline-excluded', {'shader_mode': layout['shader_pipeline']}),
        ):
            machine.reset()
            machine.thread(**parameters)
            record(name, [0] * 6, [], [], [])
        machine.reset()
        machine.thread()
        machine.fail_query.add(41)
        record('query-failure-does-not-follow', [0, 0, 1, 0, 0, 0], [], [], [41])
        machine.reset()
        machine.thread()
        machine.fail_set.add(41)
        record('set-failure-does-not-follow', [0, 0, 0, 1, 0, 0], [(41, 0, 7)], [], [41])
        machine.reset()
        teb, state = machine.thread(fixed=1, shader_mode=layout['shader_restore'], shader_core=2, shader_mask=5)
        record('pending-explicit-restore-before-exclusion', [0] * 6, [(41, 2, 5)], [(teb, 5)], [])
        assert machine.u32(state + layout['shader_mode']) == layout['shader_none']
        machine.reset()
        _, state = machine.thread(shader_mode=layout['shader_restore'])
        machine.fail_set.add(41)
        record('pending-failed-restore-remains-excluded', [0] * 6, [(41, 2, 4)], [], [])
        assert machine.u32(state + layout['shader_mode']) == layout['shader_restore']
        machine.reset()
        teb, _ = machine.thread(shader_mode=layout['shader_restore'])
        record('completed-auto-restore-then-broaden', [1, 0, 0, 0, 0, 0],
               [(41, 2, 4), (41, 2, 7)], [(teb, 4), (teb, 7)], [41])
        for process in (0, 8):
            machine.reset()
            machine.process_mask = process
            machine.thread()
            record('no-application-cores-' + str(process), [0, 0, 0, 0, 0, 1], [], [], [])
        machine.reset()
        machine.thread()
        machine.process_failure = True
        record('process-query-failure', [0, 0, 0, 0, 1, 0], [], [], [])
        machine.reset()
        machine.thread()
        machine.w32(machine.symbols['wine_nx_balance_enabled'], 0)
        record('no-balance-disables-registry-update', [0] * 6, [], [], [])
        machine.reset()
        machine.thread()
        machine.w32(machine.symbols['wine_nx_sd_auto_affinity'], 0)
        record('off-does-not-broaden-without-load', [0] * 6, [], [], [41])
        machine.reset()
        teb1, _ = machine.thread(index=0)
        teb2, _ = machine.thread(index=127, handle=42, core=1, mask=2)
        record('registry-first-and-last-slot', [2, 0, 0, 0, 0, 0],
               [(41, 0, 7), (42, 1, 7)], [(teb1, 7), (teb2, 7)], [41, 42])
    finally:
        machine.close()
    write_json(args.report, dict(status='PASS', scope=__doc__, elf_sha256=sha(args.elf),
        layout=layout, abi_probe=layout_meta, compiled_cases=cases,
        hardware_tested=False, fps_gain_measured=False,
        sources={name: sha(ROOT / 'tests' / name) for name in (
            'check_scheduler_v17_binary.py', 'extract_scheduler_v17_layout.py', 'check_low_window_binary.py')}))
    print('PASS:', len(cases), 'linked ARM64 scheduler cases; ELF', sha(args.elf), flush=True)


if __name__ == '__main__':
    main()
