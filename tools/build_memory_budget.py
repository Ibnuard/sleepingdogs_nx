"""Build cumulative native headroom/stack reserve repair in a fresh tree."""
from pathlib import Path
import argparse
import json
import shutil
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, sha, write_json
from build_launcher import prepare, build_nro
from build_thread_debug import FILES as THREAD_FILES
from sleepingdogs_fault_trace import apply as apply_faults

FILES = THREAD_FILES + tuple('wine-nx-probe/source/' + n for n in
    ('f1_gpu_arena.h', 'f1_gpu_heap.c', 'f1_native_stacks.c', 'f1_native_stacks.h', 'f1_thread_diagnostics.c'))
ADAPTER_FILES = ('f1_scratch.h', 'horizon_jit.c')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-memory-budget-v1'))
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args(); work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    out = ROOT / 'dist/memory-budget-fix'; out.mkdir(exist_ok=True)
    source, metadata = prepare(work, DEFAULT_GAME / GAME_EXE)
    stamp = work / 'fault-prepared.json'
    if stamp.exists():
        for n, digest in json.loads(stamp.read_text()).items(): assert sha(source / n) == digest, n
    else:
        apply_faults(source)
        write_json(stamp, {n: sha(source / n) for n in FILES})
    elf, nro = build_nro(work, source, Path('/home/blekjek/pes13-build'), a.jobs)
    for marker in (b'[SD-MEMORY-BUDGET] build=v1 gpu_reserve_mib=128', b'[SD-THREAD-DEBUG] build=v1',
                   b'[SD-TEB-DEBUG] build=v1', b'[SD-FIRSTFAULT] build=v3',
                   b'[SD-PIPE] local named pipes v1', b'[SD-DIRECT] allocated 1000 MiB RW', b'fastest'):
        assert marker in nro.read_bytes(), marker
    shutil.copy2(nro, out / nro.name)
    shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-memory-budget.elf')
    write_json(out / 'native.json', {'build': 'sleepingdogs-native-headroom-v1',
        'nro_sha256': sha(nro), 'elf_sha256': sha(elf), 'game': metadata,
        'gpu_preallocation_bytes': 134217728, 'previous_gpu_preallocation_bytes': 268435456,
        'stack_reserve_request_min': 4096, 'stack_reserve_request_max': 1048576,
        'stack_reserve_request_alignment': 4096, 'stack_backing_unchanged': True,
        'previous_nro_sha256': '9b6ae2ca73fba7a8ff2522e961301e5a49b565ddfa065501100d38f4744c55db',
        'source_files': {n: sha(source / n) for n in FILES},
        'adapter_files': {n: sha(work / 'fex-adapter' / n) for n in ADAPTER_FILES},
        'prepared': json.loads((work / 'sleepingdogs-prepared.json').read_text()),
        'hardware_tested': False})
    print('Native memory headroom:', sha(nro))

if __name__ == '__main__': main()
