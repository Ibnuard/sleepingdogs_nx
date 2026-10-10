"""Build an isolated diagnostic NRO on top of every existing startup fix."""
from pathlib import Path
import argparse
import json
import shutil

from build_launcher import prepare, build_nro
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, sha, write_json
from sleepingdogs_fault_trace import apply

CHANGED = ('dlls/ntdll/unix/signal_arm64.c', 'dlls/ntdll/unix/sd_fault_trace.inc',
           'wine-nx-probe/source/runtime.c', 'wine-nx-probe/source/f1_crash.c',
           'wine-nx-probe/source/sd_fault_io.inc', 'wine-nx-probe/source/sd_fault_wine_log.h')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-fault-trace-v1'))
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    work = args.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    source, _ = prepare(work, DEFAULT_GAME / GAME_EXE)
    stamp = work / 'fault-trace-prepared.json'
    if stamp.exists():
        files = json.loads(stamp.read_text())
        for name, digest in files.items():
            if sha(source / name) != digest: raise RuntimeError('Diagnostic source changed: ' + name)
    else:
        apply(source)
        write_json(stamp, {n: sha(source / n) for n in CHANGED})
    elf, nro = build_nro(work, source, Path('/home/blekjek/pes13-build'), args.jobs)
    for token in (b'[SD-FIRSTFAULT]', b'[SD-DIRECT] allocated 1000 MiB RW', b'fastest'):
        assert token in nro.read_bytes(), token
    out = ROOT / 'dist/first-fault-trace'; out.mkdir(exist_ok=True)
    shutil.copy2(nro, out / nro.name)
    shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-first-fault.elf')
    receipt = {'kind': 'diagnostic', 'build': 'sleepingdogs-first-fault-v1',
        'game_boot_confirmed': False, 'hardware_tested': False,
        'nro_sha256': sha(nro), 'elf_sha256': sha(elf),
        'base_nro_sha256': sha(ROOT / 'dist/direct-arena-fix/sleepingdogs-fex.nro'),
        'source_files': {n: sha(source / n) for n in CHANGED},
        'prepared_inputs': json.loads((work / 'sleepingdogs-prepared.json').read_text())['identity'],
        'max_guest_snapshots': 4, 'max_seh_lines': 256, 'max_wow_exception_lines': 32,
        'persistent_first_snapshot': 'crash.log offset 28672, capacity 4096',
        'exception_handling_changed': False, 'fex_profile': 'fastest (unchanged)',
        'memory_fix_preserved': True, 'wow64_dll_changed': False}
    write_json(out / 'build.json', receipt)
    print(json.dumps({'nro': str(out / nro.name), 'sha256': sha(nro), 'kind': 'diagnostic'}))

if __name__ == '__main__': main()
