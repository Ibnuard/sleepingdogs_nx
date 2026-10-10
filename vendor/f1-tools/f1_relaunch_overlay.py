"""Wire full application restart and one-shot result UI into the isolated F1 build."""
from pathlib import Path
from f1_overlay import exact

TOOLS = Path(__file__).resolve().parent

def apply(source: Path):
    native = source / 'wine-nx-probe/source'
    runtime = native / 'runtime.c'
    s = runtime.read_text()
    s = exact(s, 'static int fx_debug_live;', '#include "f1_relaunch.h"\nstatic int fx_debug_live;')
    s = exact(s, 'renderer,settings_page,debug;', 'renderer,settings_page,debug,returned;')
    s = exact(s, 'static char fx_ui_message[192];', '''static char fx_ui_message[192];
#include "f1_log_rotation.h"
static int fx_recovery_notice(void) {
    if(fx_ui_view.fatal)return 0;
    int returned=wine_nx_f1_relaunch_consume(fx_ui_message,sizeof(fx_ui_message));
    if(returned){
        fx_ui_view.returned=returned;fx_ui_view.screen=FX_FAILED;
        fx_ui_view.fatal=0;fx_ui_view.message=fx_ui_message;
    }
    return returned;
}''')
    s = exact(s, '    psm_ready=R_SUCCEEDED(psmInitialize());',
        '    if(fx_recovery_notice())splash_done=1;\n    psm_ready=R_SUCCEEDED(psmInitialize());')
    s = exact(s, '            }else fx_ui_view.screen=FX_HOME;',
        '            }else {fx_ui_view.screen=FX_HOME;fx_ui_view.returned=0;}')
    s = exact(s, '                        fx_debug_file=fopen(RUNTIME_DIR "/fex-runtime.log","wb");',
        '                        if(!fx_debug_file)fx_debug_file=f1_open_runtime_log(RUNTIME_DIR);')
    s = exact(s, '        if(!ready&&launch_error!=thread_error)', '''        if(ready){
            unsigned restart_rc=wine_nx_f1_relaunch_arm();
            log_line("[F1-RESTART] armed rc=%08x; HOME application restart; private recovery worker",restart_rc);
            if(restart_rc){
                ready=0;launch_error=thread_error;
                snprintf(thread_error,sizeof(thread_error),"Cannot prepare crash recovery (0x%08x). Check SD space, then retry.",restart_rc);
                log_line("[F1-LAUNCH] %s",thread_error);
            }
        }
        if(!ready&&launch_error!=thread_error)''')
    s = exact(s, '    char message[160];\n    if (code == 0xc0000142u)',
        '    if(wine_nx_f1_relaunch_request(F1_RETURN_GUEST,code))return;\n'
        '    char message[160];\n    if (code == 0xc0000142u)')
    closing = '__atomic_store_n(&fx_boot_started,0,__ATOMIC_RELEASE);'
    assert s.count(closing) == 4, 'Recheck launcher close/cancel/preflight paths'
    s = s.replace(closing, 'wine_nx_f1_relaunch_disarm();' + closing)
    runtime.write_text(s)
    for name in ('f1_relaunch.c', 'f1_relaunch.h', 'f1_log_rotation.h'):
        (native / name).write_bytes((TOOLS / name).read_bytes())
    cmake = source / 'wine-nx-probe/CMakeLists.txt'
    with cmake.open('a') as f:
        f.write('\ntarget_sources(wine-nx-runtime PRIVATE source/f1_relaunch.c)\n')
