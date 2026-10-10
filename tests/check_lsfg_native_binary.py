"""Run inherited ARM64 checks, LSFG link routes and shipped cache identity."""
from pathlib import Path
import argparse,importlib,json,sys,gc,struct,io
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from port_common import sha,write_json

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf',type=Path,default=ROOT/'local/symbols/sleepingdogs-lsfg-v15.elf')
    parser.add_argument('--native-dir',type=Path,default=ROOT/'local/lsfg-native-v15')
    parser.add_argument('--report-prefix',default='lsfg-v15')
    parser.add_argument('--report',type=Path,default=ROOT/'reports/lsfg-native-check.json')
    args=parser.parse_args()
    elf=args.elf; prefix=args.report_prefix
    native=json.loads((args.native_dir/'native.json').read_text())
    assert sha(elf)==native['elf_sha256']
    checks={}
    import check_v11_binary as diag
    old=diag.write_json
    diag.write_json=lambda path,value:old(ROOT/f'reports/{prefix}-diagnostic-binary.json',value)
    try:diag.diagnostics(elf)
    finally:diag.write_json=old
    gc.collect()
    for module,label in (('check_direct_sync_binary','direct-sync'),('check_low_window_binary','low-window'),('check_shader_binary','shader')):
        m=importlib.import_module(module);writer=m.write_json
        m.write_json=lambda path,value,_w=writer,_l=label:_w(ROOT/f'reports/{prefix}-{_l}-binary.json',value)
        sys.argv=[module,'--elf',str(elf)]
        try:m.main()
        finally:m.write_json=writer
        checks[label]=sha(ROOT/f'reports/{prefix}-{label}-binary.json');gc.collect()
    from check_v141_cache_binary import CacheIdentity
    layout=json.loads((ROOT/'dist/sleepingdogs-fex-v14.1-update/source/low-window-gm20b-cache-fix/layout.json').read_text())
    machine=CacheIdentity(elf,layout)
    try:cache=machine.run()
    finally:machine.close()
    assert cache['identities_match'] and cache['pipeline_build_id']==native['driver_cache_id']
    e=ELFFile(io.BytesIO(elf.read_bytes()))
    symbols={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols() if s['st_size']}
    def branches(name):
        sym=symbols[name];section=e.get_section(sym['st_shndx']);off=sym['st_value']-section['sh_addr']
        data=section.data()[off:off+sym['st_size']];dest=[]
        for i in range(0,len(data)-3,4):
            w=struct.unpack_from('<I',data,i)[0]
            if w&0x7c000000==0x14000000:
                rel=w&0x3ffffff
                if rel&0x2000000:rel-=0x4000000
                dest.append(sym['st_value']+i+4*rel)
        return dest
    # Compiler may inline the f1_impl wrapper into the exported Wine thunk.
    expected={
        'wine_nx_lsfg_prepare_swapchain':'CreateSwapchainKHR',
        'wine_nx_lsfg_create':'CreateSwapchainKHR',
        'wine_nx_lsfg_destroy':'DestroySwapchainKHR',
        'wine_nx_lsfg_device_features':'CreateDevice',
        'wine_nx_lsfg_present':'QueuePresentKHR'}
    routes={}
    for target,hint in expected.items():
        callers=[name for name in symbols if hint in name and symbols[name]['st_info']['type']=='STT_FUNC' and symbols[target]['st_value'] in branches(name)]
        assert callers,(target,hint);routes[target]=callers
    assert any('Presentation' in name and 'present' in name for name in symbols)
    data=(args.native_dir/'sleepingdogs-fex.nro').read_bytes()
    for i in range(3):
        off,size=struct.unpack_from('<II',data,0x20+8*i)
        segment=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']==off)
        raw=segment.data();skip=0x80 if i==0 else 0
        assert data[off+skip:off+len(raw)]==raw[skip:]
    write_json(args.report,dict(status='PASS',elf_sha256=sha(elf),
        nro_sha256=sha(args.native_dir/'sleepingdogs-fex.nro'),
        inherited_checks=checks,lsfg_link_routes=routes,cache_identity=cache,
        nro_matches_elf=True,hardware_tested=False))
    print('PASS: LSFG native routes, NRO payload, v14.1 cache identity and inherited ARM64 regressions')

if __name__=='__main__':main()
