"""Run real PE32 proxy sources on Windows, with a modeled native endpoint.

Use the exact source snapshot compiled into the candidate. Keep older receipts.
Reference tests compare the reproduced v9 source; other fixtures guard outputs,
identity, Map shadows and transport. No game/FEX/ARM64 performance inference.
"""
from pathlib import Path
import hashlib,json,os,subprocess

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-ref-v1'
MINGW='/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/i686-w64-mingw32-gcc'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def linux(path):
    s=Path(path).resolve().as_posix();assert s[1:3]==':/'
    return '/mnt/'+s[0].lower()+'/'+s[3:]
def main():
    assert os.name=='nt','Use Windows Python for actual native PE32 execution.'
    build=json.loads((LOCAL/'build.json').read_text());assert build['baseline_reproduced']
    for version,files in build['source_files'].items():
        for name,digest in files.items():assert sha(LOCAL/version/name)==digest,(version,name)
    work=LOCAL/'tests';work.mkdir(exist_ok=True)
    cases={};commands={}
    fixtures=[('refs-baseline','baseline','refs',[]),('refs','candidate','refs',['TEST_LOCAL_REFS']),
        ('outputs','candidate','outputs',[]),('lookup','candidate','lookup',['TEST_HASH_LOOKUP']),
        ('maps','candidate','maps',['TEST_SHADOW_CACHE']),
        ('transport','candidate','transport',['TEST_COUNT_LOCKS','TEST_FAST_ENDPOINT'])]
    compilation=[]
    for name,version,fixture,defines in fixtures:
        source=LOCAL/version/'source/native_dxvk_com';exe=work/(name+'.exe')
        path=ROOT/'tests'/('native_dxvk_guest_'+fixture+'.c')
        argv=[MINGW,'-O2','-std=c11','-DINITGUID',
              '-DSD_COM_REF_LOG_PATH="NUL"',*['-D'+d for d in defines],'-ffreestanding','-fno-builtin',
              '-fno-stack-protector','-nostdlib','-Wl,--no-insert-timestamp','-Wl,--entry,start@0',
              '-I'+linux(source),linux(path),'-o',linux(exe),'-lkernel32','-luser32']
        commands[name]=argv
        compilation.append(dict(name=name,argv=argv,log=linux(work/(name+'.compile.log'))))
    # One WSL entry for the independent compilations; avoid starting a fresh
    # Windows/WSL systemd session for every executable.
    compile_script='''import json,subprocess,sys,pathlib
for item in json.loads(sys.argv[1]):
    run=subprocess.run(item['argv'],capture_output=True,text=True,timeout=120)
    pathlib.Path(item['log']).write_text(run.stdout+run.stderr)
    if run.returncode: print(item['name'],run.stderr,flush=True);sys.exit(run.returncode)
    print('compiled '+item['name'],flush=True)
'''
    compiled=subprocess.run(['wsl','-d','Ubuntu','-u','root','--exec','python3','-c',compile_script,json.dumps(compilation)],capture_output=True,text=True,timeout=600)
    assert compiled.returncode==0,(compiled.stdout,compiled.stderr)
    print(compiled.stdout,flush=True)
    for name,version,fixture,defines in fixtures:
        exe=work/(name+'.exe');path=ROOT/'tests'/('native_dxvk_guest_'+fixture+'.c')
        result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=180)
        (work/(name+'.stdout.log')).write_text(result.stdout,newline='\n')
        (work/(name+'.stderr.log')).write_text(result.stderr,newline='\n')
        assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
        if fixture=='outputs':assert result.stdout.startswith('PASS:');observed={'status':'PASS','output':result.stdout.strip()}
        else:observed=json.loads(result.stdout);assert observed['status']=='PASS'
        cases[name]=dict(result=observed,exe_sha256=sha(exe),fixture_sha256=sha(path),source_version=version)
        print(json.dumps(dict(case=name,result=observed)),flush=True)
    current=cases['refs']['result'];before=cases['refs-baseline']['result']
    assert current['native_addrefs']==0 and before['native_addrefs']>250000
    assert before['native_calls']-current['native_calls']==current['local_addrefs']+current['local_releases']
    report=dict(status='PASS',build='native-dxvk-ref-v1',build_receipt_sha256=sha(LOCAL/'build.json'),
        candidate_sha256=sha(LOCAL/'candidate/sdndx4.dll'),source_files=build['source_files'],cases=cases,compile_argv=commands,
        bridge_calls_eliminated_in_reference_fixture=before['native_calls']-current['native_calls'],
        runner_sha256=sha(__file__),real_pe32_proxy_executed=True,modeled_native_endpoint=True,
        hardware_tested=False,game_fps_measured=False,
        coverage=['100000 exact AddRef/Release pairs','native output and local ownership interleavings',
                  'eight threads with repeated output publication and reference churn',
                  'blocked native final Release concurrent with same-token publication',
                  'all references balanced at teardown','existing output rollback and pointer guards',
                  'Map lifetime, preserving copies, failure cleanup and bounded idle cache',
                  'cold/warm endpoint discovery and concurrency'],
        limits='Fixtures compile the exact candidate guest source but model the Unix/native endpoint. Bridge-call counts are deterministic savings in this fixture, not a game workload or FPS estimate.')
    data=json.dumps(report,indent=2)+'\n'
    (LOCAL/'test.json').write_text(data,newline='\n');(ROOT/'reports/native-dxvk-ref-v1-test.json').write_text(data,newline='\n')
    print(json.dumps(dict(status='PASS',bridge_calls_eliminated=report['bridge_calls_eliminated_in_reference_fixture'],game_fps_measured=False)),flush=True)
if __name__=='__main__':main()
