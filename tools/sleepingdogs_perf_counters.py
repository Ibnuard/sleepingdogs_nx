"""Add opt-in interval reports to the v7 normal launcher, preserving execution policy."""
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT

BUILD = 'sleepingdogs-low-window-v8-perf-counters'
MARKER = 'sleepingdogs-fextendo-0.1.0-low-window-v8-perf-counters'
FILES = {'wine-nx-probe/source/runtime.c', 'wine-nx-probe/source/sd_perf_summary.h'}


def apply(source: Path):
    native = source/'wine-nx-probe/source'
    path = native/'runtime.c'
    s = path.read_text()
    s = exact(s, 'sleepingdogs-fextendo-0.1.0-low-window-v7-performance-hud', MARKER)
    s = exact(s, '#define FX_APP_VERSION "0.1.0-v7"', '#define FX_APP_VERSION "0.1.0-v8"')
    s = exact(s, '#include "sd_frame_summary.h"',
              '#include "sd_frame_summary.h"\n#include "sd_perf_summary.h"')
    s = exact(s, '        if (presented) sd_frame_summary(now);',
              '        if (presented) sd_frame_summary(now);\n'
              '        if (presented) sd_perf_summary(now,fx_ui_view.debug);')
    s = exact(s, '    runtime_profile = wine_nx_config_file_bool(RUNTIME_DIR "/profile.txt", 0);',
              '    sd_perf_counters = wine_nx_config_file_bool(RUNTIME_DIR "/performance-counters.txt", 0);\n'
              '    log_line("[SD-PERF] v1 requested=%d active=%d interval_ms=10000; normal Launch only; existing thread/driver/wait/compiler/IO counters",\n'
              '             sd_perf_counters, sd_perf_counters && !fx_ui_view.debug);\n'
              '    runtime_profile = wine_nx_config_file_bool(RUNTIME_DIR "/profile.txt", 0);')
    path.write_text(s)
    (native/'sd_perf_summary.h').write_bytes((ROOT/'src/low_window/sd_perf_summary.h').read_bytes())
