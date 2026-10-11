"""Run real PE32 guest Map wrappers on Windows with a modeled native endpoint.

The endpoint mirrors native BindMap initialization but does not execute DXVK.
Compare allocation counts against pinned v7; timings are local diagnostics only.
"""
from pathlib import Path
import hashlib
import json
import os
import statistics
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-h4-v8'
BASELINE='e0995ccfc2819d20b5df8f60bff784996fb479c1'
MINGW='/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/i686-w64-mingw32-gcc'
GIT='C:/devkitPro/msys2/usr/bin/git.exe'
NAMES=('com_guest.c','com_guest_vtables.inc','com_protocol.h','com_interfaces.h','com_guids.inc','com_methods.h')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def linux(path):
    s=Path(path).resolve().as_posix();assert s[1:3]==':/'
    return '/mnt/'+s[0].lower()+'/'+s[3:]

def main():
    assert os.name=='nt','Use Windows Python to execute actual PE32 binaries.'
    work=LOCAL/'guest-map-check';work.mkdir(parents=True,exist_ok=True)
    sources={};commands={};executables={};cases={}
    for version in ('v7','current'):
        source=work/version;source.mkdir(exist_ok=True)
        for name in NAMES:
            data=subprocess.check_output([GIT,'show',BASELINE+':src/native_dxvk_com/'+name],cwd=ROOT) if version=='v7' else (ROOT/'src/native_dxvk_com'/name).read_bytes()
            (source/name).write_bytes(data)
        sources[version]={name:sha(source/name) for name in NAMES}
        exe=work/(version+'.exe')
        argv=['wsl','-d','Ubuntu','-u','root','--exec',MINGW,'-O2','-std=c11','-DINITGUID','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib',
              '-Wl,--no-insert-timestamp','-Wl,--entry,start@0','-I'+linux(source),linux(ROOT/'tests/native_dxvk_guest_maps.c'),'-o',linux(exe),'-lkernel32','-luser32']
        if version=='current':argv.insert(8,'-DTEST_SHADOW_CACHE')
        result=subprocess.run(argv,capture_output=True,text=True,timeout=120)
        (work/(version+'.compile.log')).write_text(result.stdout+result.stderr)
        assert result.returncode==0,result.stderr
        commands[version]=argv;executables[version]=dict(path=str(exe),sha256=sha(exe))
    for round_index in range(3):
        for version in ('v7','current'):
            result=subprocess.run([executables[version]['path']],capture_output=True,text=True,timeout=180)
            (work/(version+f'-{round_index}.stdout.log')).write_text(result.stdout)
            assert result.returncode==0,(version,result.returncode,result.stdout,result.stderr)
            parsed=json.loads(result.stdout);assert parsed['status']=='PASS' and parsed['teardown_live_allocations']==0
            parsed['ms_per_4_plus_5_mib_cycle']=parsed['ticks']*1000/parsed['frequency']/parsed['frames'];cases.setdefault(version,[]).append(parsed)
    assert all(row['virtual_alloc_calls']==2 and row['heap_alloc_calls']==2 for row in cases['current'])
    assert all(row['virtual_alloc_calls']==64 and row['heap_alloc_calls']==64 for row in cases['v7'])
    medians={version:statistics.median(row['ms_per_4_plus_5_mib_cycle'] for row in rows) for version,rows in cases.items()}
    files=[ROOT/'tests/native_dxvk_guest_maps.c',ROOT/'src/native_dxvk_com/com_native.cpp']+[ROOT/'src/native_dxvk_com'/name for name in NAMES]
    report=dict(status='PASS',baseline_commit=BASELINE,original_guest_sources=sources,runner_sha256=sha(__file__),
                source_files={path.relative_to(ROOT).as_posix():sha(path) for path in files},compile_argv=commands,executables=executables,cases=cases,
                median_ms_per_4_plus_5_mib_cycle=medians,relative_modeled_cycle_speedup=medians['v7']/medians['current'],
                pe32_proxy_executed_on_windows=True,modeled_native_endpoint=True,hardware_tested=False,com_guest_execution_tested=False,game_integration_tested=False,game_fps_measured=False,
                coverage=['READ/WRITE/READ_WRITE/WRITE_DISCARD/WRITE_NO_OVERWRITE copy direction','zeroed reused DISCARD shadows before exposure','exact-size reuse','overlapping and concurrent active maps never alias','16 MiB and four-entry idle caps','oversized uncached mapping','allocation failure evicts idle memory and retries once','native Map E_OUTOFMEMORY drains idle memory and retries once without changing active mappings','persistent allocation and BindMap failures abort native maps','other native Map failures and null output','empty active maps, proxies, native refs and allocations after cache drain'],
                scope='Real PE32 Map/Unmap wrappers execute on Windows against a modeled native endpoint, which validates ranges and mirrors each version\'s BindMap initialization: v7 fresh VirtualAlloc zeros, current native zero for DISCARD, full copy-in for other modes. The 32-frame diagnostic workload maps overlapping 4 MiB and 5 MiB buffers, writes 64 bytes in each, then models full Unmap copies. Timings exclude game rendering and do not measure Wine/FEX, ARM64 DXVK, Switch, or game FPS.')
    (LOCAL/'guest-maps.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(status='PASS',median_ms_per_4_plus_5_mib_cycle=medians,relative_modeled_cycle_speedup=report['relative_modeled_cycle_speedup'],allocation_calls={version:[row['virtual_alloc_calls'] for row in rows] for version,rows in cases.items()},checks={version:rows[0]['checks'] for version,rows in cases.items()},game_fps_measured=False),indent=2))

if __name__=='__main__':main()
