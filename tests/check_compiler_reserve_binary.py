"""Run both NROs' real newlib allocator and compiler reserve entry points."""
from pathlib import Path
import json
import struct
import sys
from unicorn import UC_HOOK_CODE
from native_heap_binary import Heap
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json
MIB = 1024*1024

def check(path, decoder_size):
    data = path.read_bytes(); m = Heap(data, capacity=160*MIB)
    m.vm.mem_map(m.start+32*MIB, 128*MIB)
    def trace(vm, pc, size, unused):
        if pc == m.symbols['host_log']: m.ret()
    hook = m.vm.hook_add(UC_HOOK_CODE, trace)
    assert m.call('pes13_fex_native_host')
    slots = m.symbols['f1_scratch_slots']
    sizes = [m.uq(slots+i*24+8) for i in range(8)]
    assert sizes == [decoder_size]*4 + [16*MIB]*4, sizes
    assert all(m.uq(slots+i*24) for i in range(8))
    used = m.info()[7]
    # Exhaust the ordinary heap after initialization. Four complete compiler
    # workspaces must still be usable, and remain protected across recycling.
    m.seal()
    live = [m.call('allocate_scratch', n) for n in sizes]
    assert len(set(live)) == 8 and all(live)
    assert not m.align(4096, 16*MIB)
    for i, (p,n) in enumerate(zip(live,sizes)):
        m.vm.mem_write(p, bytes([i+1])*16); m.vm.mem_write(p+n-16, bytes([i+10])*16)
    for turn in range(64):
        i = turn % 8; p = live[i]; n = sizes[i]
        m.call('release_scratch', p)
        again = m.call('allocate_scratch', n); assert again == p
        for j,(q,qn) in enumerate(zip(live,sizes)):
            assert bytes(m.vm.mem_read(q,16)) == bytes([j+1])*16
            assert bytes(m.vm.mem_read(q+qn-16,16)) == bytes([j+10])*16
    for p in live: m.call('release_scratch', p)
    assert m.uq(slots) == live[0]
    m.vm.hook_del(hook); m.close()
    return {'elf_sha256': sha(path), 'sizes': sizes, 'reserve_bytes':sum(sizes),
            'heap_used_after_init': used, 'cycles_under_heap_exhaustion':64, 'live_data_preserved':True}

old = check(ROOT / 'local/symbols/sleepingdogs-memory-budget.elf', 8*MIB)
new = check(ROOT / 'local/symbols/sleepingdogs-compiler-memory.elf', 65536)
assert old['heap_used_after_init'] - new['heap_used_after_init'] == 33292288
report = {'status':'PASS', 'before':old, 'after':new, 'native_heap_bytes_saved':33292288,
          'boundaries':'sbrk, locks and diagnostic I/O modeled; actual NRO allocator/reserve code executes',
          'hardware_tested':False}
write_json(ROOT / 'reports/compiler-reserve-binary-check.json', report)
print(json.dumps(report))
