"""Run the first-fault recorder with ASan/UBSan and save a source-bound receipt."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    temp = out / 'tmp'; temp.mkdir(exist_ok=True)
    env = dict(os.environ, TMPDIR=str(temp))
    cc = shutil.which('gcc') or shutil.which('cc')
    exe = out / 'fault-trace'
    subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-fno-omit-frame-pointer', str(ROOT/'tests/fault_trace.c'), '-o', str(exe)],
                   check=True, env=env)
    result = subprocess.run([str(exe)], text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=True)
    (out / 'results.txt').write_text(result.stdout)
    receipt = {'status': 'PASS', 'hardware_tested': False,
               'sanitizers': ['address', 'undefined'],
               'checks': result.stdout.splitlines(),
               'sources': {n: sha(ROOT/n) for n in ('tests/fault_trace.c', 'tests/check_fault_trace.py',
                   'src/sd_fault_trace.inc', 'src/sd_fault_io.inc', 'src/sd_fault_wine_log.h')}}
    write_json(ROOT / 'reports/first-fault-host-check.json', receipt)
    print(result.stdout, end='')

if __name__ == '__main__': main()
