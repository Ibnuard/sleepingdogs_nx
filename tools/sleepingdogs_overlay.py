"""Adapt a private F1/Wine-NX source tree; never change the game executable."""
from pathlib import Path
import re
from f1_overlay import exact, replace_function
from port_common import ROOT, VERSION


def apply(source: Path, adapter: Path, game: dict):
    runtime = source / "wine-nx-probe/source/runtime.c"
    data = runtime.read_text()
    # F1's XML graphics migration is unrelated to Sleeping Dogs' binary options.
    data = exact(data, '#include "f1_game_config.h"\n', '')
    start = data.index('            int graphics_migration=f1_prepare_game_graphics(RUNTIME_DIR);')
    end = data.index('            unsigned crash_rc=', start)
    data = data[:start] + '            log_line("[SD-GRAPHICS] game-owned UserOptions.dat; display modes 1280x720/960x540");\n' + data[end:]
    data = exact(data, '400000-15ed000', f'400000-{game["image_end"]:x}', count=2)
    data = exact(data, '#define FX_APP_VERSION "0.1.28"', f'#define FX_APP_VERSION "{VERSION}"')
    data = exact(data, '"f1-fextendo-0.1.28-memory-map"', f'"sleepingdogs-fextendo-{VERSION}-32bit-dx11"')
    # Reject incompatible hosting before Wine tries to map this non-relocatable EXE.
    data = exact(data, '        char thread_error[192];', '        char thread_error[192];\n        u64 sd_host_start=0,sd_host_size=0;')
    marker = '        if(ready&&!wine_nx_f1_prepare_threads(thread_error,sizeof(thread_error))){'
    guard = '''        if(ready){
            Result a=svcGetInfo(&sd_host_start,InfoType_AslrRegionAddress,CUR_PROCESS_HANDLE,0);
            Result b=svcGetInfo(&sd_host_size,InfoType_AslrRegionSize,CUR_PROCESS_HANDLE,0);
            log_line("[SD-ADDRESS] host=%llx+%llx query=%08x/%08x; fixed EXE requires 32-bit no-alias",
                     sd_host_start,sd_host_size,a,b);
            if(R_FAILED(a)||R_FAILED(b)||sd_host_start>0x400000ULL||
               sd_host_size>0x100000000ULL||sd_host_start+sd_host_size>0x100000000ULL){
                ready=0;launch_error=thread_error;
                snprintf(thread_error,sizeof(thread_error),"Use the Sleeping Dogs 32-bit no-alias HOME forwarder.");
            }
        }
'''
    data = exact(data, marker, guard + marker)
    # No PES installation paths remain in the inactive old preset table either.
    data = data.replace('/drive_c/KONAMI/Pro Evolution Soccer 2013/settings.dat', '/launcher/unused-settings.dat')
    data = data.replace('/drive_c/users/steamuser/Documents/KONAMI/Pro Evolution Soccer 2013/settings.dat', '/launcher/unused-user-settings.dat')
    data = data.replace('/drive_c/PES13/settings.dat', '/launcher/unused-local-settings.dat')
    runtime.write_text(data)

    diagnostics = source / 'wine-nx-probe/source/f1_thread_diagnostics.c'
    diagnostics.write_text(replace_function(diagnostics.read_text(),
        'void wine_nx_f1_game_thread_result(unsigned status, uintptr_t start)', '''void wine_nx_f1_game_thread_result(unsigned status, uintptr_t start)
{
    /* No F1-specific guest address is meaningful in HKShip.exe. NtCreateThreadEx
     * already reports failures; preserve the game's handling of optional workers. */
    (void)status; (void)start;
}'''))
    (source / 'wine-nx-probe/source/f1_game_config.h').unlink()

    registry = source / 'dlls/ntdll/unix/horizon_registry_server.h'
    data = exact(registry.read_text(), '#include "f1_crypto_registry.h"',
                 '#include "f1_crypto_registry.h"\n#include "sleepingdogs_registry.h"')
    data = exact(data, '    horizon_registry_hives[0] = machine;', '''    {
        unsigned status = sleepingdogs_registry_install(&horizon_registry, machine);
        char message[128];
        snprintf(message,sizeof(message),"[SD-REGISTRY] Sleeping Dogs installed flag status=%08x",status);
        wine_nx_runtime_trace(message);
        if(status){
            horizon_reg_release(&horizon_registry,horizon_registry.root);
            horizon_registry.root=NULL;
            return status;
        }
    }
    horizon_registry_hives[0] = machine;''')
    registry.write_text(data)
    (registry.parent / 'sleepingdogs_registry.h').write_bytes((ROOT / 'src/sleepingdogs_registry.h').read_bytes())

    replacements = [
        ('switch/f1-fex', 'switch/sleepingdogs-fex'),
        ('switch/pes13-fex', 'switch/sleepingdogs-fex'),
        ('F1_2013.exe', 'HKShip.exe'), ('F1_2013.keys.txt', 'HKShip.keys.txt'),
        ('F1_2013_dxgi.log', 'HKShip_dxgi.log'), ('F1_2013', 'SleepingDogs'),
        ('F1 2013', 'Sleeping Dogs'),
        ('[F1-', '[SD-'), ('[PES13-', '[SD-'),
        ('PC racing. On your Switch.', 'Hong Kong. On your Switch.'),
        ('A new race,', 'Hong Kong,'),
        ('"Keyboard"', '"Controller"'),
        ('Set your', 'Enter'), ('race up.', 'Hong Kong.'),
        ('your next race.', 'your next session.'), ('the next race.', 'the next session.'),
        ('Ready to race.', 'Ready to play.'),
        ('launch F1 again', 'launch Sleeping Dogs again'),
        ('F1 launcher', 'Sleeping Dogs launcher'), ('F1: Cannot', 'Sleeping Dogs: Cannot'),
        ('.f1-new', '.sd-new'), ('.f1-old', '.sd-old'),
        ('f1-relaunch', 'sleepingdogs-relaunch'),
    ]
    changed = []
    for tree in (source, adapter):
        for path in tree.rglob('*'):
            if not path.is_file() or path.suffix not in ('.c', '.h', '.inc', '.in', '.txt'):
                continue
            old = path.read_text(errors='surrogateescape')
            data = old
            for before, after in replacements:
                data = data.replace(before, after)
            if data != old:
                path.write_text(data, errors='surrogateescape')
                changed.append(str(path.relative_to(tree)))
    # A copied F1 bug workaround must not change HKShip's own video files.
    data = runtime.read_text()
    for stale in ('F1_2013', 'f1_prepare_game_graphics', 'switch/f1-fex', 'switch/pes13-fex'):
        if stale in data:
            raise RuntimeError(f'Unconverted runtime field: {stale}')
    if f'400000-{game["image_end"]:x}' not in data:
        raise RuntimeError('Wrong preload reservation')
    from sleepingdogs_memory import apply as apply_memory
    apply_memory(source)
    from sleepingdogs_named_pipe import apply as apply_named_pipe
    apply_named_pipe(source)
    from sleepingdogs_debug_cache import apply as apply_debug_cache
    apply_debug_cache(source)
    from sleepingdogs_thread_debug import apply as apply_thread_debug
    apply_thread_debug(source)
    from sleepingdogs_memory_budget import apply as apply_memory_budget
    apply_memory_budget(source, adapter)
    from sleepingdogs_compiler_memory import apply_native as apply_compiler_memory
    apply_compiler_memory(source, adapter)
    from sleepingdogs_gpu_budget import apply_native as apply_gpu_budget
    apply_gpu_budget(source)
    from sleepingdogs_streaming_memory import apply_native as apply_streaming_memory
    apply_streaming_memory(source)
    from sleepingdogs_gpu_pressure import apply as apply_gpu_pressure
    apply_gpu_pressure(source)
    from sleepingdogs_scene_memory import apply_native as apply_scene_memory
    apply_scene_memory(source, adapter)
    return changed
