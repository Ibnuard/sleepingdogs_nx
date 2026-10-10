"""ASan/UBSan: actual patched loader calculation, budget gate and GPU arena."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json


def function(text, name):
    start = text.index('static u64 ' + name + '(void)')
    begin = text.index('{', start); level = 1; end = begin + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[start:end]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-gpu-budget-v1'))
    p.add_argument('--forwarder-work', type=Path, default=Path('/home/blekjek/sleepingdogs-gpu-forwarder-v1'))
    a = p.parse_args(); out = a.work / 'gpu-host-check'; out.mkdir(exist_ok=True)
    native = a.work / 'native-source/wine-nx-probe/source'
    original = ROOT / 'forwarder/hbl/source/main.c'; patched = a.forwarder_work / 'source/main.c'
    old = function(original.read_text(), 'calculateMaxHeapSize').replace('calculateMaxHeapSize', 'baselineMaxHeapSize')
    new = function(patched.read_text(), 'calculateMaxHeapSize')
    (out / 'loader_calculations.h').write_text(old + '\n' + new + '\n')
    results = []
    for name in ('gpu_budget_host', 'memory_gpu_arena'):
        exe = out / name
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-pthread', '-fsanitize=address,undefined',
            '-fno-sanitize-recover=all', '-fno-pie', '-no-pie', '-I' + str(out), '-I' + str(native),
            ROOT / 'tests' / (name + '.c'), '-o', exe], check=True, env=dict(os.environ, TMPDIR=str(out)))
        result = subprocess.run([str(exe)], check=True, text=True, capture_output=True)
        results += result.stdout.splitlines(); print(result.stdout, end='', flush=True)
    write_json(ROOT / 'reports/gpu-budget-host-check.json', {'status': 'PASS',
        'native_elf_sha256': sha(ROOT / 'local/symbols/sleepingdogs-gpu-budget.elf'),
        'forwarder_elf_sha256': sha(a.forwarder_work / 'forwarder.elf'),
        'sanitizers': ['address', 'undefined'], 'checks': results,
        'compiled_sources': {str(p): sha(p) for p in
            (original, patched, native / 'sd_gpu_budget.h', native / 'f1_gpu_arena.h')},
        'sources': {n: sha(ROOT / n) for n in ('tests/check_gpu_budget_host.py',
            'tests/gpu_budget_host.c', 'tests/memory_gpu_arena.c')}, 'hardware_tested': False})


if __name__ == '__main__': main()
