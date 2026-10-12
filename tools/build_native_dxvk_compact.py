"""Build the compact guest delta without changing the delivered v9/ref build."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
from native_dxvk_compact import ROOT,SRC,guest,native,methods,generated_header

LOCAL=ROOT/'local/native-dxvk-compact-v1'
MINGW=Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare():
    LOCAL.mkdir(parents=True,exist_ok=True)
    source=LOCAL/'source/native_dxvk_com';source.mkdir(parents=True,exist_ok=True)
    for p in SRC.iterdir():
        if p.is_file():shutil.copyfile(p,source/p.name)
    assert (source/'com_compact.h').read_text()==generated_header()
    guest(source)
    (source/'com_native.cpp').write_text(native((SRC/'com_native.cpp').read_text()),newline='\n')
    shaders=source.parent/'native_dxvk/probe_shaders.h';shaders.parent.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'src/native_dxvk/probe_shaders.h',shaders)
    return source
def main():
    assert os.name=='posix'
    source=prepare();old=json.loads((ROOT/'local/native-dxvk-ref-v1/build.json').read_text())
    assert sha(ROOT/'local/native-dxvk-ref-v1/candidate/sdndx4.dll')==old['proxy_sha256']
    commands={}
    for name in ('sdndx4.dll','sd-native-dxvk-h4-test.exe'):
        argv=list(old['compile_argv']['candidate/'+name])
        c=argv.index('-o');argv[c+1]=str(LOCAL/name)
        argv=[str(source/Path(a).name) if a.endswith(('.c',)) else
              '-Wl,--out-implib,'+str(LOCAL/'sdndx4.a') if a.startswith('-Wl,--out-implib,') else a for a in argv]
        run=subprocess.run(argv,capture_output=True,text=True,timeout=120)
        (LOCAL/(name+'.compile.log')).write_text(run.stdout+run.stderr)
        assert not run.returncode,run.stderr
        commands[name]=argv
    report=dict(status='BUILT',build='native-dxvk-compact-v1',source=str(source),
        source_files={p.relative_to(LOCAL).as_posix():sha(p) for p in sorted((LOCAL/'source').rglob('*')) if p.is_file()},
        baseline_proxy_sha256=old['proxy_sha256'],proxy_sha256=sha(LOCAL/'sdndx4.dll'),
        client_sha256=sha(LOCAL/'sd-native-dxvk-h4-test.exe'),methods=[dict(name=m['name'],index=m['index'],args=len(m['params'])) for m in methods()],
        compile_commands=commands,hardware_tested=False,game_fps_measured=False)
    (LOCAL/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','proxy_sha256','hardware_tested')}),flush=True)
if __name__=='__main__':main()
