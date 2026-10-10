"""Build the isolated 39-bit/low-window NRO, preserving the scene FEX/DXVK pair."""
from pathlib import Path
import argparse, json, shutil, struct, subprocess, zipfile
from port_common import ROOT, TITLE, VERSION, sha, write_json
from build_dxvk_memory import manifest
from f1_overlay import exact
import f1_base_build as base

BASE=Path('/home/blekjek/sleepingdogs-scene-memory-v1')
ZIP=ROOT/'dist/sleepingdogs-fex-buffer-reuse-fix.zip'
BASE_ZIP_SHA='6a9cdfcb39abe3682909057befcdb0b7a0e38c9e960ec2326b49b9f833d457d2'

def overlay(source,work):
    native=source/'wine-nx-probe/source'
    for name in ('sd_low_window.c','sd_low_window.h','sd_alias_arena_init.inc','sd_launch_memory.c'):
        shutil.copy2(ROOT/'src/low_window'/name,native/name)
    p=native/'sd_guest_arena.c'; s=p.read_text()
    s=exact(s,'#include "sd_guest_arena.h"','#include "sd_guest_arena.h"\n#include "sd_low_window.h"')
    s=s[:s.index('void sd_guest_arena_init(void)')]+'#include "sd_alias_arena_init.inc"\n'
    start=s.index('/* SPDX-License-Identifier:'); end=s.index('#include')
    s='/* SPDX-License-Identifier: LGPL-2.1-or-later\n * Data-only low alias backed by one high native heap allocation. */\n'+s[end:]
    p.write_text(s)
    p=native/'sd_guest_arena.h'; s=p.read_text(); start=s.index('/* One ordinary-heap'); end=s.index('void sd_guest_arena_init')
    p.write_text(s[:start]+'/* Low guest alias of retained high backing; serialized by Wine virtual_mutex. */\n'+s[end:])
    p=native/'fextendo_virtmem.c'; s=p.read_text()
    s=exact(s,'#include <stdint.h>','#include <stdint.h>\n#include "sd_low_window.h"')
    s=exact(s,'\n}\n\nvoid virtmemLock(void)', '''
    /* Low-window kernel reports the full alias-code span to Wine. Native
     * libnx mappings must exclude all guest addresses from the first use. */
    if (sd_is_low_window(g_AslrRegion.start,g_AslrRegion.end-g_AslrRegion.start)) {
        g_AslrRegion.start=SD_NATIVE_BASE;
        if (g_StackRegion.start<SD_NATIVE_BASE) g_StackRegion.start=SD_NATIVE_BASE;
    }
}

void virtmemLock(void)''')
    p.write_text(s)
    p=native/'runtime.c'; s=p.read_text()
    s=exact(s,'#include "sd_guest_arena.h"','#include "sd_guest_arena.h"\n#include "sd_low_window.h"')
    s=exact(s,'sleepingdogs-fextendo-0.1.0-32bit-dx11','sleepingdogs-fextendo-0.1.0-low-window-v2-dx11')
    s=exact(s,'    if (guest_tests) { consoleInit(NULL); wine_nx_console_active = 1; }', '''    if (guest_tests) {
        char memory_error[192];
        consoleInit(NULL); wine_nx_console_active = 1;
        if (!sd_launch_memory_prepare(memory_error,sizeof(memory_error))) {
            fx_native_error(memory_error); return 1;
        }
    }''')
    s=exact(s,'    wine_nx_f1_native_stacks_init();\n    sd_guest_arena_init();\n', '')
    # fx_launcher_start waits for Play and validates readiness before returning.
    # Initialization after that call can never satisfy the launch gate.
    s=exact(s,'''        if(ready){
            Result a=svcGetInfo(&sd_host_start,InfoType_AslrRegionAddress,CUR_PROCESS_HANDLE,0);''', '''        if(ready){
            ready=sd_launch_memory_prepare(thread_error,sizeof(thread_error));
            Result a=svcGetInfo(&sd_host_start,InfoType_AslrRegionAddress,CUR_PROCESS_HANDLE,0);''')
    start=s.index('            log_line("[SD-ADDRESS] host='); end=s.index('\n        if(ready&&!wine_nx_f1_prepare_threads',start)
    s=s[:start]+'''            log_line("[SD-ADDRESS] low-window-v2 host=%llx+%llx query=%08x/%08x probe=%u arena=%zu",
                     sd_host_start,sd_host_size,a,b,sd_low_window_ready(),sd_guest_arena_size());
            if(!ready){
                launch_error=thread_error;
                log_line("[SD-LAUNCH] %s",thread_error);
            }
        }''' + s[end:]
    p.write_text(s)
    p=source/'dlls/ntdll/unix/sd_guest_view.inc'; s=p.read_text()
    s=s.replace('guest and backing share one address range','low guest alias; high backing; one physical copy')
    s=s.replace('native heap neighbours excluded','native heap neighbours excluded')
    s+='''
static NTSTATUS sd_register_low_arena(void)
{
    NTSTATUS status;
    if (sd_direct_view) return STATUS_SUCCESS;
    if (!sd_guest_arena_base()) return STATUS_NO_MEMORY;
    status=create_view(&sd_direct_view,sd_guest_arena_base(),sd_guest_arena_size(),VPROT_SYSTEM);
    if (!status) wine_nx_runtime_trace("[SD-ALIAS] low arena Wine guard registered before guest allocations");
    return status;
}
'''; p.write_text(s)
    p=source/'dlls/ntdll/unix/virtual.c'; s=p.read_text()
    s=exact(s,'    horizon_reserve_guest_address_space();', '''    if (sd_register_low_arena()) {
        horizon_trace("[SD-ALIAS] cannot register low arena guard; stopping");
        abort();
    }
    horizon_reserve_guest_address_space();'''); p.write_text(s)
    p=source/'wine-nx-probe/CMakeLists.txt'; s=p.read_text().replace(str(BASE),str(work))
    p.write_text(s+'\ntarget_sources(wine-nx-runtime PRIVATE source/sd_low_window.c source/sd_launch_memory.c)\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--output',type=Path,default=ROOT/'dist/low-window-launch-order-fix')
    p.add_argument('--symbols',type=Path,default=ROOT/'local/symbols/sleepingdogs-low-window-v2.elf')
    p.add_argument('--loading-watch',action='store_true',help='Build bounded post-present Debug observations; use separate output and symbols')
    p.add_argument('--sync-watch',action='store_true',help='Add semaphore lifecycle/first-invalid evidence; requires --loading-watch and separate v4 output')
    p.add_argument('--refresh-overlay',action='store_true',help='Verify tracked work, then reapply edited overlay from pinned baseline')
    a=p.parse_args()
    if a.sync_watch:
        assert a.loading_watch, '--sync-watch requires --loading-watch'
        assert a.output.resolve() != (ROOT/'dist/low-window-loading-watch').resolve(), 'Preserve v3 NRO'
        assert a.symbols.resolve() != (ROOT/'local/symbols/sleepingdogs-low-window-v3.elf').resolve(), 'Preserve v3 symbols'
    if a.loading_watch:
        assert a.output.resolve() != (ROOT/'dist/low-window-launch-order-fix').resolve(), 'Preserve the v2 release output'
        assert a.symbols.resolve() != (ROOT/'local/symbols/sleepingdogs-low-window-v2.elf').resolve(), 'Preserve the v2 symbols'
    def apply_overlay(source,work):
        overlay(source,work)
        if a.loading_watch:
            import low_window_loading
            low_window_loading.overlay(source)
        if a.sync_watch:
            import low_window_sync
            low_window_sync.overlay(source)
    work=a.work;work.mkdir(parents=True,exist_ok=True); source=work/'native-source'
    out=a.output;out.mkdir(parents=True,exist_ok=True)
    assert sha(ZIP)==BASE_ZIP_SHA
    with zipfile.ZipFile(ZIP) as z:
        receipt=json.loads(z.read('source/scene-memory-fix/native.json'))
        for name,digest in receipt['source_files'].items(): assert sha(BASE/'native-source'/name)==digest,name
        for name,digest in receipt['adapter_files'].items(): assert sha(BASE/'fex-adapter'/name)==digest,name
    stamp=work/'low-window-prepared.json'
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'tools/f1_base_build.py',
        *(ROOT/'src/low_window'/n for n in ('sd_low_window.c','sd_low_window.h','sd_alias_arena_init.inc','sd_launch_memory.c'))]}
    if a.loading_watch:
        from low_window_loading import INPUTS
        inputs.update({name:sha(ROOT/name) for name in INPUTS})
    if a.sync_watch:
        from low_window_sync import INPUTS
        inputs.update({name:sha(ROOT/name) for name in INPUTS})
    if not stamp.exists():
        assert not source.exists(), 'Use a fresh source work tree'
        for name in ('native-source','fex-adapter','native-heap','gpu-heap'):
            shutil.copytree(BASE/name,work/name,symlinks=True)
        for name in ('native-heap-binding.json','gpu-heap-binding.json'):
            shutil.copy2(BASE/name,work/name)
        original=manifest(source); apply_overlay(source,work)
        write_json(stamp,{'inputs':inputs,'base_zip_sha256':BASE_ZIP_SHA,'baseline_source':original,
            'source':manifest(source),'adapter':manifest(work/'fex-adapter')})
    prepared=json.loads(stamp.read_text())
    if a.refresh_overlay:
        assert manifest(source)==prepared['source']
        for name,digest in prepared['source'].items():
            if prepared['baseline_source'].get(name)==digest:continue
            target=source/name
            if name in prepared['baseline_source']:
                assert sha(BASE/'native-source'/name)==prepared['baseline_source'][name]
                shutil.copy2(BASE/'native-source'/name,target)
            else:
                assert name.startswith('wine-nx-probe/source/sd_') and target.is_file()
                target.unlink()
        apply_overlay(source,work)
        prepared['source']=manifest(source);prepared['inputs']=inputs
        write_json(stamp,prepared)
    assert prepared['inputs']==inputs
    assert manifest(source)==prepared['source'] and manifest(work/'fex-adapter')==prepared['adapter']
    # Keep exactly the proven launcher artwork/metadata without restoring deleted dist trees.
    old=(BASE/'sleepingdogs-fex.nro').read_bytes(); assert sha(BASE/'sleepingdogs-fex.nro')==receipt['nro_sha256']
    nro_size=struct.unpack_from('<I',old,0x18)[0]
    icon_off,icon_len,nacp_off,nacp_len=struct.unpack_from('<4Q',old,nro_size+8)
    icon=work/'nro-icon.jpg';icon.write_bytes(old[nro_size+icon_off:nro_size+icon_off+icon_len])
    nacp=work/'sleepingdogs-fex.nacp';nacp.write_bytes(old[nro_size+nacp_off:nro_size+nacp_off+nacp_len])
    with (work/'native-build.log').open('w') as log:
        # Builder writes routine commands to stdout; compiler output remains in the log.
        import contextlib
        original_run=base.run
        def logged_run(command,**kwargs):
            kwargs.setdefault('stdout',log);kwargs.setdefault('stderr',subprocess.STDOUT)
            return original_run(command,**kwargs)
        base.run=logged_run
        with contextlib.redirect_stdout(log): elf,_=base.build_nro(work,source,Path('/home/blekjek/pes13-build'),a.jobs,icon=icon)
    nro=work/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro',str(elf),str(nro),'--nacp='+str(nacp),'--icon='+str(icon)],check=True)
    build_marker=b'low-window-v5-sync-startup-fix' if a.sync_watch else b'low-window-v3-load-watch' if a.loading_watch else b'low-window-v2-dx11'
    for marker in (b'[SD-LOWVA] v1',b'[SD-ALIAS] v1',b'[SD-INIT] v2',build_marker,b'fastest',b'[SD-GPU-PRESSURE] v1'):
        assert marker in nro.read_bytes(),marker
    shutil.copy2(nro,out/nro.name)
    a.symbols.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(elf,a.symbols)
    changes={n:h for n,h in prepared['source'].items() if prepared['baseline_source'].get(n)!=h}
    write_json(out/'native.json',{'build':'sleepingdogs-low-window-v5-sync-startup-fix' if a.sync_watch else 'sleepingdogs-low-window-v3-loading-watch' if a.loading_watch else 'sleepingdogs-low-window-v2-launch-order','nro_sha256':sha(nro),'elf_sha256':sha(elf),'build_inputs':inputs,
        'base_zip_sha256':BASE_ZIP_SHA,'source_changes':changes,'source_files':prepared['source'],
        'adapter_files':prepared['adapter'],'profile':'fastest','fex_compile_slots':2,
        'arena_bytes':1048576000,'arena_guest_base':'0x30000000','arena_backing':'native heap above 4 GiB',
        'guest_exe_unchanged':True,'loading_watch_seconds':600 if a.loading_watch else 0,'sync_watch':a.sync_watch,'hardware_tested':False})
    print('Low-window native built:',sha(nro),flush=True)

if __name__=='__main__':main()
