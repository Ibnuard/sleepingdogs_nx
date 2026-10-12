"""Build an isolated release-preparation NRO; retain H4 v9 / Native Ref / FEX.

Run in the prepared WSL build environment. Baseline objects and upstream
checkouts are read-only. Only five native input/runtime objects are replaced.
"""
from pathlib import Path
import argparse,hashlib,json,os,shlex,shutil,subprocess
from launcher_v1_overlay import ROOT,SOURCE,runtime_overlay,settings_overlay,wine_overlay

WORK=Path('/home/blekjek/sleepingdogs-launcher-v1')
LOCAL=ROOT/'local/launcher-v1'
BASE=ROOT/'dist/sd-dxvk-native-h4-v9-update/switch/sleepingdogs-fex'
FULL=ROOT/'local/buffer-reuse-validate-uzpwmdes/switch/sleepingdogs-fex'
A64=Path('/opt/devkitpro/devkitA64/bin')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,text):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,newline='\n')
def run(args,name,cwd):
    with (WORK/(name+'.log')).open('w') as out:
        p=subprocess.run([str(x) for x in args],cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(name+' failed: '+(WORK/(name+'.log')).read_text()[-14000:])
def rewritten(command,source,obj):
    command=list(command)
    for flag in ('-o','-MF','-MT'):
        if flag in command:command[command.index(flag)+1]=str(obj)+('.d' if flag=='-MF' else '')
    command[command.index('-c')+1]=str(source)
    command[1:1]=['-I'+str(source.parent),'-I'+str(source.parent/'pes13'),'-I'+str(SOURCE),'-I'+str(SOURCE/'pes13')]
    return command

def runtime_files():
    files={p.relative_to(FULL).as_posix():p for p in (FULL/'drive_c/windows').rglob('*.dll')}
    for p in (FULL/'launcher').iterdir():
        if p.is_file() and p.suffix in ('.rgba','.bin'):files[p.relative_to(FULL).as_posix()]=p
    for name in ('background.rgba','blur.rgba','icon.rgba'):
        files['launcher/'+name]=ROOT/'local/lsfg-launcher-check/preview-assets'/name
    for p in (BASE/'launcher').rglob('*'):
        if p.is_file() and p.suffix in ('.rgba','.bin','.dll'):
            files[p.relative_to(BASE).as_posix()]=p
    fex=ROOT/'dist/sd-fex-context-v1-update/switch/sleepingdogs-fex'
    refs=ROOT/'dist/sd-native-dxvk-ref-v1-update/switch/sleepingdogs-fex'
    for folder in (fex,refs):
        for p in folder.rglob('*.dll'):files[p.relative_to(folder).as_posix()]=p
    files['launcher/renderers/dxvk-native-h4/sdndx4.dll']=ROOT/'local/native-dxvk-compact-v1/sdndx4.dll'
    # Renderer transactions select the active game-side D3D DLLs; only their
    # immutable packaged sources are hashed, so switching renderer stays valid.
    files={n:p for n,p in files.items() if not n.startswith('drive_c/SleepingDogs/') and not n.endswith('/syswow64/d3d9.dll')}
    return files

def prepare():
    WORK.mkdir(parents=True,exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
    old=json.loads((ROOT/'local/native-dxvk-h4-v9/build.json').read_text())
    assert old['nro_sha256']=='4b7270cc3e132966f75b84a99e6a5c872752be636af56b07b6226675fb3edeb4'
    assert sha(old['elf'])==old['elf_sha256']
    cwd=Path(old['working_directory']);overlay=WORK/'source';objects=WORK/'objects';objects.mkdir(exist_ok=True)
    inputs={str((cwd/a).resolve()):sha(cwd/a) for a in old['link_argv'] if a.endswith(('.obj','.o','.a'))}
    pin=LOCAL/'baseline-inputs.json'
    if pin.exists():assert json.loads(pin.read_text())==inputs,'Baseline objects changed'
    else:save(pin,json.dumps(inputs,indent=2)+'\n')
    commands={};replacements={};sources={}
    runtime=Path(old['compile_commands']['runtime'][old['compile_commands']['runtime'].index('-c')+1])
    after=runtime_overlay(runtime.read_text());target=overlay/'runtime.c';save(target,after)
    save(overlay/'f1_settings.h',settings_overlay((runtime.parent/'f1_settings.h').read_text()))
    # Pin relative quoted headers from the old overlay; keep its game-quality
    # and async-native-log changes identical.
    command=old['compile_commands']['runtime'];obj=objects/'runtime.o'
    command=rewritten(command,target,obj);command.insert(1,'-I'+str(runtime.parent))
    commands['runtime']=command;replacements[old['compile_commands']['runtime'][old['compile_commands']['runtime'].index('-o')+1]]=str(obj)
    native=cwd.parent/'native-source'
    paths={'winnx_drv':native/'dlls/win32u/winnx_drv.c','driver':native/'dlls/win32u/driver.c','xinput':native/'wine-nx-probe/source/xinput_unix.c'}
    for name,source in paths.items():
        suffix='/'+source.name+'.obj'
        input_obj=next(a for a in old['link_argv'] if a.endswith(suffix))
        command=shlex.split(subprocess.check_output(['ninja','-C',str(cwd),'-t','commands',input_obj],text=True).strip())
        # Ninja may print prerequisite generation commands; take the compile line.
        if command[0]!=str(A64/'aarch64-none-elf-gcc'):
            lines=subprocess.check_output(['ninja','-C',str(cwd),'-t','commands',input_obj],text=True).splitlines()
            command=shlex.split(next(x for x in reversed(lines) if ' -c ' in x))
        dst=overlay/(name+'.c');save(dst,wine_overlay(name,source.read_text()));sources[str(source)]=sha(source)
        obj=objects/(name+'.o');command=rewritten(command,dst,obj);command.insert(1,'-I'+str(source.parent))
        commands[name]=command;replacements[input_obj]=str(obj)
    apc=json.loads((ROOT/'local/apc-v18/native.json').read_text())
    horizon_name=next(k for k in apc['compile_commands'] if k.endswith('/horizon.c'))
    command=apc['compile_commands'][horizon_name];source=Path(command[command.index('-c')+1])
    dst=overlay/'horizon.c';save(dst,wine_overlay('horizon',source.read_text()));sources[str(source)]=sha(source)
    header=native/'dlls/ntdll/unix/horizon_keyboard.h'
    save(overlay/header.name,wine_overlay('horizon_keyboard',header.read_text()));sources[str(header)]=sha(header)
    obj=objects/'horizon.o';commands['horizon']=rewritten(command,dst,obj);commands['horizon'].insert(1,'-I'+str(source.parent))
    replacements[command[command.index('-o')+1]]=str(obj)
    files=runtime_files();entries=[dict(path=n,bytes=p.stat().st_size,sha256=sha(p),source=str(p)) for n,p in sorted(files.items())]
    catalog='/* Generated from immutable runtime inputs, excluding user settings/game payloads. */\nstatic const struct sd_check_file sd_check_files[]={\n'
    for e in entries:
        alternate='a03a58b6023a7b74ff0d96d0460ce247715fa1210b6f6d02428f206908541344' if e['path']=='launcher/renderers/dxvk-native-h4/sdndx4.dll' else ''
        catalog+='    {'+json.dumps(e['path'])+','+str(e['bytes'])+','+json.dumps(e['sha256'])+','+json.dumps(alternate)+'},\n'
    catalog+='};\n#define SD_CHECK_FILE_COUNT (sizeof(sd_check_files)/sizeof(*sd_check_files))\n'
    save(overlay/'system_catalog.h',catalog);save(LOCAL/'catalog.json',json.dumps(entries,indent=2)+'\n')
    font=files['launcher/font.bin'];data=font.read_bytes()
    save(overlay/'boot_font.c','const unsigned sd_boot_font_size='+str(len(data))+';\nconst unsigned char sd_boot_font[]={\n'+
         '\n'.join(','.join(str(c) for c in data[i:i+64])+',' for i in range(0,len(data),64))+'\n};\n')
    flags=['-O2','-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-ffixed-x18','-ftls-model=local-exec','-ffunction-sections','-fdata-sections','-fPIE','-D__SWITCH__','-DNX',
           '-isystem','/opt/devkitpro/libnx/include','-isystem','/opt/devkitpro/portlibs/switch/include']
    commands['font']=[str(A64/'aarch64-none-elf-gcc'),*flags,'-c',str(overlay/'boot_font.c'),'-o',str(objects/'font.o')]
    commands['osk']=[str(A64/'aarch64-none-elf-g++'),*flags,'-I/home/blekjek/pes13-build/mesa-vulkan/install/opt/devkitpro/portlibs/switch/include','-std=c++17','-I'+str(SOURCE),'-c',str(SOURCE/'osk_vulkan.cpp'),'-o',str(objects/'osk.o')]
    compact=json.loads((ROOT/'local/native-dxvk-compact-v1/build.json').read_text())
    com_command=old['compile_commands']['com'];obj=objects/'com.o'
    commands['com']=rewritten(com_command,Path(compact['source'])/'com_native.cpp',obj)
    replacements[com_command[com_command.index('-o')+1]]=str(obj)
    # Keep imported files byte-identical; the sole game-specific label is in a
    # generated copy, preceding the pinned include directory.
    branded=overlay/'pes13';shutil.copytree(SOURCE/'pes13',branded,dirs_exist_ok=True)
    kb=branded/'fextendo_keyboard_switch.h';save(kb,kb.read_text().replace('PES13 - FEXTendo','Sleeping Dogs - FEXTendo'))
    elf=WORK/'sleepingdogs-launcher-v1.elf';link=[replacements.get(a,a) for a in old['link_argv']]
    link[link.index('-o')+1]=str(elf)
    link=[('-Wl,-Map='+str(WORK/'launcher.map') if a.startswith('-Wl,-Map=') else a) for a in link]
    first=next(i for i,a in enumerate(link) if a.endswith('.a'))
    link[first:first]=[str(objects/'font.o'),str(objects/'osk.o'),'-Wl,--wrap=vkGetInstanceProcAddr','-Wl,--wrap=vkGetDeviceProcAddr']
    receipt=dict(build='launcher-v1',working_directory=str(cwd),compile_commands=commands,link_argv=link,inputs=inputs,baseline_sources=sources,
                 native_dxvk_sha256=old['native_dxvk_sha256'],baseline_nro_sha256=old['nro_sha256'],elf=str(elf),runtime_catalog_sha256=sha(LOCAL/'catalog.json'))
    save(LOCAL/'prepared.json',json.dumps(receipt,indent=2)+'\n');return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare-only',action='store_true');args=p.parse_args()
    assert os.name=='posix';os.environ.setdefault('DEVKITPRO','/opt/devkitpro');r=prepare()
    if args.prepare_only:print('Prepared launcher-v1 overlay');return
    cwd=Path(r['working_directory'])
    for name,command in r['compile_commands'].items():
        print('Compiling',name,flush=True);run(command,name,cwd)
    print('Linking launcher-v1',flush=True);run(r['link_argv'],'link',cwd)
    nacp=WORK/'launcher.nacp';nro=WORK/'sleepingdogs-fex.nro'
    run(['/opt/devkitpro/tools/bin/nacptool','--create','Sleeping Dogs - FEXTendo','AndroSwitch Project','0.1.0-l1',nacp],'nacp',WORK)
    run(['/opt/devkitpro/tools/bin/elf2nro',r['elf'],nro,'--nacp='+str(nacp)],'nro',WORK)
    shutil.copy2(nro,LOCAL/nro.name)
    r.update(status='BUILT',nro_sha256=sha(nro),nro_bytes=nro.stat().st_size,elf_sha256=sha(r['elf']),hardware_tested=False)
    r['source_files']={str(p.relative_to(ROOT)):sha(p) for p in SOURCE.rglob('*') if p.is_file()}
    r['generated_sources']={str(p.relative_to(WORK)):sha(p) for p in (WORK/'source').rglob('*') if p.is_file()}
    r['builder_sources']={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'tools/launcher_v1_overlay.py',ROOT/'tools/native_dxvk_compact.py')}
    r['compact_build_receipt_sha256']=sha(ROOT/'local/native-dxvk-compact-v1/build.json')
    save(LOCAL/'build.json',json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('status','build','nro_sha256','nro_bytes','hardware_tested')}))
if __name__=='__main__':main()
