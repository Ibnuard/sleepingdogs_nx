"""Package verified v5 startup repair without game, kernel or DLL changes."""
from pathlib import Path
import argparse
import json
import zipfile
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from build_sync_startup import BUILD, EXPECTED
from recover_sync_v3 import V4_SHA
from package_named_pipe import PREFIX, archive, encode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    args = parser.parse_args()
    base = ROOT / 'dist/sleepingdogs-fex-low-window-sync-watch.zip'
    assert sha(base) == V4_SHA
    with zipfile.ZipFile(base) as z:
        previous = json.loads(z.read('source/low-window-sync-watch/native.json'))
        entries = {n: z.read(n) for n in z.namelist() if n.startswith(PREFIX)}
    compatible = json.loads(entries[PREFIX+'launcher/sync-watch.json'])['compatible_forwarder_sha256']
    out = ROOT / 'dist/low-window-sync-startup-fix'
    native = json.loads((out/'native.json').read_text())
    assert native['build'] == BUILD and native['startup_cpu_guard']
    assert native['source_files'] == manifest(args.work/'native-source')
    assert native['adapter_files'] == manifest(args.work/'fex-adapter') == previous['adapter_files']
    for name, digest in native['build_inputs'].items():
        assert sha(ROOT/name) == digest, name
    changes = {n for n, h in native['source_files'].items() if previous['source_files'].get(n) != h}
    assert changes == EXPECTED and not set(previous['source_files']) - set(native['source_files'])
    nro = out/'sleepingdogs-fex.nro'
    elf = ROOT/'local/symbols/sleepingdogs-low-window-v5.elf'
    assert sha(nro) == native['nro_sha256'] and sha(elf) == native['elf_sha256']
    for name in ('sd_sync_watch.h', 'sd_sync_watch.inc', 'sd_sync_bridge.inc'):
        assert sha(ROOT/'src/low_window'/name) == native['source_files']['wine-nx-probe/source/'+name]
    reports = {}
    for name in ('low-window-v5-sync-watch', 'low-window-v5-sync-startup-binary',
                 'low-window-v5-loading-watch', 'low-window-v5-binary', 'low-window-sync-guest-frame'):
        report = json.loads((ROOT/'reports'/f'{name}.json').read_text())
        assert report['status'] == 'PASS'
        if 'elf_sha256' in report:
            assert report['elf_sha256'] == native['elf_sha256']
        for path, digest in report.get('sources', {}).items():
            # ARM64 emulation runs on Windows; host sanitizers run on WSL.
            assert sha(ROOT/path.replace('\\', '/')) == digest, (name, path)
        for path, digest in report.get('source_files', {}).items():
            assert native['source_files'][path] == digest, (name, path)
        reports[name] = report
    frame = reports['low-window-sync-guest-frame']
    assert frame['test_sha256'] == sha(ROOT/'tests/check_sync_guest_frame.py')
    assert frame['game_sha256'] == sha(ROOT.parent/'Sleeping Dogs/HKShip.exe')
    assert frame['kernelbase_sha256'] == sha(ROOT.parent/'pes13-nx/local/production-input-fix/approved/switch/pes13-fex/drive_c/windows/syswow64/kernelbase.dll')
    assert len(reports['low-window-v5-sync-watch']['cases']) == 12
    assert len(reports['low-window-v5-sync-startup-binary']['cases']) == 21
    entries[PREFIX+nro.name] = nro.read_bytes()
    entries[PREFIX+'launcher/fex-mode.txt'] = b'fastest\n'
    for name, payload in list(entries.items()):
        if not name.endswith('.json'):
            continue
        receipt = json.loads(payload)
        if 'nro_sha256' in receipt:
            receipt.update(nro_sha256=native['nro_sha256'], additional_overlay=BUILD, hardware_tested=False)
            if 'profile' in receipt:
                receipt['profile'] = 'fastest'
            entries[name] = encode(receipt)
    entries[PREFIX+'launcher/sync-watch.json'] = encode({
        'build': BUILD, 'nro_sha256': native['nro_sha256'], 'profile': 'fastest',
        'startup_cpu_guard': True, 'debug_window_seconds': 600, 'hardware_tested': False,
        'freeze_fixed': False, 'compatible_forwarder_sha256': compatible,
        'forwarder_identity_source': 'pinned v4 package receipt; no new NSP included'})
    entries['README-INSTALL.txt'] = (ROOT/'docs/low-window-sync-startup-fix.md').read_bytes()
    prefix = 'source/low-window-sync-startup-fix/'
    entries[prefix+'native.json'] = encode(native)
    for name in changes:
        entries[prefix+'native/'+name] = (args.work/'native-source'/name).read_bytes()
    files = set(native['build_inputs']) | {
        'tools/package_sync_startup.py', 'tools/port_common.py', 'tools/build_dxvk_memory.py',
        'tools/f1_overlay.py', 'tools/package_named_pipe.py', 'tests/check_sync_watch.py',
        'tests/sync_watch.c', 'tests/check_sync_startup_binary.py', 'tests/check_low_window_binary.py',
        'tests/check_loading_watch.py', 'tests/loading_watch.c', 'tests/check_launch_order.py',
        'tests/check_sync_guest_frame.py', 'docs/low-window-sync-startup-fix.md', 'LICENSE'}
    for name in files:
        entries[prefix+name] = (ROOT/name).read_bytes()
    for name, report in reports.items():
        entries[prefix+'reports/'+name+'.json'] = encode(report)
    for name in entries:
        assert not name.startswith(('atmosphere/', 'bootloader/', 'forwarder/'))
        assert '/drive_c/' not in name and not name.endswith(('.dll', '.nsp', '.kip', '.keys', '.log', '.exe'))
        if name.startswith(PREFIX):
            assert name in (PREFIX+nro.name, PREFIX+'launcher/fex-mode.txt') or (
                name.startswith(PREFIX+'launcher/') and name.endswith('.json'))
    update = archive(ROOT/'dist/sleepingdogs-fex-low-window-sync-startup-fix.zip', entries)
    stage = ROOT/'dist/sleepingdogs-fex-low-window-sync-startup-fix'
    for name, payload in entries.items():
        if name.startswith(PREFIX) or name == 'README-INSTALL.txt':
            path = stage/name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                assert path.read_bytes() == payload, f'Preserve existing file: {path}'
            else:
                path.write_bytes(payload)
    recovery = json.loads((ROOT/'reports/low-window-v3-recovery.json').read_text())
    assert sha(ROOT/'dist/sleepingdogs-fex-low-window-v3-recovery.zip') == recovery['package']['sha256']
    result = dict(status='PASS', update=update, rollback=recovery['package'],
        nro_sha256=native['nro_sha256'], elf_sha256=native['elf_sha256'],
        changed_native_files=sorted(changes), profile='fastest', fex_adapter_unchanged=True,
        baseline_preserved=sha(base)==V4_SHA, startup_cpu_guard=True, hardware_tested=False,
        freeze_fixed=False, compatible_forwarder_sha256=compatible)
    write_json(ROOT/'reports/low-window-sync-startup-package.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
