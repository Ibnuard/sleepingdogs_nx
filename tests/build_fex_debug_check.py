"""Compile the actual JIT guard emitter against its private FEX source tree."""
from pathlib import Path
import argparse
import json
import subprocess
import shutil
import shlex
import struct

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-fex-debug-v1'))
a = p.parse_args(); work = a.work
source, adapter = work / 'source', work / 'adapter'
out = work / 'check'; out.mkdir(exist_ok=True)
command = ['g++', '-std=c++20', '-O2', '-g', '-DASSERTIONS_ENABLED=1', '-DFMT_HEADER_ONLY',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           '-I' + str(source / 'CodeEmitter'), '-I' + str(source / 'FEXCore/include'),
           '-I' + str(source / 'Source/Common'), '-I' + str(source / 'External/fmt/include'),
           '-I' + str(source / 'FEXHeaderUtils'), '-I' + str(adapter),
           str(ROOT / 'tests/fex_debug_emitter.cpp'), '-o', str(out / 'emitter')]
with (out / 'compile.log').open('w') as log:
    subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
result = subprocess.check_output([str(out / 'emitter'), str(out / 'guard.bin')], text=True)
json.loads(result)
(out / 'layout.json').write_text(result)
target = ROOT / 'local/fex-debug-check'; target.mkdir(exist_ok=True)
for name in ('guard.bin', 'layout.json'): shutil.copy2(out / name, target / name)
# Verify the offsets with the actual production cross-compiler as well.
commands = json.loads((work / 'build/compile_commands.json').read_text())
entry = next(c for c in commands if c['file'].endswith('/JIT/MiscOps.cpp'))
flags = shlex.split(entry['command'])
for option in ('-o', '-c', '-MF', '-MT'):
    if option in flags:
        i = flags.index(option); del flags[i:i+2]
flags = [f for f in flags if f != '-MD']
obj = out / 'layout.obj'
flags += ['-fno-access-control', '-Wno-invalid-offset', '-Wno-invalid-offset-of',
          '-c', str(ROOT / 'tests/fex_debug_layout.cpp'), '-o', str(obj)]
with (out / 'layout-compile.log').open('w') as log:
    subprocess.run(flags, cwd=entry['directory'], stdout=log, stderr=subprocess.STDOUT, check=True)
data = obj.read_bytes(); machine, sections = struct.unpack_from('<HH', data)
assert machine == 0xaa64
optional_size = struct.unpack_from('<H', data, 16)[0]
for i in range(sections):
    at = 20 + optional_size + 40 * i
    if data[at:at+8].rstrip(b'\0') == b'.sdmeta':
        size, offset = struct.unpack_from('<II', data, at + 16)
        values = struct.unpack_from('<' + 'Q' * (size // 8), data, offset)
        break
else: raise RuntimeError('No compiler fixture section')
names = ['jit_size', 'buffer', 'cursor', 'buffer_size', 'writable', 'entry', 'spills', 'op_size',
         'op_offset', 'frame_size', 'address', 'enabled', 'hit', 'resume_rip', 'rip', 'rf', 'fault', 'signal']
cross = dict(zip(names, values))
for key, value in json.loads(result).items():
    if key != 'bytes': assert cross[key] == value, (key, cross[key], value)
(target / 'dll-layout.json').write_text(json.dumps(cross, indent=2) + '\n')
print(result)
