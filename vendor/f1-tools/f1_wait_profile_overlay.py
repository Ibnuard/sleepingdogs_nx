"""Observe the remaining in-race wait bottleneck after targeted wakes."""
from pathlib import Path
VERSION='0.1.35-wait1'
BUILD='f1-fextendo-0.1.35-race-waits'
PARENT='f1-fextendo-0.1.34-indexed-wake'
def once(text,before,after):
    assert text.count(before)==1,before
    return text.replace(before,after,1)
def apply(source):
    tools=Path(__file__).resolve().parent
    native=source/'wine-nx-probe/source';unix=source/'dlls/ntdll/unix'
    p=unix/'horizon.c';text=p.read_text()
    text=once(text,'#include "f1_sync_horizon.h"','#include "f1_sync_horizon.h"\n#include "f1_wait_trace.h"')
    start=text.index('static int horizon_server_handle_select(')
    end=text.index('\nstatic ',start+10)
    body=text[start:end]
    body=once(body,'    struct pes27_interest interest;','    struct pes27_interest interest;\n    struct f1_wait_probe probe;')
    body=once(body,'    pthread_mutex_lock( &horizon_server_objects_mutex );',
        '    f1_wait_begin(&probe,connection->tid);\n    pthread_mutex_lock( &horizon_server_objects_mutex );\n    f1_wait_locked(&probe);')
    body=once(body,'        fex_sync_select_sleep_locked( timeout, &interest );',
        '        f1_wait_before_park(&probe);\n        fex_sync_select_sleep_locked( timeout, &interest );\n        f1_wait_after_park(&probe);')
    body=once(body,'    pthread_mutex_unlock( &horizon_server_objects_mutex );',
        '    f1_wait_end(&probe,reply.header.error);\n    pthread_mutex_unlock( &horizon_server_objects_mutex );')
    text=text[:start]+body+text[end:];p.write_text(text)
    (unix/'f1_wait_trace.h').write_bytes((tools/'f1_wait_trace.h').read_bytes())
    p=native/'runtime.c';text=p.read_text()
    text=once(text,'#define FX_APP_VERSION "0.1.34-index1"',f'#define FX_APP_VERSION "{VERSION}"')
    text=once(text,f'"{PARENT}"',f'"{BUILD}"')
    text=once(text,'int wine_nx_f1_indexed_wake = 0;',
        'int wine_nx_f1_indexed_wake = 0;\nint wine_nx_f1_wait_stats = 0;')
    marker='    wine_nx_f1_indexed_wake = wine_nx_config_file_bool(RUNTIME_DIR "/f1-indexed-wake.txt", 0);'
    text=once(text,marker,marker+'\n    wine_nx_f1_wait_stats = wine_nx_config_file_bool(RUNTIME_DIR "/f1-wait-stats.txt", 0);\n'
        '    log_line("[F1-WAIT] startup enabled=%d; per-thread select counts, timing 1/64; wall time includes scheduling", wine_nx_f1_wait_stats);')
    text=once(text,'circuit sampler off by default; f1-sampler.txt=1 opts in for 60s;',
        'race sampler off by default; f1-sampler.txt=1 opts in after three 3-16 FPS windows for 60s;')
    p.write_text(text)
    p=native/'f1_perf_observer.h';text=p.read_text()
    text=once(text,'    wine_nx_thread_report();','    wine_nx_thread_report();\n    extern void wine_nx_f1_wait_report(void);\n    wine_nx_f1_wait_report();')
    p.write_text(text)
    p=native/'f1_bounded_profile.h';text=p.read_text()
    text=once(text,'Two consecutive nonempty 3-25 FPS windows','Three consecutive nonempty 3-16 FPS windows')
    text=once(text,'elapsed_us*25','elapsed_us*16')
    text=once(text,'gate->slow_windows < 2','gate->slow_windows < 3')
    p.write_text(text)
    p=native/'thread_profile.c';text=p.read_text()
    text=once(text,'trigger=two-slow-windows','trigger=three-3-to-16fps-windows')
    p.write_text(text)
    p=native/'f1_crash.c';text=once(p.read_text(),PARENT,BUILD)
    text=once(text,'/ crash.log / 0.1.34-index1',f'/ crash.log / {VERSION}');p.write_text(text)
    return ['dlls/ntdll/unix/'+n for n in ('horizon.c','f1_wait_trace.h')] + [
        'wine-nx-probe/source/'+n for n in ('runtime.c','f1_crash.c','f1_perf_observer.h','thread_profile.c','f1_bounded_profile.h')]
