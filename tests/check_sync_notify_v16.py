"""Exercise actual v16 handlers with pthreads + ASan/UBSan; no FPS inference."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'tools')]
from port_common import ROOT, sha, write_json
from prepare_lsfg_native import replace
from prepare_sync_notify_v16 import WORK, NATIVE, BASE, HORIZON, ROUTES
from sleepingdogs_direct_sync import function
from check_direct_sync import generate, struct


def fixture():
    source = (NATIVE / HORIZON / 'horizon.c').read_text()
    body = generate(NATIVE)
    body = replace(body, '/* Platform fixture for',
        '\n#include "horizon_completion.h"\n#define max(a,b) ((a)>(b)?(a):(b))\n' +
        struct(source, 'horizon_set_timer_request') + struct(source, 'horizon_set_timer_reply') +
        '\n/* Platform fixture for')
    body = replace(body, '    long long timer_when;\n', '''    long long timer_when;
    unsigned timer_period;
    struct horizon_completion_queue completion;
    struct horizon_completion_msg wait_msg;
    struct horizon_server_object *wait_port;
    int completion_closed, wait_has_msg;
''')
    body = replace(body, 'struct horizon_server_handle_entry { struct horizon_server_object *object; };',
        'struct horizon_server_handle_entry { struct horizon_server_object *object; struct horizon_server_handle_entry *next; };\n'
        'static struct horizon_server_handle_entry *horizon_server_handles;\nstatic int horizon_server_timers_armed;')
    body = replace(body, 'static void horizon_server_update_timers_locked(void) {}',
                   function(source, 'horizon_server_update_timers_locked'))
    anchor = '    if (!o->signaled) return HORIZON_STATUS_TIMEOUT;'
    body = replace(body, anchor, '''    if (o->type == HORIZON_SERVER_OBJECT_COMPLETION_WAIT) {
        struct horizon_server_object *p = o->wait_port;
        if (!horizon_completion_wait_signaled(p ? &p->completion : NULL, p && p->completion_closed))
            return HORIZON_STATUS_TIMEOUT;
        if (consume && horizon_completion_wait_satisfy(p ? &p->completion : NULL,
                p && p->completion_closed, &o->wait_msg, &o->wait_has_msg))
            return HORIZON_STATUS_ABANDONED_WAIT_0;
        return 0;
    }
''' + anchor)
    extra = '\n'.join(function(source, n) for n in
        ('horizon_server_post_completion_locked', 'horizon_server_handle_set_timer'))
    extra += '\n' + (ROOT / 'tests/sync_notify_v16_cases.c').read_text()
    body = replace(body, 'int main(void) {', extra + '''
int main(void) {
    horizon_server_handles = handles + 1;
    for (unsigned i=1;i<16;++i) handles[i].next = i<15 ? handles+i+1 : NULL;
''')
    body = replace(body, '    clear_events();\n    pthread_t t, t2;',
                   '    v16_cases();\n    clear_events();\n    pthread_t t, t2;')
    # Interleave real completion enqueue/dequeue with all 3000 event round trips.
    loop = '    for (int i=0;i<loops;++i) { assert(!event(1,1,HORIZON_SET_EVENT)); assert(!wait_for(1,2,-(clock_ticks()+20000000))); }'
    body = replace(body, loop, '''    for (int i=0;i<loops;++i) {
        pthread_mutex_lock(&horizon_server_objects_mutex);
        for (int k=0;k<4;++k) {
            struct horizon_completion_msg msg;
            horizon_server_post_completion_locked(objects+7, i, k, 0, 1);
            assert(horizon_completion_take(&objects[7].completion, &msg));
            assert(msg.ckey == (unsigned)i && msg.cvalue == (unsigned)k);
        }
        pthread_mutex_unlock(&horizon_server_objects_mutex);
        assert(!event(1,1,HORIZON_SET_EVENT));
        assert(!wait_for(1,2,-(clock_ticks()+20000000)));
    }
    puts("PASS v16 12000 real completion notifications interleaved with event ping-pong");''')
    return body


def main():
    prepared = json.loads((WORK / 'prepared.json').read_text())
    for name, expected in prepared['files'].items():
        assert sha(NATIVE / name) == expected, name
    source = (NATIVE / HORIZON / 'horizon.c').read_text()
    old = (BASE / HORIZON / 'horizon.c').read_text()
    for name, reason in ROUTES.items():
        assert function(source, name) == replace(function(old, name),
            'horizon_server_signal_changed_locked();', 'sd_sync_signal_legacy_locked(' + reason + ');'), name
    reconstructed = source
    for reason in ROUTES.values():
        reconstructed = replace(reconstructed, 'sd_sync_signal_legacy_locked(' + reason + ');',
                                'horizon_server_signal_changed_locked();')
    assert reconstructed == old, 'Unexpected horizon.c change outside the three audited calls'
    for name in ('sd_named_pipe.inc', 'horizon_registry_server.h', 'sd_sync_queue.h', 'sd_sync_state.h',
                 'sd_sync_dispatch.h', 'sd_sync_legacy_wait.h'):
        assert sha(NATIVE / HORIZON / name) == sha(BASE / HORIZON / name), name
    generated = WORK / 'tests'
    generated.mkdir(exist_ok=True)
    code = generated / 'sync.c'
    code.write_text(fixture(), newline='\n')
    compiler = shutil.which('clang') or shutil.which('cc')
    assert compiler
    exe = generated / 'sync-test'
    command = [compiler, '-std=gnu11', '-O1', '-g', '-pthread', '-fsanitize=address,undefined',
        '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-Werror=implicit-function-declaration',
        '-I' + str(NATIVE / HORIZON), str(code), '-o', str(exe)]
    subprocess.run(command, check=True)
    result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=50)
    print(result.stdout, end='', flush=True)
    write_json(ROOT / 'reports/sync-notify-v16-host.json', dict(status='PASS',
        sanitizer='AddressSanitizer + UndefinedBehaviorSanitizer',
        scope=__doc__, hardware_tested=False, fps_gain_measured=False,
        output=result.stdout.strip().splitlines(), generated_sha256=sha(code),
        compiler=subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
        source_files=prepared['files'], unchanged_global_and_pipe_registry_notifications=True,
        sources={n: sha(ROOT / n) for n in ('tests/check_sync_notify_v16.py',
            'tests/sync_notify_v16_cases.c', 'tests/check_direct_sync.py',
            'tests/direct_sync_cases.c', 'tests/direct_sync_fixture.c')}))


if __name__ == '__main__':
    main()
