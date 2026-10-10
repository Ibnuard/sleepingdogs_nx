"""Extract decoder fixture offsets with the exact production FEX compiler flags."""
from pathlib import Path
import argparse
import json
import shlex
import struct
import subprocess
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-compiler-memory-v2'))
a = p.parse_args(); fex = a.work / 'fex'
commands = json.loads((fex / 'build/compile_commands.json').read_text())
entry = next(c for c in commands if c['file'].endswith('/Core/Frontend.cpp'))
flags = shlex.split(entry['command'])
for option in ('-o', '-c', '-MF', '-MT'):
    if option in flags:
        i = flags.index(option); del flags[i:i+2]
flags = [f for f in flags if f != '-MD']
out = a.work / 'host-check'; out.mkdir(exist_ok=True)
obj = out / 'compiler-layout.obj'
flags += ['-fno-access-control', '-Wno-invalid-offset-of', '-c',
          str(ROOT / 'tests/compiler_memory_layout.cpp'), '-o', str(obj)]
with (out / 'layout-compile.log').open('w') as log:
    subprocess.run(flags, cwd=entry['directory'], stdout=log, stderr=subprocess.STDOUT, check=True)
data = obj.read_bytes(); machine, sections = struct.unpack_from('<HH', data); assert machine == 0xaa64
optional = struct.unpack_from('<H', data, 16)[0]
for i in range(sections):
    at = 20 + optional + 40*i
    if data[at:at+8].rstrip(b'\0') == b'.sdmeta':
        size, offset = struct.unpack_from('<II', data, at+16)
        values = struct.unpack_from('<'+'Q'*(size//8), data, offset); break
else: raise RuntimeError('Fixture metadata missing')
names = ('decoder_size ctx_size thread_size frame_size pool_size entry_size ctx pool capacity buffer '
         'decoded maxinst final paused info range_base range_end ctx_pool ctx_maxinst ctx_multiblock '
         'thread_ctx thread_frame segments blocks block_size block_entry block_bytes block_count '
         'block_data block_status pending start_offset entry_block erase_block frame_thread syscall').split()
assert len(names) == len(values)
target = ROOT / 'local/compiler-memory-layout.json'
target.write_text(json.dumps(dict(zip(names, values)), indent=2)+'\n')
print(target)
