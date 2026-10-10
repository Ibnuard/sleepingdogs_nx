"""Execute shipped ARM64 allocators and loader sizing; synthetic heap pressure.

No hardware allocation timeline is available. This reproduces the essential
failure condition (free space split into sub-MiB holes, a 5 MiB GPU request),
holding the same live CPU/GPU allocations in both versions. Kernel information,
sbrk and diagnostic boundaries are modeled; allocator results are not mocked.
"""
from pathlib import Path
import argparse
import io
import json
import os
import struct
import sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm64_const as arm
from native_heap_binary import Heap, reg
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json

MiB = 1048576
CAPACITY = 2002944000
INFO = b'sphaira 3.0.0; sleepingdogs-gpu-budget-v1 reserve=32MiB\0'


class BudgetHeap(Heap):
    def __init__(self, data, capacity, paired):
        super().__init__(data, capacity=capacity)
        self.vm.mem_map(self.start + 32 * MiB, ((capacity + 4095) & -4096) - 32 * MiB)
        self.q(self.symbols['fake_heap_start'], self.start)
        self.q(self.symbols['fake_heap_end'], self.cap)
        self.info_text = INFO if paired else b'sphaira 3.0.0\0'
        self.vm.mem_write(self.data + 0x4000, self.info_text)
        self.env_hooks = {self.symbols[n]: n for n in ('envGetLoaderInfo', 'envGetLoaderInfoSize') if n in self.symbols}
        self.env_hook = self.vm.hook_add(UC_HOOK_CODE, self.environment)

    def environment(self, vm, pc, size, user):
        name = self.env_hooks.get(pc)
        if name == 'envGetLoaderInfo': self.ret(self.data + 0x4000)
        elif name == 'envGetLoaderInfoSize': self.ret(len(self.info_text))

    def close(self):
        self.vm.hook_del(self.env_hook); super().close()


def pressure(data, paired, capacity, filler=None):
    m = BudgetHeap(data, capacity, paired)
    m.call('wine_nx_f1_gpu_heap_init'); pool = m.symbols['f1_gpu_pool']
    base = m.uq(pool); reserved = struct.unpack('<I', m.vm.mem_read(pool + 8, 4))[0] * 65536
    assert reserved == (256 if paired else 128) * MiB
    # Persistent GPU resources plus the observed ~207 MiB total live backing.
    gpu = [m.align(65536, 128 * MiB, True)]
    gpu += [m.align(65536, MiB, True) for _ in range(79)]
    assert all(gpu)
    game = m.align(65536, 1000 * MiB); assert game
    cpu = [game]
    # Four full 16 MiB IR buffers and four 64 KiB decoders remain live throughout.
    cpu += [m.align(4096, n) for n in [16 * MiB] * 4 + [65536] * 4]
    assert all(cpu)
    for i, p in enumerate(gpu + cpu): m.vm.mem_write(p, struct.pack('<Q', i + 1))
    holes = []
    for i in range(64):
        holes.append(m.malloc(768 * 1024))
        guard = m.malloc(65536); assert holes[-1] and guard
        cpu.append(guard); m.vm.mem_write(guard, b'GUARD!')
    if filler is None:
        filler = (m.cap - m.brk - 131072) & -4096
    held = m.malloc(filler); assert held
    for ptr in holes: m.free(ptr)
    available = m.info()[8] + m.cap - m.brk
    before = m.info()
    request = m.align(65536, 5 * MiB, True)
    assert bool(request) == paired, (reserved, available, m.stats())
    if paired:
        assert base <= request < base + reserved
        m.vm.mem_write(request, b'START!'); m.vm.mem_write(request + 5 * MiB - 6, b'FINISH')
        # The same block is repeatedly returned to the GPU pool, not newlib.
        for i in range(64):
            m.call('wine_nx_f1_gpu_free', request)
            request = m.align(65536, 5 * MiB, True)
            assert request and base <= request < base + reserved
        m.call('wine_nx_f1_gpu_free', request)
        assert before == m.info(), 'GPU churn changed general heap accounting'
        native_extra = m.align(4096, 8 * MiB); assert native_extra
        m.free(native_extra)
    else:
        assert available >= 48 * MiB and m.stats()[4] < MiB
    for i, p in enumerate(gpu + cpu[:9]):
        assert bytes(m.vm.mem_read(p, 8)) == struct.pack('<Q', i + 1)
    for p in cpu[9:]: assert bytes(m.vm.mem_read(p, 6)) == b'GUARD!'
    for p in gpu: m.call('wine_nx_f1_gpu_free', p)
    for p in cpu + [held]: m.free(p)
    # Pool return/coalescing after all simulated GPU resource lifetimes end.
    p = m.align(65536, reserved, True); assert p == base
    m.call('wine_nx_f1_gpu_free', p)
    result = {'reserved': reserved, 'filler': filler, 'general_available': available,
        'five_mib_succeeds': paired, 'compiler_and_guest_data_preserved': True,
        'gpu_reuse_cycles': 64 if paired else 0}
    m.close(); return result


def gate_cases(data):
    cases = []
    for capacity, tag, expected in ((CAPACITY, False, 128), (CAPACITY, True, 128),
        (CAPACITY + 64 * MiB, False, 128), (CAPACITY + 64 * MiB, True, 256)):
        m = BudgetHeap(data, capacity, tag); m.call('wine_nx_f1_gpu_heap_init')
        pool = m.symbols['f1_gpu_pool']; units = struct.unpack('<I', m.vm.mem_read(pool + 8, 4))[0]
        assert units * 65536 == expected * MiB
        # Reentry never reserves a second arena.
        before = m.info(); m.call('wine_nx_f1_gpu_heap_init'); assert before == m.info()
        cases.append({'capacity': capacity, 'paired_tag': tag, 'reserved_mib': expected}); m.close()
    return cases


