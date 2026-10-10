"""Package the v8 counter diagnostic, with immutable v7 rollback and no game-file changes."""
from pathlib import Path
import argparse
import json
import zipfile
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from build_perf_counters import V7_SHA
from sleepingdogs_perf_counters import BUILD, FILES
from package_named_pipe import PREFIX, archive, encode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    args = parser.parse_args()
    baseline = ROOT/'dist/sleepingdogs-fex-low-window-performance-hud.zip'
    assert sha(baseline) == V7_SHA
    with zipfile.ZipFile(baseline) as z:
        previous = json.loads(z.read('source/low-window-performance-hud/native.json'))
        entries = {n:z.read(n) for n in z.namelist() if n.startswith(PREFIX)}
    out = ROOT/'dist/low-window-perf-counters'
    native = json.loads((out/'native.json').read_text())
    assert native['build'] == BUILD
    assert manifest(args.work/'native-source') == native['source_files']
    assert manifest(args.work/'fex-adapter') == native['adapter_files'] == previous['adapter_files']
    for name, digest in native['build_inputs'].items():
        assert sha(ROOT/name) == digest, name
    changed = {n for n,h in native['source_files'].items() if previous['source_files'].get(n) != h}
    assert changed == FILES and not set(previous['source_files'])-set(native['source_files'])
    nro = out/'sleepingdogs-fex.nro'
    elf = ROOT/'local/symbols/sleepingdogs-low-window-v8.elf'
    assert sha(nro) == native['nro_sha256'] and sha(elf) == native['elf_sha256']
    reports = {}
    for name in ('low-window-v8-counters','low-window-v8-cpu-topology',
                 'low-window-v8-sync-startup-binary','low-window-v8-binary',
                 'gameplay-v7-performance-analysis'):
        report = json.loads((ROOT/'reports'/f'{name}.json').read_text())
        assert report['status'] == 'PASS', name
        if 'elf_sha256' in report:
            assert report['elf_sha256'] == native['elf_sha256'], name
        for path,digest in report.get('sources',{}).items():
            assert sha(ROOT/path.replace('\\','/')) == digest, (name,path)
        for path,digest in report.get('source_files',{}).items():
            assert native['source_files'][path] == digest, (name,path)
        reports[name] = report
    assert reports['low-window-v8-counters']['all_native_changes_match_overlay']
    assert reports['low-window-v8-cpu-topology']['new_game']['worker_count'] == 4
    assert reports['gameplay-v7-performance-analysis']['log_sha256'] == sha(ROOT/'local/performance-v7/fex-runtime.log')
    entries[PREFIX+nro.name] = nro.read_bytes()
    for name,payload in list(entries.items()):
        if name.endswith('.json'):
            receipt = json.loads(payload)
            if 'nro_sha256' in receipt:
                receipt.update(nro_sha256=native['nro_sha256'], additional_overlay=BUILD, hardware_tested=False)
                entries[name] = encode(receipt)
    entries[PREFIX+'performance-counters.txt'] = b'1\n'
    entries[PREFIX+'launcher/perf-counters.json'] = encode(dict(build=BUILD,
        nro_sha256=native['nro_sha256'], counter_interval_ms=10000, normal_launch_only=True,
        performance_optimization=False, hardware_tested=False))
    entries['README-INSTALL.txt'] = (ROOT/'docs/low-window-perf-counters.md').read_bytes()
    prefix = 'source/low-window-perf-counters/'
    entries[prefix+'native.json'] = encode(native)
    for name in changed:
        entries[prefix+'native/'+name] = (args.work/'native-source'/name).read_bytes()
    inputs = set(native['build_inputs']) | {'tools/package_perf_counters.py',
        'tools/analyze_gameplay_performance.py','tests/check_perf_counters.py',
        'tests/check_cpu_topology_binary.py','tests/check_sync_startup_binary.py','tests/check_low_window_binary.py'}
    for name in inputs:
        entries[prefix+name] = (ROOT/name).read_bytes()
    for name,report in reports.items():
        entries[prefix+'reports/'+name+'.json'] = encode(report)
    for name in entries:
        assert not name.endswith(('.dll','.exe','.nsp','.kip','.keys','.log'))
        assert not name.startswith(('atmosphere/','bootloader/','forwarder/'))
        if name.startswith(PREFIX):
            assert '/drive_c/' not in name
            assert name in (PREFIX+nro.name, PREFIX+'performance-counters.txt') or name.endswith('.json') or name.startswith(PREFIX+'launcher/presets/performance/')
    update = archive(ROOT/'dist/sleepingdogs-fex-low-window-perf-counters.zip', entries)
    stage = ROOT/'dist/sleepingdogs-fex-low-window-perf-counters'
    for name,payload in entries.items():
        if name.startswith(PREFIX) or name == 'README-INSTALL.txt':
            path = stage/name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                assert path.read_bytes() == payload, f'Preserve existing file: {path}'
            else:
                path.write_bytes(payload)
    result = dict(status='PASS', update=update, build=BUILD,
        nro_sha256=native['nro_sha256'], elf_sha256=native['elf_sha256'],
        changed_native_files=sorted(changed), baseline_sha256=V7_SHA,
        baseline_preserved=sha(baseline)==V7_SHA, game_files_changed=[],
        fex_and_dxvk_unchanged=True, cpu_gpu_scheduling_unchanged=True,
        config_added='performance-counters.txt=1', hardware_tested=False,
        performance_optimization=False, fps_gain_measured=False, graphics_undefined_fixed=False,
        reports={name:sha(ROOT/'reports'/f'{name}.json') for name in reports})
    write_json(ROOT/'reports/low-window-perf-counters-package.json', result)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
