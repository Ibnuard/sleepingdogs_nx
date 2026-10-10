"""Resolve native crash.log addresses using the exact matching local release ELF."""
from pathlib import Path
import argparse
import re
import subprocess

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--log',type=Path,required=True)
    p.add_argument('--elf',type=Path,required=True)
    args=p.parse_args()
    log=args.log.read_text(errors='replace')
    build=re.search(r'\bbuild=(f1-fextendo-[\w.-]+)',log)
    assert build and build[1].encode() in args.elf.read_bytes(),'ELF build tag does not match the log'
    run_anchor=re.search(r'native_anchor_wine_nx_f1_crash_init=(0x[0-9a-f]+)',log)
    assert run_anchor,'Native anchor missing; do not guess a relocation base'
    prefix='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-'
    symbols=subprocess.check_output([prefix+'nm','-n',str(args.elf)],text=True)
    linked=re.search(r'^(\w+)\s+T\s+wine_nx_f1_crash_init$',symbols,re.M)
    assert linked
    delta=int(run_anchor[1],16)-int(linked[1],16)
    addresses=re.findall(r'\b(pc|lr|caller)=(0x[0-9a-f]+)',log)
    addresses += [('exit-caller',value) for value in re.findall(r'native-_?exit result=\S+ a=(0x[0-9a-f]+)',log)]
    if not addresses:
        print('No native exception/exit address was captured; checkpoints alone cannot locate the crash.')
    for key,value in addresses:
        address=int(value,16)
        if not address:continue
        relocated=address-delta
        print(f'{key}: runtime={address:#x} ELF={relocated:#x}')
        if relocated<0:print('Outside native image; may be generated JIT code.');continue
        subprocess.run([prefix+'addr2line','-a','-f','-C','-e',str(args.elf),hex(relocated)],check=True)

if __name__=='__main__':main()
