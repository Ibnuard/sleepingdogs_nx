"""Build inline v1 from the immutable Compact v1 receipt."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
from native_dxvk_inline import ROOT,guest,native,methods
from native_dxvk_present_overlap import prepare as prepare_overlap
LOCAL=ROOT/'local/native-dxvk-inline-v1'
BASE=ROOT/'local/native-dxvk-compact-v1'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(native_transform=None,with_present_overlap=True):
    old=json.loads((BASE/'build.json').read_text())
    for name,digest in old['source_files'].items():assert sha(BASE/name)==digest,name
    source=LOCAL/'source/native_dxvk_com';source.mkdir(parents=True,exist_ok=True)
    shutil.copytree(BASE/'source',LOCAL/'source',dirs_exist_ok=True)
    shutil.copyfile(ROOT/'src/native_dxvk_com/com_inline.h',source/'com_inline.h')
    guest(source);text=native((source/'com_native.cpp').read_text())
    if native_transform:text=native_transform(text)
    (source/'com_native.cpp').write_text(text,newline='\n')
    if with_present_overlap:prepare_overlap(source)
    return source,old

def main():
    assert os.name=='posix';source,old=prepare();commands={}
    for name,argv in old['compile_commands'].items():
        argv=[a.replace(str(BASE),str(LOCAL)) for a in argv]
        run=subprocess.run(argv,capture_output=True,text=True,timeout=120)
        (LOCAL/(name+'.compile.log')).write_text(run.stdout+run.stderr);assert not run.returncode,run.stderr
        commands[name]=argv
    report=dict(status='BUILT',build='native-dxvk-inline-v1',source=str(source),
        source_files={p.relative_to(LOCAL).as_posix():sha(p) for p in sorted((LOCAL/'source').rglob('*')) if p.is_file()},
        baseline_proxy_sha256=old['proxy_sha256'],proxy_sha256=sha(LOCAL/'sdndx4.dll'),
        client_sha256=sha(LOCAL/'sd-native-dxvk-h4-test.exe'),
        methods=[dict(name=m['name'],index=m['index'],args=len(m['params'])) for m in methods()],
        present_deferred_overlap=True,
        compile_commands=commands,hardware_tested=False,game_fps_measured=False)
    (LOCAL/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','proxy_sha256','hardware_tested')}),flush=True)
if __name__=='__main__':main()
