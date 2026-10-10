"""Compile the actual Horizon APC handlers/select loop and NtReadFile exit path.

Host pthread tests replace kernel sleep/file I/O, not the changed queue,
protocol handler, select decision, or completion status code. No game is run.
"""
from pathlib import Path
import argparse
import subprocess
import shutil
from check_startup import function

ROOT = Path(__file__).resolve().parents[1]


def struct(source, name):
    start = source.index('struct ' + name + '\n{')
    return source[start:source.index('\n};', start) + 3] + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    unix = args.source / 'dlls/ntdll/unix'
    horizon = (unix / 'horizon.c').read_text()
    code = (ROOT / 'tests/apc_server.c').read_text()
    wire = ''.join(struct(horizon, name) for name in (
        'horizon_server_request_header', 'horizon_server_reply_header',
        'horizon_select_request', 'horizon_select_reply',
        'horizon_select_wait_op', 'horizon_select_signal_and_wait_op'))
    code = code.replace('/* ACTUAL_WIRE */', wire)
    select = ''.join(function(horizon, sig) for sig in (
        'static unsigned int horizon_server_select_wait(',
        'static unsigned int horizon_server_select_signal_and_wait(',
        'static unsigned int horizon_server_select_status(',
        'static int horizon_server_handle_select('))
    apc = horizon[horizon.index('static unsigned long long f1_apc_queued,'):
                  horizon.index('static int horizon_server_handle_select(')]
    code = code.replace('/* ACTUAL_SERVER */', apc + select)
    read = function((unix / 'file.c').read_text(), 'static NTSTATUS WINAPI f1_original_NtReadFile(')
    # Read I/O itself is synchronous and already finished at this boundary.
    code = code.replace('/* ACTUAL_READ_EXIT */', read[read.index('done:\n'):])
    target = args.output / 'apc.c'
    target.write_text(code)
    cc = shutil.which('clang') or shutil.which('cc')
    exe = args.output / 'apc-server'
    subprocess.run([cc, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-D__WINESRC__', '-O1', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-I', str(args.source / 'include'), '-I', str(unix),
                    str(target), '-pthread', '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
