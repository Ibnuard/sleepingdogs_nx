"""Run the actual direct arena/view implementation with ASan/UBSan on Linux."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--production-size',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,TMPDIR=str(out),ASAN_OPTIONS='detect_leaks=1:handle_segv=0')
    binary=out/'direct-arena-check'
    command=['cc','-std=c11','-g','-O1','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie',
             '-I',str(ROOT/'src'),str(ROOT/'tests/direct_arena.c'),'-o',str(binary)]
    if args.production_size: command.insert(1,'-DSD_GUEST_ARENA_BYTES=1048576000UL')
    subprocess.run(command,env=env,check=True)
    result=subprocess.run([binary],env=env,text=True,capture_output=True)
    (out/'output.txt').write_text(result.stdout+result.stderr)
    print(result.stdout+result.stderr)
    result.check_returncode()
    cases=[line[5:] for line in result.stdout.splitlines() if line.startswith('PASS ')]
    assert len(cases)==15, cases
    write_json(ROOT/'reports/direct-arena-host-check.json',{'status':'PASS','hardware_tested':False,
        'sanitizers':['address','undefined'],'cases':cases,'test_arena_bytes':1048576000 if args.production_size else 1048576,
        'production_arena_bytes':1048576000,'sources':{str(p.relative_to(ROOT)):sha(p)
          for p in [ROOT/'tests/direct_arena.c',ROOT/'src/sd_guest_arena.c',ROOT/'src/sd_guest_arena.h',ROOT/'src/sd_guest_view.inc']}})

if __name__=='__main__':main()
