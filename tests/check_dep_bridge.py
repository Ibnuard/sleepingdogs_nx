"""Run source-bound DEP notification ordering tests under ASan/UBSan."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); out=a.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    temp=out/'tmp'; temp.mkdir(exist_ok=True)
    exe=out/'dep-bridge'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-g','-O1',
        '-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread',
        str(ROOT/'tests/dep_bridge.c'),'-o',str(exe)],env=dict(os.environ,TMPDIR=str(temp)),check=True)
    result=subprocess.check_output([str(exe)],text=True)
    write_json(ROOT/'reports/dep-bridge-host-check.json',{'status':'PASS',
        'checks':result.splitlines(),'concurrent_changes':4000,'hardware_tested':False,
        'sources':{n:sha(ROOT/n) for n in ('src/sd_wow64_dep.inc','tests/dep_bridge.c','tests/check_dep_bridge.py')},
        'sanitizers':['address','undefined']})
    print(result,end='')
if __name__=='__main__': main()
