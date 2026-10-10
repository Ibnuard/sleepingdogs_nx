"""Package verified v11 diagnostics; preserve the v10 ZIP and user log."""
from pathlib import Path
import argparse
import json
import zipfile
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from build_frame_diagnostics import V10_SHA
from sleepingdogs_frame_diagnostics import BUILD, FILES
from package_named_pipe import PREFIX, archive, encode

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    a=p.parse_args()
    baseline=ROOT/'dist/sleepingdogs-fex-low-window-direct-sync.zip'
    assert sha(baseline)==V10_SHA
    with zipfile.ZipFile(baseline) as z:
        previous=json.loads(z.read('source/low-window-direct-sync/native.json'))
        # Include the v10 source payload, which documents the underlying port.
        entries={n:z.read(n) for n in z.namelist() if n.startswith((PREFIX,'source/'))}
    original={n:data for n,data in entries.items() if n.startswith(PREFIX)}
    out=ROOT/'dist/low-window-frame-diagnostics'
    native=json.loads((out/'native.json').read_text())
    assert native['build']==BUILD and native['target_resolution']==[1280,720]
    assert manifest(a.work/'native-source')==native['source_files']
    assert manifest(a.work/'fex-adapter')==native['adapter_files']==previous['adapter_files']
    for name,digest in native['build_inputs'].items(): assert sha(ROOT/name)==digest,name
    changed={n for n,h in native['source_files'].items() if previous['source_files'].get(n)!=h}
    assert changed==FILES and not set(previous['source_files'])-set(native['source_files'])
    nro=out/'sleepingdogs-fex.nro'; elf=ROOT/'local/symbols/sleepingdogs-low-window-v11.elf'
    assert sha(nro)==native['nro_sha256'] and sha(elf)==native['elf_sha256']
    reports={}
    for name in ('frame-diagnostics','diagnostic-binary','direct-sync-binary','shader-binary',
                 'cpu-topology','sync-startup-binary','binary'):
        report=json.loads((ROOT/'reports'/('low-window-v11-'+name+'.json')).read_text())
        assert report['status']=='PASS',name
        if 'elf_sha256' in report: assert report['elf_sha256']==native['elf_sha256'],name
        for f,h in report.get('sources',{}).items(): assert sha(ROOT/f.replace('\\','/'))==h,(name,f)
        for f,h in report.get('source_files',{}).items(): assert native['source_files'][f]==h,(name,f)
        reports[name]=report
    assert reports['frame-diagnostics']['native_source_verified']
    entries[PREFIX+nro.name]=nro.read_bytes()
    for name,payload in list(entries.items()):
        if name.startswith(PREFIX) and name.endswith('.json'):
            value=json.loads(payload)
            if 'nro_sha256' in value:
                value.update(nro_sha256=native['nro_sha256'],additional_overlay=BUILD,hardware_tested=False)
                entries[name]=encode(value)
    entries[PREFIX+'frame-diagnostics.txt']=b'1\n'
    entries[PREFIX+'launcher/frame-diagnostics.json']=encode(dict(build=BUILD,nro_sha256=native['nro_sha256'],
        target_resolution=[1280,720],diagnostics=native['diagnostics'],hardware_tested=False,
        fps_gain_measured=False,fex_port_origin=native['fex_port_origin']))
    entries['README-INSTALL.txt']=(ROOT/'docs/low-window-frame-diagnostics.md').read_bytes()
    prefix='source/low-window-frame-diagnostics/'
    entries[prefix+'native.json']=encode(native)
    entries[prefix+'THIRD-PARTY.md']=(ROOT/'docs/PES13-THIRD-PARTY.md').read_bytes()
    entries[prefix+'COPYING.LIB']=(a.work/'native-source/COPYING.LIB').read_bytes()
    assert sha(a.work/'native-source/COPYING.LIB')==native['source_files']['COPYING.LIB']
    entries[prefix+'FEXTendo-adapter-LICENSE']=(a.work/'fex-adapter/LICENSE').read_bytes()
    for n in changed: entries[prefix+'native/'+n]=(a.work/'native-source'/n).read_bytes()
    inputs=set(native['build_inputs'])|{'tools/package_frame_diagnostics.py','tests/check_frame_diagnostics.py',
        'tests/frame_diagnostics.c','tests/direct_sync_client.c','tests/check_v11_binary.py',
        'tests/check_direct_sync_binary.py','tests/check_cpu_topology_binary.py',
        'tests/check_sync_startup_binary.py','tests/check_low_window_binary.py','tests/check_shader_binary.py',
        'docs/low-window-frame-diagnostics.md','tools/analyze_frame_diagnostics.py'}
    for n in inputs: entries[prefix+n]=(ROOT/n).read_bytes()
    for name,report in reports.items(): entries[prefix+'reports/'+name+'.json']=encode(report)
    allowed={PREFIX+nro.name,PREFIX+'frame-diagnostics.txt',PREFIX+'launcher/frame-diagnostics.json'}
    for name,payload in entries.items():
        assert not name.endswith(('.dll','.exe','.nsp','.kip','.keys','.log')),name
        assert not name.startswith(('atmosphere/','bootloader/','forwarder/'))
        if name.startswith(PREFIX):
            assert '/drive_c/' not in name
            assert name in original or name in allowed,name
            if name in original and name not in allowed and not name.endswith('.json'):
                assert payload==original[name],name
    update=archive(ROOT/'dist/sleepingdogs-fex-low-window-frame-diagnostics.zip',entries)
    stage=ROOT/'dist/sleepingdogs-fex-low-window-frame-diagnostics'
    for name,payload in entries.items():
        if name.startswith(PREFIX) or name=='README-INSTALL.txt':
            path=stage/name; path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists(): assert path.read_bytes()==payload,f'Preserve existing file: {path}'
            else: path.write_bytes(payload)
    result=dict(status='PASS',update=update,build=BUILD,nro_sha256=native['nro_sha256'],elf_sha256=native['elf_sha256'],
        baseline_sha256=V10_SHA,baseline_preserved=sha(baseline)==V10_SHA,changed_native_files=sorted(changed),
        game_files_changed=[],fex_adapter_unchanged=True,dxvk_unchanged=True,graphics_presets_unchanged=True,
        target_resolution=[1280,720],sync_mode=2,hardware_tested=False,fps_gain_measured=False,
        diagnostics_duration_ms=30000,reports={n:sha(ROOT/'reports'/('low-window-v11-'+n+'.json')) for n in reports})
    write_json(ROOT/'reports/low-window-frame-diagnostics-package.json',result)
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__': main()
