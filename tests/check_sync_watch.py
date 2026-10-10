"""Run the exact sync collector/bridge under ASan and UBSan on the host."""
from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/low-window-v5-sync-watch.json')
    args = parser.parse_args()
    out = args.work / 'sync-watch-check'
    out.mkdir(exist_ok=True)
    executable = out / 'check'
    subprocess.run(['gcc', '-std=gnu11', '-g', '-O1', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-pthread', '-I'+str(ROOT / 'src/low_window'), str(ROOT / 'tests/sync_watch.c'),
                    '-o', str(executable)], check=True)
    result = subprocess.run([str(executable)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout, end='')
    cases = result.stdout.splitlines()
    assert len(cases) == 12 and all(line.startswith('PASS ') for line in cases)
    write_json(args.report, {
        'status': 'PASS', 'asan': True, 'ubsan': True, 'hardware_tested': False, 'cases': cases,
        'sources': {name: sha(ROOT / name) for name in
                    ('src/low_window/sd_sync_watch.h', 'src/low_window/sd_sync_watch.inc',
                     'src/low_window/sd_sync_bridge.inc', 'tests/sync_watch.c', 'tests/check_sync_watch.py')}})


if __name__ == '__main__':
    main()
