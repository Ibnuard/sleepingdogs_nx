"""Package a one-file Fast/TSO comparison and a separate Fastest restoration."""
from pathlib import Path
import argparse
import json
import zipfile

from port_common import ROOT, sha, write_json
from package_named_pipe import archive, PREFIX


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('//wsl$/Ubuntu/home/blekjek/sleepingdogs-low-window-v1'))
    args = parser.parse_args()
    baseline = ROOT / 'dist/sleepingdogs-fex-low-window-loading-watch.zip'
    baseline_hash = '7d6f58a6ec01e053807d6093b52eceb7f13c737949c9290d0516a213aaf24094'
    assert sha(baseline) == baseline_hash
    with zipfile.ZipFile(baseline) as z:
        native = json.loads(z.read('source/low-window-loading-watch/native.json'))
    nro = ROOT / 'dist/low-window-loading-watch/sleepingdogs-fex.nro'
    assert sha(nro) == native['nro_sha256']
    dll = ROOT / 'vendor/fex/libwow64fex-sd-scene.dll'
    dll_hash = '48b169a80966676100c7b361343072766973809a80727cb2fcfe8bb33a300024'
    assert sha(dll) == dll_hash
    selector = 'wine-nx-probe/source/f1_fex_mode.h'
    assert sha(args.work / 'native-source' / selector) == native['source_files'][selector]
    for name in ('module_profile.cpp', 'horizon_jit.c', 'horizon_host.h', 'module_host.cpp'):
        assert sha(args.work / 'fex-adapter' / name) == native['adapter_files'][name]
    assert b'[FEX3-PRESET] fast x87=64 scalar_tso=1 vector_tso=1 memcpy_tso=1 multiblock=1 smc=mtrack' in dll.read_bytes()
    assert b'launcher/fex-mode.txt: fast' in nro.read_bytes()
    analysis_path = ROOT / 'reports/low-window-invalid-semaphore-analysis.json'
    analysis = json.loads(analysis_path.read_text())
    assert analysis['input_sha256'] == 'bc83d378715f4e3284feeff39ffea08fda92f74b661605d7e5b8a63a0791b7f3'
    assert analysis['profile'] == 'fastest' and not analysis['hardware_fix_confirmed']

    target = PREFIX + 'launcher/fex-mode.txt'
    entries = {
        target: b'fast\n',
        'README.txt': (ROOT / 'docs/low-window-tso-test.md').read_bytes(),
        'source/low-window-tso-test/analysis.json': analysis_path.read_bytes(),
        'source/low-window-tso-test/package_tso_test.py': Path(__file__).read_bytes(),
        'source/low-window-tso-test/analyze_loading_freeze.py': (ROOT / 'tools/analyze_loading_freeze.py').read_bytes(),
    }
    assert {n for n in entries if n.startswith('switch/')} == {target}
    assert entries[target] == b'fast\n'
    for name in entries:
        assert not name.lower().endswith(('.log', '.nsp', '.kip', '.nro', '.dll', '.exe', '.big', '.bix'))
    out = ROOT / 'dist/sleepingdogs-fex-low-window-tso-test.zip'
    update = archive(out, entries)
    restore = archive(ROOT / 'dist/sleepingdogs-fex-restore-fastest.zip', {
        target: b'fastest\n',
        'README.txt': b'Tutup Sleeping Dogs dari HOME, lalu timpa folder switch/ ke root SD. '
                      b'Mengembalikan hanya launcher/fex-mode.txt ke fastest. Buka ulang aplikasi; '
                      b'tidak perlu install NSP/reboot. Jangan pasang bersamaan dengan ZIP tes TSO.\n',
    })
    # Keep a ready-to-copy directory as well; never overwrite a returned log or
    # unrelated extracted data, even if the user reuses this directory later.
    stage = ROOT / 'dist/sleepingdogs-fex-low-window-tso-test'
    for name in (target, 'README.txt'):
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            assert path.read_bytes() == entries[name], f'Preserve edited staging file: {path}'
        else:
            path.write_bytes(entries[name])
    report = dict(status='PASS', update=update, restore=restore, diagnostic_only=True,
                  runtime_files_changed=[target], new_mode='fast', previous_mode='fastest',
                  full_tso_enabled=True, native_and_dll_payloads=0,
                  prerequisite_nro_sha256=native['nro_sha256'], prerequisite_dll_sha256=dll_hash,
                  baseline_zip_preserved=sha(baseline) == baseline_hash,
                  source_selector_verified=True, hardware_tested=False, freeze_fix_confirmed=False)
    write_json(ROOT / 'reports/low-window-tso-test-package.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
