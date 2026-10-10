"""Execute old/new native ARM64 allocators with exhausted newlib and live resources.

The synthetic pool layout matches the log's capacity, used and largest-free
values, not its unknown complete lifetime trace. Kernel/sbrk/log I/O are modeled.
"""
from pathlib import Path
import json,struct,sys
from check_gpu_budget_binary import BudgetHeap,MiB
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json


def pressure(path,new):
    m=BudgetHeap(path.read_bytes(),2070040576,True);m.call('wine_nx_f1_gpu_heap_init')
    pool=m.symbols['f1_gpu_pool'];base=m.uq(pool);U=65536
    cpu=[m.align(U,1000*MiB)]+[m.align(4096,n) for n in [16*MiB]*4+[U]*4];assert all(cpu)
    for p in cpu:m.vm.mem_write(p,b'LIVECPU!')
    general=[m.align(U,2*MiB,True) for _ in range(96)];assert all(general)
    sizes=[9*MiB,16*MiB,5*MiB,16*MiB,50*U,238*U]
    large=[m.align(U,n,True) for n in sizes];assert all(large)
    for p in general+large:m.vm.mem_write(p,b'LIVEGPU!')
    m.seal()
    for i in (0,2,4):m.call('wine_nx_f1_gpu_free',large[i])
    assert struct.unpack('<I',m.vm.mem_read(pool+12,4))[0]*U==250478592
    before=m.info();success=[]
    for need in (U,131072,196608,262144,524288,1048576,2097152):
        p=m.align(U,need,True);assert bool(p)==new,(need,new)
        if p:
            assert base<=p and p+need<=base+256*MiB and p%U==0
            m.vm.mem_write(p,b'START');m.vm.mem_write(p+need-3,b'END')
            m.call('wine_nx_f1_gpu_free',p);success.append(need)
        assert m.info()==before
    if new:
        for _ in range(128):
            p=m.align(U,196608,True);assert p;m.call('wine_nx_f1_gpu_free',p)
        # Every idle byte may be borrowed; the following real exhaustion fails.
        loans=[m.align(U,U,True) for _ in range(274)];assert all(loans)
        assert not m.align(U,U,True)
        for p in loans:m.call('wine_nx_f1_gpu_free',p)
        assert m.info()==before
        assert m.uq(m.symbols['sd_gpu_emergency_takes'])>=409
    for p in cpu:assert bytes(m.vm.mem_read(p,8))==b'LIVECPU!'
    for p in general+[large[i] for i in (1,3,5)]:assert bytes(m.vm.mem_read(p,8))==b'LIVEGPU!'
    for p in general+[large[i] for i in (1,3,5)]:m.call('wine_nx_f1_gpu_free',p)
    assert struct.unpack('<I',m.vm.mem_read(pool+12,4))[0]==0
    m.close();return {'recovered_sizes':success,'live_game_compiler_gpu_data_preserved':True,'newlib_accounting_unchanged':True}


def main():
    old=ROOT/'local/symbols/sleepingdogs-streaming-memory.elf'
    new=ROOT/'local/symbols/sleepingdogs-gpu-pressure.elf'
    before=pressure(old,False);after=pressure(new,True)
    report={'status':'PASS','old':before,'new':after,'native_elf_sha256':sha(new),
        'previous_native_elf_sha256':sha(old),'scope':__doc__,'hardware_tested':False,
        'sources':{n:sha(ROOT/n) for n in ('tests/check_gpu_pressure_binary.py','tests/check_gpu_budget_binary.py','tests/native_heap_binary.py')}}
    write_json(ROOT/'reports/gpu-pressure-binary-check.json',report)
    print('PASS: actual ARM64 old guard fails; new 64 KiB-2 MiB requests/recycling succeed, true exhaustion fails, live data and newlib accounting intact',flush=True)


if __name__=='__main__':main()
