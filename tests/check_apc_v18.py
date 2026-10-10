"""Host-test the production v18 notifier, accepted APC handler and select queues."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'tools')]
from port_common import ROOT, sha, write_json
from prepare_apc_v18 import WORK, NATIVE, BASE, HORIZON, RUNTIME, HEADER, host_path
from prepare_lsfg_native import replace
from sleepingdogs_direct_sync import function
from check_direct_sync import generate, struct

PROTOCOL = host_path('/home/blekjek/sleepingdogs-low-window-v1/native-source/include/wine/server_protocol.h')

def fixture():
    source = (NATIVE/HORIZON/'horizon.c').read_text()
    protocol = PROTOCOL.read_text()
    body = generate(NATIVE)
    body = replace(body, 'union apc_call { struct user_apc user;',
                   'union apc_call { unsigned type; struct user_apc user;')
    wire = '\n'.join(struct(protocol, n) for n in ('queue_apc_request', 'queue_apc_reply'))
    wire = wire.replace('struct request_header', 'struct horizon_server_request_header')
    wire = wire.replace('struct reply_header', 'struct horizon_server_reply_header')
    wire = wire.replace('obj_handle_t', 'unsigned int')
    body = replace(body, '/* Platform fixture for', wire + '''
#define APC_USER 1
#define STATUS_INVALID_PARAMETER 0xc000000du
#define STATUS_NOT_IMPLEMENTED 0xc0000002u
#define STATUS_NOT_SUPPORTED 0xc00000bbu
#define STATUS_THREAD_IS_TERMINATING 0xc000004bu
/* Platform fixture for''')
    body = replace(body, 'static unsigned long long f1_apc_delivered;',
                   'static unsigned long long f1_apc_delivered, f1_apc_queued, f1_apc_rejected;')
    # Capture condvar requests without replacing their real pthread behavior.
    body = replace(body, 'int horizon_fast_sync_enabled;', '''
static unsigned observed_signals, observed_broadcasts;
static int observed_signal(pthread_cond_t *c) { ++observed_signals; return pthread_cond_signal(c); }
static int observed_broadcast(pthread_cond_t *c) { ++observed_broadcasts; return pthread_cond_broadcast(c); }
#define pthread_cond_signal observed_signal
#define pthread_cond_broadcast observed_broadcast
int horizon_fast_sync_enabled;''')
    extra = '\n' + (NATIVE/HORIZON/HEADER).read_text() + '\n'
    extra += function(source, 'horizon_server_get_thread_locked') + '\n'
    extra += function(source, 'f1_server_queue_apc') + '\n'
    extra += (ROOT/'tests/apc_v18_cases.c').read_text()
    body = replace(body, 'int main(void) {', extra+'\nint main(void) {')
    body = replace(body, '    clear_events();\n    pthread_t t, t2;',
                   '    v18_cases();\n    clear_events();\n    pthread_t t, t2;')
    return body

def main():
    assert sys.platform != 'win32', 'Run WSL host clang for pthread ASan/UBSan tests'
    prepared = json.loads((WORK/'prepared.json').read_text())
    for name, expected in prepared['files'].items():
        assert sha(NATIVE/name) == expected, name
    source, old = [(p/HORIZON/'horizon.c').read_text() for p in (NATIVE, BASE)]
    reconstructed = replace(source, '#include "sd_sync_queue.h"\n#include "sd_apc_notify_v18.h"',
                             '#include "sd_sync_queue.h"')
    reconstructed = replace(reconstructed, 'sd_sync_signal_apc_locked(thread);',
                             'horizon_server_signal_changed_locked();')
    assert reconstructed == old, 'Unexpected change outside accepted APC notifier'
    for name in ('sd_sync_queue.h', 'sd_sync_router.h', 'sd_sync_state.h', 'sd_sync_dispatch.h',
                 'sd_sync_legacy_wait.h', 'sd_sync_notify_v16.h', 'horizon_registry_server.h',
                 'sd_named_pipe.inc', 'f1_apc_queue.h'):
        assert sha(NATIVE/HORIZON/name) == sha(BASE/HORIZON/name), name
    generated = WORK/'tests'
    generated.mkdir(exist_ok=True)
    code = generated/'apc.c'
    code.write_text(fixture(), newline='\n')
    compiler = shutil.which('clang') or shutil.which('cc')
    assert compiler
    exe = generated/'apc-test'
    command = [compiler, '-std=gnu11', '-O1', '-g', '-pthread', '-fsanitize=address,undefined',
        '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-Werror=implicit-function-declaration',
        '-I'+str(NATIVE/HORIZON), str(code), '-o', str(exe)]
    subprocess.run(command, check=True)
    result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=55)
    print(result.stdout, end='', flush=True)
    write_json(ROOT/'reports/apc-v18-host-check.json', dict(status='PASS',
        scope=__doc__, hardware_tested=False, fps_gain_measured=False,
        sanitizer='AddressSanitizer + UndefinedBehaviorSanitizer',
        compiler=subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
        test_output=result.stdout.strip().splitlines(), generated_sha256=sha(code),
        source_files=prepared['files'], protocol_sha256=sha(PROTOCOL),
        sources={n:sha(ROOT/n) for n in ('tests/check_apc_v18.py', 'tests/apc_v18_cases.c',
            'tests/check_direct_sync.py', 'tests/direct_sync_fixture.c', 'tests/direct_sync_cases.c',
            'src/low_window/sd_apc_notify_v18.h', 'tools/prepare_apc_v18.py')}))

if __name__ == '__main__':
    main()
