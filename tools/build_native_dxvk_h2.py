"""Build an isolated PE32 -> Wine/FEX WOW64 -> native DXVK H2 diagnostic.

Reuses verified v18 objects and the H1 native library. Only task-owned Wine
source overlays and objects are changed. No SDK, baseline or game file edits.
"""
from pathlib import Path
import argparse
import difflib
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import struct
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SDK=Path('/opt/devkitpro')
TOOLS=SDK/'devkitA64/bin'
MINGW=Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin')
INPUTS=ROOT/'vendor/wine/native-dxvk-h2-inputs.json'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(argv,log,cwd):
    env=dict(os.environ,DEVKITPRO=str(SDK),DEVKITA64=str(SDK/'devkitA64'))
    with log.open('w') as output:
        p=subprocess.run(list(map(str,argv)),cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT)
    if p.returncode:print(log.read_text()[-9000:]);raise RuntimeError(str(log))
def replace(text,before,after):
    assert text.count(before)==1, ('source anchor',before[:80])
    return text.replace(before,after)
def rewrite_command(argv,source,obj):
    argv=list(argv)
    for key,value in [('-c',source),('-o',obj),('-MT',obj),('-MF',str(obj)+'.d')]:
        if key in argv:argv[argv.index(key)+1]=str(value)
    return argv
def audit_pe(path,dll=False):
    data=path.read_bytes();offset=struct.unpack_from('<I',data,0x3c)[0]
    assert data[:2]==b'MZ' and data[offset:offset+4]==b'PE\0\0'
    assert struct.unpack_from('<H',data,offset+4)[0]==0x14c and struct.unpack_from('<H',data,offset+24)[0]==0x10b
    details=subprocess.check_output([str(MINGW/'llvm-objdump'),'-p',str(path)],text=True)
    imports=re.findall(r'DLL Name: (\S+)',details)
    assert imports and all(x.lower()=='kernel32.dll' for x in imports), ('CRT or unexpected imports',imports)
    exports=[];dll_name=None
    if dll:
        count=struct.unpack_from('<H',data,offset+6)[0]
        optional_bytes=struct.unpack_from('<H',data,offset+20)[0]
        sections=offset+24+optional_bytes
        def mapped(rva):
            for i in range(count):
                virtual_bytes,address,raw_bytes,raw=struct.unpack_from('<IIII',data,sections+i*40+8)
                if address<=rva<address+raw_bytes:return raw+rva-address
            raise AssertionError(('unmapped export RVA',rva))
        def string(rva):
            start=mapped(rva);return data[start:data.index(0,start)].decode('ascii')
        export_rva=struct.unpack_from('<I',data,offset+24+96)[0]
        directory=mapped(export_rva)
        dll_name=string(struct.unpack_from('<I',data,directory+12)[0])
        names_count,names_rva=struct.unpack_from('<I',data,directory+24)[0],struct.unpack_from('<I',data,directory+32)[0]
        names=mapped(names_rva)
        exports=[string(struct.unpack_from('<I',data,names+i*4)[0]) for i in range(names_count)]
        assert dll_name=='sdndx.dll' and exports==['SdNdxCall'], ('DLL gate lookup',dll_name,exports)
    return dict(machine='i386',format='PE32',imports=imports,bytes=len(data),sha256=sha(path),exports=exports,dll_export_name=dll_name)
