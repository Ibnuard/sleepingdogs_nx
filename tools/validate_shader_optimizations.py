"""Run the v9 build and focused source/binary regression checks sequentially."""
from pathlib import Path
import argparse
import subprocess
import sys
from port_common import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',action='store_true')
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--native-only',action='store_true',help='WSL compiler/build/source checks')
    modes.add_argument('--binary-only',action='store_true',help='Python environment with Unicorn/pyelftools/pefile')
    args=parser.parse_args()
    commands=[]
    assert not (args.build and args.binary_only)
    if args.build:
        commands += [['tests/check_shader_optimizations.py','--before-build'],['tools/build_shader_optimizations.py']]
    if not args.binary_only:commands.append(['tests/check_shader_optimizations.py'])
    if not args.native_only:commands.append(['tests/check_shader_binary.py'])
    for script,name in ([] if args.native_only else [('check_cpu_topology_binary.py','cpu-topology'),
                        ('check_sync_startup_binary.py','sync-startup-binary'),
                        ('check_low_window_binary.py','binary')]):
        commands.append(['tests/'+script,'--elf','local/symbols/sleepingdogs-low-window-v9.elf',
                         '--report','reports/low-window-v9-'+name+'.json'])
    for command in commands:
        print('Running',command[0],flush=True)
        subprocess.run([sys.executable,*command],cwd=ROOT,check=True)


if __name__=='__main__':main()
