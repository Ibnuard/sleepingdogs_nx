"""Execute the built-source monitor/handoff/sampler with modeled time and SVCs."""
from pathlib import Path
import argparse
import subprocess
import sys

from check_launch_order import function

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json

MAIN = r'''
int main(int argc,char **argv){
    assert(argc==2);mode=(unsigned)atoi(argv[1]);
    fx_debug_live=mode!=7;f1_startup_watch_enabled=fx_debug_live;
    if(mode==4)pthread_mutex_lock(&registry_mutex);
    if(mode==5)pthread_mutex_lock(&profile_mutex);
    if(!setjmp(stop_monitor)) f1_startup_monitor(NULL);
    running();
    assert(handoffs==1&&fx_ui_stop);
    if(mode==7){
        assert(!watch_survived&&!resource_calls&&!detail_calls&&!captures&&!pause_calls);
    }else{
        assert(watch_survived&&expiry_seen==1&&!f1_startup_watch_enabled);
        assert(detail_calls>30&&last_detail>=570&&last_detail<600&&freeze_seen);
        assert(resource_calls>detail_calls&&pipe_lines>=detail_calls*5);
        if(mode>=4&&mode<=6) assert(!pause_calls&&!captures);
        else{
            assert(captures==19&&pause_calls==19*6&&stack_lines==19*6);
            unsigned successful=mode==1?19*4:19*6;
            assert(read_calls==successful);
            assert(resume_calls==successful+(mode==3));
        }
    }
    /* Boundary checks: expiry, clock rollback and capture count cannot spin. */
    unsigned n=0,last=0;
    assert(!sd_loading_snapshot_due(29,&n,&last));
    assert(sd_loading_snapshot_due(30,&n,&last));
    assert(!sd_loading_snapshot_due(31,&n,&last));
    assert(!sd_loading_snapshot_due(29,&n,&last));
    assert(sd_loading_snapshot_due(60,&n,&last));
    assert(!sd_loading_snapshot_due(600,&n,&last));
    n=20;assert(!sd_loading_snapshot_due(90,&n,&last));
    puts("PASS");return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/low-window-loading-watch.json')
    args = parser.parse_args()
    native = args.work / 'native-source/wine-nx-probe/source'
    runtime = (native / 'runtime.c').read_text()
    profile = (native / 'thread_profile.c').read_text()
    fixture = (ROOT / 'tests/loading_watch.c').read_text()
    structure = profile[profile.index('struct fex_stall_capture {'):profile.index('\nvoid wine_nx_fex_stall_probe(')]
    sampler = profile[profile.index('/* Bounded loading sampling,'):]
    source = fixture + '\nstatic void wine_nx_sd_sync_report(void) { running(); }\n' + structure + sampler
    source += '\n#define pthread_join fixture_join\n' + function(runtime, 'static int fx_handoff(void)')
    source += '\n#undef pthread_join\n' + function(runtime, 'static void fex_pipeline_report(void)')
    source += '\n#include "sd_loading_report.inc"\n' + function(runtime, 'static void *f1_startup_monitor(void *unused)')
    source += MAIN
    out = args.work / 'loading-watch-check'
    out.mkdir(exist_ok=True)
    (out / 'check.c').write_text(source)
    metrics = ROOT.parent / 'pes13-nx/local/production-input-fix/approved/source/src/runtime'
    exe = out / 'check'
    subprocess.run(['gcc', '-std=c11', '-D_GNU_SOURCE', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                    '-pthread', '-I'+str(native), '-I'+str(metrics), str(out / 'check.c'), '-o', str(exe)], check=True)
    cases = ['post-present freeze; exact 600s expiry; resource logging continues',
             'pause rejected; do not resume an unpaused target',
             'context read failed; immediately resume target',
             'resume first attempt rejected; retry once before logging',
             'registry busy; skip capture without waiting',
             'profiler busy; release registry and skip capture',
             'pause/context capability unavailable; preserve call observations',
             'GUI launch; no detailed diagnostics or thread pauses']
    for mode, name in enumerate(cases):
        result = subprocess.run([exe, str(mode)], text=True, capture_output=True)
        if result.returncode:
            raise AssertionError((name, result.returncode, result.stdout, result.stderr))
        assert result.stdout == 'PASS\n'
        print('PASS', name, flush=True)
    report = {'status': 'PASS', 'scope': __doc__, 'hardware_tested': False, 'cases': cases,
              'no_logging_while_paused': True, 'ubsan': True,
              'source_files': {str(p.relative_to(args.work / 'native-source')): sha(p) for p in
                               (native / 'runtime.c', native / 'thread_profile.c', native / 'f1_startup_watch.h',
                                native / 'sd_loading_watch.h', native / 'sd_loading_report.inc')},
              'sources': {str(p.relative_to(ROOT)): sha(p) for p in
                          (Path(__file__), ROOT / 'tests/loading_watch.c', ROOT / 'tests/check_launch_order.py')},
              'metrics_sha256': sha(metrics / 'fex_frame_metrics.h')}
    write_json(args.report, report)


if __name__ == '__main__':
    main()
