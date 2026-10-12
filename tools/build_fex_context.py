"""Relink the pinned scene FEX with an exact x87 import shortcut in isolation."""
from pathlib import Path
import difflib,hashlib,json,os,shlex,shutil,struct,subprocess
from port_common import ROOT,sha,write_json

BUILD='sd-fex-context-v1'
LOCAL=ROOT/'local'/BUILD
WORK=Path('/home/blekjek/sleepingdogs-fex-context-v1')
BASE=Path('/home/blekjek/sleepingdogs-scene-memory-v1/fex')
PIN=ROOT/'vendor/fex/libwow64fex-sd-scene.json'
MARKER='[SD-FEX-CONTEXT] v1 exact x87 import; normal/zero shortcut; all rounding modes; full context/suspend preserved'

def invoke(command,log,cwd):
    result=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    log.write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(str(log)+'\n'+result.stderr[-6000:])

def main():
    assert os.name=='posix'
    WORK.mkdir(parents=True,exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
    pin=json.loads(PIN.read_text());receipt=pin['debug_register_build']
    original=BASE/'build/Bin/libwow64fex.dll'
    assert sha(original)==pin['sha256']
    paths=[BASE/'adapter/module_fpu.cpp',BASE/'adapter/horizon_fpu.h',BASE/'source/Source/Windows/WOW64/Module.cpp']
    assert sha(paths[0])==receipt['adapter_files']['module_fpu.cpp']
    assert sha(paths[1])==receipt['adapter_files']['horizon_fpu.h']
    assert sha(paths[2])==receipt['source_changes']['Source/Windows/WOW64/Module.cpp']
    # Use ninja only to read the existing command graph. No baseline rebuild.
    raw=subprocess.check_output(['ninja','-C',str(BASE/'build'),'-t','commands','Bin/libwow64fex.dll'],text=True)
    lines=raw.splitlines();line=next(x for x in reversed(lines) if ' -o Bin/libwow64fex.dll ' in x)
    link=shlex.split(line.split(' && ')[1]);assert link[-1]!='&&'
    assert link[link.index('-o')+1]=='Bin/libwow64fex.dll'
    input_paths=[(BASE/'build'/x).resolve() for x in link if not x.startswith('-') and x.endswith(('.obj','.a','.def'))]
    inputs={str(p):sha(p) for p in input_paths}
    timestamp=struct.unpack_from('<I',original.read_bytes(),struct.unpack_from('<I',original.read_bytes(),0x3c)[0]+8)[0]
    def output_link(folder,replacements):
        folder.mkdir(exist_ok=True)
        command=[replacements.get(x,x) for x in link]
        command[command.index('-o')+1]=str(folder/'libwow64fex.dll')
        command=[('-Wl,--out-implib,'+str(folder/'libwow64fex.dll.a') if x.startswith('-Wl,--out-implib,') else x) for x in command]
        command+=['-Wl,--Xlink=/timestamp:'+str(timestamp)]
        invoke(command,folder/'link.log',BASE/'build')
        dll=folder/'libwow64fex.dll';data=bytearray(dll.read_bytes())
        builtin=BASE/'source/Source/Windows/wine_builtin.bin'
        data[64:96]=builtin.read_bytes()[:32]
        dll.write_bytes(data)
        return dll,command
    baseline,baseline_link=output_link(WORK/'baseline',{})
    assert sha(baseline)==pin['sha256'],('baseline reproduction mismatch',sha(baseline),pin['sha256'])
    overlay=WORK/'source';overlay.mkdir(exist_ok=True);objects=WORK/'objects';objects.mkdir(exist_ok=True)
    shutil.copy2(paths[1],overlay/'horizon_fpu.h')
    shutil.copy2(ROOT/'src/fex_context/exact_x87.h',overlay/'exact_x87.h')
    patches={};commands={};replacements={};headers={}
    for kind,path in [('fpu',paths[0]),('module',paths[2])]:
        before=path.read_text()
        if kind=='fpu':
            assert before.count('pes13_fex_fp::narrow(value, control)')==1
            after=before.replace('#include "horizon_fpu.h"','#include "horizon_fpu.h"\n#include "exact_x87.h"')
            after=after.replace('pes13_fex_fp::narrow(value, control)',
                'sd_fex_context::narrow(value, control, pes13_fex_fp::narrow)')
        else:
            anchor='  PES13FexLog("[FEX3-FP] context v1 MXCSR, x87 TOP/F64, legacy registers");'
            assert before.count(anchor)==1
            after=before.replace(anchor,anchor+'\n  PES13FexLog("'+MARKER+'");')
        target=overlay/path.name;target.write_text(after,newline='\n')
        diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path.name,tofile='b/'+path.name))
        (WORK/(kind+'.patch')).write_text(diff,newline='\n')
        command=shlex.split(next(x for x in lines if ' -c '+str(path) in x))
        old_object=command[command.index('-o')+1];new_object=objects/(kind+'.obj')
        command=[str(target) if x==str(path) else x for x in command]
        command[command.index('-o')+1]=str(new_object)
        for flag in ('-MF','-MT'):
            if flag in command:command[command.index(flag)+1]=str(new_object)+('.d' if flag=='-MF' else '')
        command.insert(1,'-I'+str(path.parent))
        invoke(command,WORK/(kind+'.compile.log'),BASE/'build')
        dep=Path(command[command.index('-MF')+1])
        for name in shlex.split(dep.read_text().replace('\\\n','').split(':',1)[1]):
            p=Path(name) if Path(name).is_absolute() else BASE/'build'/name
            if p.is_file():headers[str(p)]=sha(p)
        commands[kind]=command;replacements[old_object]=str(new_object)
        patches[kind]=dict(original=str(path),baseline_sha256=sha(path),source_sha256=sha(target),patch_sha256=sha(WORK/(kind+'.patch')))
    candidate,candidate_link=output_link(WORK/'candidate',replacements)
    assert MARKER.encode() in candidate.read_bytes()
    for p,h in inputs.items():assert sha(p)==h,('baseline changed',p)
    assert sha(original)==pin['sha256']
    shutil.copy2(candidate,LOCAL/'libwow64fex.dll');shutil.copy2(baseline,LOCAL/'baseline-libwow64fex.dll')
    for kind in patches:shutil.copy2(WORK/(kind+'.patch'),LOCAL/(kind+'.patch'))
    report=dict(status='BUILT',build=BUILD,baseline_reproduced=True,baseline_sha256=sha(baseline),dll_sha256=sha(candidate),
        dll_bytes=candidate.stat().st_size,work=str(WORK),baseline_work=str(BASE),timestamp=timestamp,compile_commands=commands,
        baseline_link=baseline_link,candidate_link=candidate_link,inputs=inputs,header_inputs=headers,patches=patches,pin_sha256=sha(PIN),
        source_files={p.relative_to(ROOT).as_posix():sha(p) for p in (Path(__file__),ROOT/'src/fex_context/exact_x87.h')},
        hardware_tested=False,game_fps_measured=False)
    write_json(LOCAL/'build.json',report)
    print(json.dumps({k:report[k] for k in ('status','build','baseline_reproduced','dll_sha256','dll_bytes','hardware_tested')}),flush=True)
if __name__=='__main__':main()
