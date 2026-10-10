"""Sanitize the production suspended-thread debug handler with pinned Wine types."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
    exe = a.output / 'thread-debug'; unix = a.source / 'dlls/ntdll/unix'
    env = dict(os.environ, TMPDIR=str(a.output))
    subprocess.run(['gcc', '-std=c11', '-D_WIN64', '-D__WINESRC__', '-Wall', '-Wextra', '-Werror',
        '-Wno-attributes', '-g', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
        '-fno-omit-frame-pointer', '-I' + str(a.source / 'include'), '-I' + str(ROOT / 'src'),
        '-I' + str(unix), str(ROOT / 'tests/thread_debug.c'), '-pthread', '-o', str(exe)], check=True, env=env)
    result = subprocess.run([str(exe)], check=True, text=True, capture_output=True)
    write_json(ROOT / 'reports/thread-debug-host-check.json', {'status': 'PASS',
        'sanitizers': ['address', 'undefined'], 'checks': result.stdout.splitlines(),
        'wine_header_sha256': sha(a.source / 'include/winternl.h'),
        'thread_header_sha256': sha(unix / 'horizon_threads.h'),
        'sources': {n: sha(ROOT / n) for n in ('src/sd_thread_debug.h', 'src/sd_thread_debug.inc',
            'src/sd_wow64_debug_cache.h', 'tests/thread_debug.c', 'tests/check_thread_debug.py')},
        'scope': 'Production handlers, stub handle table; native binary test covers actual table lookup.',
        'hardware_tested': False})
    print(result.stdout, end='')

if __name__ == '__main__': main()
