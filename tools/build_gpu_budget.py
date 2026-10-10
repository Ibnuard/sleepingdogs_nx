"""Build the cumulative native GPU budget repair in an immutable fresh tree."""
from pathlib import Path
import argparse
import json
import shutil
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, sha, write_json
from build_launcher import prepare, build_nro
from build_memory_budget import FILES as PREVIOUS_FILES, ADAPTER_FILES
from sleepingdogs_fault_trace import apply as apply_faults

FILES = PREVIOUS_FILES + ('wine-nx-probe/source/sd_gpu_budget.h',)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-gpu-budget-v1'))
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args(); work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    out = ROOT / 'dist/gpu-budget-fix'; out.mkdir(exist_ok=True)
    source, metadata = prepare(work, DEFAULT_GAME / GAME_EXE)
    stamp = work / 'fault-prepared.json'
    if not stamp.exists():
        apply_faults(source); write_json(stamp, {n: sha(source / n) for n in FILES})
    for n, digest in json.loads(stamp.read_text()).items(): assert sha(source / n) == digest, n
    elf, nro = build_nro(work, source, Path('/home/blekjek/pes13-build'), a.jobs)
    for marker in (b'[SD-GPU-BUDGET] v1 paired_loader=', b'[SD-COMPILER-MEM] native=v1',
                   b'[SD-FIRSTFAULT] build=v3', b'[SD-THREAD-DEBUG] build=v1',
                   b'[SD-MEMORY-BUDGET] build=v2 gpu_reserve_max_mib=256', b'fastest'):
        assert marker in nro.read_bytes(), marker
    shutil.copy2(nro, out / nro.name)
    shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-gpu-budget.elf')
    write_json(out / 'native.json', {'build': 'sleepingdogs-gpu-budget-v1',
        'nro_sha256': sha(nro), 'elf_sha256': sha(elf), 'game': metadata,
        'gpu_preallocation_bytes': 268435456, 'fallback_gpu_preallocation_bytes': 134217728,
        'loader_required': 'sleepingdogs-gpu-budget-v1', 'minimum_heap_bytes': 2046820352,
        'fex_sha256': sha(ROOT / 'vendor/fex/libwow64fex-sd-compiler.dll'),
        'source_files': {n: sha(source / n) for n in FILES},
        'adapter_files': {n: sha(work / 'fex-adapter' / n) for n in ADAPTER_FILES},
        'prepared': json.loads((work / 'sleepingdogs-prepared.json').read_text()),
        'hardware_tested': False})
    print('Native GPU budget:', sha(nro), flush=True)


if __name__ == '__main__': main()
