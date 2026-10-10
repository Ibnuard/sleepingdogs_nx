"""Execute actual ARM64 newlib/GPU/stack code from old and new runtime ELFs.

The heap pressure pattern is synthetic, using the recorded process capacity
and GPU usage. It is not a reconstruction of every hardware allocation.
Only sbrk, locks, diagnostic I/O and libnx kernel thread boundaries are modeled.
Allocator results, arena ownership, stack retry and cleanup execute unchanged.
"""
from pathlib import Path
import json
import struct
import sys
from unicorn import UC_HOOK_CODE
from native_heap_binary import Heap, reg
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json

MiB = 1024 * 1024
CAPACITY = 2002944000
GPU_USED = 112525312


def pressure(data, reserved, filler=None):
    m = Heap(data, capacity=CAPACITY)
    m.vm.mem_map(m.start + 32 * MiB, ((CAPACITY + 4095) & -4096) - 32 * MiB)
    m.q(m.symbols['fake_heap_start'], m.start); m.q(m.symbols['fake_heap_end'], m.cap)
    m.call('wine_nx_f1_gpu_heap_init')
    pool = m.symbols['f1_gpu_pool']; base = m.uq(pool)
    assert base and struct.unpack('<I', m.vm.mem_read(pool + 8, 4))[0] * 65536 == reserved
    g = m.align(65536, GPU_USED, True); assert g == base
    m.vm.mem_write(g, b'GPU!'); m.vm.mem_write(g + GPU_USED - 4, b'TAIL')
    game = m.align(4096, 1000 * MiB); assert game
    m.vm.mem_write(game, b'GAME'); m.vm.mem_write(game + 1000 * MiB - 4, b'END!')
    # Same live CPU allocations and fragmented holes in both binaries.
    cpu = [m.malloc(96 * MiB), m.malloc(16 * MiB), m.malloc(128 * MiB), m.malloc(200 * MiB)]
    assert all(cpu)
    holes = []
    for _ in range(5):
        holes.append(m.malloc(6 * MiB)); guard = m.malloc(MiB); assert holes[-1] and guard
        cpu.append(guard); m.vm.mem_write(guard, b'KEEP')
    if filler is None:
        filler = ((m.cap - m.brk - 65536) & -4096)
    held = m.malloc(filler); assert held
    for p in holes: m.free(p)
    available = m.info()[8] + m.cap - m.brk
    # Invoke native FEX allocation on the new success path. The baseline only
    # tests its real ordinary-heap request, not the separate page-store fallback.
    if reserved == 256 * MiB:
        scratch = m.align(4096, 16 * MiB); assert not scratch
        assert available >= 29 * MiB
    else:
        def io(vm, pc, size, unused):
            if pc == m.symbols['host_log']: m.ret()
        hook = m.vm.hook_add(UC_HOOK_CODE, io)
        scratch = m.call('allocate_scratch', 16 * MiB)
        assert scratch and not scratch % 4096
        m.vm.mem_write(scratch, b'FEX!'); m.vm.mem_write(scratch + 16 * MiB - 4, b'LAST')
        # Fill the remaining reservation, then prove GPU can grow past 128 MiB.
        rest = m.align(65536, reserved - GPU_USED, True); assert rest
        extra = m.align(65536, 8 * MiB, True); assert extra
        assert not (base <= extra < base + reserved)
        m.vm.mem_write(extra, b'MORE')
        for p in (rest, extra): m.call('wine_nx_f1_gpu_free', p)
        assert bytes(m.vm.mem_read(scratch, 4)) == b'FEX!'
        m.call('release_scratch', scratch); m.vm.hook_del(hook)
    assert bytes(m.vm.mem_read(g, 4)) == b'GPU!'
    assert bytes(m.vm.mem_read(g + GPU_USED - 4, 4)) == b'TAIL'
    assert bytes(m.vm.mem_read(game, 4)) == b'GAME'
    assert bytes(m.vm.mem_read(game + 1000 * MiB - 4, 4)) == b'END!'
    for p in cpu[4:]: assert bytes(m.vm.mem_read(p, 4)) == b'KEEP'
    m.call('wine_nx_f1_gpu_free', g)
    for p in cpu + [held, game]: m.free(p)
    report = {'gpu_reserve_bytes': reserved, 'gpu_live_bytes': GPU_USED,
        'common_filler_bytes': filler, 'general_heap_available_before_request': available,
        'ordinary_16m_request_success': bool(scratch), 'live_data_preserved': True,
        'gpu_fallback_above_reservation': reserved == 128 * MiB}
    m.close(); return report


