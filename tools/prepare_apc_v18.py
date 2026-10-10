"""Prepare an isolated APC queued-waiter notification overlay on delivered v17."""
from pathlib import Path
import difflib
import os
import shutil
from port_common import ROOT, sha, write_json
from prepare_lsfg_native import replace
from sleepingdogs_direct_sync import change_function

LINUX_WORK = '/home/blekjek/sleepingdogs-apc-v18'

def host_path(path):
    return Path('//wsl.localhost/Ubuntu' + path) if os.name == 'nt' else Path(path)

WORK = host_path(LINUX_WORK)
NATIVE = WORK / 'native-source'
BASE = host_path('/home/blekjek/sleepingdogs-scheduler-v17/native-source')
HORIZON = 'dlls/ntdll/unix/'
RUNTIME = 'wine-nx-probe/source/'
CHANGED = (HORIZON+'horizon.c', RUNTIME+'runtime.c', RUNTIME+'sd_sync_report.h')
HEADER = 'sd_apc_notify_v18.h'

def main():
    NATIVE.mkdir(parents=True, exist_ok=True)
    shutil.copytree(BASE, NATIVE, dirs_exist_ok=True)
    before = {n: (BASE/n).read_text() for n in CHANGED}
    shutil.copy2(ROOT/'src/low_window'/HEADER, NATIVE/HORIZON/HEADER)
    source = replace(before[HORIZON+'horizon.c'], '#include "sd_sync_queue.h"',
                     '#include "sd_sync_queue.h"\n#include "sd_apc_notify_v18.h"')
    source = change_function(source, 'f1_server_queue_apc', lambda f: replace(f,
        'horizon_server_signal_changed_locked();', 'sd_sync_signal_apc_locked(thread);'))
    (NATIVE/HORIZON/'horizon.c').write_text(source, newline='\n')

    runtime = replace(before[RUNTIME+'runtime.c'], 'sleepingdogs-fextendo-0.1.0-v17-scheduler',
                      'sleepingdogs-fextendo-0.1.0-v18-apc')
    runtime = replace(runtime, '#define FX_APP_VERSION "0.1.0-v17-sched"',
                      '#define FX_APP_VERSION "0.1.0-v18-apc"')
    anchor = '    horizon_fast_sync_enabled = guest_tests ? 0 : sd_sync_load_mode(RUNTIME_DIR "/sync-mode.txt");'
    runtime = replace(runtime, anchor, anchor+'''
    extern int wine_nx_sd_apc_targeted_wake;
    wine_nx_sd_apc_targeted_wake = !guest_tests &&
        wine_nx_config_file_bool(RUNTIME_DIR "/apc-targeted-wake.txt", 1);
    log_line("[SD-APC-V18] enabled=%d active=%d; accepted user APC wakes target queued waiters; legacy broad paths unchanged",
        wine_nx_sd_apc_targeted_wake, wine_nx_sd_apc_targeted_wake && horizon_fast_sync_enabled == 2);''')
    (NATIVE/RUNTIME/'runtime.c').write_text(runtime, newline='\n')
    report = replace(before[RUNTIME+'sd_sync_report.h'], '\n}', '''
    extern void wine_nx_sd_apc_notify_snapshot(uint64_t out[5]);
    uint64_t a[5];
    wine_nx_sd_apc_notify_snapshot(a);
    log_line("[SD-APC-V18] enabled=%llu accepted_notices=%llu target_candidates=%llu unrelated_candidates_skipped=%llu target_signals=%llu; cumulative counts, not CPU or FPS",
        (unsigned long long)a[0], (unsigned long long)a[1], (unsigned long long)a[2],
        (unsigned long long)a[3], (unsigned long long)a[4]);
}''')
    (NATIVE/RUNTIME/'sd_sync_report.h').write_text(report, newline='\n')
    patch = ''.join(''.join(difflib.unified_diff(before[n].splitlines(True),
        (NATIVE/n).read_text().splitlines(True), fromfile='a/'+n, tofile='b/'+n)) for n in CHANGED)
    patch += ''.join(difflib.unified_diff([], (NATIVE/HORIZON/HEADER).read_text().splitlines(True),
        fromfile='/dev/null', tofile='b/'+HORIZON+HEADER))
    (WORK/'v18.patch').write_text(patch, newline='\n')
    write_json(WORK/'prepared.json', dict(source=LINUX_WORK+'/native-source',
        base='/home/blekjek/sleepingdogs-scheduler-v17/native-source',
        changed_files=list(CHANGED)+[HORIZON+HEADER],
        input_sha256={n:sha(BASE/n) for n in CHANGED},
        files={p.relative_to(NATIVE).as_posix():sha(p) for p in NATIVE.rglob('*') if p.is_file()},
        hardware_tested=False, fps_gain_measured=False,
        mode='target-only queued APC notifications; OFF exact v17 wake routing'))
    print('Prepared v18 APC source overlay; no native build or baseline changes', flush=True)

if __name__ == '__main__':
    main()
