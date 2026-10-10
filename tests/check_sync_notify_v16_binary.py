"""Execute the shipped ARM64 notification helper with modeled condvars/mutexes.

Concurrent waits are covered by the production-handler pthread sanitizer suite.
This check verifies that the real compiled ON/OFF guards and counters preserve
shared/private legacy wakes and skip only the unrelated direct-queue broadcast.
"""
from pathlib import Path
import json
import struct
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'tools')]
from port_common import ROOT, sha, write_json
from check_low_window_binary import Machine


class NotifyMachine(Machine):
    def __init__(self, path):
        super().__init__('good', path)
        self.notifications = []
        self.lock_depth = 0
        for name in ('pthread_cond_signal', 'pthread_cond_broadcast',
                     'pthread_mutex_lock', 'pthread_mutex_unlock'):
            self.hooks[self.symbols[name]] = name

    def hook(self, vm, pc, size, unused):
        name = self.hooks.get(pc)
        if name in ('pthread_cond_signal', 'pthread_cond_broadcast'):
            self.notifications.append((name, self.x(0)))
            self.ret()
        elif name == 'pthread_mutex_lock':
            self.lock_depth += 1
            assert self.lock_depth == 1
            self.ret()
        elif name == 'pthread_mutex_unlock':
            assert self.lock_depth == 1
            self.lock_depth -= 1
            self.ret()
        else:
            super().hook(vm, pc, size, unused)

    def u32(self, p):
        return struct.unpack('<I', self.vm.mem_read(p, 4))[0]

    def w32(self, p, value):
        self.vm.mem_write(p, struct.pack('<I', value))


def main():
    elf = ROOT / 'local/symbols/sleepingdogs-sync-v16.elf'
    receipt = json.loads((ROOT / 'local/sync-notify-v16/native.json').read_text())
    assert sha(elf) == receipt['elf_sha256']
    m = NotifyMachine(elf)
    cases = []
    try:
        s = m.symbols
        assert m.u32(s['wine_nx_sd_sync_notify_filter']) == 1, 'default not ON'
        direct = m.back
        legacy, condition, snapshot = m.back + 512, m.back + 1024, m.back + 2048
        # AArch64 C ABI: five pointers, three unsigneds, three ints precede
        # pthread_cond_t in the production sd_sync_waiter. No packing applies.
        notified_offset, condition_offset = 56, 64
        for mode in (0, 1, 2):
            for enabled in (0, 1):
                for routed in (0, 1):
                    for reason in (0, 1, 2):
                        m.vm.mem_write(m.back, bytes(4096))
                        m.vm.mem_write(s['sd_sync_counts'], bytes(64))
                        m.vm.mem_write(s['sd_sync_legacy_counts'], bytes(32))
                        m.vm.mem_write(s['fex_sync_router'], bytes(56))
                        m.q(s['sd_sync_waiters'], direct)
                        m.q(s['sd_sync_counts'] + 6 * 8, 1)
                        m.w32(direct + 52, 1)
                        m.w32(s['horizon_fast_sync_enabled'], mode)
                        m.w32(s['wine_nx_sd_sync_notify_filter'], enabled)
                        m.w32(s['wine_nx_fex_targeted_wake'], routed)
                        m.w32(s['horizon_server_sleepers'], 1)
                        if routed:
                            m.q(s['fex_sync_router'], legacy)
                            m.q(legacy + 16, condition)  # NULL interest is broad.
                        m.notifications = []
                        m.call('sd_sync_signal_legacy_locked', reason)
                        active = mode == 2 and bool(enabled)
                        expected = [('pthread_cond_broadcast', s['horizon_server_objects_cond'])]
                        if routed:
                            expected.append(('pthread_cond_signal', condition))
                        if not active:
                            expected.append(('pthread_cond_signal', direct + condition_offset))
                        assert sorted(m.notifications) == sorted(expected), (mode, enabled, routed, reason, m.notifications)
                        assert m.u32(direct + notified_offset) == (not active)
                        assert m.u32(direct + 60) == 0, 'broad route consumed a signal'
                        assert m.uq(s['sd_sync_counts'] + 2 * 8) == (not active)
                        m.call('wine_nx_sd_sync_notify_snapshot', snapshot)
                        got = struct.unpack('<5Q', m.vm.mem_read(snapshot, 40))
                        counts = [0, 0, 0]
                        counts[reason] = 1
                        assert got == (enabled, *counts, int(active)), got
                        assert m.lock_depth == 0
                        cases.append(dict(mode=mode, filter=enabled, legacy_router=routed,
                            reason=reason, direct_signals=int(not active), shared_broadcasts=1,
                            private_legacy_signals=routed, snapshot=list(got)))
    finally:
        m.close()
    write_json(ROOT / 'reports/sync-notify-v16-binary.json', dict(status='PASS',
        scope=__doc__, elf_sha256=sha(elf), default_enabled=True,
        compiled_cases=cases, hardware_tested=False, fps_gain_measured=False,
        sources={'tests/check_sync_notify_v16_binary.py': sha(Path(__file__)),
                 'tests/check_low_window_binary.py': sha(ROOT / 'tests/check_low_window_binary.py')}))
    print('PASS:', len(cases), 'actual ARM64 notification guard/counter cases; legacy wakes preserved', flush=True)


if __name__ == '__main__':
    main()
