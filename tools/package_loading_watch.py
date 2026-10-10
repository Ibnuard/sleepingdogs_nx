"""Package an NRO-only Debug observation update against the shipped v2 NRO."""
from pathlib import Path
import argparse
import json
import zipfile

from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode, PREFIX
from build_dxvk_memory import manifest

BASE_SHA = '9035631d3c17c7b10ccc09f24dab96097bb18c27c18acbb8fad33f4b6b65dd8a'
EXPECTED_CHANGES = {'wine-nx-probe/source/runtime.c', 'wine-nx-probe/source/thread_profile.c',
                    'wine-nx-probe/source/sd_loading_watch.h', 'wine-nx-probe/source/sd_loading_report.inc'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    args = parser.parse_args()
    out = ROOT / 'dist/low-window-loading-watch'
    native = json.loads((out / 'native.json').read_text())
    assert native['build'] == 'sleepingdogs-low-window-v3-loading-watch'
    assert native['source_files'] == manifest(args.work / 'native-source')
    assert native['adapter_files'] == manifest(args.work / 'fex-adapter')
    for name, digest in native['build_inputs'].items():
        assert sha(ROOT / name) == digest, name
    nro = out / 'sleepingdogs-fex.nro'
    assert sha(nro) == native['nro_sha256']
    assert sha(ROOT / 'local/symbols/sleepingdogs-low-window-v3.elf') == native['elf_sha256']
    data = nro.read_bytes()
    for marker in (b'low-window-v3-load-watch', b'[SD-LOAD] v1', b'[SD-WATCH] v2',
                   b'[SD-INIT] v2', b'[SD-LOWVA] v1', b'fastest'):
        assert marker in data, marker
    base = ROOT / 'dist/sleepingdogs-fex-low-window-launch-order-fix.zip'
    assert sha(base) == BASE_SHA
    with zipfile.ZipFile(base) as z:
        old = json.loads(z.read('source/low-window-launch-order-fix/native.json'))
        receipts = {n: json.loads(z.read(n)) for n in z.namelist()
                    if n.startswith(PREFIX + 'launcher/') and n.endswith('.json')}
    assert native['adapter_files'] == old['adapter_files']
    assert not set(old['source_files']) - set(native['source_files'])
    changed = {n: h for n, h in native['source_files'].items() if old['source_files'].get(n) != h}
    assert set(changed) == EXPECTED_CHANGES, sorted(changed)
    reports = {}
    for name in ('low-window-loading-watch', 'low-window-v3-launch-order',
                 'low-window-v3-binary', 'low-window-v3-admission-binary'):
        report = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        assert report['status'] == 'PASS'
        if 'elf_sha256' in report:
            assert report['elf_sha256'] == native['elf_sha256']
        for n, digest in report.get('source_files', {}).items():
            relative = n if '/' in n else 'wine-nx-probe/source/' + n
            assert native['source_files'][relative] == digest, (name, n)
        for n, digest in report.get('sources', {}).items():
            assert sha(ROOT / n) == digest, (name, n)
        reports[name] = report
    assert reports['low-window-v3-launch-order']['test_sha256'] == sha(ROOT / 'tests/check_launch_order.py')
    assert reports['low-window-v3-admission-binary']['test_sha256'] == sha(ROOT / 'tests/check_launch_memory_binary.py')
    assert reports['low-window-v3-admission-binary']['harness_sha256'] == sha(ROOT / 'tests/check_low_window_binary.py')
    metrics = ROOT.parent / 'pes13-nx/local/production-input-fix/approved/source/src/runtime/fex_frame_metrics.h'
    assert reports['low-window-loading-watch']['metrics_sha256'] == sha(metrics)
    compatible = json.loads((ROOT / 'dist/low-window-startup-fix/forwarder/build.json').read_text())
    assert compatible['sha256'] == sha(ROOT / 'dist/low-window-startup-fix/forwarder' / compatible['nsp'])
    entries = {PREFIX + nro.name: data, 'README-INSTALL.txt': (ROOT / 'docs/low-window-loading-watch.md').read_bytes()}
    for name, receipt in receipts.items():
        assert '/presets/' not in name
        if 'nro_sha256' not in receipt:
            continue
        receipt['nro_sha256'] = native['nro_sha256']
        receipt['additional_overlay'] = native['build']
        receipt['hardware_tested'] = False
        entries[name] = encode(receipt)
    entries[PREFIX + 'launcher/loading-watch.json'] = encode({
        'build': native['build'], 'nro_sha256': native['nro_sha256'],
        'compatible_forwarder_sha256': compatible['sha256'], 'profile': 'fastest',
        'diagnostic_only': True, 'debug_window_seconds': 600, 'hardware_tested': False})
    src = 'source/low-window-loading-watch/'
    entries[src + 'native.json'] = encode(native)
    for name in changed:
        entries[src + 'native/' + name] = (args.work / 'native-source' / name).read_bytes()
    for name in ('tools/build_low_window.py', 'tools/low_window_loading.py', 'tools/package_loading_watch.py',
                 'tools/f1_base_build.py', 'tools/port_common.py', 'tools/f1_overlay.py',
                 'tests/check_loading_watch.py', 'tests/loading_watch.c', 'tests/check_launch_order.py',
                 'tests/check_launch_memory_binary.py', 'tests/check_low_window_binary.py',
                 'docs/low-window-loading-watch.md', 'LICENSE'):
        entries[src + name] = (ROOT / name).read_bytes()
    for path in (ROOT / 'src/low_window').iterdir():
        if path.is_file():
            entries[src + 'src/low_window/' + path.name] = path.read_bytes()
    entries[src + 'test-dependencies/fex_frame_metrics.h'] = metrics.read_bytes()
    entries[src + 'test-dependencies/f1_startup_watch.h'] = (args.work / 'native-source/wine-nx-probe/source/f1_startup_watch.h').read_bytes()
    for name, report in reports.items():
        entries[src + 'reports/' + name + '.json'] = encode(report)
    for name in entries:
        assert not name.startswith(('atmosphere/', 'bootloader/', 'forwarder/'))
        assert '/drive_c/' not in name and '/presets/' not in name
        assert not name.endswith(('.dll', '.nsp', '.keys', 'crash.log', 'fex-runtime.log'))
        if name.startswith(PREFIX):
            assert name == PREFIX + 'sleepingdogs-fex.nro' or (name.startswith(PREFIX + 'launcher/') and name.endswith('.json'))
    output = ROOT / 'dist/sleepingdogs-fex-low-window-loading-watch.zip'
    report = {'status': 'PASS', 'update': archive(output, entries),
              'nro_sha256': native['nro_sha256'], 'elf_sha256': native['elf_sha256'],
              'compatible_forwarder_sha256': compatible['sha256'], 'diagnostic_only': True,
              'hardware_tested': False, 'changed_native_files': sorted(changed),
              'fex_adapter_unchanged': True, 'v2_release_preserved': sha(base) == BASE_SHA}
    write_json(ROOT / 'reports/low-window-loading-watch-package.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
