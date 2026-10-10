"""Package verified v10 at unchanged 720p, preserving the v9 rollback archive."""
from pathlib import Path
import argparse
import json
import zipfile
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from build_direct_sync import V9_SHA
from sleepingdogs_direct_sync import BUILD, FILES, MODIFIED
from package_named_pipe import PREFIX, archive, encode


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    a=p.parse_args()
    baseline=ROOT/'dist/sleepingdogs-fex-low-window-shader-optimizations.zip'
    assert sha(baseline)==V9_SHA
    with zipfile.ZipFile(baseline) as z:
        previous=json.loads(z.read('source/low-window-shader-optimizations/native.json'))
        original={n:z.read(n) for n in z.namelist() if n.startswith(PREFIX)}
    entries=dict(original)
    out=ROOT/'dist/low-window-direct-sync'
    native=json.loads((out/'native.json').read_text())
    assert native['build']==BUILD and native['target_resolution']==[1280,720]
    assert manifest(a.work/'native-source')==native['source_files']
    assert manifest(a.work/'fex-adapter')==native['adapter_files']==previous['adapter_files']
    for name,digest in native['build_inputs'].items(): assert sha(ROOT/name)==digest,name
    changed={n for n,h in native['source_files'].items() if previous['source_files'].get(n)!=h}
    assert changed==FILES and not set(previous['source_files'])-set(native['source_files'])
    nro=out/'sleepingdogs-fex.nro'; elf=ROOT/'local/symbols/sleepingdogs-low-window-v10.elf'
    assert sha(nro)==native['nro_sha256'] and sha(elf)==native['elf_sha256']
    reports={}
    for name in ('direct-sync','direct-sync-binary','shader-binary','cpu-topology','sync-startup-binary','binary'):
        report=json.loads((ROOT/'reports'/('low-window-v10-'+name+'.json')).read_text())
        assert report['status']=='PASS',name
        if 'elf_sha256' in report: assert report['elf_sha256']==native['elf_sha256'],name
        for f,digest in report.get('sources',{}).items(): assert sha(ROOT/f.replace('\\','/'))==digest,(name,f)
        for f,digest in report.get('source_files',{}).items(): assert native['source_files'][f]==digest,(name,f)
        reports[name]=report
    entries[PREFIX+nro.name]=nro.read_bytes()
    for name,payload in list(entries.items()):
        if name.endswith('.json'):
            receipt=json.loads(payload)
            if 'nro_sha256' in receipt:
                receipt.update(nro_sha256=native['nro_sha256'],additional_overlay=BUILD,hardware_tested=False)
                entries[name]=encode(receipt)
    entries[PREFIX+'sync-mode.txt']=b'2\n'
    entries[PREFIX+'launcher/direct-sync.json']=encode(dict(build=BUILD,nro_sha256=native['nro_sha256'],
        sync_mode=2,target_resolution=[1280,720],graphics_resolution_unchanged=True,
        hardware_tested=False,fps_gain_measured=False,fex_port_origin=native['fex_port_origin']))
    # The entire preset payload is byte-identical, including the 720p preset.
    for name,payload in original.items():
        if '/presets/' in name: assert entries[name]==payload,name
    entries['README-INSTALL.txt']=(ROOT/'docs/low-window-direct-sync.md').read_bytes()
    prefix='source/low-window-direct-sync/'
    entries[prefix+'native.json']=encode(native)
    entries[prefix+'THIRD-PARTY.md']=(ROOT/'docs/PES13-THIRD-PARTY.md').read_bytes()
    entries[prefix+'COPYING.LIB']=(a.work/'native-source/COPYING.LIB').read_bytes()
    assert sha(a.work/'native-source/COPYING.LIB')==native['source_files']['COPYING.LIB']
    entries[prefix+'FEXTendo-adapter-LICENSE']=(a.work/'fex-adapter/LICENSE').read_bytes()
    for name in changed: entries[prefix+'native/'+name]=(a.work/'native-source'/name).read_bytes()
    base=ROOT/'local/sync-v10-v9-source'
    entries[prefix+'local/sync-v10-v9-source/native.json']=encode(previous)
    for name in MODIFIED | {'dlls/ntdll/unix/horizon_threads.h','dlls/ntdll/unix/f1_apc_queue.h'}:
        assert sha(base/name)==previous['source_files'][name],name
        entries[prefix+'local/sync-v10-v9-source/'+name]=(base/name).read_bytes()
    inputs=set(native['build_inputs']) | {'tools/package_direct_sync.py','tests/check_direct_sync.py',
        'tests/direct_sync_fixture.c','tests/direct_sync_cases.c','tests/direct_sync_client.c',
        'tests/check_direct_sync_binary.py','tests/check_shader_binary.py','tests/check_v10_regressions.py',
        'tests/check_cpu_topology_binary.py','tests/check_sync_startup_binary.py',
        'tests/check_low_window_binary.py','docs/low-window-direct-sync.md'}
    for name in inputs: entries[prefix+name]=(ROOT/name).read_bytes()
    for name,report in reports.items(): entries[prefix+'reports/'+name+'.json']=encode(report)
    allowed={PREFIX+nro.name,PREFIX+'sync-mode.txt',PREFIX+'launcher/direct-sync.json'}
    for name in entries:
        assert not name.endswith(('.dll','.exe','.nsp','.kip','.keys','.log'))
        assert not name.startswith(('atmosphere/','bootloader/','forwarder/'))
        if name.startswith(PREFIX):
            assert '/drive_c/' not in name
            assert name in original or name in allowed,name
            if name in original and name not in allowed and not name.endswith('.json'):
                assert entries[name]==original[name],name
    update=archive(ROOT/'dist/sleepingdogs-fex-low-window-direct-sync.zip',entries)
    stage=ROOT/'dist/sleepingdogs-fex-low-window-direct-sync'
    for name,payload in entries.items():
        if name.startswith(PREFIX) or name=='README-INSTALL.txt':
            path=stage/name; path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists(): assert path.read_bytes()==payload,f'Preserve existing file: {path}'
            else: path.write_bytes(payload)
    result=dict(status='PASS',update=update,build=BUILD,nro_sha256=native['nro_sha256'],elf_sha256=native['elf_sha256'],
        baseline_sha256=V9_SHA,baseline_preserved=sha(baseline)==V9_SHA,changed_native_files=sorted(changed),
        game_files_changed=[],fex_adapter_unchanged=True,dxvk_unchanged=True,graphics_presets_unchanged=True,
        target_resolution=[1280,720],sync_mode=2,hardware_tested=False,fps_gain_measured=False,
        reports={name:sha(ROOT/'reports'/('low-window-v10-'+name+'.json')) for name in reports})
    write_json(ROOT/'reports/low-window-direct-sync-package.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__': main()
