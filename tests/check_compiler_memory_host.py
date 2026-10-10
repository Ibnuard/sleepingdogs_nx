"""Sanitize real FEX ownership with the production compile permits."""
from pathlib import Path
import argparse
import os
import resource
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-compiler-memory-v2'))
a = p.parse_args(); fex = a.work / 'fex'; source = fex / 'source'
out = a.work / 'host-check'; out.mkdir(exist_ok=True)
command = ['g++', '-std=c++20', '-O1', '-g', '-pthread', '-DASSERTIONS_ENABLED=1', '-DFMT_HEADER_ONLY',
    '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie',
    '-I' + str(source / 'FEXCore/include'), '-I' + str(source / 'External/fmt/include'),
    '-I' + str(source / 'FEXHeaderUtils'), '-I' + str(fex / 'adapter'),
    str(ROOT / 'tests/compiler_memory_host.cpp'), '-o', str(out / 'compiler-memory')]
with (out / 'compile.log').open('w') as log:
    subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True,
                   env=dict(os.environ, TMPDIR=str(out)))
result = subprocess.check_output([str(out / 'compiler-memory')], text=True, timeout=60)
print(result)
# Same controlled race against the previous pool: FREE is published before
# acquiring AllocationMutex. Disable core dumps for this expected assertion.
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
negative = [x.replace(str(source / 'FEXCore/include'), '/home/blekjek/sleepingdogs-fex-debug-v1/source/FEXCore/include')
            for x in command]
negative[-1] = str(out / 'compiler-memory-old-pool')
with (out / 'negative-compile.log').open('w') as log:
    subprocess.run(negative, stdout=log, stderr=subprocess.STDOUT, check=True)
old = subprocess.run([negative[-1]], text=True, capture_output=True, timeout=15)
assert old.returncode != 0 and 'flags[3].load()==ClientFlags::FLAG_DISOWNED' in old.stderr, old
print('Previous pool retirement race: reproduced expected assertion')
write_json(ROOT / 'reports/compiler-memory-host-check.json', {'status': 'PASS',
    'sanitizers': ['address', 'undefined'], 'results': result.splitlines(),
    'concurrent_threads': 32, 'compiler_lifetimes': 8000, 'decoder_sizes': 70002,
    'previous_pool_retirement_race_reproduced': True,
    'pool_source_sha256': sha(source / 'FEXCore/include/FEXCore/Utils/ThreadPoolAllocator.h'),
    'header_sha256': sha(fex / 'adapter/sd_fex_workspace.h'),
    'sources': {n: sha(ROOT / n) for n in ('src/sd_fex_workspace.h', 'tests/compiler_memory_host.cpp',
                                        'tests/check_compiler_memory_host.py')},
    'hardware_tested': False})