def audit_elf(path):
    header=subprocess.check_output([str(TOOLS/'aarch64-none-elf-readelf'),'-h',str(path)],text=True)
    assert re.search(r'Machine:\s+AArch64',header) and re.search(r'Type:\s+DYN',header)
    symbols=subprocess.check_output([str(TOOLS/'aarch64-none-elf-readelf'),'-Ws',str(path)],text=True)
    defined=set();missing=[]
    for line in symbols.splitlines():
        f=line.split()
        if len(f)<8 or not f[0].endswith(':'):continue
        if f[6]=='UND' and f[4]!='WEAK':missing.append(f[7])
        elif f[6]!='UND':defined.add(f[7])
    required=['wine_nx_sd_ndx_wow64_unix_funcs','wine_nx_sd_ndx_wow64_unix_count','__wine_unix_call_dispatcher_impl','wine_nx_pe_unix_call_dispatcher',
              'virtual_check_buffer_for_read','virtual_check_buffer_for_write','D3D11CreateDevice','sd_ndx_dispatch',
              'vkGetInstanceProcAddr','nvk_CreateDevice','pes13_fex_context_preflight']
    assert not missing, ('unresolved symbols',missing)
    assert all(x in defined for x in required), ('required native/gate symbols',set(required)-defined)
    return dict(status='PASS',machine='AArch64',type='PIE',required_symbols=required,unresolved_nonweak=missing)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-native-dxvk-h2-v1'))
    args=parser.parse_args();assert os.name=='posix'
    work=args.work;work.mkdir(parents=True,exist_ok=True)
    lock=(work/'build.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    objects=work/'objects';objects.mkdir(exist_ok=True)
    local=ROOT/'local/native-dxvk-h2-v1';local.mkdir(parents=True,exist_ok=True)
    pin=json.loads(INPUTS.read_text())
    for kind in ('runtime','virtual'):
        assert sha(pin[kind+'_source'])==pin[kind+'_sha256'], ('Wine source changed',kind)
    assert sha(pin['winternl_header'])==pin['winternl_sha256']
    assert sha(pin['wow64_virtual_source'])==pin['wow64_virtual_sha256']
    assert 'NtQueryVirtualMemory( handle, addr, MemoryWineUnixWow64Funcs, ptr, len, &res_len )' in Path(pin['wow64_virtual_source']).read_text()
    assert re.search(r'MemoryWineUnixFuncs\s*=\s*1000,\s*MemoryWineUnixWow64Funcs,',Path(pin['winternl_header']).read_text())
    assert '#define MEMORY_WINE_UNIX_FUNCS 1000' in (ROOT/'src/native_dxvk_bridge/bridge_guest_dll.c').read_text()
    old_path=ROOT/'local/apc-v18/native.json';assert sha(old_path)==pin['baseline_receipt_sha256']
    old=json.loads(old_path.read_text());cwd=Path(old['working_directory'])
    original_link=old['link_argv'];baseline_elf=Path(original_link[original_link.index('-o')+1])
    assert sha(baseline_elf)==pin['baseline_elf_sha256']
    baseline_nro=ROOT/'local/apc-v18/sleepingdogs-fex.nro';assert sha(baseline_nro)==pin['baseline_nro_sha256']
    inputs={str((cwd/a).resolve() if not Path(a).is_absolute() else Path(a)):sha(cwd/a) for a in original_link if a.endswith(('.obj','.o','.a'))}
    for name,digest in inputs.items():
        if name in old['inputs']:assert digest==old['inputs'][name], ('v18 input changed',name)
    # Reproduce the complete v18 ELF before adding native code. A link map's
    # output pathname is non-semantic; all actual compiled inputs are retained.
    # libnx embeds the output basename in .nx-module-name. Keep it identical
    # when comparing the relink; an owned subdirectory prevents overwriting v18.
    baseline=work/'baseline'/baseline_elf.name;baseline.parent.mkdir(exist_ok=True)
    relink=[('-Wl,-Map='+str(work/'baseline.map') if a.startswith('-Wl,-Map=') else str(baseline) if a==str(baseline_elf) else a) for a in original_link]
    run(relink,work/'baseline.link.log',cwd)
    assert sha(baseline)==pin['baseline_elf_sha256'], 'v18 baseline relink differs'
    dxvk_receipt=ROOT/'local/native-dxvk-probe-v1/build-horizon.json'
    dxvk=json.loads(dxvk_receipt.read_text());library=Path(dxvk['library']);assert sha(library)==dxvk['sha256']
    for name,digest in dxvk['probe_sources'].items():assert sha(ROOT/name)==digest, ('H1 source changed',name)
    for name,digest in dxvk['adapted_files'].items():assert sha(library.parent.parent/'source'/name)==digest
    inputs[str(library)]=sha(library)
    overlay=work/'native-source';overlay.mkdir(exist_ok=True)
    patches={};compile_commands={}
    for kind,relative in [('virtual','dlls/ntdll/unix/virtual.c'),('runtime','wine-nx-probe/source/runtime.c')]:
        before=Path(pin[kind+'_source']).read_text();after=before
        if kind=='virtual':
            after=replace(after,'} wine_nx_static_wow64_unix_libs[] =\n{',
                '} wine_nx_static_wow64_unix_libs[] =\n{\n    { "sdndx.dll", wine_nx_sd_ndx_wow64_unix_funcs, &wine_nx_sd_ndx_wow64_unix_count },')
            anchor='extern const unixlib_entry_t wine_nx_ws2_32_wow64_unix_funcs[];'
            after=replace(after,anchor,'/* H2 diagnostic: existing static WOW64 gate, offscreen only. */\n'
                'extern const unixlib_entry_t wine_nx_sd_ndx_wow64_unix_funcs[];\n'
                'extern const unsigned int wine_nx_sd_ndx_wow64_unix_count;\n'+anchor)
            target='CMakeFiles/wine-virtual-real.dir/home/blekjek/sleepingdogs-low-window-v1/native-source/dlls/ntdll/unix/virtual.c.obj'
            command=shlex.split(subprocess.check_output(['ninja','-C',str(cwd),'-t','commands',target],text=True).strip())
        else:
            after=replace(after,'"sleepingdogs-fextendo-0.1.0-v18-apc"','"sleepingdogs-native-dxvk-h2-v1"')
            after=replace(after,'const int guest_tests = wine_nx_config_file_bool(RUNTIME_DIR "/run-guest-tests.txt", 0);','const int guest_tests = 1; /* H2 standalone PE32 diagnostic */')
            after=replace(after,'"%s/fex-stress.exe"','"%s/sd-native-dxvk-guest.exe"')
            after=replace(after,'    if (guest_tests && !pes13_fex_fault_stress()) park_forever();','    /* H2 uses the context preflight above; no unrelated fault stress. */')
            anchor='    mkdir( WINE_SYSTEM_DIR, 0777 );'
            setup='''
    mkdir(RUNTIME_DIR "/native-dxvk-h2",0777);
    mkdir(RUNTIME_DIR "/native-dxvk-h2/cache",0777);
    fx_debug_file=fopen(RUNTIME_DIR "/native-dxvk-h2/runtime.log","w");
    remove(WINE_DRIVE_C "/native-dxvk-h2-result.json");
    __atomic_store_n(&fx_debug_live,1,__ATOMIC_RELEASE);
    setenv("DXVK_LOG_PATH",RUNTIME_DIR "/native-dxvk-h2",1);
    setenv("DXVK_SHADER_CACHE_PATH",RUNTIME_DIR "/native-dxvk-h2/cache",1);
    setenv("MESA_SHADER_CACHE_DIR",RUNTIME_DIR "/native-dxvk-h2/cache",1);
    setenv("DXVK_CONFIG_FILE",RUNTIME_DIR "/native-dxvk-h2/probe.conf",1);
    FILE *h2_config=fopen(RUNTIME_DIR "/native-dxvk-h2/probe.conf","w");
    if(!h2_config || fprintf(h2_config,"dxvk.numCompilerThreads = 2\\nd3d11.fextendoCoalesceVertexBuffers = False\\n")<0) return 1;
    fclose(h2_config);
    log_line("[SD-NDX-H2] BUILD native-dxvk-h2-v1; PE32/Wine/FEX/native-DXVK; no game, no present");'''
            after=replace(after,anchor,anchor+setup)
            after=replace(after,'consoleInit(NULL); wine_nx_console_active = 1;','consoleInit(NULL); wine_nx_console_active = 1;\n        printf("FEXTendo native DXVK H2\\nPE32 -> Wine/FEX -> ARM64 DXVK\\nOffscreen 1280x720 readback test.\\nSee native-dxvk-h2/runtime.log and drive_c/native-dxvk-h2-result.json.\\n");\n        consoleUpdate(NULL);')
            after=replace(after,'    if(wine_nx_f1_relaunch_request(F1_RETURN_GUEST,code))return;',
                '    printf("\\nH2 guest exited: %08x\\nSee result JSON and logs. Close from HOME.\\n",code);\n    consoleUpdate(NULL);\n    return; /* diagnostic: preserve result and do not relaunch game */\n'+
                '    if(wine_nx_f1_relaunch_request(F1_RETURN_GUEST,code))return;')
            command=old['compile_commands'][relative]
        dst=overlay/relative;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(after,newline='\n')
        patch=work/(kind+'.patch');patch.write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
        patches[kind]=dict(source_sha256=sha(dst),patch_sha256=sha(patch),baseline_sha256=pin[kind+'_sha256'])
        command=rewrite_command(command,dst,objects/(kind+'.obj'))
        compile_commands[kind]=command;run(command,work/(kind+'.compile.log'),cwd)
    flags=['-O2','-std=gnu++17','-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-ffixed-x18',
           '-ftls-model=local-exec','-ffunction-sections','-fdata-sections','-fPIE','-D__SWITCH__','-DNX',
           '-isystem',str(SDK/'libnx/include'),'-isystem',str(SDK/'portlibs/switch/include')]
    command=[str(TOOLS/'aarch64-none-elf-g++'),*flags,'-MD','-MF',str(objects/'bridge.d'),'-c',str(ROOT/'src/native_dxvk_bridge/bridge_host.cpp'),'-o',str(objects/'bridge.obj')]
    compile_commands['bridge']=command;run(command,work/'bridge.compile.log',work)
    for target,compiler,width in [('pe32',MINGW/'i686-w64-mingw32-gcc',4),('arm64',TOOLS/'aarch64-none-elf-gcc',8)]:
        command=[str(compiler),'-std=c11','-DSD_NDX_EXPECT_POINTER_BYTES='+str(width),'-I'+str(ROOT/'src/native_dxvk_bridge'),'-c',str(ROOT/'tests/native_dxvk_bridge_abi.c'),'-o',str(objects/(target+'-abi.o'))]
        compile_commands[target+'-abi']=command;run(command,work/(target+'-abi.log'),work)
    pe=work/'pe';pe.mkdir(exist_ok=True)
    for name,source,dll,entry in [('sdndx.dll','bridge_guest_dll.c',True,'DllMain@12'),('sd-native-dxvk-guest.exe','bridge_guest_main.c',False,'start@0')]:
        command=[str(MINGW/'i686-w64-mingw32-gcc'),'-O2','-std=c11','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-Wl,--no-insert-timestamp','-Wl,--entry,'+entry,'-Wl,--kill-at','-Wl,--subsystem,console']
        if dll:command+=['-shared']
        command+=[str(ROOT/'src/native_dxvk_bridge'/source),'-o',str(pe/name),'-lkernel32']
        compile_commands[name]=command;run(command,work/(name+'.compile.log'),work)
    pe_audits={p.name:audit_pe(p,p.suffix=='.dll') for p in pe.iterdir() if p.suffix in ('.dll','.exe')}
    elf=work/'sleepingdogs-native-dxvk-h2.elf'
    link=[]
    for a in original_link:
        if a.endswith('/runtime.c.obj'):a=str(objects/'runtime.obj')
        if a.startswith('CMakeFiles/wine-virtual-real.dir/'):a=str(objects/'virtual.obj')
        if a==str(baseline_elf):a=str(elf)
        if a.startswith('-Wl,-Map='):a='-Wl,-Map='+str(work/'h2.map')
        link.append(a)
        if a=='-Wl,--start-group':link.extend([str(objects/'bridge.obj'),str(library)])
    run(link,work/'h2.link.log',cwd);elf_audit=audit_elf(elf)
    nacp=work/'app.nacp';nro=work/'sleepingdogs-fex.nro'
    subprocess.run([str(SDK/'tools/bin/nacptool'),'--create','FEXTendo Native DXVK H2','AndroSwitch Project','0.1.0-h2',str(nacp)],check=True)
    subprocess.run([str(SDK/'tools/bin/elf2nro'),str(elf),str(nro),'--nacp='+str(nacp)],check=True)
    data=nro.read_bytes();assert data[0x10:0x14]==b'NRO0'
    for name,digest in inputs.items():assert sha(name)==digest, ('baseline input mutated',name)
    headers={}
    for dependency in objects.glob('*.d'):
        for p in shlex.split(dependency.read_text().replace('\\\n','').split(':',1)[1]):
            h=(cwd/p).resolve() if not Path(p).is_absolute() else Path(p)
            headers[str(h)]=sha(h)
    for p in re.findall(r'^LOAD (.+)$',(work/'h2.map').read_text(),re.M):
        h=(cwd/p.strip()).resolve() if not Path(p.strip()).is_absolute() else Path(p.strip())
        if h.is_file():inputs[str(h)]=sha(h)
    shutil.copy2(nro,local/nro.name)
    for p in pe.iterdir():
        if p.suffix in ('.dll','.exe'):shutil.copy2(p,local/p.name)
    result=dict(status='BUILT',build='native-dxvk-h2-v1',baseline_reproduced=True,baseline_elf_sha256=sha(baseline),
                baseline_nro_sha256=sha(baseline_nro),nro_sha256=sha(nro),nro_bytes=len(data),elf=str(elf),elf_sha256=sha(elf),
                native_dxvk_sha256=sha(library),mesa_sha256=old['driver_library_sha256'],work=str(work),patches=patches,
                compile_commands=compile_commands,link_argv=link,working_directory=str(cwd),inputs=inputs,header_inputs=headers,
                pe_audits=pe_audits,elf_audit=elf_audit,abi_checks=['PE32 4-byte pointers','ARM64 8-byte pointers','identical 64-byte packets'],
                builder_sha256=sha(__file__),input_manifest_sha256=sha(INPUTS),
                source_files={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src/native_dxvk_bridge').iterdir() if p.is_file()},
                hardware_tested=False,guest_execution_tested=False,game_integration=False,game_fps_measured=False,
                scope='single guest caller owns arena; offscreen only; no COM proxy or native swapchain')
    (local/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','build','baseline_reproduced','nro_sha256','nro_bytes','pe_audits','elf_audit','hardware_tested','game_integration']},indent=2))

if __name__=='__main__':main()
