"""Package the verified v6 CPU topology update for the existing low-window install."""
from pathlib import Path
import argparse
import json
import zipfile
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from build_cpu_topology import BUILD, EXPECTED, V5_SHA
from package_named_pipe import PREFIX, archive, encode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    args = parser.parse_args()
    base = ROOT / 'dist/sleepingdogs-fex-low-window-sync-startup-fix.zip'
    assert sha(base) == V5_SHA
    with zipfile.ZipFile(base) as z:
        previous = json.loads(z.read('source/low-window-sync-startup-fix/native.json'))
        entries = {n: z.read(n) for n in z.namelist() if n.startswith(PREFIX)}
    out = ROOT / 'dist/low-window-cpu-topology-fix'
    native = json.loads((out/'native.json').read_text())
    assert native['build'] == BUILD and native['startup_cpu_guard']
    assert native['source_files'] == manifest(args.work/'native-source')
    assert native['adapter_files'] == manifest(args.work/'fex-adapter') == previous['adapter_files']
    for name, digest in native['build_inputs'].items():
        assert sha(ROOT/name) == digest, name
    changes = {n for n, h in native['source_files'].items() if previous['source_files'].get(n) != h}
    assert changes == EXPECTED and not set(previous['source_files']) - set(native['source_files'])
    nro = out/'sleepingdogs-fex.nro'
    elf = ROOT/'local/symbols/sleepingdogs-low-window-v6.elf'
    assert sha(nro) == native['nro_sha256'] and sha(elf) == native['elf_sha256']
    assert sha(ROOT/'src/low_window/sd_cpu_topology.inc') == native['source_files']['dlls/ntdll/unix/sd_cpu_topology.inc']
    reports = {}
    for name in ('low-window-v6-cpu-topology', 'low-window-v6-sync-startup-binary',
                 'low-window-v6-binary', 'loading-freeze-v5-cpu-topology-analysis'):
        report = json.loads((ROOT/'reports'/f'{name}.json').read_text())
        assert report['status'] == 'PASS'
        if 'elf_sha256' in report: assert report['elf_sha256'] == native['elf_sha256']
        for path, digest in report.get('sources', {}).items():
            assert sha(ROOT/path.replace('\\', '/')) == digest, (name, path)
        for path, digest in report.get('source_files', {}).items():
            assert native['source_files'][path] == digest, (name, path)
        reports[name] = report
    topology = reports['low-window-v6-cpu-topology']
    assert topology['game_sha256'] == sha(ROOT.parent/'Sleeping Dogs/HKShip.exe')
    assert topology['new_game']['worker_count'] == 4
    assert topology['new_game']['indices'] == [1,0,0,0]
    assert topology['old_game']['indices'] == [0xffffffde]
    assert len(topology['cases']) == 10
    assert len(reports['low-window-v6-sync-startup-binary']['cases']) == 21
    assert reports['loading-freeze-v5-cpu-topology-analysis']['original_code_replay']['report_sha256'] == sha(ROOT/'reports/low-window-v6-cpu-topology.json')
    entries[PREFIX+nro.name] = nro.read_bytes()
    entries[PREFIX+'launcher/fex-mode.txt'] = b'fastest\n'
    for name, payload in list(entries.items()):
        if not name.endswith('.json'): continue
        receipt = json.loads(payload)
        if 'nro_sha256' in receipt:
            receipt.update(nro_sha256=native['nro_sha256'], additional_overlay=BUILD, hardware_tested=False)
            if 'profile' in receipt: receipt['profile'] = 'fastest'
            entries[name] = encode(receipt)
    compatible = ['f893d51849443ae6da59925aeec8659f68e94b15347d8528ce56412fbad52598',
                  '04607905b44c42e9a4825d255f745690b647d7d78b7ebe815a6c6b4c175ae929']
    entries[PREFIX+'launcher/cpu-topology.json'] = encode({
        'build':BUILD, 'nro_sha256':native['nro_sha256'], 'profile':'fastest',
        'backend':'Horizon: PEB CPU count, one thread per core',
        'old_queue_failure_reproduced':True, 'new_queue_initialization_replay_passed':True,
        'compatible_forwarder_sha256':compatible, 'hardware_tested':False})
    entries['README-INSTALL.txt'] = (ROOT/'docs/low-window-cpu-topology-fix.md').read_bytes()
    prefix = 'source/low-window-cpu-topology-fix/'
    entries[prefix+'native.json'] = encode(native)
    for name in changes:
        entries[prefix+'native/'+name] = (args.work/'native-source'/name).read_bytes()
    files = set(native['build_inputs']) | {
        'tools/package_cpu_topology.py','tools/analyze_cpu_topology_freeze.py',
        'tools/port_common.py','tools/build_dxvk_memory.py','tools/f1_overlay.py',
        'tools/package_named_pipe.py','tests/check_cpu_topology_binary.py',
        'tests/check_sync_startup_binary.py','tests/check_low_window_binary.py',
        'docs/low-window-cpu-topology-fix.md','LICENSE'}
    for name in files: entries[prefix+name] = (ROOT/name).read_bytes()
    for name, report in reports.items(): entries[prefix+'reports/'+name+'.json'] = encode(report)
    for name in entries:
        assert not name.startswith(('atmosphere/','bootloader/','forwarder/'))
        assert '/drive_c/' not in name and not name.endswith(('.dll','.nsp','.kip','.keys','.log','.exe'))
        if name.startswith(PREFIX):
            assert name in (PREFIX+nro.name,PREFIX+'launcher/fex-mode.txt') or (
                name.startswith(PREFIX+'launcher/') and name.endswith('.json'))
    update = archive(ROOT/'dist/sleepingdogs-fex-low-window-cpu-topology-fix.zip', entries)
    stage = ROOT/'dist/sleepingdogs-fex-low-window-cpu-topology-fix'
    for name, payload in entries.items():
        if name.startswith(PREFIX) or name == 'README-INSTALL.txt':
            path = stage/name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists(): assert path.read_bytes() == payload, f'Preserve existing file: {path}'
            else: path.write_bytes(payload)
    result = dict(status='PASS', update=update, nro_sha256=native['nro_sha256'],
        elf_sha256=native['elf_sha256'], changed_native_files=sorted(changes),
        profile='fastest', fex_adapter_unchanged=True, startup_cpu_guard=True,
        hardware_tested=False, game_modified=False, compatible_forwarders=compatible,
        rollback=dict(path=str(base),sha256=V5_SHA),
        reports={name:sha(ROOT/'reports'/f'{name}.json') for name in reports})
    write_json(ROOT/'reports/low-window-cpu-topology-package.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':main()
