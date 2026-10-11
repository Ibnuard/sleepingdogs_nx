"""Windows runner: execute real PE32 proxies against a modeled native endpoint.

The v4 negative controls must fail the same scalar/publication assertions.
Requires the repository history, WSL Ubuntu and the pinned llvm-mingw compiler.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-h4-v6'
BASELINE='9e234fbdf31c24323dc26ed0544a30179d7f5e02'
MINGW='/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/i686-w64-mingw32-gcc'
GIT='C:/devkitPro/msys2/usr/bin/git.exe'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def linux(path):
    s=Path(path).resolve().as_posix();assert s[1:3]==':/'
    return '/mnt/'+s[0].lower()+'/'+s[3:]

def main():
    assert os.name=='nt','Run with Windows Python; test executables use native Windows PE32 execution.'
    work=LOCAL/'guest-output-check';work.mkdir(parents=True,exist_ok=True)
    old=work/'v4';old.mkdir(exist_ok=True)
    old_hashes={}
    for name in ('com_guest.c','com_guest_vtables.inc','com_protocol.h','com_interfaces.h','com_guids.inc','com_methods.h'):
        path=old/name;path.write_bytes(subprocess.check_output([GIT,'show',BASELINE+':src/native_dxvk_com/'+name],cwd=ROOT))
        old_hashes[name]=sha(path)
    cases={};commands={}
    for name,source,define,expected in [
        ('current',ROOT/'src/native_dxvk_com',None,None),
        ('v4-scalar',old,'TEST_ONLY_SCALAR','FAIL: scalar DSV output overwrites adjacent caller storage'),
        ('v4-publication',old,'TEST_ONLY_PUBLICATION','FAIL: native token exposed in caller COM output during transport')]:
        exe=work/(name+'.exe')
        argv=['wsl','-d','Ubuntu','-u','root','--exec',MINGW,'-O2','-std=c11','-DINITGUID','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib',
              '-Wl,--no-insert-timestamp','-Wl,--entry,start@0','-I'+linux(source),linux(ROOT/'tests/native_dxvk_guest_outputs.c'),'-o',linux(exe),'-lkernel32','-luser32']
        if define:argv.insert(8,'-D'+define)
        result=subprocess.run(argv,capture_output=True,text=True,timeout=120)
        (work/(name+'.compile.log')).write_text(result.stdout+result.stderr)
        assert result.returncode==0,result.stderr
        commands[name]=argv
        result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
        (work/(name+'.stdout.log')).write_text(result.stdout);(work/(name+'.stderr.log')).write_text(result.stderr)
        if expected:assert result.returncode==1 and expected in result.stdout,(name,result.returncode,result.stdout,result.stderr)
        else:assert result.returncode==0 and result.stdout.startswith('PASS:'),(name,result.returncode,result.stdout,result.stderr)
        cases[name]=dict(exit_code=result.returncode,output=result.stdout.strip(),exe_sha256=sha(exe),expected_regression_failure=bool(expected))
    sources=[ROOT/'tests/native_dxvk_guest_outputs.c',ROOT/'tools/generate_native_dxvk_com.py']
    sources += [ROOT/'src/native_dxvk_com'/name for name in old_hashes]
    report=dict(status='PASS',pe32_proxy_executed_on_windows=True,modeled_native_endpoint=True,cases=cases,
                baseline_commit=BASELINE,baseline_sha256=old_hashes,compile_argv=commands,runner_sha256=sha(__file__),
                source_files={p.relative_to(ROOT).as_posix():sha(p) for p in sources},
                hardware_tested=False,com_guest_execution_tested=False,game_integration_tested=False,game_fps_measured=False,
                scope='Actual PE32 guest wrappers run on Windows with a mocked Unix endpoint, including a synthetic 129-slot transport stress case. Negative controls reproduce caller overrun and transient wire-token publication in v4. This does not execute Wine/FEX, ARM64 DXVK or the game.')
    (LOCAL/'guest-output-check.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(status=report['status'],cases=cases,hardware_tested=False),indent=2))

if __name__=='__main__':main()
