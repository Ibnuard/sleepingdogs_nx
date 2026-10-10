"""Compile/run the actual pipe transport under ASan/UBSan against pinned Wine headers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('/home/blekjek/sleepingdogs-fault-trace-v2/native-source'))
    p.add_argument('--output', type=Path, default=Path('/home/blekjek/sleepingdogs-pipe-tests'))
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    command = ['gcc', '-std=gnu11', '-g', '-O1', '-fno-omit-frame-pointer', '-fshort-wchar',
               '-fsanitize=address,undefined', '-pthread', '-Wno-attributes',
               '-I' + str(ROOT / 'src'), '-I' + str(a.source / 'include'),
               '-I' + str(a.source / 'dlls/ntdll/unix'), str(ROOT / 'tests/named_pipe.c'),
               '-o', str(a.output / 'named_pipe')]
    subprocess.run(command, check=True)
    result = subprocess.run([str(a.output / 'named_pipe')], check=True, capture_output=True, text=True, timeout=40)
    result = json.loads(result.stdout)
    result['sanitizers'] = ['address', 'undefined']
    result['sources'] = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in
                         ('src/sd_named_pipe.inc', 'src/sd_named_pipe.h', 'tests/named_pipe.c')}
    result['limitations'] = ['Host handle/TEB/scheduler fixture; Switch boot not confirmed',
                             'APC completion and alertable synchronous pipe I/O explicitly unsupported']
    (ROOT / 'reports/named-pipe-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
