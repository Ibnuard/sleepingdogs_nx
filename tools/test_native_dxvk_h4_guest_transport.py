"""Windows PE32 discovery/race regression and v8 transport cost comparison.

The actual guest source executes; only endpoint discovery/native work is modeled.
Lock counting and timings use separate executables. No game/FEX FPS inference.
"""
from pathlib import Path
import hashlib
import json
import os
import statistics
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-h4-v9'
BASELINE='951ffdc4192b01a88a8fc51224ea02804f5776ab'
MINGW='/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/i686-w64-mingw32-gcc'
GIT='C:/devkitPro/msys2/usr/bin/git.exe'
NAMES=('com_guest.c','com_guest_vtables.inc','com_protocol.h','com_interfaces.h','com_guids.inc','com_methods.h')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def linux(path):
    s=Path(path).resolve().as_posix();assert s[1:3]==':/'
    return '/mnt/'+s[0].lower()+'/'+s[3:]

def main():
    assert os.name=='nt','Execute these real PE32 binaries using Windows Python.'
    work=LOCAL/'guest-transport-check';work.mkdir(parents=True,exist_ok=True)
    original={};commands={};executables={};cases={}
    for version in ('v8','current'):
        source=work/version;source.mkdir(exist_ok=True)
        for name in NAMES:
            data=subprocess.check_output([GIT,'show',BASELINE+':src/native_dxvk_com/'+name],cwd=ROOT) if version=='v8' else (ROOT/'src/native_dxvk_com'/name).read_bytes()
            (source/name).write_bytes(data)
        original[version]={name:sha(source/name) for name in NAMES}
        for measured in (False,True):
            name=version+('-timing' if measured else '-correctness');exe=work/(name+'.exe')
            argv=['wsl','-d','Ubuntu','-u','root','--exec',MINGW,'-O2','-std=c11','-DINITGUID','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib',
                  '-Wl,--no-insert-timestamp','-Wl,--entry,start@0','-I'+linux(source),linux(ROOT/'tests/native_dxvk_guest_transport.c'),'-o',linux(exe),'-lkernel32','-luser32']
            if not measured:argv.insert(8,'-DTEST_COUNT_LOCKS')
            if version=='current':argv.insert(8,'-DTEST_FAST_ENDPOINT')
            result=subprocess.run(argv,capture_output=True,text=True,timeout=120)
            (work/(name+'.compile.log')).write_text(result.stdout+result.stderr)
            assert result.returncode==0,result.stderr
            commands[name]=argv;executables[name]=dict(path=str(exe),sha256=sha(exe))
    for version in ('v8','current'):
        name=version+'-correctness';result=subprocess.run([executables[name]['path']],capture_output=True,text=True,timeout=120)
        (work/(name+'.stdout.log')).write_text(result.stdout)
        assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
        cases[name]=json.loads(result.stdout);assert cases[name]['status']=='PASS'
    for round_index in range(5):
        for version in (('v8','current') if round_index%2==0 else ('current','v8')):
            name=version+'-timing';result=subprocess.run([executables[name]['path']],capture_output=True,text=True,timeout=60)
            (work/(name+f'-{round_index}.stdout.log')).write_text(result.stdout)
            assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
            parsed=json.loads(result.stdout);assert parsed['status']=='PASS'
            parsed['ns_per_draw_wrapper']=parsed['ticks']*1e9/parsed['frequency']/parsed['calls']
            cases.setdefault(name,[]).append(parsed)
    medians={v:statistics.median(r['ns_per_draw_wrapper'] for r in cases[v+'-timing']) for v in ('v8','current')}
    sources=[ROOT/'tests/native_dxvk_guest_transport.c']+[ROOT/'src/native_dxvk_com'/n for n in NAMES]
    report=dict(status='PASS',baseline_commit=BASELINE,original_guest_sources=original,runner_sha256=sha(__file__),
                source_files={p.relative_to(ROOT).as_posix():sha(p) for p in sources},compile_argv=commands,executables=executables,cases=cases,
                median_ns_per_draw_wrapper=medians,relative_draw_wrapper_speedup=medians['v8']/medians['current'],
                hot_lock_pairs_per_10000_calls={v:cases[v+'-correctness']['hot_lock_pairs'] for v in ('v8','current')},
                pe32_proxy_executed_on_windows=True,modeled_discovery_and_native_endpoint=True,
                hardware_tested=False,com_guest_execution_tested=False,game_integration_tested=False,game_fps_measured=False,
                coverage=['eight 12-thread first-call races with a split 64-bit handle','missing query and endpoint symbols','failed query after writing a handle','zero-handle success rejection','successful retry after each discovery failure','native packet fault and transport error precedence','warm dispatch while another thread holds the proxy lock','unchanged complete generated DrawIndexed wrapper with 160-byte packet'],
                scope='Windows PE32 actual guest code, modeled Wine endpoint discovery and native work. Timing has no lock-count instrumentation. Demonstrates removed synchronization on this path, not total frame cost or Switch performance.')
    (LOCAL/'guest-transport.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(status='PASS',hot_lock_pairs_per_10000_calls=report['hot_lock_pairs_per_10000_calls'],median_ns_per_draw_wrapper=medians,game_fps_measured=False),indent=2))

if __name__=='__main__':main()