class Stacks(Heap):
    def __init__(self, data):
        super().__init__(data, capacity=32 * MiB)
        self.borrowed = set(); self.creates = 0; self.fail_close = False; self.fail_create = 0
        self.trace_oom = 0
        self.boundaries = {self.symbols[n]: n for n in ('svcQueryMemory', 'threadCreate', 'threadClose',
            'wine_nx_f1_resource_snapshot', 'wine_nx_f1_crash_stage', 'wine_nx_release_idle_backing_pages')}
        self.kernel_hook = self.vm.hook_add(UC_HOOK_CODE, self.kernel)

    def kernel(self, vm, pc, size, unused):
        name = self.boundaries.get(pc)
        if not name: return
        x = lambda n: vm.reg_read(reg(n))
        if name == 'svcQueryMemory':
            address = x(2); borrowed = address in self.borrowed
            amount = self.uq(self.symbols['f1_native_stack_bytes'])
            vm.mem_write(x(0), struct.pack('<QQ6I', address, amount, 5, int(borrowed),
                                           0 if borrowed else 3, 0, 0, 0))
            vm.mem_write(x(1), bytes(4)); self.ret()
        elif name == 'threadCreate':
            thread, entry, arg, stack, size_, priority, core = [x(i) for i in range(7)]
            assert entry == 0x123400 and arg == 0x234500 and priority == 59 and (core & 0xffffffff) == 0xfffffffe
            if not stack: self.ret(0x559); return
            assert stack not in self.borrowed and size_ == self.uq(self.symbols['f1_native_stack_bytes'])
            self.creates += 1
            if self.fail_create: self.ret(self.fail_create); return
            self.borrowed.add(stack)
            # Actual libnx Thread layout: handle/owns_stack_mem/pointers/size.
            vm.mem_write(thread, struct.pack('<II6Q', 1, 0, stack, stack + 4096, size_ - 4096, 0, 0, 0))
            self.ret()
        elif name == 'threadClose':
            address = self.uq(x(0) + 8)
            if self.fail_close: self.ret(0xd401); return
            if address in self.borrowed: self.borrowed.remove(address)
            self.ret()
        elif name == 'wine_nx_f1_resource_snapshot': self.trace_oom += 1; self.ret()
        else: self.ret()

    def retry(self, requested, previous=0x559, supplied=0):
        return self.call('wine_nx_f1_native_stack_retry', previous, self.data + 0x5000,
                         0x123400, 0x234500, supplied, requested, 59, -2)


