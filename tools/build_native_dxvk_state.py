"""Build state v1 without changing any previously delivered COM binaries."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
from native_dxvk_state import ROOT,guest,native,METHODS
LOCAL=ROOT/'local/native-dxvk-state-v1'
BASE=ROOT/'local/native-dxvk-compact-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare():
    old=json.loads((BASE/'build.json').read_text())
    for name,digest in old['source_files'].items():assert sha(BASE/name)==digest,name
    source=LOCAL/'source/native_dxvk_com';source.mkdir(parents=True,exist_ok=True)
    shutil.copytree(BASE/'source',LOCAL/'source',dirs_exist_ok=True)
    for name in ('com_state_cache.h','com_state_guest.inc'):shutil.copyfile(ROOT/'src/native_dxvk_com'/name,source/name)
    guest(source);(source/'com_native.cpp').write_text(native((source/'com_native.cpp').read_text()),newline='\n')
    return source,old
def main():
    assert os.name=='posix';source,old=prepare();commands={}
    for name,argv in old['compile_commands'].items():
        argv=[a.replace(str(BASE),str(LOCAL)) for a in argv]
        run=subprocess.run(argv,capture_output=True,text=True,timeout=120)
        (LOCAL/(name+'.compile.log')).write_text(run.stdout+run.stderr);assert not run.returncode,run.stderr
        commands[name]=argv
    report=dict(status='BUILT',build='native-dxvk-state-v1',source=str(source),
        source_files={p.relative_to(LOCAL).as_posix():sha(p) for p in sorted((LOCAL/'source').rglob('*')) if p.is_file()},
        baseline_proxy_sha256=old['proxy_sha256'],proxy_sha256=sha(LOCAL/'sdndx4.dll'),
        client_sha256=sha(LOCAL/'sd-native-dxvk-h4-test.exe'),methods=METHODS,compile_commands=commands,
        hardware_tested=False,game_fps_measured=False)
    (LOCAL/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','proxy_sha256','hardware_tested')}),flush=True)
if __name__=='__main__':main()
