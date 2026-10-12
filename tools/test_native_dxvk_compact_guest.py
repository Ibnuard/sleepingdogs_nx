"""Actual PE32 execution; model only native endpoint. PC timings are not FPS."""
from pathlib import Path
import hashlib,json,os,statistics,subprocess
from native_dxvk_compact import ROOT,methods
LOCAL=ROOT/'local/native-dxvk-compact-v1'
MINGW='/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/i686-w64-mingw32-gcc'
def linux(p):
    value=Path(p).resolve().as_posix()
    return '/mnt/'+value[0].lower()+value[2:] if os.name=='nt' else value
def build():
    work=LOCAL/'tests';work.mkdir(exist_ok=True)
    original=(ROOT/'tests/native_dxvk_guest_transport.c').read_text()
    text=original.replace('#include "com_methods.h"','#include "com_methods.h"\n#include "com_compact.h"')
    text=text.replace('    require(p->abi==SD_COM_ABI&&!p->reserved,"packet header altered");',
        '    struct sd_com_packet decoded;require(sd_com_wire_decode(&decoded,p),"invalid compact packet");\n    require(decoded.abi==SD_COM_ABI,"packet ABI altered");')
    # Every generated compact method is invoked against the same checked decoder.
    calls=[]
    for m in methods():
        args=[]
        for p in m['params']:
            ty=p['type']+('*' if p['array'] else '')
            args.append('('+ty+')0')
        calls.append('    ID3D11DeviceContext_'+m['name']+'(context'+(' ,'+','.join(args) if args else '')+');')
    intro='''    struct proxy object={.vtbl=proxy_vtable(SD_COM_IF_ID3D11DeviceContext),.magic=PROXY_MAGIC,.token=0x10001,.interface_id=SD_COM_IF_ID3D11DeviceContext,.refs=1};
    ID3D11DeviceContext *context=(ID3D11DeviceContext*)&object;
'''
    text=text.replace('    for(UINT i=0;i<8;++i)race();errors();',intro+'\n'.join(calls)+'\n    for(UINT i=0;i<8;++i)race();errors();')
    (work/'transport.c').write_text(text)
    (work/'baseline-bench.c').write_text(original)
    commands={}
    for name,source,defs in (
        ('transport',LOCAL/'source/native_dxvk_com',['TEST_COUNT_LOCKS','TEST_FAST_ENDPOINT']),
        ('compact-bench',LOCAL/'source/native_dxvk_com',[]),
        ('baseline-bench',ROOT/'local/native-dxvk-ref-v1/candidate/source/native_dxvk_com',[])):
        argv=[MINGW,'-O2','-std=c11','-DINITGUID',*['-D'+d for d in defs],'-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib',
            '-Wl,--no-insert-timestamp','-Wl,--entry,start@0','-I'+str(source),str(work/('baseline-bench.c' if name=='baseline-bench' else 'transport.c')),'-o',str(work/(name+'.exe')),'-lkernel32','-luser32']
        result=subprocess.run(argv,capture_output=True,text=True,timeout=120);(work/(name+'.compile.log')).write_text(result.stdout+result.stderr)
        assert not result.returncode,result.stderr
        commands[name]=argv
    (work/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
def execute():
    assert os.name=='nt'
    work=LOCAL/'tests';results={}
    for name in ('transport','baseline-bench','compact-bench'):
        trials=[]
        for i in range(1 if name=='transport' else 7):
            r=subprocess.run([str(work/(name+'.exe'))],capture_output=True,text=True,timeout=180)
            assert not r.returncode,(name,r.returncode,r.stdout,r.stderr)
            data=json.loads(r.stdout);assert data['status']=='PASS';trials.append(data)
        results[name]=trials
    report=dict(status='PASS',real_pe32_executed=True,modeled_native_endpoint=True,hardware_tested=False,game_fps_measured=False,
        methods=46,results=results,baseline_proxy_sha256='a03a58b6023a7b74ff0d96d0460ce247715fa1210b6f6d02428f206908541344',
        candidate_sha256=json.loads((LOCAL/'build.json').read_text())['proxy_sha256'],
        scope='PC microbenchmark of generated guest DrawIndexed wrapper; excludes Wine/FEX/DXVK/GPU; not a Switch FPS or speedup estimate.')
    report['pc_median_ns_per_call']={n:statistics.median(t['ticks']/t['frequency']*1e9/t['calls'] for t in results[n]) for n in ('baseline-bench','compact-bench')}
    (LOCAL/'guest-test.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['pc_median_ns_per_call']))
if __name__=='__main__':
    if os.name=='posix':build()
    else:execute()
