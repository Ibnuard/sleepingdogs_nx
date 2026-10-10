"""Test the actual v10 handlers/queue with host pthreads and sanitizers.

libnx condvar member access is adapted to host pthread types only. Wire structs,
mutex/thread helpers, APC queue and request handlers come from verified sources.
The small object table and platform services are fixtures, not a Switch benchmark.
"""
from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from port_common import ROOT, sha, write_json
from sleepingdogs_direct_sync import apply, function, FILES, MODIFIED, COPIES

SUPPORT = ('horizon_threads.h', 'f1_apc_queue.h')


def struct(source, name):
    start = re.search(r'^struct ' + name + r'\s*\{', source, re.M)
    assert start, name
    end = source.index('\n};', start.end()) + 3
    return source[start.start():end] + '\n'


def prepare():
    baseline = ROOT / 'local/sync-v10-v9-source'
    receipt = json.loads((baseline / 'native.json').read_text())
    stage = ROOT / 'local/direct-sync-v10-source'
    for name in MODIFIED | {'dlls/ntdll/unix/' + n for n in SUPPORT}:
        assert sha(baseline / name) == receipt['source_files'][name], name
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(baseline / name, target)
    apply(stage)
    return stage


def generate(stage):
    source = (stage / 'dlls/ntdll/unix/horizon.c').read_text()
    constants = '\n'.join(re.findall(r'^#define HORIZON_(?:STATUS_|REQ_|SELECT_|SERVER_FIXED_MESSAGE_SIZE|APC_|CURRENT_THREAD_HANDLE).*', source, re.M))
    constants += '\n' + '\n'.join(re.findall(r'enum horizon_(?:select_opcode|event_op|server_object_type)\s*\{[^}]+\};', source))
    names = ('server_request_header', 'server_reply_header', 'select_request', 'select_reply',
             'select_wait_op', 'select_signal_and_wait_op', 'event_op_request', 'event_op_reply',
             'query_event_request', 'query_event_reply', 'release_mutex_request', 'release_mutex_reply',
             'query_mutex_request', 'query_mutex_reply', 'release_semaphore_request', 'release_semaphore_reply',
             'query_semaphore_request', 'query_semaphore_reply')
    body = constants + '\n' + ''.join(struct(source, 'horizon_' + n) for n in names)
    body += (ROOT / 'tests/direct_sync_fixture.c').read_text()
    body += (stage / 'dlls/ntdll/unix/sd_sync_state.h').read_text()
    body += (stage / 'dlls/ntdll/unix/sd_sync_router.h').read_text()
    names = ('sleep_locked', 'current_tid', 'sync_reply', 'signal_object_locked',
             'handle_event_op', 'handle_query_event', 'handle_release_mutex', 'handle_query_mutex',
             'handle_release_semaphore', 'handle_query_semaphore', 'select_wait',
             'select_signal_and_wait', 'select_status', 'handle_polls_locked', 'select_polls_locked')
    body += '\n'.join(function(source, 'horizon_server_' + n) for n in names)
    body += '\n' + function(source, 'f1_server_select_apc') + '\n'
    body += (stage / 'dlls/ntdll/unix/sd_sync_queue.h').read_text()
    body += function(source, 'horizon_server_handle_select') + '\n'
    body += (stage / 'dlls/ntdll/unix/sd_sync_dispatch.h').read_text()
    body += (ROOT / 'src/low_window/sd_sync_config.h').read_text()
    body += (ROOT / 'tests/direct_sync_cases.c').read_text()
    for old, new in (('&horizon_server_objects_cond.cond', '&horizon_server_objects_cond'),
                     ('&horizon_server_objects_mutex.normal', '&horizon_server_objects_mutex'),
                     ('&private_cond.cond', '&private_cond'),
                     ('&waiter->condition.cond', '&waiter->condition')):
        assert old in body, old
        body = body.replace(old, new)
    return body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--native', type=Path)
    args = parser.parse_args()
    stage = prepare()
    generated = ROOT / 'local/direct-sync-v10-tests'
    generated.mkdir(parents=True, exist_ok=True)
    fixture = generated / 'sync.c'
    fixture.write_text(generate(stage), newline='\n')
    if args.prepare_only:
        print('Prepared v10 overlay and production-handler fixture', flush=True)
        return
    assert sys.platform != 'win32', 'Run with WSL clang for ASan/UBSan pthread coverage'
    exe = Path('/tmp/sleepingdogs-direct-sync-v10-tests')
    compiler = shutil.which('clang') or shutil.which('cc')
    assert compiler, 'Host C compiler required for sanitizer tests'
    cmd = [compiler, '-std=gnu11', '-O1', '-g', '-pthread', '-fsanitize=address,undefined',
           '-fno-sanitize-recover=all',
           '-fno-omit-frame-pointer', '-Werror=implicit-function-declaration',
           '-I' + str(stage / 'dlls/ntdll/unix'), str(fixture), '-o', str(exe)]
    subprocess.run(cmd, check=True)
    result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=50)
    print(result.stdout, end='', flush=True)
    client = generated / 'client.c'
    code = (ROOT/'tests/direct_sync_client.c').read_text().replace('/* ACTUAL_SERVER_CALL */',
        function((stage/'dlls/ntdll/unix/server.c').read_text(), 'server_call_unlocked'))
    client.write_text(code, newline='\n')
    client_cmd = cmd.copy()
    client_cmd[client_cmd.index(str(fixture))] = str(client)
    subprocess.run(client_cmd, check=True)
    client_result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=10)
    print(client_result.stdout, end='', flush=True)
    tested = {n: sha(stage / n) for n in sorted(FILES)}
    if args.native:
        for name, digest in tested.items():
            assert sha(args.native / name) == digest, ('native source differs from tests', name)
    inputs = set(COPIES.values()) | {'tools/sleepingdogs_direct_sync.py',
        'tests/check_direct_sync.py', 'tests/direct_sync_fixture.c', 'tests/direct_sync_cases.c',
        'tests/direct_sync_client.c'}
    report = dict(status='PASS', scope=__doc__, hardware_tested=False, fps_gain_measured=False,
        sanitizer='AddressSanitizer + UndefinedBehaviorSanitizer',
        compiler=subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
        test_output=(result.stdout+client_result.stdout).strip().splitlines(), generated_sha256=sha(fixture),
        sources={n:sha(ROOT/n) for n in sorted(inputs)}, source_files=tested,
        native_source_verified=bool(args.native))
    write_json(ROOT / 'reports/low-window-v10-direct-sync.json', report)


if __name__ == '__main__':
    main()
