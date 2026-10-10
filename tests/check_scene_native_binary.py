"""Run real old/new ARM64 heaps at identical quota and identical live workload.

Synthetic pressure tests headroom, not the unknown full hardware lifetime trace.
Only sbrk, locks, loader metadata and diagnostics are modeled.
"""
from pathlib import Path
import json,sys
from unicorn import UC_HOOK_CODE
from check_gpu_budget_binary import BudgetHeap,MiB
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json

def run(path,pairs,filler=None):
    m=BudgetHeap(path.read_bytes(),2070040576,True)
    def trace(vm,pc,size,unused):
        if pc==m.symbols['host_log']:m.ret()
    hook=m.vm.hook_add(UC_HOOK_CODE,trace)
    m.call('wine_nx_f1_gpu_heap_init');assert m.call('pes13_fex_native_host')
    slots=m.symbols['f1_scratch_slots'];sizes=[m.uq(slots+i*24+8) for i in range(2*pairs)]
    assert sizes==[65536]*pairs+[16*MiB]*pairs
    reserve_used=m.info()[7]
    game=m.align(65536,1000*MiB);assert game;m.vm.mem_write(game,b'LIVEGAME')
    gpu=[m.align(65536,2*MiB,True) for _ in range(96)]+[m.align(65536,64*MiB,True)]
    assert all(gpu)
    for p in gpu:m.vm.mem_write(p,b'LIVEGPU!')
    if filler is None:filler=(m.cap-m.brk-512*1024)&-4096
    held=m.malloc(filler);assert held;m.vm.mem_write(held,b'LIVENAT!')
    # The old four-pair reserve leaves no full 1 MiB block; reducing only the
    # number of workspaces makes 32 MiB available to the same resource load.
    allocations=[]
    for _ in range(16):
        p=m.align(256,MiB,True)
        if pairs==4:assert not p;break
        assert p;allocations.append(p);m.vm.mem_write(p,b'EXTRAGPU')
    # Exhaust remaining ordinary heap. Both protected pairs still work.
    m.seal();live=[m.call('allocate_scratch',n) for n in sizes]
    assert len(set(live))==2*pairs and all(live)
    for i,(p,n) in enumerate(zip(live,sizes)):
        m.vm.mem_write(p,bytes([i+1])*16);m.vm.mem_write(p+n-16,bytes([i+10])*16)
    for turn in range(64):
        i=turn%len(live);p=live[i];m.call('release_scratch',p)
        assert m.call('allocate_scratch',sizes[i])==p
        for j,(q,n) in enumerate(zip(live,sizes)):
            assert bytes(m.vm.mem_read(q,16))==bytes([j+1])*16
            assert bytes(m.vm.mem_read(q+n-16,16))==bytes([j+10])*16
    for p in live:m.call('release_scratch',p)
    assert m.call('wine_nx_f1_release_idle_scratch')==0
    assert all(m.uq(slots+i*24)==p for i,p in enumerate(live))
    for p in gpu:assert bytes(m.vm.mem_read(p,8))==b'LIVEGPU!'
    for p in allocations:assert bytes(m.vm.mem_read(p,8))==b'EXTRAGPU'
    assert bytes(m.vm.mem_read(game,8))==b'LIVEGAME'
    assert bytes(m.vm.mem_read(held,8))==b'LIVENAT!'
    m.vm.hook_del(hook);m.close()
    return {'elf_sha256':sha(path),'pairs':pairs,'reserve_payload_bytes':sum(sizes),
        'heap_used_after_init':reserve_used,'same_live_filler_bytes':filler,
        'additional_one_mib_gpu_allocations':len(allocations),'protected_reserve_recycles':64,
        'live_game_gpu_compiler_data_preserved':True}

def main():
    old=run(ROOT/'local/symbols/sleepingdogs-gpu-pressure.elf',4)
    new=run(ROOT/'local/symbols/sleepingdogs-scene-memory.elf',2,old['same_live_filler_bytes'])
    saved=old['heap_used_after_init']-new['heap_used_after_init'];assert saved>=33685504
    report={'status':'PASS','before':old,'after':new,'native_heap_bytes_saved':saved,
        'native_elf_sha256':new['elf_sha256'],'previous_native_elf_sha256':old['elf_sha256'],
        'scope':__doc__,'hardware_tested':False,'sources':{n:sha(ROOT/n) for n in (
        'tests/check_scene_native_binary.py','tests/check_gpu_budget_binary.py','tests/native_heap_binary.py')}}
    write_json(ROOT/'reports/scene-native-binary-check.json',report);print(json.dumps(report))

if __name__=='__main__':main()
