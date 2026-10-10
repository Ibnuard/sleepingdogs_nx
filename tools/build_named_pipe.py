"""Build the cumulative native named-pipe patch in an isolated source tree."""
from pathlib import Path
import argparse
import json
import shutil

from build_launcher import prepare, build_nro
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, sha, write_json
from sleepingdogs_fault_trace import apply as apply_fault_trace

CHANGED = ('dlls/ntdll/unix/horizon.c', 'dlls/ntdll/unix/file.c',
           'dlls/ntdll/unix/sd_named_pipe.h', 'dlls/ntdll/unix/sd_named_pipe.inc',
           'dlls/ntdll/unix/signal_arm64.c', 'dlls/ntdll/unix/sd_fault_trace.inc',
           'wine-nx-probe/source/runtime.c', 'wine-nx-probe/source/f1_crash.c',
           'wine-nx-probe/source/sd_fault_io.inc', 'wine-nx-probe/source/sd_fault_wine_log.h')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-pipe-v1'))
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--refresh-pipe-source', action='store_true',
                   help='Verify the old receipt, then refresh only the two private pipe implementation files')
    a = p.parse_args()
    work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    test = json.loads((ROOT / 'reports/named-pipe-check.json').read_text())
    for n, digest in test['sources'].items():
        if sha(ROOT / n) != digest: raise RuntimeError('Rerun named-pipe tests: ' + n)
    stamp = work / 'pipe-prepared.json'
    if a.refresh_pipe_source:
        # A native compile can expose a missing platform include. Refresh this
        # private implementation without blessing unrelated generated edits.
        prepared = work / 'sleepingdogs-prepared.json'
        previous = json.loads(prepared.read_text())
        source = work / 'native-source'
        for n, digest in json.loads(stamp.read_text()).items():
            if sha(source / n) != digest: raise RuntimeError('Generated source edited outside the build tool: ' + n)
        inputs = {str(f.relative_to(ROOT)): sha(f)
                  for directory in ('tools', 'src', 'config') for f in sorted((ROOT / directory).rglob('*'))
                  if f.is_file() and '__pycache__' not in f.parts and f.suffix != '.pyc'}
        old = previous['identity']['inputs']
        changed = {n for n in set(old) | set(inputs) if old.get(n) != inputs.get(n)}
        allowed = {'src/sd_named_pipe.h', 'src/sd_named_pipe.inc', 'tools/build_named_pipe.py'}
        if not changed <= allowed: raise RuntimeError('Use a fresh work directory for changed inputs: ' + repr(changed))
        write_json(work / 'pipe-refresh-previous.json', {'prepared': previous, 'sources': json.loads(stamp.read_text())})
        for n in ('sd_named_pipe.h', 'sd_named_pipe.inc'):
            shutil.copy2(ROOT / 'src' / n, source / 'dlls/ntdll/unix' / n)
        previous['identity']['inputs'] = inputs
        write_json(prepared, previous)
        write_json(stamp, {n: sha(source / n) for n in CHANGED})
    source, metadata = prepare(work, DEFAULT_GAME / GAME_EXE)
    if stamp.exists():
        for n, digest in json.loads(stamp.read_text()).items():
            if sha(source / n) != digest: raise RuntimeError('Native source changed: ' + n)
    else:
        apply_fault_trace(source)
        write_json(stamp, {n: sha(source / n) for n in CHANGED})
    elf, nro = build_nro(work, source, Path('/home/blekjek/pes13-build'), a.jobs)
    for marker in (b'[SD-PIPE] local named pipes v1', b'[SD-FIRSTFAULT]',
                   b'[SD-DIRECT] allocated 1000 MiB RW', b'fastest'):
        assert marker in nro.read_bytes(), marker
    output = ROOT / 'dist/named-pipe-fix'; output.mkdir(exist_ok=True)
    shutil.copy2(nro, output / nro.name)
    shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-named-pipe.elf')
    receipt = {'build': 'sleepingdogs-local-named-pipe-v1', 'kind': 'compatibility fix',
               'game_boot_confirmed': False, 'hardware_tested': False, 'game': metadata,
               'nro_sha256': sha(nro), 'elf_sha256': sha(elf),
               'base_nro_sha256': '5caf68ad45598cc1a3d461eeeec1f043f5c62d9a8da1e43ae4b91d232d68843f',
               'source_files': {n: sha(source / n) for n in CHANGED},
               'port_inputs': json.loads((work / 'sleepingdogs-prepared.json').read_text())['identity'],
               'tests': test, 'fex_profile': 'fastest (unchanged)',
               'fex_dll_sha256': sha(ROOT / 'vendor/fex/libwow64fex-sd-debug.dll'),
               'memory_fix_preserved': True, 'wow64_context_fix_preserved': True,
               'unsupported': ['APC pipe completion', 'alertable synchronous pipe I/O',
                               'remote pipes', 'pipe impersonation', 'FSCTL_PIPE_WAIT/TRANSCEIVE'],
               'game_exe_or_dll_modified': False}
    write_json(output / 'build.json', receipt)
    print(json.dumps({'nro': str(output / nro.name), 'sha256': sha(nro)}))


if __name__ == '__main__': main()
