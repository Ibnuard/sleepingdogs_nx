"""Build DEP notification WoW64 and non-debug fault capture in isolated trees."""
from pathlib import Path
import argparse
import json
import shutil
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, sha, write_json
from build_launcher import prepare, build_nro
from sleepingdogs_fault_trace import apply as apply_faults
from wow64_context_fix import build as build_wow64

NATIVE_FILES = ('dlls/ntdll/unix/signal_arm64.c', 'dlls/ntdll/unix/sd_fault_trace.inc',
    'wine-nx-probe/source/runtime.c', 'wine-nx-probe/source/f1_crash.c',
    'wine-nx-probe/source/sd_fault_io.inc', 'wine-nx-probe/source/sd_fault_wine_log.h')
WOW_FILES = tuple('dlls/wow64/' + n for n in ('syscall.c', 'process.c', 'wow64_private.h', 'sd_wow64_dep.inc'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-dep-v1'))
    p.add_argument('--component', choices=('native', 'wow64'), required=True)
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args()
    out = ROOT / 'dist/dep-policy-fix'; out.mkdir(exist_ok=True)
    deps = Path('/home/blekjek/pes13-build')
    work = a.work.resolve() / a.component; work.mkdir(parents=True, exist_ok=True)
    if a.component == 'wow64':
        dll, receipt = build_wow64(work, deps, a.jobs)
        receipt['build'] = 'sleepingdogs-wow64-dep-notification-v1'
        receipt['source_files'] = {n: sha(work / 'source' / n) for n in WOW_FILES}
        receipt['previous_dll_sha256'] = 'cce529e75bc5417f56781b2654d8298e0a8e9cfced0a6b5a742a0768c7dab199'
        shutil.copy2(dll, out / 'wow64.dll')
        write_json(out / 'wow64.json', receipt)
        print('WoW64 DEP bridge:', sha(dll))
    else:
        source, metadata = prepare(work, DEFAULT_GAME / GAME_EXE)
        stamp = work / 'fault-prepared.json'
        if stamp.exists():
            for n, digest in json.loads(stamp.read_text()).items(): assert sha(source / n) == digest, n
        else:
            apply_faults(source)
            write_json(stamp, {n: sha(source / n) for n in NATIVE_FILES})
        elf, nro = build_nro(work, source, deps, a.jobs)
        for marker in (b'[SD-PIPE] local named pipes v1', b'[SD-FIRSTFAULT] build=v2',
                       b'[SD-DIRECT] allocated 1000 MiB RW', b'fastest'):
            assert marker in nro.read_bytes(), marker
        shutil.copy2(nro, out / nro.name)
        shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-dep-policy.elf')
        write_json(out / 'native.json', {'build': 'sleepingdogs-post-frame-fault-v2',
            'nro_sha256': sha(nro), 'elf_sha256': sha(elf), 'game': metadata,
            'previous_nro_sha256': 'bbcee4dfc39105a8f40545e5c0e0156ddd9b9eeea7f4c190387090accf705b29',
            'source_files': {n: sha(source / n) for n in NATIVE_FILES},
            'prepared': json.loads((work / 'sleepingdogs-prepared.json').read_text()),
            'hardware_tested': False})
        print('Native post-frame fault capture:', sha(nro))


if __name__ == '__main__': main()
