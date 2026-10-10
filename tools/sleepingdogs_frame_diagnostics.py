"""One bounded passive capture on verified v10; no execution-policy changes."""
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT
from sleepingdogs_direct_sync import change_function

BUILD = 'sleepingdogs-low-window-v11-frame-diagnostics'
MARKER = 'sleepingdogs-fextendo-0.1.0-low-window-v11-frame-diagnostics'
NATIVE = 'wine-nx-probe/source/'
COPIES = {NATIVE+n:'src/low_window/'+n for n in
          ('sd_frame_diag_core.h', 'sd_frame_diag_runtime.h', 'sd_frame_diag_thread_map.h')}
COPIES[NATIVE+'f1_bounded_profile.h'] = 'tools/f1_bounded_profile.h'
MODIFIED = {NATIVE+'runtime.c', NATIVE+'thread_profile.c', 'dlls/ntdll/unix/server.c'}
FILES = MODIFIED | set(COPIES)


def apply(source: Path):
    for target, origin in COPIES.items():
        dest=source/target; dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((ROOT/origin).read_bytes())
    p=source/NATIVE/'runtime.c'; s=p.read_text()
    s=exact(s,'sleepingdogs-fextendo-0.1.0-low-window-v10-direct-sync',MARKER)
    s=exact(s,'#define FX_APP_VERSION "0.1.0-v10"','#define FX_APP_VERSION "0.1.0-v11-diag"')
    s=exact(s,'static int fex_gap_probe_enabled = 1;',
              '#include "sd_frame_diag_runtime.h"\nstatic int fex_gap_probe_enabled = 1;')
    s=exact(s,'        fex_gap_present(queue, swapchain, 0);',
              '        fex_gap_present(queue, swapchain, 0);\n        sd_frame_diag_present(queue, swapchain, end, 0);')
    s=exact(s,'    fex_gap_present(queue, swapchain, 1);',
              '    fex_gap_present(queue, swapchain, 1);\n    sd_frame_diag_present(queue, swapchain, end, 1);')
    s=exact(s,'    fex_gap_pipeline_note(stage, armTicksToNs(end - begin) / 1000);',
              '    fex_gap_pipeline_note(stage, armTicksToNs(end - begin) / 1000);\n'
              '    wine_nx_sd_diag_note(stage+3, begin, end, result == 2, result < 0, 0);')
    s=exact(s,'        if (presented) sd_perf_summary(now,fx_ui_view.debug);',
              '        if (presented) sd_perf_summary(now,fx_ui_view.debug);\n'
              '        sd_frame_diag_monitor(now,__atomic_load_n(&fex_frame_ok,__ATOMIC_RELAXED));')
    s=exact(s,'    horizon_server_profile_enabled = sd_perf_counters || runtime_profile || fx_ui_view.debug;',
              '    __atomic_store_n(&sd_frame_diag_enabled, !guest_tests && sd_sync_load_mode(RUNTIME_DIR "/frame-diagnostics.txt") == 1, __ATOMIC_RELEASE);\n'
              '    horizon_server_profile_enabled = sd_perf_counters || runtime_profile || fx_ui_view.debug || sd_frame_diag_enabled;\n'
              '    log_line("[SD-DIAG] v1 enabled=%d capture_ms=30000 trigger=two-slow-windows sampler=off; timing only, 720p unchanged", sd_frame_diag_enabled);')
    p.write_text(s,newline='\n')
    p=source/NATIVE/'thread_profile.c'
    p.write_text(p.read_text()+'\n#include "sd_frame_diag_thread_map.h"\n',newline='\n')
    p=source/'dlls/ntdll/unix/server.c'; s=p.read_text()
    s=exact(s,'int horizon_server_profile_enabled;',
              'int horizon_server_profile_enabled;\n'
              'extern void wine_nx_sd_diag_note(unsigned stage, uint64_t begin, uint64_t end,\n'
              '                                  unsigned timeout, unsigned error, unsigned route);')
    def hook(f):
        return exact(f,'        __atomic_add_fetch( &wine_nx_server_ticks[code], armGetSystemTick() - start, __ATOMIC_RELAXED );',
            '        u64 end = armGetSystemTick();\n'
            '        __atomic_add_fetch( &wine_nx_server_ticks[code], end - start, __ATOMIC_RELAXED );\n'
            '        wine_nx_sd_diag_note(code == REQ_select ? 0 : code == REQ_event_op ? 1 : 2,\n'
            '                             start, end, ret == STATUS_TIMEOUT, !!(ret & 0x80000000u), direct ? 1 : 2);')
    s=change_function(s,'server_call_unlocked',hook)
    p.write_text(s,newline='\n')
