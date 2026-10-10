"""Compile only the two changed Wine units plus native LSFG and relink v14.1."""
from pathlib import Path
import json, os, shlex, shutil, subprocess, struct
from port_common import ROOT,sha,write_json
from build_lsfg_backend import WORK,MESA_HEADERS
from prepare_lsfg_native import NATIVE

RECEIPT=ROOT/'dist/sleepingdogs-fex-v14.1-update/source/low-window-gm20b-cache-fix/native.json'
DEST=ROOT/'local/lsfg-native-v15'

def run(args,cwd,log):
    env=dict(os.environ,DEVKITPRO='/opt/devkitpro',DEVKITA64='/opt/devkitpro/devkitA64')
    with log.open('w') as out:
        result=subprocess.run(args,cwd=cwd,env=env,stdout=out,stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text()[-10000:]);raise RuntimeError('Command failed: '+str(log))

def main():
    previous=json.loads(RECEIPT.read_text());cwd=Path(previous['working_directory'])
    out=WORK/'runtime';out.mkdir(exist_ok=True);objects=WORK/'objects';objects.mkdir(exist_ok=True)
    # The old receipt's inputs refer to its own pre-replacement Mesa archive.
    # Audit every actual link input, then reproduce the delivered ELF exactly.
    original=previous['link_argv'];inputs={}
    for x in original[1:]:
        if x.startswith('-') or not x.endswith(('.obj','.o','.a')):continue
        p=(cwd/x).resolve();inputs[str(p)]=sha(p)
    baseline=out/'baseline/wine-nx-runtime.elf';baseline.parent.mkdir(exist_ok=True)
    cmd=original.copy();cmd[cmd.index('-o')+1]=str(baseline)
    cmd=[('-Wl,-Map='+str(out/'baseline.map')) if x.startswith('-Wl,-Map=') else x for x in cmd]
    run(cmd,cwd,out/'baseline.log')
    assert sha(baseline)==previous['elf_sha256'],'Baseline changed; stop before packaging'
    changed={};commands={}
    pairs={
        'CMakeFiles/wine-nx-runtime.dir/source/runtime.c.obj':'wine-nx-probe/source/runtime.c',
        'CMakeFiles/wine-win32u-real.dir/home/blekjek/sleepingdogs-low-window-v1/native-source/dlls/win32u/window.c.obj':'dlls/win32u/window.c',
        'CMakeFiles/wine-win32u-real.dir/home/blekjek/sleepingdogs-low-window-v1/native-source/dlls/win32u/vulkan.c.obj':'dlls/win32u/vulkan.c'}
    for old,src in pairs.items():
        raw=subprocess.check_output(['ninja','-t','commands',old],cwd=cwd,text=True).splitlines()[-1]
        argv=shlex.split(raw);obj=objects/(Path(src).name+'.obj');new=[];i=0
        while i<len(argv):
            if argv[i] in ('-c','-o','-MF','-MT'):
                flag=argv[i];new.extend([flag,str(NATIVE/src if flag=='-c' else obj.with_suffix('.d') if flag=='-MF' else obj)]);i+=2
            else:new.append(argv[i]);i+=1
        new[1:1]=['-I'+str(NATIVE/'wine-nx-probe/source')]
        run(new,cwd,out/(Path(src).name+'.compile.log'));changed[old]=str(obj);commands[src]=new
    backend_cmd=json.loads((WORK/'backend-cross/compile_commands.json').read_text())[0]
    argv=shlex.split(backend_cmd['command']);new=[];i=0
    while i<len(argv):
        if argv[i] in ('-c','-o','-MF','-MT'):i+=2;continue
        if argv[i]=='-MD':i+=1;continue
        if argv[i].endswith('.cpp'):i+=1;continue
        new.append(argv[i]);i+=1
    obj=objects/'lsfg.cpp.obj'
    new+=['-I'+str(NATIVE/'wine-nx-probe/source'),'-c',str(NATIVE/'wine-nx-probe/source/lsfg.cpp'),'-o',str(obj)]
    run(new,WORK,out/'lsfg.compile.log');commands['lsfg.cpp']=new
    candidate=out/'candidate/wine-nx-runtime.elf';candidate.parent.mkdir(exist_ok=True)
    cmd=[changed.get(x,x) for x in original];cmd[cmd.index('-o')+1]=str(candidate)
    cmd=[('-Wl,-Map='+str(out/'candidate.map')) if x.startswith('-Wl,-Map=') else x for x in cmd]
    # Resolve the new bridge/backend before Vulkan static archives are visited.
    index=next(i for i,x in enumerate(cmd) if x.endswith('.a'))
    cmd[index:index]=[str(obj),str(WORK/'portlibs/lib/liblsfg-vk.a')]
    run(cmd,cwd,out/'candidate.log')
    for p,h in inputs.items():assert sha(p)==h,('input changed during build',p)
    old=(ROOT/'dist/sleepingdogs-fex-v14.1-update/switch/sleepingdogs-fex/sleepingdogs-fex.nro').read_bytes()
    size=struct.unpack_from('<I',old,0x18)[0];assert old[size:size+4]==b'ASET'
    io,il,no,nl,ro,rl=struct.unpack_from('<6Q',old,size+8);assert not rl
    (out/'icon.jpg').write_bytes(old[size+io:size+io+il])
    nacp=bytearray(old[size+no:size+no+nl]);nacp[0x3060:0x3070]=b'0.1.0-v15'.ljust(16,b'\0')
    (out/'app.nacp').write_bytes(nacp)
    nro=out/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro',str(candidate),str(nro),
        '--icon='+str(out/'icon.jpg'),'--nacp='+str(out/'app.nacp')],check=True)
    DEST.mkdir(exist_ok=True);shutil.copy2(nro,DEST/nro.name)
    shutil.copy2(candidate,ROOT/'local/symbols/sleepingdogs-lsfg-v15.elf')
    write_json(DEST/'native.json',dict(status='BUILT',build='sleepingdogs-v15-native-lsfg',
        nro_sha256=sha(nro),elf_sha256=sha(candidate),baseline_reproduced=True,
        baseline_elf_sha256=sha(baseline),baseline_nro_sha256=previous['nro_sha256'],
        driver_cache_id=previous['cache_id'],driver_library_sha256=sha('/home/blekjek/sleepingdogs-mesa-v141/library/libvulkan.a'),
        backend_library_sha256=sha(WORK/'portlibs/lib/liblsfg-vk.a'),
        link_argv=cmd,working_directory=str(cwd),inputs=inputs,changed_objects=changed,compile_commands=commands,
        fex_unchanged=True,dxvk_unchanged=True,hardware_tested=False,fps_gain_measured=False))
    print('BUILT',sha(nro),flush=True)

if __name__=='__main__':main()
