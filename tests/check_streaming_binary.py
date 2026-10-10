"""Real ARM64 heap/segregation and real x86 deferred Map regression checks.

Heap workload is synthetic: exhaust ordinary backing, release separated small
GPU blocks, then request 5 MiB. It is not a full hardware allocation replay.
Vulkan creation and diagnostic boundaries are modeled in the x86 Map checks.
"""
from pathlib import Path
import json, struct, sys
from check_gpu_budget_binary import BudgetHeap, MiB
from check_dxvk_map_binary import MapReplay
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
CAPACITY=2070044672


def pressure(data,new):
    m=BudgetHeap(data,CAPACITY,True);m.call('wine_nx_f1_gpu_heap_init')
    base=m.uq(m.symbols['f1_gpu_pool'])
    cpu=[m.align(65536,1000*MiB)]+[m.align(4096,n) for n in [16*MiB]*4+[65536]*4]
    assert all(cpu)
    for p in cpu:m.vm.mem_write(p,b'LIVECPU!')
    gpu=[m.align(65536,2*MiB,True) for _ in range(128)];assert all(gpu)
    for p in gpu:m.vm.mem_write(p,b'LIVEGPU!')
    m.seal()
    for i in range(0,128,4):m.call('wine_nx_f1_gpu_free',gpu[i]);gpu[i]=0
    before=m.info();p=m.align(65536,5*MiB,True)
    assert bool(p)==new
    if new:
        assert base+192*MiB<=p and p+5*MiB<=base+256*MiB
        for _ in range(64):
            m.vm.mem_write(p,b'BEGIN');m.vm.mem_write(p+5*MiB-3,b'END')
            m.call('wine_nx_f1_gpu_free',p);p=m.align(65536,5*MiB,True);assert p
        m.call('wine_nx_f1_gpu_free',p);assert m.info()==before
    else:assert m.stats()[4]<5*MiB
    for p in cpu:assert bytes(m.vm.mem_read(p,8))==b'LIVECPU!'
    for p in gpu:
        if p:assert bytes(m.vm.mem_read(p,8))==b'LIVEGPU!'
    report={'five_mib_succeeds':new,'recycled_large_allocations':64 if new else 0,
            'game_and_four_compiler_buffers_preserved':True,'general_heap_before':before}
    m.close();return report


def borrowing(data):
    m=BudgetHeap(data,CAPACITY,True);m.call('wine_nx_f1_gpu_heap_init');base=m.uq(m.symbols['f1_gpu_pool'])
    general=[m.align(65536,2*MiB,True) for _ in range(96)];assert all(general);m.seal()
    loans=[m.align(65536,2*MiB,True) for _ in range(24)]
    assert all(base+192*MiB<=p<base+256*MiB for p in loans)
    assert not m.align(65536,65536,True)
    large=[m.align(65536,5*MiB,True) for _ in range(3)];assert all(large)
    assert not m.align(65536,5*MiB,True)
    for p in large+loans+general:m.call('wine_nx_f1_gpu_free',p)
    pool=m.symbols['f1_gpu_pool'];assert bytes(m.vm.mem_read(pool+12,4))==bytes(4)
    m.close();return {'loaned_bytes':48*MiB,'retained_contiguous_bytes':16*MiB,'three_full_five_mib_requests':True}


def main():
    old_path=ROOT/'local/symbols/sleepingdogs-gpu-budget.elf';new_path=ROOT/'local/symbols/sleepingdogs-streaming-memory.elf'
    old,new=old_path.read_bytes(),new_path.read_bytes()
    before=pressure(old,False);after=pressure(new,True);loans=borrowing(new)
    print('PASS ARM64: fragmented 5 MiB failure reproduced; isolated large range/reuse, CPU data and bounded borrowing verified',flush=True)
    dll=ROOT/'dist/streaming-memory-fix/x32/d3d11.dll';oom=[]
    for need in (1,65536,5242880,9437184):
        m=MapReplay(dll);state=m.state();assert m.call(need)==0x8007000e
        assert bytes(m.vm.mem_read(m.output,12))==bytes(12) and m.state()==state and not m.faults
        m.call(need,update=True);assert m.state()==state and m.calls==m.logs==2
        oom.append(need)
    m=MapReplay(dll);m.fail=False;assert m.call()==0
    assert m.u(m.output)==m.storage and m.u(m.queue+0x4c)==m.allocation and m.u(m.queue+0x48)==m.dxbuf
    assert m.q(m.dxbuf+8)==2 and m.u(m.allocation)==1
    state=m.state();m.fail=True;assert m.call()==0x8007000e and m.state()==state
    print('PASS x86: deferred Map/Update OOM handling and live command/allocation ownership remain intact',flush=True)
    write_json(ROOT/'reports/streaming-binary-check.json',{'status':'PASS','native_elf_sha256':sha(new_path),
        'previous_native_elf_sha256':sha(old_path),'dll_sha256':sha(dll),'pressure':{'old':before,'new':after},
        'borrowing':loans,'map_oom_sizes':oom,'map_command_ownership':True,'scope':__doc__,'hardware_tested':False,
        'sources':{n:sha(ROOT/n) for n in ('tests/check_streaming_binary.py','tests/check_gpu_budget_binary.py',
            'tests/native_heap_binary.py','tests/check_dxvk_map_binary.py','tests/check_wow64_context_binary.py')}})


if __name__=='__main__':main()