def loader_size(path, total, used):
    data = path.read_bytes(); elf = ELFFile(io.BytesIO(data)); bias = 0x1000000
    symbols = {s.name: bias + s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
    vm = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    segments = [s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
    low = min(s['p_vaddr'] for s in segments) & -4096
    high = max((s['p_vaddr'] + s['p_memsz'] + 4095) & -4096 for s in segments)
    vm.mem_map(bias + low, high - low)
    for s in segments: vm.mem_write(bias + s['p_vaddr'], s.data())
    # Load-time relative relocations in the ELF, exactly as the NRO harness does.
    relr = elf.get_section_by_name('.relr.dyn')
    if relr:
        for r in relr.iter_relocations():
            p = bias + r['r_offset']; value = struct.unpack('<Q', vm.mem_read(p, 8))[0]
            vm.mem_write(p, struct.pack('<Q', value + bias))
    stack = 0x50000000; tls = 0x51000000
    vm.mem_map(stack, 65536); vm.mem_map(tls, 65536)
    vm.reg_write(arm.UC_ARM64_REG_SP, stack + 0xf000)
    vm.reg_write(arm.UC_ARM64_REG_TPIDRRO_EL0, tls)
    seen = []
    def hook(vm, pc, size, unused):
        x = lambda i: vm.reg_read(reg(i))
        def ret(v=0):
            vm.reg_write(reg(0), v); vm.reg_write(arm.UC_ARM64_REG_PC, x(30))
        if pc == symbols['svcGetInfo']:
            assert x(1) in (6, 7)
            vm.mem_write(x(0), struct.pack('<Q', total if x(1) == 6 else used)); ret()
        elif pc == symbols['svcSetHeapSize']:
            seen.append(x(1)); vm.emu_stop()
        elif pc == symbols.get('memcpy'):
            vm.mem_write(x(0), bytes(vm.mem_read(x(1), x(2)))); ret(x(0))
    vm.hook_add(UC_HOOK_CODE, hook)
    vm.emu_start(symbols['main'], 0, count=100000)
    assert len(seen) == 1
    return seen[0]


def main():
    p = argparse.ArgumentParser()
    home = Path('//wsl$/Ubuntu/home/blekjek') if os.name == 'nt' else Path('/home/blekjek')
    p.add_argument('--forwarder-work', type=Path, default=home / 'sleepingdogs-gpu-forwarder-v1')
    a = p.parse_args()
    old_path = ROOT / 'local/symbols/sleepingdogs-compiler-memory.elf'
    new_path = ROOT / 'local/symbols/sleepingdogs-gpu-budget.elf'
    old, new = old_path.read_bytes(), new_path.read_bytes()
    def image_size(path):
        blob = path.read_bytes()
        data_off, data_size, bss = struct.unpack_from('<3I', blob, 0x30)
        return data_off + ((data_size + bss + 4095) & -4096)
    overhead = image_size(ROOT / 'dist/gpu-budget-fix/sleepingdogs-fex.nro') - image_size(ROOT / 'dist/compiler-memory-fix/sleepingdogs-fex.nro')
    before = pressure(old, False, CAPACITY)
    after = pressure(new, True, CAPACITY + 64 * MiB - overhead, before['filler'])
    print('PASS ARM64: old fragmented heap rejects 5 MiB; paired heap/pool succeeds and preserves all live buffers', flush=True)
    gates = gate_cases(new)
    print('PASS ARM64: old/unknown loader and undersized heap keep 128 MiB; matching pair gets 256 MiB; init is idempotent', flush=True)
    old_fw = home / 'sleepingdogs-forwarder-build/forwarder.elf'
    new_fw = a.forwarder_work / 'forwarder.elf'; sizing = []
    for total, used in ((2048 * MiB, 12 * MiB), (2048 * MiB, 32473088),
        (2048 * MiB, 27 * MiB + 4096), (512 * MiB, 8 * MiB), (1536 * MiB, 32 * MiB)):
        before_size = loader_size(old_fw, total, used); after_size = loader_size(new_fw, total, used)
        assert after_size - before_size == (64 * MiB if total >= 2048 * MiB else 0)
        assert total - used - after_size >= (34 if total >= 2048 * MiB else 98) * MiB
        sizing.append({'total': total, 'used': used, 'old': before_size, 'new': after_size})
    print('PASS ARM64: both real forwarders execute to svcSetHeapSize; new adds 64 MiB only at full quota', flush=True)
    write_json(ROOT / 'reports/gpu-budget-binary-check.json', {'status': 'PASS',
        'native_elf_sha256': sha(new_path), 'forwarder_elf_sha256': sha(new_fw),
        'previous_native_elf_sha256': sha(old_path), 'previous_forwarder_elf_sha256': sha(old_fw),
        'additional_native_image_bytes': overhead,
        'memory_pressure': {'old': before, 'new': after}, 'gates': gates, 'loader_sizing': sizing,
        'scope': __doc__, 'hardware_tested': False,
        'sources': {n: sha(ROOT / n) for n in ('tests/check_gpu_budget_binary.py', 'tests/native_heap_binary.py')}})


if __name__ == '__main__': main()
