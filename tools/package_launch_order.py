"""Package the NRO admission fix against the shipped low-window installation."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import zipfile

from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode, PREFIX
from build_dxvk_memory import manifest

BASE_SHA = '08a3263f9d452140a9768bfb043a5e0b97453b0991de67ae5fd250338befbb56'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    a = p.parse_args()
    out = ROOT / 'dist/low-window-launch-order-fix'
    native = json.loads((out / 'native.json').read_text())
    assert native['source_files'] == manifest(a.work / 'native-source')
    assert native['adapter_files'] == manifest(a.work / 'fex-adapter')
    for name, digest in native['build_inputs'].items():
        assert sha(ROOT / name) == digest, name
    nro = out / 'sleepingdogs-fex.nro'
    assert sha(nro) == native['nro_sha256']
    assert sha(ROOT / 'local/symbols/sleepingdogs-low-window-v2.elf') == native['elf_sha256']
    assert b'[SD-INIT] v2' in nro.read_bytes() and b'low-window-v2-dx11' in nro.read_bytes()
    fw = json.loads((ROOT / 'dist/low-window-startup-fix/forwarder/build.json').read_text())
    assert fw['sha256'] == sha(ROOT / 'dist/low-window-startup-fix/forwarder' / fw['nsp'])
    assert fw['private_bookkeeping_heap_bytes'] == 16384
    base = ROOT / 'dist/sleepingdogs-fex-low-window-fix.zip'
    assert sha(base) == BASE_SHA
    with zipfile.ZipFile(base) as z:
        old_native = json.loads(z.read('source/low-window-fix/native.json'))
        old = {n: z.read(n) for n in z.namelist() if n.startswith(PREFIX + 'launcher/') and n.endswith('.json') and '/presets/' not in n}
    assert native['adapter_files'] == old_native['adapter_files']
    changed = {n: h for n, h in native['source_files'].items() if old_native['source_files'].get(n) != h}
    assert set(changed) == {'wine-nx-probe/CMakeLists.txt', 'wine-nx-probe/source/runtime.c',
                            'wine-nx-probe/source/sd_low_window.h', 'wine-nx-probe/source/sd_launch_memory.c'}
    reports = {}
    for name in ('low-window-launch-order', 'low-window-admission-binary', 'low-window-v2-binary', 'low-window-arena-full'):
        j = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        assert j['status'] == 'PASS'
        if 'elf_sha256' in j:
            assert j['elf_sha256'] == native['elf_sha256']
        for n, digest in j.get('source_files', {}).items():
            path = a.work / 'native-source' / n if '/' in n else a.work / 'native-source/wine-nx-probe/source' / n
            assert sha(path) == digest, n
        for kind in ('sources', 'tests'):
            for n, digest in j.get(kind, {}).items():
                assert sha(ROOT / n) == digest, n
        reports[name] = j
    assert reports['low-window-launch-order']['test_sha256'] == sha(ROOT / 'tests/check_launch_order.py')
    assert reports['low-window-admission-binary']['test_sha256'] == sha(ROOT / 'tests/check_launch_memory_binary.py')
    assert reports['low-window-admission-binary']['harness_sha256'] == sha(ROOT / 'tests/check_low_window_binary.py')
    entries = {PREFIX + nro.name: nro.read_bytes(), 'README-INSTALL.txt': (ROOT / 'docs/low-window-launch-order-fix.md').read_bytes()}
    for name, data in old.items():
        j = json.loads(data)
        touched = False
        if 'nro_sha256' in j:
            j['nro_sha256'] = native['nro_sha256']
            touched = True
        for key in ('forwarder_sha256', 'compatible_forwarder_sha256'):
            if key in j:
                j[key] = fw['sha256']
                touched = True
        if touched:
            j['additional_overlay'] = native['build']
            j['hardware_tested'] = False
            if name.endswith('/low-window-fix.json'):
                j['build'] = native['build']
                j['initialization'] = 'on Play, before admission validation'
            entries[name] = encode(j)
    entries[PREFIX + 'launcher/launch-order-fix.json'] = encode({
        'build': native['build'], 'nro_sha256': native['nro_sha256'],
        'compatible_forwarder_sha256': fw['sha256'], 'fex_profile': 'fastest',
        'hardware_tested': False, 'observed_previous_heap_capacity_bytes': 3349303296,
        'observed_previous_low_window_active': True})
    src = 'source/low-window-launch-order-fix/'
    entries[src + 'native.json'] = encode(native)
    entries[src + 'compatible-forwarder.json'] = encode(fw)
    for name in changed:
        entries[src + 'native/' + name] = (a.work / 'native-source' / name).read_bytes()
    for name in ('tools/build_low_window.py', 'tools/package_launch_order.py', 'tools/f1_base_build.py',
                 'tests/check_launch_order.py', 'tests/check_launch_memory_binary.py', 'tests/check_low_window_binary.py',
                 'tests/check_low_window_arena.py', 'tests/low_window_arena_boundary.inc', 'tests/direct_arena.c',
                 'docs/low-window-launch-order-fix.md', 'LICENSE'):
        entries[src + name] = (ROOT / name).read_bytes()
    for path in (ROOT / 'src/low_window').iterdir():
        if path.is_file():
            entries[src + 'src/low_window/' + path.name] = path.read_bytes()
    for name, value in reports.items():
        entries[src + 'reports/' + name + '.json'] = encode(value)
    for name in entries:
        assert not name.startswith(('atmosphere/', 'bootloader/', 'forwarder/'))
        assert '/drive_c/' not in name and '/presets/' not in name
        assert not name.endswith(('.dll', '.nsp', '.keys', 'crash.log', 'fex-runtime.log'))
    output = ROOT / 'dist/sleepingdogs-fex-low-window-launch-order-fix.zip'
    report = {'status': 'PASS', 'update': archive(output, entries), 'nro_sha256': native['nro_sha256'],
              'elf_sha256': native['elf_sha256'], 'compatible_forwarder_sha256': fw['sha256'],
              'hardware_tested': False, 'changed_native_files': sorted(changed),
              'fex_adapter_unchanged': True, 'original_release_preserved': sha(base) == BASE_SHA}
    write_json(ROOT / 'reports/low-window-launch-order-package.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
