"""Package v7 without overwriting saves, video settings, or existing user choices."""
from pathlib import Path
import argparse
import json
import zipfile
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from build_performance_hud import V6_SHA
from sleepingdogs_performance_hud import BUILD, FILES, performance_config
from package_named_pipe import PREFIX, archive, encode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    args = parser.parse_args()
    baseline = ROOT/'dist/sleepingdogs-fex-low-window-cpu-topology-fix.zip'
    assert sha(baseline) == V6_SHA
    with zipfile.ZipFile(baseline) as z:
        previous=json.loads(z.read('source/low-window-cpu-topology-fix/native.json'))
        entries={n:z.read(n) for n in z.namelist() if n.startswith(PREFIX) and n.endswith(('.nro','.json'))}
    out=ROOT/'dist/low-window-performance-hud'
    native=json.loads((out/'native.json').read_text())
    assert native['build']==BUILD
    assert manifest(args.work/'native-source')==native['source_files']
    assert manifest(args.work/'fex-adapter')==native['adapter_files']==previous['adapter_files']
    for name,digest in native['build_inputs'].items():assert sha(ROOT/name)==digest,name
    changed={n for n,h in native['source_files'].items() if previous['source_files'].get(n)!=h}
    assert changed==FILES and not set(previous['source_files'])-set(native['source_files'])
    nro=out/'sleepingdogs-fex.nro';elf=ROOT/'local/symbols/sleepingdogs-low-window-v7.elf'
    assert sha(nro)==native['nro_sha256'] and sha(elf)==native['elf_sha256']
    reports={}
    for name in ('low-window-v7-launcher','low-window-v7-cpu-topology',
                 'low-window-v7-sync-startup-binary','low-window-v7-binary','gameplay-v6-performance-analysis'):
        report=json.loads((ROOT/'reports'/f'{name}.json').read_text())
        assert report['status']=='PASS',name
        if 'elf_sha256' in report:assert report['elf_sha256']==native['elf_sha256'],name
        for path,digest in report.get('sources',{}).items():assert sha(ROOT/path.replace('\\','/'))==digest,(name,path)
        for path,digest in report.get('source_files',{}).items():assert native['source_files'][path]==digest,(name,path)
        reports[name]=report
    assert reports['low-window-v7-launcher']['combinations']==30
    assert reports['low-window-v7-cpu-topology']['new_game']['worker_count']==4
    assert reports['gameplay-v6-performance-analysis']['log_sha256']==sha(ROOT/'local/gameplay-v6/fex-runtime.log')
    entries[PREFIX+nro.name]=nro.read_bytes()
    for name,payload in list(entries.items()):
        if name.endswith('.json'):
            receipt=json.loads(payload)
            if 'nro_sha256' in receipt:
                receipt.update(nro_sha256=native['nro_sha256'],additional_overlay=BUILD,hardware_tested=False)
                entries[name]=encode(receipt)
    for renderer in ('dxvk-3.1.1','dxvk-2.7.1-async'):
        entries[PREFIX+f'launcher/presets/performance/{renderer}/dxvk.conf']=performance_config(renderer.endswith('async')).encode()
    entries[PREFIX+'launcher/performance-hud.json']=encode(dict(
        build=BUILD,nro_sha256=native['nro_sha256'],hud_modes=['None','FPS','Full'],
        performance_profile_optional=True,choices_preserved=True,normal_launch_detailed_watch=False,
        fps_gain_measured=False,hardware_tested=False))
    entries['README-INSTALL.txt']=(ROOT/'docs/low-window-performance-hud.md').read_bytes()
    prefix='source/low-window-performance-hud/'
    entries[prefix+'native.json']=encode(native)
    for name in changed:entries[prefix+'native/'+name]=(args.work/'native-source'/name).read_bytes()
    inputs=set(native['build_inputs'])|{'tools/package_performance_hud.py','tests/check_performance_hud.py',
          'tests/check_cpu_topology_binary.py','tests/check_sync_startup_binary.py','tests/check_low_window_binary.py'}
    for name in inputs:entries[prefix+name]=(ROOT/name).read_bytes()
    for name,report in reports.items():entries[prefix+'reports/'+name+'.json']=encode(report)
    for name in entries:
        assert not name.endswith(('.dll','.exe','.nsp','.kip','.keys','.log'))
        assert not name.startswith(('atmosphere/','bootloader/','forwarder/'))
        if name.startswith(PREFIX):
            assert '/drive_c/' not in name
            assert name==PREFIX+nro.name or name.endswith('.json') or name.startswith(PREFIX+'launcher/presets/performance/')
    update=archive(ROOT/'dist/sleepingdogs-fex-low-window-performance-hud.zip',entries)
    stage=ROOT/'dist/sleepingdogs-fex-low-window-performance-hud'
    for name,payload in entries.items():
        if name.startswith(PREFIX) or name=='README-INSTALL.txt':
            path=stage/name;path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():assert path.read_bytes()==payload,f'Preserve existing file: {path}'
            else:path.write_bytes(payload)
    result=dict(status='PASS',update=update,build=BUILD,nro_sha256=native['nro_sha256'],
        elf_sha256=native['elf_sha256'],changed_native_files=sorted(changed),
        hud=['None','FPS','Full'],normal_launch_detailed_watch=False,performance_optional=True,
        user_choice_files_changed=[],game_files_changed=[],fex_and_dxvk_unchanged=True,
        baseline_sha256=V6_SHA,baseline_preserved=sha(baseline)==V6_SHA,
        hardware_tested=False,fps_gain_measured=False,graphics_undefined_fixed=False,
        reports={n:sha(ROOT/'reports'/f'{n}.json') for n in reports})
    write_json(ROOT/'reports/low-window-performance-hud-package.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
