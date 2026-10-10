"""Build the cumulative TEB debug-cache repair in a fresh isolated native tree."""
from pathlib import Path
import argparse
import json
import shutil
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, sha, write_json
from build_launcher import prepare, build_nro
from build_dep_fix import NATIVE_FILES
from sleepingdogs_fault_trace import apply as apply_faults

FILES = NATIVE_FILES + ('dlls/ntdll/unix/horizon_wow64.h',
                        'dlls/ntdll/unix/sd_wow64_debug_cache.h', 'dlls/ntdll/signal_i386.c')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-debug-cache-v1'))
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args(); work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    out = ROOT / 'dist/debug-cache-fix'; out.mkdir(exist_ok=True)
    source, metadata = prepare(work, DEFAULT_GAME / GAME_EXE)
    stamp = work / 'fault-prepared.json'
    if stamp.exists():
        for n, digest in json.loads(stamp.read_text()).items(): assert sha(source / n) == digest, n
    else:
        apply_faults(source)
        write_json(stamp, {n: sha(source / n) for n in FILES})
    elf, nro = build_nro(work, source, Path('/home/blekjek/pes13-build'), a.jobs)
    for marker in (b'[SD-TEB-DEBUG] build=v1', b'[SD-FIRSTFAULT] build=v3',
                   b'[SD-PIPE] local named pipes v1', b'[SD-DIRECT] allocated 1000 MiB RW', b'fastest'):
        assert marker in nro.read_bytes(), marker
    shutil.copy2(nro, out / nro.name)
    shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-debug-cache.elf')
    write_json(out / 'native.json', {'build': 'sleepingdogs-teb-debug-cache-v1',
        'nro_sha256': sha(nro), 'elf_sha256': sha(elf), 'game': metadata,
        'previous_nro_sha256': 'c4658fab27181d98ce39b4dd08f71725b775bcf182ff61010e956736de07abbf',
        'source_files': {n: sha(source / n) for n in FILES},
        'prepared': json.loads((work / 'sleepingdogs-prepared.json').read_text()),
        'hardware_tested': False})
    print('Native TEB debug cache:', sha(nro))

if __name__ == '__main__': main()
