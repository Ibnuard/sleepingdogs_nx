"""Exercise interval reporting with overflow, cadence, Debug ownership and disabled-mode cases."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from port_common import ROOT, sha, write_json
from sleepingdogs_perf_counters import apply, FILES
from build_perf_counters import V7_SHA

HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <limits.h>
static uint64_t clock_ns;
static unsigned calls[4], snapshots, lines;
static char output[16384];
unsigned int wine_nx_file_reads, wine_nx_sd_reads, wine_nx_sd_hits, wine_nx_syscalls;
unsigned long long wine_nx_sd_read_ns;
static unsigned fast[2], poll[2];
static uint64_t armGetSystemTick(void) { return clock_ns; }
static uint64_t armTicksToNs(uint64_t n) { return n; }
static void log_line(const char *fmt, ...) {
    size_t n = strlen(output); va_list args; va_start(args,fmt);
    int rc = vsnprintf(output+n,sizeof(output)-n,fmt,args); va_end(args);
    assert(rc>=0 && (size_t)rc+2<sizeof(output)-n);
    strcat(output,"\n"); ++lines;
}
void wine_nx_thread_report(void) { ++calls[0]; clock_ns+=1000000; }
static void fex_pipeline_report(void) { ++calls[1]; clock_ns+=1000000; }
static void fex_warm_report(void) { ++calls[2]; clock_ns+=1000000; }
static void fex_sync_report(void) { ++calls[3]; clock_ns+=1000000; }
void wine_nx_fex_fast_api_totals(unsigned out[2]) { memcpy(out,fast,sizeof(fast)); ++snapshots; }
void wine_nx_fex_poll_totals(unsigned out[2]) { memcpy(out,poll,sizeof(poll)); ++snapshots; }
#include "sd_perf_summary.h"
static void run(uint64_t time, int debug) { clock_ns=time; sd_perf_summary(time,debug); }
static void clear(void) { output[0]=0; lines=0; }
int main(void) {
    run(1000000000ULL,0); assert(!lines && !snapshots);
    sd_perf_counters=1;
    run(1000000000ULL,1); assert(!lines && !snapshots);
    wine_nx_file_reads=UINT_MAX-2; wine_nx_sd_reads=99; wine_nx_sd_hits=17;
    wine_nx_syscalls=500; wine_nx_sd_read_ns=7000000000ULL;
    fast[0]=400; fast[1]=50; poll[0]=300; poll[1]=20;
    run(1000000000ULL,0);
    assert(lines==3 && snapshots==2);
    assert(strstr(output,"report=0 phase=baseline tick=1000000000 window_ms=0"));
    assert(strstr(output,"reads=0 sd_reads=0 cache_hits=0 sd_ms=0 syscalls=0 qpc=0 delay=0 fast_qpc=0 fast_delay=0"));
    assert(strstr(output,"observer_us=4000"));
    clear();
    run(10999999999ULL,0); assert(!lines && snapshots==2);
    wine_nx_file_reads+=10; wine_nx_sd_reads+=3; wine_nx_sd_hits+=2;
    wine_nx_syscalls+=100; wine_nx_sd_read_ns+=21000000;
    fast[0]+=8; fast[1]+=7; poll[0]+=6; poll[1]+=5;
    run(11000000000ULL,0);
    assert(lines==3 && snapshots==4);
    assert(strstr(output,"report=1 phase=sample tick=11000000000 window_ms=10000"));
    assert(strstr(output,"reads=10 sd_reads=3 cache_hits=2 sd_ms=21 syscalls=100 qpc=6 delay=5 fast_qpc=8 fast_delay=7"));
    clear();
    /* A skipped Debug/disabled call must not consume the report's baseline. */
    run(21000000000ULL,1); assert(!lines);
    sd_perf_counters=0; run(25000000000ULL,0); assert(!lines && snapshots==4);
    sd_perf_counters=1; wine_nx_file_reads+=7;
    run(31000000000ULL,0);
    assert(strstr(output,"window_ms=20000")); assert(strstr(output,"reads=7 sd_reads=0"));
    clear();
    /* A backwards clock re-primes counters, never printing huge unsigned times. */
    run(1000000000ULL,0);
    assert(strstr(output,"phase=baseline tick=1000000000 window_ms=0"));
    clear(); run(11000000000ULL,0);
    assert(strstr(output,"phase=sample tick=11000000000 window_ms=10000"));
    assert(strstr(output,"reads=0 sd_reads=0 cache_hits=0"));
    assert(snapshots==10);
    for(unsigned i=0;i<4;i++) assert(calls[i]==5);
    puts("PASS: disabled and Debug modes do not touch counters; ten-second cadence; startup baseline; unsigned wrap; interval deltas; backwards-clock recovery; observer cost.");
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1/native-source'))
    parser.add_argument('--before-build', action='store_true')
    args = parser.parse_args()
    package = ROOT/'dist/sleepingdogs-fex-low-window-performance-hud.zip'
    assert sha(package) == V7_SHA
    output = ROOT/'local/perf-counters-check'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output, prefix='source-') as tmp:
        source = Path(tmp)
        native = source/'wine-nx-probe/source'
        native.mkdir(parents=True)
        with zipfile.ZipFile(package) as z:
            original = z.read('source/low-window-performance-hud/native/wine-nx-probe/source/runtime.c')
        (native/'runtime.c').write_bytes(original)
        apply(source)
        expected = (native/'runtime.c').read_text()
        if not args.before_build:
            for name in FILES:
                assert (args.source/name).read_bytes() == (source/name).read_bytes(), name
        # Only the two gated monitor calls and the opt-in configuration are new.
        assert 'if (presented) sd_frame_summary(now);\n        if (presented) sd_perf_summary(now,fx_ui_view.debug);' in expected
        assert '__atomic_store_n(&f1_startup_watch_enabled,fx_ui_view.debug,__ATOMIC_RELEASE);' in expected
        assert '"/performance-counters.txt", 0)' in expected
        program, binary = output/'counters.c', output/'counters'
        program.write_text(HARNESS)
        subprocess.run([shutil.which('clang') or shutil.which('cc'), '-std=c11', '-O1', '-g',
            '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
            '-I',str(native),str(program),'-o',str(binary)],check=True)
        result = subprocess.run([str(binary)], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout+result.stderr
        print(result.stdout,end='')
        report = dict(status='PASS', hardware_tested=False, result=result.stdout.strip(),
            sanitizers=['address','undefined'], source_files={n:sha(source/n) for n in FILES},
            sources={n:sha(ROOT/n) for n in ('tests/check_perf_counters.py',
                'src/low_window/sd_perf_summary.h','tools/sleepingdogs_perf_counters.py')},
            all_native_changes_match_overlay=not args.before_build,
            v7_package_preserved=sha(package)==V7_SHA)
        write_json(ROOT/'reports'/('low-window-v8-counters-prebuild.json' if args.before_build
                                   else 'low-window-v8-counters.json'), report)


if __name__ == '__main__':
    main()