def stacks(data, new):
    m = Stacks(data); m.call('wine_nx_f1_native_stacks_init')
    size = m.uq(m.symbols['f1_native_stack_bytes']); assert 1048576 < size < 1114112
    m.cap = m.brk  # Prevent reserve code from buying additional backing on failure.
    supported = 0
    for requested in (4096, 128 * 1024, 512 * 1024, 1024 * 1024):
        status = m.retry(requested)
        assert status == (0 if new or requested == MiB else 0x559)
        if status == 0:
            supported += 1
            assert m.call('__wrap_threadClose', m.data + 0x5000) == 0
    for previous, supplied, amount in ((0xd401, 0, MiB), (0x559, 0x8000, 128 * 1024),
        (0x559, 0, 0), (0x559, 0, 131073), (0x559, 0, 2 * MiB)):
        before = m.creates
        assert m.retry(amount, previous, supplied) == previous and m.creates == before
    if new:
        # A failed close quarantines the slot; no later request can reuse it.
        assert m.retry(128 * 1024) == 0
        first = m.uq(m.data + 0x5008); m.fail_close = True
        assert m.call('__wrap_threadClose', m.data + 0x5000) == 0xd401
        m.fail_close = False; assert m.retry(128 * 1024) == 0
        assert m.uq(m.data + 0x5008) != first
        assert m.call('__wrap_threadClose', m.data + 0x5000) == 0
        # The actual wrapper now rescues the 128 KiB failed SDK creation.
        assert m.call('__wrap_threadCreate', m.data + 0x5000, 0x123400, 0x234500, 0, 131072, 59, -2) == 0
        assert m.call('__wrap_threadClose', m.data + 0x5000) == 0
    report = {'supported_sizes_of_four': supported, 'backing_size': size,
              'oversize_invalid_caller_stack_and_non_oom_preserved': True, 'quarantine_checked': new}
    m.vm.hook_del(m.kernel_hook); m.close(); return report


def exhausted_diagnostics(data):
    m = Heap(data, capacity=4 * MiB)
    assert m.malloc(3 * MiB); m.seal()
    # Leave no reusable source pages for the existing scatter-page fallback.
    names = ('wine_nx_f1_resource_snapshot', 'wine_nx_f1_gpu_heap_snapshot',
             'wine_nx_f1_native_stacks_snapshot')
    hooks = {m.symbols[n]: n for n in (*names, 'wine_nx_release_idle_backing_pages', 'host_log')}
    seen = []
    def boundary(vm, pc, size, unused):
        name = hooks.get(pc)
        if name:
            if name in names: seen.append(name)
            assert m.depth == m.arena_depth == 0
            m.ret()
    hook = m.vm.hook_add(UC_HOOK_CODE, boundary)
    assert m.call('allocate_scratch', 16 * MiB) == 0
    assert seen == list(names), seen
    m.vm.hook_del(hook); m.close()
    return {'allocation_still_fails': True, 'failure_snapshots_in_order': seen}


def main():
    paths = [ROOT / 'local/symbols' / name for name in ('sleepingdogs-thread-debug.elf', 'sleepingdogs-memory-budget.elf')]
    old, new = [p.read_bytes() for p in paths]
    before = pressure(old, 256 * MiB)
    after = pressure(new, 128 * MiB, before['common_filler_bytes'])
    assert after['general_heap_available_before_request'] - before['general_heap_available_before_request'] == 128 * MiB
    print('PASS real ARM64 allocator: +128 MiB general headroom; FEX 16 MiB succeeds; GPU grows beyond reserve', flush=True)
    old_stack, new_stack = stacks(old, False), stacks(new, True)
    print('PASS real ARM64 stack retry/wrapper: 128 KiB uses idle slot; invalid cases and quarantine preserved', flush=True)
    diagnostics = exhausted_diagnostics(new)
    print('PASS true exhaustion returns NULL and collects all three failure snapshots outside allocator locks', flush=True)
    report = {'status': 'PASS', 'elf_sha256': sha(paths[1]), 'previous_elf_sha256': sha(paths[0]),
        'memory_pressure': {'old': before, 'new': after}, 'stack_recovery': {'old': old_stack, 'new': new_stack},
        'exhausted_diagnostics': diagnostics,
        'scope': __doc__, 'hardware_tested': False, 'game_boot_confirmed': False,
        'sources': {n: sha(ROOT / n) for n in ('tests/check_memory_budget_binary.py', 'tests/native_heap_binary.py')}}
    write_json(ROOT / 'reports/memory-budget-binary-check.json', report)

if __name__ == '__main__': main()
