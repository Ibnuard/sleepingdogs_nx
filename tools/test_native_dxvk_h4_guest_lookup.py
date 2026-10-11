"""Windows PE32 identity/lifetime tests and controlled v6 lookup comparison.

Only the Unix/native endpoint is modeled. Instrumented builds count visited list
nodes; separate uninstrumented builds measure complete repeated output wrappers.
This does not measure FEX, ARM64 DXVK, Switch, or game FPS.
"""
from pathlib import Path
import hashlib
import json
import os
import statistics
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-h4-v8'
BASELINE='b98557b28f0011c5eb75d934b20fe60b29cc1a18'
MINGW='/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/i686-w64-mingw32-gcc'
GIT='C:/devkitPro/msys2/usr/bin/git.exe'
NAMES=('com_guest.c','com_guest_vtables.inc','com_protocol.h','com_interfaces.h','com_guids.inc','com_methods.h')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def linux(path):
    s=Path(path).resolve().as_posix();assert s[1:3]==':/'
    return '/mnt/'+s[0].lower()+'/'+s[3:]

def main():
    assert os.name=='nt','Use Windows Python: these executables run as native PE32 processes.'
    work=LOCAL/'guest-lookup-check';work.mkdir(parents=True,exist_ok=True)
    originals={};commands={};executables={};cases={}
    for version in ('v6','current'):
        original={name:(subprocess.check_output([GIT,'show',BASELINE+':src/native_dxvk_com/'+name],cwd=ROOT) if version=='v6' else (ROOT/'src/native_dxvk_com'/name).read_bytes()) for name in NAMES}
        originals[version]={name:hashlib.sha256(data).hexdigest() for name,data in original.items()}
        for instrumented in (False,True):
            name=version+('-visits' if instrumented else '-timing');source=work/name;source.mkdir(exist_ok=True)
            for file,data in original.items():(source/file).write_bytes(data)
            if instrumented:
                path=source/'com_guest.c';text=path.read_text()
                needle=('for(struct proxy *p=proxies;p;p=p->next) {' if version=='v6' else 'for(struct proxy *p=*bucket;p;p=p->hash_next) {')
                assert text.count(needle)==1
                text=text.replace(needle,needle+' if(count_visits)++lookup_visits;')
                if version=='v6':
                    needle='while(*at && *at!=self)at=&(*at)->next;';assert text.count(needle)==1
                    text=text.replace(needle,'while(*at && *at!=self){if(count_visits)++remove_visits;at=&(*at)->next;}')
                path.write_text(text,newline='\n')
            exe=work/(name+'.exe')
            argv=['wsl','-d','Ubuntu','-u','root','--exec',MINGW,'-O2','-std=c11','-DINITGUID','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib',
                  '-Wl,--no-insert-timestamp','-Wl,--entry,start@0','-I'+linux(source),linux(ROOT/'tests/native_dxvk_guest_lookup.c'),'-o',linux(exe),'-lkernel32','-luser32']
            if version=='current':argv.insert(8,'-DTEST_HASH_LOOKUP')
            result=subprocess.run(argv,capture_output=True,text=True,timeout=120)
            (work/(name+'.compile.log')).write_text(result.stdout+result.stderr)
            assert result.returncode==0,result.stderr
            commands[name]=argv;executables[name]=dict(path=str(exe),sha256=sha(exe),compiled_guest_sha256=sha(source/'com_guest.c'))
    for round_index in range(3):
        for version in ('v6','current'):
            name=version+'-timing';exe=Path(executables[name]['path'])
            result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=180)
            (work/(name+f'-{round_index}.stdout.log')).write_text(result.stdout)
            assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
            parsed=json.loads(result.stdout);assert parsed['status']=='PASS'
            parsed['ns_per_lookup']=parsed['ticks']*1e9/parsed['frequency']/parsed['timed_lookups']
            cases.setdefault(name,[]).append(parsed)
    for version in ('v6','current'):
        name=version+'-visits';result=subprocess.run([executables[name]['path']],capture_output=True,text=True,timeout=180)
        (work/(name+'.stdout.log')).write_text(result.stdout)
        assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
        cases[name]=json.loads(result.stdout);assert cases[name]['status']=='PASS'
    assert cases['current-visits']['lookup_visits']<cases['v6-visits']['lookup_visits']/100
    assert cases['current-visits']['removal_visits']==0 and cases['v6-visits']['removal_visits']>1000000
    medians={version:statistics.median(run['ns_per_lookup'] for run in cases[version+'-timing']) for version in ('v6','current')}
    sources=[ROOT/'tests/native_dxvk_guest_lookup.c']+[ROOT/'src/native_dxvk_com'/name for name in NAMES]
    report=dict(status='PASS',baseline_commit=BASELINE,original_guest_sources=originals,runner_sha256=sha(__file__),
                source_files={p.relative_to(ROOT).as_posix():sha(p) for p in sources},compile_argv=commands,executables=executables,cases=cases,
                median_ns_per_lookup=medians,relative_output_wrapper_speedup=medians['v6']/medians['current'],
                pe32_proxy_executed_on_windows=True,modeled_native_endpoint=True,hardware_tested=False,com_guest_execution_tested=False,game_integration_tested=False,game_fps_measured=False,
                coverage=['16000 simultaneously live tokens','full token generation and interface keys','repeated proxy identity','IUnknown alias roundtrip','null token','failed allocation native-reference rollback','concurrent same-token insertion and repeated lookup','permuted final release','global and hash backlink invariants','zero guest/native references at teardown'],
                scope='Actual PE32 guest wrappers execute on Windows. Native endpoint and token-bearing sampler descriptors are modeled. Separate instrumented builds count visited nodes; uninstrumented timings include complete CreateSamplerState output publication and nonfinal Release with 16000 live sampler proxies. Does not execute Wine/FEX, ARM64 DXVK, Switch, or the game.')
    (LOCAL/'guest-lookup.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(status='PASS',median_ns_per_lookup=medians,relative_output_wrapper_speedup=report['relative_output_wrapper_speedup'],visits={v:cases[v+'-visits'] for v in ('v6','current')},game_fps_measured=False),indent=2))

if __name__=='__main__':main()
