"""Prepare an isolated v16 Wine wake-routing overlay on the exact v15 inputs."""
from pathlib import Path
import difflib
import shutil
from port_common import ROOT, sha, write_json
from prepare_lsfg_native import replace
from sleepingdogs_direct_sync import change_function, function

WORK = Path('/home/blekjek/sleepingdogs-sync-v16')
NATIVE = WORK / 'native-source'
BASE = Path('/home/blekjek/sleepingdogs-low-window-v1/native-source')
V15 = Path('/home/blekjek/sleepingdogs-lsfg-v15/native-source')
HORIZON = 'dlls/ntdll/unix/'
RUNTIME = 'wine-nx-probe/source/'
CHANGED = (HORIZON + 'horizon.c', HORIZON + 'sd_sync_router.h',
           RUNTIME + 'runtime.c', RUNTIME + 'sd_sync_report.h')
ROUTES = {
    'horizon_server_post_completion_locked': 'SD_SYNC_COMPLETION_POST',
    'horizon_server_handle_set_timer': 'SD_SYNC_TIMER_REARM',
    'horizon_server_close_object_handle': 'SD_SYNC_COMPLETION_CLOSE',
}


def main():
    before = {}
    for rel, base in ((HORIZON, BASE), (RUNTIME, V15)):
        dest = NATIVE / rel
        dest.mkdir(parents=True, exist_ok=True)
        for p in (base / rel).iterdir():
            if p.is_file():
                shutil.copy2(p, dest / p.name)
        for name in CHANGED:
            if name.startswith(rel):
                before[name] = (base / name).read_text()
    queue = (NATIVE / HORIZON / 'sd_sync_queue.h').read_text()
    assert 'default: goto unsupported;' in queue
    for name in ('TIMER', 'COMPLETION', 'COMPLETION_WAIT', 'FILE'):
        assert 'case HORIZON_SERVER_OBJECT_' + name + ':' not in queue

    source = before[HORIZON + 'horizon.c']
    for name, reason in ROUTES.items():
        source = change_function(source, name, lambda f, r=reason: replace(f,
            'horizon_server_signal_changed_locked();',
            'sd_sync_signal_legacy_locked(' + r + ');'))
    (NATIVE / HORIZON / 'horizon.c').write_text(source, newline='\n')
    router = before[HORIZON + 'sd_sync_router.h']
    original = function(router, 'horizon_server_signal_changed_locked')
    router = replace(router, original, original + '\n\n#include "sd_sync_notify_v16.h"')
    (NATIVE / HORIZON / 'sd_sync_router.h').write_text(router, newline='\n')
    shutil.copy2(ROOT / 'src/low_window/sd_sync_notify_v16.h', NATIVE / HORIZON / 'sd_sync_notify_v16.h')

    runtime = before[RUNTIME + 'runtime.c']
    runtime = replace(runtime, 'sleepingdogs-fextendo-0.1.0-v15-native-lsfg',
                      'sleepingdogs-fextendo-0.1.0-v16-sync-notify')
    runtime = replace(runtime, '#define FX_APP_VERSION "0.1.0-v15-native"',
                      '#define FX_APP_VERSION "0.1.0-v16-sync"')
    anchor = '    horizon_fast_sync_enabled = guest_tests ? 0 : sd_sync_load_mode(RUNTIME_DIR "/sync-mode.txt");'
    runtime = replace(runtime, anchor, anchor + '''
    extern int wine_nx_sd_sync_notify_filter;
    wine_nx_sd_sync_notify_filter = !guest_tests &&
        wine_nx_config_file_bool(RUNTIME_DIR "/sync-notify-filter.txt", 1);
    log_line("[SD-SYNC-V16] filter=%d active=%d; IOCP/timer notices skip event/mutex/semaphore/thread queues; global APC/resume/exit unchanged",
             wine_nx_sd_sync_notify_filter, wine_nx_sd_sync_notify_filter && horizon_fast_sync_enabled == 2);''')
    (NATIVE / RUNTIME / 'runtime.c').write_text(runtime, newline='\n')
    report = before[RUNTIME + 'sd_sync_report.h']
    report = replace(report, '\n}', '''
    extern void wine_nx_sd_sync_notify_snapshot(uint64_t out[5]);
    uint64_t n[5];
    wine_nx_sd_sync_notify_snapshot(n);
    log_line("[SD-SYNC-V16] filter=%llu completion_post=%llu timer_rearm=%llu completion_close=%llu queued_candidates_skipped=%llu; cumulative candidates, not elapsed time or FPS",
        (unsigned long long)n[0], (unsigned long long)n[1], (unsigned long long)n[2],
        (unsigned long long)n[3], (unsigned long long)n[4]);
}''')
    (NATIVE / RUNTIME / 'sd_sync_report.h').write_text(report, newline='\n')

    patch = ''.join(''.join(difflib.unified_diff(before[n].splitlines(True),
        (NATIVE / n).read_text().splitlines(True), fromfile='a/' + n, tofile='b/' + n)) for n in CHANGED)
    (WORK / 'v16.patch').write_text(patch, newline='\n')
    write_json(WORK / 'prepared.json', dict(
        source=str(NATIVE), base=str(BASE), runtime_base=str(V15),
        changed_files=list(CHANGED) + [HORIZON + 'sd_sync_notify_v16.h'],
        files={p.relative_to(NATIVE).as_posix(): sha(p) for p in NATIVE.rglob('*') if p.is_file()},
        hardware_tested=False, fps_gain_measured=False))
    print('Prepared v16: three legacy-only notifications; APC/resume/exit/pipe/registry unchanged', flush=True)


if __name__ == '__main__':
    main()
