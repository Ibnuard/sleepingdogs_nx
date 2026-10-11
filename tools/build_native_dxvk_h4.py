"""Build native COM DLLs and an isolated Sleeping Dogs H4 runtime overlay.

Requires the pinned v18/H1 prepared inputs. Never modifies the SDK or any
baseline object/source. The same NRO supports COM self-test and native game
selection, retaining both existing x86 renderer choices.
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
from build_native_dxvk_h3 import run, replace, rewrite_command

ROOT=Path(__file__).resolve().parents[1]
SDK=Path('/opt/devkitpro')
A64=SDK/'devkitA64/bin'
MINGW=Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin')
BUILD='native-dxvk-h4-v6'
APP_VERSION='0.1.0-h4.6'
WORK=Path('/home/blekjek/sleepingdogs-'+BUILD)
LOCAL=ROOT/'local'/BUILD
SOURCES=ROOT/'src/native_dxvk_com'
PIN=ROOT/'vendor/wine/native-dxvk-h3-inputs.json'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,newline='\n')
def patch(before,after,path,relative):
    save(path,''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
    return dict(baseline_sha256=hashlib.sha256(before.encode()).hexdigest(),patch_sha256=sha(path),source_sha256=hashlib.sha256(after.encode()).hexdigest())

def overlay_runtime(before):
    text=replace(before,'"sleepingdogs-fextendo-0.1.0-v18-apc"','"sleepingdogs-'+BUILD+'"')
    text=text.replace('fx_renderer_ids[2]','fx_renderer_ids[3]').replace('fx_renderer_names[2]','fx_renderer_names[3]')
    text=replace(text,'{"dxvk-3.1.1","dxvk-2.7.1-async"}','{"dxvk-3.1.1","dxvk-2.7.1-async","dxvk-native-h4"}')
    text=replace(text,'{"DXVK 3.1.1","DXVK 2.7.1 async"}','{"DXVK 3.1.1","DXVK 2.7.1 async","DXVK Native ARM64"}')
    assert text.count('selected>1')==2
    text=text.replace('selected>1','selected>2')
    text=replace(text,'"%s/launcher/renderer-choice.txt",root);\n    return fx_read(p,b,2)==2&&b[0]==\'1\'&&b[1]==\'\\n\';',
                 '"%s/launcher/renderer-choice.txt",root);\n    return fx_read(p,b,2)==2&&b[0]>=\'0\'&&b[0]<=\'2\'&&b[1]==\'\\n\' ? b[0]-\'0\' : 0;')
    text=replace(text,"renderer[0]!='1'","(renderer[0]<'0'||renderer[0]>'2')")
    text=replace(text,'#define FX_APP_VERSION "0.1.0-v18-apc"','#define FX_APP_VERSION "'+APP_VERSION+'"')
    # Add the bridge companion to the same durable transaction as both graphics
    # DLLs. Separate the eight-bit journal from existing five/seven-bit updates.
    text=replace(text,'fx_renderer_targets[7]','fx_renderer_targets[8]')
    text=replace(text,'"/drive_c/SleepingDogs/d3d11.dll","/drive_c/SleepingDogs/dxgi.dll"};',
                 '"/drive_c/SleepingDogs/d3d11.dll","/drive_c/SleepingDogs/dxgi.dll","/drive_c/SleepingDogs/sdndx4.dll"};')
    text=replace(text,'fx_renderer_sources[4]={"d3d9.dll","dxvk.conf","d3d11.dll","dxgi.dll"}',
                 'fx_renderer_sources[5]={"d3d9.dll","dxvk.conf","d3d11.dll","dxgi.dll","sdndx4.dll"}')
    text=replace(text,'fx_renderer_source_index[7]={0,0,1,1,-1,2,3}',
                 'fx_renderer_source_index[8]={0,0,1,1,-1,2,3,4}')
    text=replace(text,'fx_renderer_recover_journal(root,"renderer-dx11.txn",7);',
                 'fx_renderer_recover_journal(root,"renderer-dx11.txn",7)&&\n           fx_renderer_recover_journal(root,"renderer-native-com.txn",8);')
    text=replace(text,'st.st_size<1024*1024||st.st_size>32*1024*1024',
                 'st.st_size<(selected==2?1024:1024*1024)||st.st_size>32*1024*1024')
    start=text.index('static int fx_apply_renderer(const char *root,int selected) {')
    end=text.index('\n#endif',start)
    transaction=text[start:end].replace('[4][768]','[5][768]').replace('[7][','[8][').replace('i<4','i<5').replace('i<7','i<8')
    transaction=transaction.replace('fx_renderer_ids[selected],fx_renderer_sources[i]',
                                    'fx_renderer_ids[i==4?2:selected],fx_renderer_sources[i]')
    transaction=transaction.replace('fx_renderer_valid(source[i],source[1],selected)',
                                    'fx_renderer_valid(source[i],source[1],i==4?2:selected)')
    transaction=transaction.replace('renderer-dx11.txn','renderer-native-com.txn')
    text=text[:start]+transaction+text[end:]
    text=replace(text,'extern void wine_nx_runtime_platform_init(void);',
        'extern void sd_com_shutdown(void);\nextern void sd_com_progress_report(void);\nextern void *sd_com_native_window(void);\nstatic int sd_com_enabled,sd_com_diagnostic;\nextern void wine_nx_runtime_platform_init(void);')
    # Disk writes must not hold the native COM gate. The existing maintenance
    # thread drains a bounded queue; its file lock is never taken by producers.
    text=replace(text,'static void *log_flusher( void *arg )',
        '#include "native_log_queue.h"\n'
        'static void sd_native_log_write(const char *data,size_t bytes,void *unused) {\n'
        '    (void)unused;pthread_mutex_lock(&fx_debug_file_lock);\n'
        '    if(fx_debug_file){fwrite(data,1,bytes,fx_debug_file);fflush(fx_debug_file);}\n'
        '    pthread_mutex_unlock(&fx_debug_file_lock);\n'
        '}\n\nstatic void *log_flusher( void *arg )')
    text=replace(text,'        fx_production_maintenance_tick(++ticks);',
        '        if(__atomic_load_n(&sd_com_enabled,__ATOMIC_ACQUIRE) && __atomic_load_n(&fx_debug_live,__ATOMIC_ACQUIRE))sd_native_log_drain(sd_native_log_write,NULL);\n'
        '        fx_production_maintenance_tick(++ticks);')
    text=replace(text,'    pthread_mutex_lock(&fx_debug_file_lock);\n    if (fx_debug_file)',
        '    if(__atomic_load_n(&sd_com_enabled,__ATOMIC_ACQUIRE)){sd_native_log_enqueue(line);return;}\n'
        '    pthread_mutex_lock(&fx_debug_file_lock);\n    if (fx_debug_file)')
    text=replace(text,'        unsigned presented = __atomic_load_n(&fx_first_present, __ATOMIC_ACQUIRE);',
        '        if(__atomic_load_n(&sd_com_enabled,__ATOMIC_ACQUIRE)){sd_com_progress_report();continue;} /* native compact monitor; no bulk observer */\n'
        '        unsigned presented = __atomic_load_n(&fx_first_present, __ATOMIC_ACQUIRE);')
    # Native DXVK bypasses Wine's GL/Vulkan surface acquisition. Explicitly use
    # the existing joined launcher handoff, and keep later Wine/GDI surfaces
    # from taking the same default NWindow during native COM rendering.
    text=replace(text,'    if (fx_owned()) return -1;','    if (sd_com_enabled || fx_owned()) return -1;')
    text=replace(text,'    if (fx_owned()) return NULL;','    if (sd_com_enabled || fx_owned()) return NULL;')
    text=replace(text,'    if (fx_owned() || !wine_nx_compositor_mode) return 0;',
                 '    if (sd_com_enabled || fx_owned() || !wine_nx_compositor_mode) return 0;')
    text=replace(text,'    if (!fx_handoff()) return NULL;','    if (sd_com_enabled || !fx_handoff()) return NULL;')
    anchor='/* Whether the compositor presents the screen, starting it on the first call.'
    text=replace(text,anchor,'''/* H4 native COM owns the default NWindow before starting the guest. */
static int sd_com_prepare_screen(void) {
    if(!fx_handoff()) {
        log_line("[SD-NDX-WINDOW] FAIL stage=launcher-handoff");return 0;
    }
    wine_nx_screen_leave_console();
    log_line("[SD-NDX-WINDOW] handoff complete launcher_owned=%d console_active=%d",fx_owned(),wine_nx_console_active);
    return sd_com_native_window()!=NULL;
}

'''+anchor)
    # This callback marks actual native COM Present, without attributing its
    # total D3D call time to the old Vulkan-driver timing counters.
    anchor='static void fx_record_first_present(void) {'
    text=replace(text,anchor,anchor)
    marker='static void fx_native_error(const char *message) {'
    text=replace(text,marker,'void wine_nx_sd_com_first_present(void) { fx_record_first_present(); }\n\n'+marker)
    text=replace(text,'            wine_nx_lsfg_configure(lsfg.enabled,lsfg.performance,lsfg.flow);',
        '            __atomic_store_n(&sd_com_enabled,renderer==2,__ATOMIC_RELEASE);\n            wine_nx_lsfg_configure(sd_com_enabled?0:lsfg.enabled,lsfg.performance,lsfg.flow);\n'
        '            if(sd_com_enabled)log_line("[SD-NDX-COM] game selection native ARM64; LSFG OFF; measured FPS pending");')
    text=replace(text,'    if(wine_nx_f1_relaunch_request(F1_RETURN_GUEST,code))return;',
        '    if(sd_com_enabled)sd_com_shutdown();\n'
        '    if(sd_com_diagnostic){consoleInit(NULL);wine_nx_console_active=1;printf("\\nH4 COM test exited: %08x\\nSee drive_c/native-dxvk-h4-result.json. Close from HOME.\\n",code);consoleUpdate(NULL);return;}\n'
        '    if(wine_nx_f1_relaunch_request(F1_RETURN_GUEST,code))return;')
    text=replace(text,'    const int guest_tests = wine_nx_config_file_bool(RUNTIME_DIR "/run-guest-tests.txt", 0);',
        '    sd_com_diagnostic=wine_nx_config_file_bool(RUNTIME_DIR "/run-native-com-test.txt",0);\n'
        '    const int guest_tests = sd_com_diagnostic || wine_nx_config_file_bool(RUNTIME_DIR "/run-guest-tests.txt", 0);')
    text=replace(text,'    if (guest_tests) snprintf(target, sizeof(target), "%s/fex-stress.exe", WINE_DRIVE_C);',
        '    if (guest_tests) snprintf(target, sizeof(target), "%s/%s", WINE_DRIVE_C,sd_com_diagnostic?"sd-native-dxvk-h4-test.exe":"fex-stress.exe");\n'
        '    if(sd_com_diagnostic){\n'
        '        if(!fx_apply_renderer(RUNTIME_DIR,2)||!fx_apply_preset(RUNTIME_DIR,fx_selected(RUNTIME_DIR))){log_line("[SD-NDX-COM] diagnostic renderer install failed");return 1;}\n'
        '        __atomic_store_n(&sd_com_enabled,1,__ATOMIC_RELEASE);wine_nx_lsfg_configure(0,1,0);\n'
        '    }\n'
        '    if(sd_com_enabled){\n'
        '        mkdir(RUNTIME_DIR "/native-dxvk-h4",0777);mkdir(RUNTIME_DIR "/native-dxvk-h4/cache",0777);\n'
        '        if(sd_com_diagnostic){fx_debug_file=fopen(RUNTIME_DIR "/native-dxvk-h4/runtime.log","w");__atomic_store_n(&fx_debug_live,1,__ATOMIC_RELEASE);}\n'
        '        setenv("DXVK_WSI_DRIVER","FEXTendoProbe",1);setenv("DXVK_LOG_PATH",RUNTIME_DIR "/native-dxvk-h4",1);\n'
        '        setenv("DXVK_CONFIG_FILE",sd_com_diagnostic?RUNTIME_DIR "/native-dxvk-h4/com-test.conf":WINE_DRIVE_C "/SleepingDogs/dxvk.conf",1);\n'
        '        setenv("DXVK_SHADER_CACHE_PATH",RUNTIME_DIR "/native-dxvk-h4/cache",1);setenv("MESA_SHADER_CACHE_DIR",RUNTIME_DIR "/native-dxvk-h4/cache",1);\n'
        '        log_line("[SD-NDX-COM] BUILD '+BUILD+' mode=%s target=%s; x86 COM to ARM64 DXVK",sd_com_diagnostic?"COM-self-test":"SleepingDogs",target);\n'
        '        log_line("[SD-NDX-LOG] async queue=512 batch=32; native progress=5s; bulk observer disabled; missing tail possible after forced restart");\n'
        '        log_line("[SD-NDX-PERF] progress_stride=256 critical_calls=full stats_clock_stride=1024; sampled call state is not every active call");\n'
        '        if(!sd_com_diagnostic)wine_nx_f1_crash_note("[SD-NDX-COM] build='+BUILD+' renderer=DXVK Native ARM64");\n'
        '        if(!sd_com_prepare_screen()){log_line("[SD-NDX-COM] FAIL trusted native window");return 1;}\n'
        '    }')
    text=replace(text,'    if (guest_tests && !pes13_fex_fault_stress()) park_forever();','    if (guest_tests && !sd_com_diagnostic && !pes13_fex_fault_stress()) park_forever();')
    text=replace(text,'setenv("WINEDLLOVERRIDES", "d3d9,d3d11,dxgi=n,b", 1)',
                 'setenv("WINEDLLOVERRIDES", sd_com_enabled?"d3d11,dxgi,sdndx4=n;d3d9=n,b":"d3d9,d3d11,dxgi=n,b", 1)')
    # Also enforce native-only loading in the actual guest PEB. Preserve the
    # chosen JIT/disk-cache environment and remove its older duplicate key.
    text=replace(text,'    chars += environment_bytes;',
        '    if(sd_com_enabled){\n'
        '        static char native_environment[8192];size_t used=0;\n'
        '        for(const char *entry=environment;entry<environment+environment_bytes && *entry;entry+=strlen(entry)+1){\n'
        '            size_t length=strlen(entry)+1;if(!strncmp(entry,"WINEDLLOVERRIDES=",17))continue;\n'
        '            if(used+length+64>=sizeof(native_environment))return NULL;\n'
        '            memcpy(native_environment+used,entry,length);used+=length;\n'
        '        }\n'
        '        const char overrides[]="WINEDLLOVERRIDES=d3d11,dxgi,sdndx4=n;d3d9=n,b\\0";\n'
        '        memcpy(native_environment+used,overrides,sizeof(overrides));used+=sizeof(overrides);\n'
        '        environment=native_environment;environment_bytes=used;\n'
        '    }\n'
        '    chars += environment_bytes;')
    return text

def pe_audit(path):
    data=path.read_bytes();offset=struct.unpack_from('<I',data,0x3c)[0]
    assert data[:2]==b'MZ' and data[offset:offset+4]==b'PE\0\0'
    assert struct.unpack_from('<H',data,offset+4)[0]==0x14c and struct.unpack_from('<H',data,offset+24)[0]==0x10b
    details=subprocess.check_output([str(MINGW/'llvm-objdump'),'-p',str(path)],text=True)
    imports=re.findall(r'DLL Name: (\S+)',details)
    assert all(x.lower() in ('kernel32.dll','user32.dll','sdndx4.dll') for x in imports),imports
    exports=re.findall(r'^\s*\d+\s+0x[0-9a-f]+\s+(\w+)\s*$',details,re.M)
    return dict(machine='i386',format='PE32',imports=imports,bytes=len(data),sha256=sha(path),exports=exports)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=WORK)
    parser.add_argument('--pe-only',action='store_true')
    args=parser.parse_args();assert os.name=='posix'
    work=args.work;work.mkdir(parents=True,exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
    lock=(work/'build.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    objects=work/'objects';objects.mkdir(exist_ok=True);pe=work/'pe';pe.mkdir(exist_ok=True)
    run(['python3',ROOT/'tools/generate_native_dxvk_com.py'],work/'generate.log',ROOT)
    commands={}
    targets=[('sdndx4.dll','com_guest.c',True),('d3d11.dll','d3d11_guest.c',True),('dxgi.dll','dxgi_guest.c',True),('sd-native-dxvk-h4-test.exe','com_guest_test.c',False)]
    for name,source,dll in targets:
        command=[str(MINGW/'i686-w64-mingw32-gcc'),'-O2','-std=c11','-DINITGUID','-DSD_COM_BUILD="'+BUILD+'"','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib',
                 '-Wl,--no-insert-timestamp','-Wl,--kill-at','-Wl,--entry,'+('DllMain@12' if dll else 'start@0')]
        if dll:command+=['-shared']
        if name=='sdndx4.dll':command+=['-Wl,--out-implib,'+str(pe/'sdndx4.a')]
        command+=[str(SOURCES/source),'-o',str(pe/name)]
        if name in ('d3d11.dll','dxgi.dll'):command+=[str(pe/'sdndx4.a')]
        command+=['-lkernel32']
        if name=='sdndx4.dll':command+=['-luser32']
        commands[name]=command;run(command,work/(name+'.compile.log'),work)
    audits={name:pe_audit(pe/name) for name,_,_ in targets}
    if args.pe_only:print(json.dumps(audits,indent=2));return
    pin=json.loads(PIN.read_text());old=json.loads((ROOT/'local/apc-v18/native.json').read_text());cwd=Path(old['working_directory'])
    for kind in ('runtime','virtual'):assert sha(pin[kind+'_source'])==pin[kind+'_sha256'],kind
    assert sha(ROOT/'local/apc-v18/native.json')==pin['baseline_receipt_sha256']
    original_link=old['link_argv'];baseline_elf=Path(original_link[original_link.index('-o')+1]);assert sha(baseline_elf)==pin['baseline_elf_sha256']
    inputs={str((cwd/a).resolve() if not Path(a).is_absolute() else Path(a)):sha(cwd/a) for a in original_link if a.endswith(('.obj','.o','.a'))}
    baseline=work/'baseline'/baseline_elf.name;baseline.parent.mkdir(exist_ok=True)
    relink=[('-Wl,-Map='+str(work/'baseline.map') if a.startswith('-Wl,-Map=') else str(baseline) if a==str(baseline_elf) else a) for a in original_link]
    run(relink,work/'baseline.link.log',cwd);assert sha(baseline)==pin['baseline_elf_sha256']
    native_source=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1/source')
    h1=json.loads((ROOT/'local/native-dxvk-probe-v1/build-horizon.json').read_text());library=Path(h1['library']);assert sha(library)==h1['sha256']
    overlay=work/'native-source';overlay.mkdir(exist_ok=True);patches={}
    for kind,relative in [('runtime','wine-nx-probe/source/runtime.c'),('virtual','dlls/ntdll/unix/virtual.c')]:
        before=Path(pin[kind+'_source']).read_text()
        if kind=='runtime':
            after=overlay_runtime(before);command=old['compile_commands'][relative]
            log_header=overlay/'wine-nx-probe/source/native_log_queue.h';log_header.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(SOURCES/'native_log_queue.h',log_header)
            settings_path=Path(pin['runtime_source']).parent/'f1_settings.h';settings=settings_path.read_text()
            settings_after=replace(settings,'{7,5,2,3,2,3,2}','{7,5,3,3,2,3,2}')
            settings_after=replace(settings_after,'return row?"Async shader compilation  /  Alternative renderer":"Default renderer";',
                'return row==2?"Native ARM64 graphics / experimental":row?"Async shader compilation  /  Alternative renderer":"Default renderer";')
            save(overlay/'wine-nx-probe/source/f1_settings.h',settings_after)
            patches['settings']=patch(settings,settings_after,work/'settings.patch','wine-nx-probe/source/f1_settings.h')
        else:
            anchor='extern const unixlib_entry_t wine_nx_ws2_32_wow64_unix_funcs[];'
            after=replace(before,anchor,'extern const unixlib_entry_t wine_nx_sd_com_wow64_unix_funcs[];\nextern const unsigned int wine_nx_sd_com_wow64_unix_count;\n'+anchor)
            after=replace(after,'} wine_nx_static_wow64_unix_libs[] =\n{','} wine_nx_static_wow64_unix_libs[] =\n{\n    { "sdndx4.dll", wine_nx_sd_com_wow64_unix_funcs, &wine_nx_sd_com_wow64_unix_count },')
            target='CMakeFiles/wine-virtual-real.dir/home/blekjek/sleepingdogs-low-window-v1/native-source/dlls/ntdll/unix/virtual.c.obj'
            command=shlex.split(subprocess.check_output(['ninja','-C',str(cwd),'-t','commands',target],text=True).strip())
        dst=overlay/relative;save(dst,after);patches[kind]=patch(before,after,work/(kind+'.patch'),relative)
        command=rewrite_command(command,dst,objects/(kind+'.obj'));commands[kind]=command;run(command,work/(kind+'.compile.log'),cwd)
    flags=['-O2','-std=gnu++17','-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-ffixed-x18','-ftls-model=local-exec','-ffunction-sections','-fdata-sections','-fPIE','-D__SWITCH__','-DNX',
        '-isystem',str(SDK/'libnx/include'),'-isystem',str(SDK/'portlibs/switch/include')]
    includes=[native_source/'include/native/windows',native_source/'include/native/directx',native_source/'include/native',native_source/'include']
    for kind,source in [('com','com_native.cpp'),('horizon','com_horizon.cpp')]:
        command=[str(A64/'aarch64-none-elf-g++'),*flags,*['-I'+str(p) for p in includes],'-MD','-MF',str(objects/(kind+'.d')),'-c',str(SOURCES/source),'-o',str(objects/(kind+'.obj'))]
        commands[kind]=command;run(command,work/(kind+'.compile.log'),work)
    # Give native DXVK the real application profile and record its host workers.
    env_source=native_source/'src/util/util_env.cpp';env_before=env_source.read_text()
    env_after=replace(env_before,'return "sd-dxvk-native-probe";','return "HKShip.exe";')
    env_after=replace(env_after,'    (void)posixName; // libnx has no optional POSIX thread-name API.',
        '    sd_com_native_worker(posixName.data());')
    env_after=replace(env_after,'#include "util_env.h"','#include "util_env.h"\n#ifdef __SWITCH__\nextern "C" void sd_com_native_worker(const char*);\n#endif')
    env_target=overlay/'dxvk/src/util/util_env.cpp';save(env_target,env_after)
    patches['dxvk-env']=patch(env_before,env_after,work/'dxvk-env.patch','src/util/util_env.cpp')
    compile_db=json.loads((library.parent/'compile_commands.json').read_text())
    env_compile=next(x for x in compile_db if Path(x['file'])==env_source)
    env_command=shlex.split(env_compile['command']);old_object=env_command[env_command.index('-o')+1]
    env_object=objects/Path(old_object).name;env_command=rewrite_command(env_command,env_target,env_object)
    # Relative quote includes in the copied source need its original parent.
    env_command.insert(1,'-I'+str(env_source.parent));commands['dxvk-env']=env_command;run(env_command,work/'dxvk-env.compile.log',Path(env_compile['directory']))
    native_library=work/'libsd_native_dxvk_com.a';shutil.copyfile(library,native_library)
    members=subprocess.check_output([str(A64/'aarch64-none-elf-ar'),'t',str(native_library)],text=True).splitlines();assert members.count(env_object.name)==1
    subprocess.run([str(A64/'aarch64-none-elf-ar'),'r',str(native_library),str(env_object)],check=True)
    elf=work/'sleepingdogs-native-dxvk-h4.elf';link=[]
    for argument in original_link:
        if argument.endswith('/runtime.c.obj'):argument=str(objects/'runtime.obj')
        if argument.startswith('CMakeFiles/wine-virtual-real.dir/'):argument=str(objects/'virtual.obj')
        if argument==str(baseline_elf):argument=str(elf)
        if argument.startswith('-Wl,-Map='):argument='-Wl,-Map='+str(work/'h4.map')
        link.append(argument)
        if argument=='-Wl,--start-group':link += [str(objects/'com.obj'),str(objects/'horizon.obj'),str(native_library)]
    run(link,work/'h4.link.log',cwd)
    symbols=subprocess.check_output([str(A64/'aarch64-none-elf-readelf'),'-Ws',str(elf)],text=True)
    missing=[line for line in symbols.splitlines() if len(line.split())>=8 and ' UND ' in line and ' WEAK ' not in line]
    assert not missing,missing
    for required in ('wine_nx_sd_com_wow64_unix_funcs','sd_com_shutdown','sd_com_progress_report','sd_com_native_window','sd_com_presented','sd_com_native_worker','wine_nx_sd_com_first_present','D3D11CreateDevice','vkGetInstanceProcAddr','nvk_CreateDevice'):
        assert re.search(r'\b'+required+r'\s*$',symbols,re.M),required
    nacp=work/'app.nacp';nro=work/'sleepingdogs-fex.nro'
    subprocess.run([str(SDK/'tools/bin/nacptool'),'--create','FEXTendo Native DXVK H4','AndroSwitch Project',APP_VERSION,str(nacp)],check=True)
    subprocess.run([str(SDK/'tools/bin/elf2nro'),str(elf),str(nro),'--nacp='+str(nacp)],check=True)
    for name,digest in inputs.items():assert sha(name)==digest,('baseline changed',name)
    assert sha(library)==h1['sha256']
    headers={}
    for dependency in objects.glob('*.d'):
        for name in shlex.split(dependency.read_text().replace('\\\n','').split(':',1)[1]):
            path=(cwd/name).resolve() if not Path(name).is_absolute() else Path(name)
            if path.is_file():headers[str(path)]=sha(path)
    for file in [nro,*[pe/name for name,_,_ in targets]]:shutil.copy2(file,LOCAL/file.name)
    inventory=json.loads((SOURCES/'com_inventory.json').read_text())
    receipt=dict(status='BUILT',build=BUILD,work=str(work),baseline_reproduced=True,baseline_elf_sha256=sha(baseline),baseline_nro_sha256=pin['baseline_nro_sha256'],
        nro_sha256=sha(nro),nro_bytes=nro.stat().st_size,elf=str(elf),elf_sha256=sha(elf),native_dxvk_sha256=sha(native_library),native_dxvk_baseline_sha256=sha(library),
        interface_count=inventory['interface_count'],vtable_entries=inventory['vtable_entries'],pe_audits=audits,patches=patches,compile_commands=commands,link_argv=link,working_directory=str(cwd),
        inputs=inputs,header_inputs=headers,builder_sha256=sha(__file__),input_manifest_sha256=sha(PIN),source_files={str(p.relative_to(ROOT)):sha(p) for p in SOURCES.iterdir() if p.is_file()},
        software_game_route_implemented=True,hardware_tested=False,com_guest_execution_tested=False,game_integration_tested=False,game_fps_measured=False)
    save(LOCAL/'build.json',json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('status','build','nro_sha256','nro_bytes','interface_count','vtable_entries','hardware_tested','game_integration_tested')},indent=2))

if __name__=='__main__':main()
