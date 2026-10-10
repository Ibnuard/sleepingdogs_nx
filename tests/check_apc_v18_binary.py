"""Replay the linked ARM64 APC notifier with modeled condition variables.

The actual target filter, ON/OFF guards, legacy router, and counters execute.
ABI offsets come from an unlinked probe compiled with the candidate recipe.
This is not a hardware scheduler test; concurrent delivery and object waits
are exercised separately by the production-handler pthread sanitizer suite.
"""
from pathlib import Path
import argparse
import io
import json
import struct

from elftools.elf.elffile import ELFFile
from check_low_window_binary import Machine, ROOT
from port_common import sha, write_json


class ApcMachine(Machine):
    def __init__(self, elf, layout):
        super().__init__(elf_path=elf)
        self.layout = layout
        self.lock_depth = 0
        self.notifications = []
        for name in ('pthread_cond_signal', 'pthread_cond_broadcast',
                     'pthread_mutex_lock', 'pthread_mutex_unlock'):
            self.hooks[self.symbols[name]] = name

    def w32(self, address, value):
        self.vm.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def u32(self, address):
        return struct.unpack('<I', self.vm.mem_read(address, 4))[0]

    def hook(self, vm, pc, size, unused):
        name = self.hooks.get(pc)
        if name in ('pthread_cond_signal', 'pthread_cond_broadcast'):
            assert self.lock_depth == 1, 'notification outside object lock'
            self.notifications.append((name, self.x(0)))
            self.ret()
        elif name == 'pthread_mutex_lock':
            assert self.x(0) == self.symbols['horizon_server_objects_mutex']
            assert self.lock_depth == 0
            self.lock_depth = 1
            self.ret()
        elif name == 'pthread_mutex_unlock':
            assert self.x(0) == self.symbols['horizon_server_objects_mutex']
            assert self.lock_depth == 1
            self.lock_depth = 0
            self.ret()
        else:
            super().hook(vm, pc, size, unused)

    def reset(self, enabled, mode, routed, sleepers, shape):
        assert self.lock_depth == 0
        self.vm.mem_write(self.back, bytes(65536))
        self.cursor = self.back
        self.notifications = []
        layout, symbols = self.layout, self.symbols
        self.vm.mem_write(symbols['fex_sync_router'], bytes(layout['router_size']))
        self.q(symbols['sd_sync_waiters'], 0)
        for name, value in (('wine_nx_sd_apc_targeted_wake', enabled),
                            ('horizon_fast_sync_enabled', mode),
                            ('wine_nx_fex_targeted_wake', routed),
                            ('horizon_server_sleepers', sleepers)):
            self.w32(symbols[name], value)
        self.apc_seed = [7, 11, 13, 17]
        self.sync_seed = [101, 103, 107, 109, 113, 127, len(shape), 131]
        self.vm.mem_write(symbols['sd_apc_notify_counts'], struct.pack('<4Q', *self.apc_seed))
        self.vm.mem_write(symbols['sd_sync_counts'], struct.pack('<8Q', *self.sync_seed))
        self.objects = [self.allocate(layout['object_size']) for unused in range(3)]
        for address in self.objects:
            self.vm.mem_write(address, bytes([0xa5]) * layout['object_size'])
        self.object_before = [bytes(self.vm.mem_read(p, layout['object_size'])) for p in self.objects]
        self.waiters = []
        self.connections = []
        for identity, pending in shape:
            connection = self.allocate(layout['connection_size'])
            self.q(connection + layout['connection_thread'], self.objects[identity])
            address = self.allocate(layout['waiter_size'])
            self.q(address + layout['waiter_connection'], connection)
            # Poisoned request/data pointers detect accidental predicate access.
            self.q(address + layout['waiter_request'], 0xdead1000)
            self.q(address + layout['waiter_data'], 0xdead2000)
            for name, value in (('data_size', 12), ('count', 2), ('status', 0x102),
                                ('queued', 1), ('notified', pending), ('completed', 1)):
                self.w32(address + layout['waiter_' + name], value)
            self.waiters.append(address)
            self.connections.append(connection)
        for index, address in enumerate(self.waiters):
            self.q(address + layout['waiter_next'], self.waiters[index + 1] if index + 1 < len(shape) else 0)
        if self.waiters:
            self.q(symbols['sd_sync_waiters'], self.waiters[0])
        self.waiter_before = [bytes(self.vm.mem_read(p, layout['waiter_size'])) for p in self.waiters]
        self.connection_before = [bytes(self.vm.mem_read(p, layout['connection_size'])) for p in self.connections]
        self.legacy_conditions = []
        legacy = []
        for index in range(2):
            address = self.allocate(layout['legacy_waiter_size'])
            condition = self.allocate(layout['condition_size'])
            interest = self.allocate(layout['legacy_interest_size'])
            self.w32(interest + layout['legacy_interest_count'], 1)
            self.w32(interest + layout['legacy_interest_handles'], 0xdeadbeef)
            self.q(interest + layout['legacy_interest_thread'], self.objects[1])
            self.q(address + layout['legacy_waiter_interest'], interest if index else 0)
            self.q(address + layout['legacy_waiter_condition'], condition)
            legacy.append(address)
            self.legacy_conditions.append(condition)
        self.q(legacy[0] + layout['legacy_waiter_next'], legacy[1])
        self.q(symbols['fex_sync_router'] + layout['router_head'], legacy[0])
        self.router_seed = dict(notices=19, broad_notices=23, candidates=29,
                                notified=31, filtered=37, sleeps=41)
        for name, value in self.router_seed.items():
            self.q(symbols['fex_sync_router'] + layout['router_' + name], value)
        self.snapshot = self.allocate(40)

    def allocate(self, size):
        address = self.cursor
        self.cursor += (size + 15) & ~15
        assert self.cursor <= self.back + 65536
        return address


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, default=ROOT / 'local/symbols/sleepingdogs-apc-v18.elf')
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/apc-v18-binary.json')
    args = parser.parse_args()
    destination = ROOT / 'local/apc-v18'
    receipt = json.loads((destination / 'native.json').read_text())
    metadata = json.loads((destination / 'apc-layout.json').read_text())
    obj = destination / 'apc-layout.o'
    assert sha(args.elf) == receipt['elf_sha256'] == metadata['build_elf_sha256']
    assert sha(obj) == metadata['object_sha256']
    assert sha(destination / 'apc-layout.c') == metadata['probe_sha256']
    assert sha(destination / 'apc-notifier-disassembly.txt') == metadata['disassembly_sha256']
    assert sha(destination / 'apc-notifier-caller.txt') == metadata['caller_evidence_sha256']
    host_report_path = ROOT / 'reports/apc-v18-host-check.json'
    host_report = json.loads(host_report_path.read_text())
    assert host_report['status'] == 'PASS'
    rejection_test = next(line for line in host_report['test_output']
                          if 'accepted enqueue only:' in line)
    assert 'invalid/wrong-type/terminated cause no notice' in rejection_test
    raw = ELFFile(io.BytesIO(obj.read_bytes())).get_section_by_name('.sd_v18_apc_layout').data()
    assert len(raw) == len(metadata['fields']) * 8
    layout = dict(zip(metadata['fields'], struct.unpack('<' + 'Q' * len(metadata['fields']), raw)))
    assert layout['apc_counter_bytes'] == 32 and layout['sync_counter_bytes'] == 64
    machine = ApcMachine(args.elf, layout)
    cases = []
    shapes = {
        'empty-list': [],
        'one-target': [(0, 0)],
        'one-unrelated': [(1, 0)],
        'multiple-targets': [(0, 0), (1, 0), (0, 0)],
        'pending-target': [(0, 1), (1, 0)],
        'pending-unrelated': [(1, 1), (0, 0)],
        'all-pending': [(0, 1), (1, 1), (0, 1)],
    }
    try:
        assert machine.u32(machine.symbols['wine_nx_sd_apc_targeted_wake']) == 1, 'default not ON'
        for mode in (0, 1, 2):
            for enabled in (0, 1):
                for routed in (0, 1):
                    for sleepers in (0, 1):
                        for shape_name, shape in shapes.items():
                            # The only production caller first checks if(thread).
                            # GCC specializes this static helper by omitting its
                            # defensive NULL guard, so NULL is not a reachable
                            # input to the linked function. Host tests cover the
                            # source guard and rejected handle enqueue path.
                            for target_kind in ('matching', 'absent'):
                                machine.reset(enabled, mode, routed, sleepers, shape)
                                target = machine.objects[0] if target_kind == 'matching' else machine.objects[2]
                                active = enabled and mode == 2
                                target_indices = [i for i, (identity, pending) in enumerate(shape)
                                                  if machine.objects[identity] == target]
                                candidates = target_indices if active else list(range(len(shape)))
                                signal_indices = [i for i in candidates if not shape[i][1]]
                                expected = [('pthread_cond_signal', machine.waiters[i] + layout['waiter_condition']) for i in signal_indices]
                                if routed:
                                    expected += [('pthread_cond_signal', c) for c in machine.legacy_conditions]
                                if sleepers:
                                    expected.append(('pthread_cond_broadcast', machine.symbols['horizon_server_objects_cond']))
                                machine.lock_depth = 1
                                machine.call('sd_sync_signal_apc_locked', target)
                                assert machine.lock_depth == 1
                                machine.lock_depth = 0
                                label = (mode, enabled, routed, sleepers, shape_name, target_kind)
                                assert sorted(machine.notifications) == sorted(expected), (label, machine.notifications, expected)
                                for i, address in enumerate(machine.waiters):
                                    wanted = bytearray(machine.waiter_before[i])
                                    if i in signal_indices:
                                        struct.pack_into('<I', wanted, layout['waiter_notified'], 1)
                                    assert bytes(machine.vm.mem_read(address, layout['waiter_size'])) == wanted, (label, 'waiter mutation', i)
                                for addresses, before, size in ((machine.objects, machine.object_before, layout['object_size']),
                                                                (machine.connections, machine.connection_before, layout['connection_size'])):
                                    for address, original in zip(addresses, before):
                                        assert bytes(machine.vm.mem_read(address, size)) == original, (label, 'object/connection mutation')
                                sync_expected = machine.sync_seed.copy()
                                sync_expected[1 if active else 2] += len(signal_indices)
                                assert struct.unpack('<8Q', machine.vm.mem_read(machine.symbols['sd_sync_counts'], 64)) == tuple(sync_expected), label
                                apc_expected = machine.apc_seed.copy()
                                apc_expected[0] += 1
                                if active:
                                    apc_expected[1] += len(target_indices)
                                    apc_expected[2] += len(shape) - len(target_indices)
                                    apc_expected[3] += len(signal_indices)
                                machine.call('wine_nx_sd_apc_notify_snapshot', machine.snapshot)
                                got = struct.unpack('<5Q', machine.vm.mem_read(machine.snapshot, 40))
                                assert got == (enabled, *apc_expected), (label, got, apc_expected)
                                assert machine.lock_depth == 0
                                for name, seed in machine.router_seed.items():
                                    addition = (1 if name in ('notices', 'broad_notices') else 2 if name in ('candidates', 'notified') else 0) if routed else 0
                                    assert machine.uq(machine.symbols['fex_sync_router'] + layout['router_' + name]) == seed + addition, (label, 'legacy router', name)
                                cases.append(dict(mode=mode, enabled=enabled, legacy_router=routed,
                                    shared_sleepers=sleepers, shape=shape_name, target=target_kind,
                                    direct_signals=len(signal_indices), target_candidates=len(target_indices) if active else 0,
                                    unrelated_skipped=len(shape) - len(target_indices) if active else 0,
                                    shared_broadcasts=sleepers, private_legacy_signals=2 * routed,
                                    snapshot=list(got)))
    finally:
        machine.close()
    write_json(args.report, dict(status='PASS', scope=__doc__, elf_sha256=sha(args.elf),
        default_enabled=True, compiled_cases=cases, case_count=len(cases),
        hardware_tested=False, fps_gain_measured=False,
        reachable_input_contract=dict(
            target_nonnull=True, sole_caller='f1_server_queue_apc',
            caller_line=metadata['caller_line'], caller_count=metadata['caller_count'],
            caller_precondition='if (thread), nonterminated target, successful f1_apc_push before notice',
            excluded_synthetic_cases=168,
            excluded_input='NULL target passed directly to static helper',
            reason='GCC specialized away the defensive NULL-target guard; production caller cannot pass NULL.',
            disassembly_observation='Flag guard at 0x1e56d4, mode guard at 0x1e56e4, target stored from x0 at 0x1e56ec and compared to connection.thread at 0x1e5730; no target NULL guard.',
            disassembly_sha256=metadata['disassembly_sha256'],
            caller_evidence_sha256=metadata['caller_evidence_sha256'],
            host_rejection_test=rejection_test, host_report_sha256=sha(host_report_path)),
        layout=dict(values=layout, object_sha256=sha(obj),
                    metadata_sha256=sha(destination / 'apc-layout.json'),
                    probe_sha256=metadata['probe_sha256'], production_sha256=metadata['production_sha256']),
        sources={name:sha(ROOT / name) for name in ('tests/check_apc_v18_binary.py',
            'tests/extract_apc_v18_layout.py', 'tests/check_low_window_binary.py')}))
    print('PASS:', len(cases), 'actual ARM64 APC guards/counters; legacy wakes and object state preserved', flush=True)


if __name__ == '__main__':
    main()
