"""Reproduce the delivered v9 proxy, then build a PE-only local-reference delta.

Run with WSL Python. No NRO, Wine, FEX, DXVK or shared SDK sources are changed.
"""
from pathlib import Path
import hashlib,io,json,os,shutil,subprocess,tarfile

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-ref-v1'
BASELINE='407b3201a6ec7ee1596d600601c30119f36880f6'
MINGW=Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin')
EXPECTED='886a969f68e969cc52fa7dd9b199dcb4fcf1d982d47a53ae7b81fa7c06b2a7e7'
NRO='4b7270cc3e132966f75b84a99e6a5c872752be636af56b07b6226675fb3edeb4'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path,value):path.write_text(json.dumps(value,indent=2)+'\n',newline='\n')
def main():
    assert os.name=='posix','Build with WSL Ubuntu Python.'
    LOCAL.mkdir(parents=True,exist_ok=True)
    commands={};audits={};sources={}
    previous=ROOT/'local/native-dxvk-h4-v9'
    assert sha(previous/'sdndx4.dll')==EXPECTED
    assert sha(previous/'sleepingdogs-fex.nro')==NRO
    archived=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-c','core.fsmonitor=false',
        'archive',BASELINE,'src/native_dxvk_com'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archived)) as archive:
        baseline={member.name:archive.extractfile(member).read() for member in archive if member.isfile()}
    for version in ('baseline','candidate'):
        work=LOCAL/version;source=work/'source/native_dxvk_com';source.mkdir(parents=True,exist_ok=True)
        # Keep source layout including the COM client's shared shader header.
        for path in sorted((ROOT/'src/native_dxvk_com').iterdir()):
            if path.suffix not in ('.c','.h','.inc'):continue
            relative=path.relative_to(ROOT).as_posix()
            data=baseline[relative] if version=='baseline' else path.read_bytes()
            (source/path.name).write_bytes(data)
        shaders=source.parent/'native_dxvk/probe_shaders.h';shaders.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT/'src/native_dxvk/probe_shaders.h',shaders)
        sources[version]={p.relative_to(work).as_posix():sha(p) for p in sorted((work/'source').rglob('*')) if p.is_file()}
        targets=['sdndx4.dll'] if version=='baseline' else ['sdndx4.dll','sd-native-dxvk-h4-test.exe']
        for name in targets:
            dll=name.endswith('.dll');src='com_guest.c' if dll else 'com_guest_test.c'
            argv=[str(MINGW/'i686-w64-mingw32-gcc'),'-O2','-std=c11','-DINITGUID','-DSD_COM_BUILD="native-dxvk-h4-v9"',
                  '-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-Wl,--no-insert-timestamp',
                  '-Wl,--kill-at','-Wl,--entry,'+('DllMain@12' if dll else 'start@0')]
            if dll:argv+=['-shared','-Wl,--out-implib,'+str(work/'sdndx4.a')]
            else:argv+=['-DSD_COM_REF_TEST']
            argv+=[str(source/src),'-o',str(work/name),'-lkernel32']
            if dll:argv+=['-luser32']
            result=subprocess.run(argv,capture_output=True,text=True,timeout=120)
            (work/(name+'.compile.log')).write_text(result.stdout+result.stderr)
            assert result.returncode==0,result.stderr
            commands[version+'/'+name]=argv
            from build_native_dxvk_h4 import pe_audit
            audits[version+'/'+name]=pe_audit(work/name)
    assert sha(LOCAL/'baseline/sdndx4.dll')==EXPECTED,'Baseline proxy reproduction differs'
    assert 'SdComRefStats' in audits['candidate/sdndx4.dll']['exports']
    assert set(audits['candidate/sdndx4.dll']['imports'])=={'KERNEL32.dll','USER32.dll'}
    report=dict(status='BUILT',build='native-dxvk-ref-v1',baseline_commit=BASELINE,baseline_reproduced=True,
        baseline_proxy_sha256=EXPECTED,proxy_sha256=sha(LOCAL/'candidate/sdndx4.dll'),
        com_client_sha256=sha(LOCAL/'candidate/sd-native-dxvk-h4-test.exe'),
        unchanged_nro_sha256=NRO,protocol_abi=4,compiler_sha256=sha(MINGW/'i686-w64-mingw32-gcc'),
        source_files=sources,compile_argv=commands,pe_audits=audits,builder_sha256=sha(__file__),
        hardware_tested=False,game_fps_measured=False)
    write_json(LOCAL/'build.json',report);write_json(ROOT/'reports/native-dxvk-ref-v1-build.json',report)
    print(json.dumps({k:report[k] for k in ('status','baseline_reproduced','proxy_sha256','com_client_sha256')},indent=2))
if __name__=='__main__':main()
