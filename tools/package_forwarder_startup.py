"""Package only the repaired HOME NSP; require regression on the actual ELF."""
from pathlib import Path
import argparse
import json
import sys
import zipfile

from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode

BASE_SHA = '08a3263f9d452140a9768bfb043a5e0b97453b0991de67ae5fd250338befbb56'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    args = p.parse_args()
    out = ROOT / 'dist/low-window-startup-fix/forwarder'
    fw = json.loads((out / 'build.json').read_text())
    test = json.loads((ROOT / 'reports/forwarder-startup-binary.json').read_text())
    base = ROOT / 'dist/sleepingdogs-fex-low-window-fix.zip'
    assert sha(base) == BASE_SHA, 'Previous release changed'
    assert test['status'] == 'PASS' and test['old_abort_result'] == '0x515b'
    assert test['test_sha256'] == sha(ROOT / 'tests/check_forwarder_startup_binary.py')
    assert test['elf_sha256'] == fw['elf_sha256'] == sha(args.work / 'forwarder.elf')
    assert test['nsp_sha256'] == fw['sha256'] == sha(out / fw['nsp'])
    assert test['source_files'] == fw['source_files']
    assert fw['packed_payload_verified'] and test['npdm_nacp_icon_target_unchanged']
    assert fw['private_bookkeeping_heap_bytes'] == 16384 and fw['native_nro_above_4g']
    assert fw['low_window_overlay'] == 'sleepingdogs-forwarder-startup-v2'
    with zipfile.ZipFile(base) as z:
        old = json.loads(z.read('forwarder/build.json'))
    assert old['nro_sha256'] == fw['nro_sha256'] == test['nro_sha256']
    assert old['elf_sha256'] == test['old_elf_sha256']
    for key in ('title_id', 'target', 'address_space', 'capabilities', 'system_resource_bytes',
                'full_application_reserve_bytes', 'loader_commit', 'packer_commit'):
        assert old[key] == fw[key], key
    entries = {'README-INSTALL.txt': (ROOT / 'docs/low-window-startup-fix.md').read_bytes()}
    for path in sorted(out.rglob('*')):
        if path.is_file():
            entries['forwarder/' + path.relative_to(out).as_posix()] = path.read_bytes()
    source = 'source/forwarder-startup-fix/'
    for name, digest in fw['source_files'].items():
        path = args.work / 'source' / name
        assert sha(path) == digest, name
        entries[source + 'compiled-source/' + name] = path.read_bytes()
    entries[source + 'symbols/forwarder.elf'] = (args.work / 'forwarder.elf').read_bytes()
    entries[source + 'reports/forwarder-startup-binary.json'] = encode(test)
    sources = ('forwarder/build_forwarder.py', 'tools/package_forwarder_startup.py',
               'tools/sleepingdogs_gpu_budget.py', 'tools/f1_overlay.py', 'tools/port_common.py',
               'tests/check_forwarder_startup_binary.py', 'docs/low-window-startup-fix.md')
    for name in sources:
        entries[source + name] = (ROOT / name).read_bytes()
    entries[source + 'inputs.json'] = encode({
        'previous_release_sha256': BASE_SHA, 'previous_nsp_sha256': old['sha256'],
        'nro_sha256_unchanged': fw['nro_sha256'],
        'kernel_loader_nro_rebuild_required': False, 'fex_profile': 'fastest',
        'hardware_tested': False, 'build_script_sha256': sha(ROOT / 'forwarder/build_forwarder.py')})
    for name in entries:
        assert not name.startswith(('switch/', 'atmosphere/', 'bootloader/'))
        assert not name.lower().endswith(('.keys', 'crash.log', 'fex-runtime.log'))
    path = ROOT / 'dist/sleepingdogs-fex-low-window-startup-fix.zip'
    report = {'status': 'PASS', 'update': archive(path, entries), 'nsp_sha256': fw['sha256'],
              'elf_sha256': fw['elf_sha256'], 'nro_sha256_unchanged': fw['nro_sha256'],
              'previous_release_preserved': sha(base) == BASE_SHA, 'hardware_tested': False}
    write_json(ROOT / 'reports/forwarder-startup-package.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
