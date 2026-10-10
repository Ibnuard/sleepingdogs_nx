"""Build cumulative suspended-thread debug support in a fresh native tree."""
from pathlib import Path
import argparse
import json
import shutil
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, sha, write_json
from build_launcher import prepare, build_nro
from build_debug_cache import FILES as CACHE_FILES
from sleepingdogs_fault_trace import apply as apply_faults

FILES = CACHE_FILES + ('dlls/ntdll/unix/horizon.c', 'dlls/ntdll/unix/horizon_threads.h',
    'dlls/ntdll/unix/sd_thread_debug.h', 'dlls/ntdll/unix/sd_thread_debug.inc')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-thread-debug-v1'))
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args(); work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    out = ROOT / 'dist/thread-debug-fix'; out.mkdir(exist_ok=True)
    source, metadata = prepare(work, DEFAULT_GAME / GAME_EXE)
    stamp = work / 'fault-prepared.json'
    if stamp.exists():
        for n, digest in json.loads(stamp.read_text()).items(): assert sha(source / n) == digest, n
    else:
        apply_faults(source)
        write_json(stamp, {n: sha(source / n) for n in FILES})
    elf, nro = build_nro(work, source, Path('/home/blekjek/pes13-build'), a.jobs)
    for marker in (b'[SD-THREAD-DEBUG] build=v1', b'[SD-TEB-DEBUG] build=v1', b'[SD-FIRSTFAULT] build=v3',
                   b'[SD-PIPE] local named pipes v1', b'[SD-DIRECT] allocated 1000 MiB RW', b'fastest'):
        assert marker in nro.read_bytes(), marker
    shutil.copy2(nro, out / nro.name)
    shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-thread-debug.elf')
    write_json(out / 'native.json', {'build': 'sleepingdogs-suspended-thread-debug-v1',
        'nro_sha256': sha(nro), 'elf_sha256': sha(elf), 'game': metadata,
        'previous_nro_sha256': '8e692c7d2f0f1b1b46c42348eb6bc20ecca4412e4ad55eb36d97909b9057c201',
        'source_files': {n: sha(source / n) for n in FILES},
        'prepared': json.loads((work / 'sleepingdogs-prepared.json').read_text()),
        'hardware_tested': False})
    print('Native suspended-thread debug context:', sha(nro))

if __name__ == '__main__': main()
