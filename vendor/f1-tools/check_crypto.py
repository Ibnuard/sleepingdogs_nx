"""Check F1 crypto registration using the actual Horizon registry implementation."""
from pathlib import Path
import argparse
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
compiler = shutil.which('clang') or shutil.which('cc')
if not compiler:
    raise SystemExit('A host C compiler is required')
exe = args.output.resolve() / 'crypto-registry-check'
subprocess.run([compiler, '-std=c11', '-O1', '-g', '-Wall',
                '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                '-I', str(args.source.resolve() / 'dlls/ntdll/unix'),
                str(Path(__file__).resolve().parents[1] / 'tests/crypto_registry.c'),
                '-o', str(exe)], check=True)
subprocess.run([str(exe)], check=True)
