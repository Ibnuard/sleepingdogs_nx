"""Keep bounded Debug observations alive after the first game presentation."""
import shutil
from port_common import ROOT
from f1_overlay import exact

INPUTS = ('tools/low_window_loading.py', 'src/low_window/sd_loading_watch.h',
          'src/low_window/sd_loading_report.inc')


def overlay(source):
    native = source / 'wine-nx-probe/source'
    for name in ('sd_loading_watch.h', 'sd_loading_report.inc'):
        shutil.copy2(ROOT / 'src/low_window' / name, native / name)
    p = native / 'runtime.c'
    s = p.read_text()
    s = exact(s, '#include "sd_low_window.h"',
              '#include "sd_low_window.h"\n#include "sd_loading_watch.h"')
    s = exact(s, 'sleepingdogs-fextendo-0.1.0-low-window-v2-dx11',
              'sleepingdogs-fextendo-0.1.0-low-window-v3-load-watch')
    s = exact(s, '        __atomic_store_n(&f1_startup_watch_enabled,0,__ATOMIC_RELEASE);',
              '        /* Debug sampling expires in the monitor, not at the first frame. */')
    s = exact(s, '/* Runs independently of registry persistence, balancing and guest log output. */',
              '#include "sd_loading_report.inc"\n\n'
              '/* Runs independently of registry persistence, balancing and guest log output. */')
    s = exact(s, '        if (seconds-last < (presented ? 30u : 5u)) continue;', '''        if (seconds >= SD_LOADING_WATCH_SECONDS &&
            __atomic_exchange_n(&f1_startup_watch_enabled,0,__ATOMIC_ACQ_REL))
            log_line("[SD-LOAD] detail window ended at t=%us; resource/error logging continues",seconds);
        unsigned watching = __atomic_load_n(&f1_startup_watch_enabled,__ATOMIC_ACQUIRE);
        if (seconds-last < (presented ? (watching ? SD_LOADING_REPORT_SECONDS : 30u) : 5u)) continue;''')
    s = exact(s, '        /* Handoff stops syscall sampling, not persistent error capture. */',
              '        /* Bound detailed observations to ten minutes of a Debug launch. */')
    s = exact(s, '        if (!__atomic_load_n(&f1_startup_watch_enabled,__ATOMIC_ACQUIRE)) continue;\n',
              '        if (!__atomic_load_n(&f1_startup_watch_enabled,__ATOMIC_ACQUIRE)) continue;\n'
              '        sd_loading_report(seconds);\n')
    s = exact(s, '        /* Three bounded captures before any 3D handoff: 30, 45 and 60 seconds. */',
              '        /* Two observations per capture, at most once per thirty seconds. */')
    s = exact(s, '[SD-WATCH] heartbeat=5s; startup snapshots=30/45/60s; latest syscall/file boundaries and saved guest PCs; active status=ffffffff means no return yet',
              '[SD-WATCH] v2 debug detail=600s; heartbeat=5s before present/15s after; snapshots=30s; latest syscall/file boundaries and saved guest PCs; active status=ffffffff means no return yet')
    p.write_text(s)
    p = native / 'thread_profile.c'
    s = p.read_text()
    start = s.index('static int f1_snapshot_due(')
    end = s.index('\nvoid wine_nx_f1_thread_snapshot(', start)
    s = s[:start] + '#include "sd_loading_watch.h"\n' + s[end:]
    s = exact(s, 'if (!f1_snapshot_due(seconds, &captures, &last)) return;',
              'if (!sd_loading_snapshot_due(seconds, &captures, &last)) return;')
    s = exact(s, '/* Startup-only sampling, independent of the presentation counter.',
              '/* Bounded loading sampling, independent of the presentation counter.')
    p.write_text(s)
