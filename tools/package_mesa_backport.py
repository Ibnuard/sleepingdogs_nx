"""Package the first post-v12 trial, preserving DXVK and complete rollback."""
from pathlib import Path
import argparse
import hashlib
import json
import tarfile
import zipfile
from port_common import ROOT,sha,write_json
from build_mesa_runtime import OLD_ZIP,OLD_NRO,BUILD
from build_mesa_backport import PATCHES,verify_changed

NAME='sleepingdogs-fex-low-window-mesa-backport'
SOURCE='source/low-window-mesa-backport/'
PREFIX='switch/sleepingdogs-fex/'


def encode(value): return (json.dumps(value,indent=2)+'\n').encode()


def archive(path,entries):
    entries=dict(entries)
    entries['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n'
        for name,data in sorted(entries.items())).encode()
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in sorted(entries.items()): z.writestr(name,data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1)
            assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha(path),files=len(entries))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-mesa-v13'))
    a=p.parse_args()
    base=ROOT/'dist/sleepingdogs-fex-low-window-submit-batching.zip'
    assert sha(base)==OLD_ZIP
    with zipfile.ZipFile(base) as z:
        assert z.testzip() is None
        entries={n:z.read(n) for n in z.namelist() if n.startswith((PREFIX,'source/'))}
    original=dict(entries)
    out=ROOT/'dist/low-window-mesa-backport'
    native=json.loads((out/'native.json').read_text())
    driver=json.loads((out/'driver.json').read_text())
    prepared=json.loads((a.work/'prepared.json').read_text())
    assert native['build']==BUILD and native['baseline_reproduced']
    assert native['shared_sdk_unchanged'] and native['changed_horizon_objects_explicit']
    assert native['candidate_vulkan_sha256']==driver['library_sha256']==sha(Path(driver['library']))
    assert native['driver_build_sha256']==sha(out/'driver.json')==sha(a.work/'build.json')
    assert sha(ROOT/'tools/build_mesa_runtime.py')==native['script_sha256']
    assert sha(ROOT/'tools/build_mesa_backport.py')==driver['builder_sha256']
    verify_changed(a.work/'source',prepared)
    assert driver['all_compiled_dependencies_verified']
    assert sha(a.work/'dependencies.json')==driver['dependencies_sha256']
    dependencies=json.loads((a.work/'dependencies.json').read_text())
    for name,digest in dependencies.items(): assert sha(Path(name))==digest,name
    assert driver['changed_sources']==prepared['changed']
    assert sha(a.work/'prepared.json')==driver['source_manifest_sha256']
    for n,digest in native['inputs'].items(): assert sha(Path(n))==digest,n
    for commit,digest in PATCHES.items(): assert sha(ROOT/'vendor/mesa/v13'/(commit+'.patch'))==digest
    nro=out/'sleepingdogs-fex.nro'
    assert sha(nro)==native['nro_sha256']
    assert sha(ROOT/'local/symbols/sleepingdogs-low-window-v13.elf')==native['elf_sha256']
    reports={}
    for filename in ('mesa-v13-host.json','low-window-v13-runtime-binary.json'):
        report=json.loads((ROOT/'reports'/filename).read_text())
        assert report['status']=='PASS'
        for n,digest in report.get('test_sources',report.get('sources',{})).items(): assert sha(ROOT/n)==digest,n
        reports[filename]=report
    assert reports['mesa-v13-host.json']['changed_sources']==driver['changed_sources']
    assert sha(ROOT/'reports/mesa-v13-host.json')==driver['tests_sha256']
    assert reports['low-window-v13-runtime-binary.json']['elf_sha256']==native['elf_sha256']
    for label,digest in reports['low-window-v13-runtime-binary.json']['reports'].items():
        name='low-window-v13-'+label+'.json'
        assert sha(ROOT/'reports'/name)==digest
        reports[name]=json.loads((ROOT/'reports'/name).read_text())
    rollback={PREFIX+nro.name:original[PREFIX+nro.name]}
    entries[PREFIX+nro.name]=nro.read_bytes()
    changed={PREFIX+nro.name}
    for name,data in list(entries.items()):
        if name.startswith(PREFIX) and name.endswith('.json'):
            value=json.loads(data)
            if value.get('nro_sha256')==OLD_NRO:
                rollback[name]=data
                value.update(nro_sha256=native['nro_sha256'],additional_overlay=BUILD,hardware_tested=False)
                entries[name]=encode(value); changed.add(name)
    identity=PREFIX+'launcher/mesa-backport.json'
    entries[identity]=encode(dict(build=BUILD,trial=1,trial_budget=2,nro_sha256=native['nro_sha256'],
        driver_version=driver['version'],driver_build_id=driver['build_id'],base_commit=driver['baseline_commit'],
        upstream_patches=list(PATCHES),private_gpu_memory_type=True,dxvk='3.1.1-sdbatch1',
        fex_origin='AndroSwitch Project / Ibnuard; own pes13-fex port using FEX-Emu',
        target_resolution=[1280,720],hardware_tested=False,fps_gain_measured=False))
    rollback[identity]=encode(dict(build='sleepingdogs-v12',rolled_back=True,private_gpu_memory_type=False,
        driver_version='26.2.2',nro_sha256=OLD_NRO))
    changed.add(identity)
    for name,data in entries.items():
        if name.startswith(PREFIX) and name not in changed: assert data==original[name],name
        assert not name.lower().endswith(('.exe','.nsp','.keys','.kip','.log','.big','.bix'))
    restored={n:data for n,data in entries.items() if n.startswith(PREFIX)}
    restored.update(rollback)
    for name,data in original.items():
        if name.startswith(PREFIX): assert restored[name]==data,('Rollback mismatch',name)
    assert json.loads(restored[identity])['rolled_back']
    entries['README-INSTALL.txt']=(ROOT/'docs/low-window-mesa-backport.md').read_bytes()
    sources=['tools/build_mesa_backport.py','tools/build_mesa_runtime.py','tools/package_mesa_backport.py',
        'tools/port_common.py','tools/analyze_frame_diagnostics.py','tools/analyze_gameplay_v11.py',
        'tools/analyze_gameplay_v12.py','tests/check_mesa_backport.py','tests/check_v13_runtime_binary.py',
        'tests/check_v11_binary.py','tests/check_direct_sync_binary.py','tests/check_low_window_binary.py',
        'tests/check_shader_binary.py','docs/low-window-mesa-backport.md','docs/v13-dxvk-research.md']
    sources+=['vendor/mesa/v13/'+p.name for p in sorted((ROOT/'vendor/mesa/v13').glob('*')) if p.is_file()]
    for name in sources: entries[SOURCE+name]=(ROOT/name).read_bytes()
    for name in prepared['changed']: entries[SOURCE+'mesa/'+name]=(a.work/'source'/name).read_bytes()
    with tarfile.open(a.work/'baseline-source.tar') as tar:
        for name in prepared['changed']:
            if name in prepared['baseline_files']:
                entries[SOURCE+'mesa-base/'+name]=tar.extractfile(name).read()
    for name in ('docs/license.rst',):
        entries[SOURCE+'mesa/'+name]=(a.work/'source'/name).read_bytes()
    entries[SOURCE+'native.json']=encode(native)
    entries[SOURCE+'driver.json']=encode(driver)
    entries[SOURCE+'prepared.json']=encode(prepared)
    entries[SOURCE+'compile-recipes.json']=(a.work/'compile-recipes.json').read_bytes()
    entries[SOURCE+'dependencies.json']=(a.work/'dependencies.json').read_bytes()
    entries[SOURCE+'reports/gameplay-v12-performance-analysis.json']=(ROOT/'reports/gameplay-v12-performance-analysis.json').read_bytes()
    for name,data in reports.items(): entries[SOURCE+'reports/'+name]=encode(data)
    rollback['README-INSTALL.txt']=b'Close FEXTendo from HOME. Copy the entire switch folder to the SD root and overwrite. Restores the v12 NRO and receipts, retaining DXVK 3.1.1-sdbatch1. No game or save files are included.\n'
    update=archive(ROOT/'dist'/(NAME+'.zip'),entries)
    undo=archive(ROOT/'dist'/(NAME+'-rollback.zip'),rollback)
    for name,data in entries.items():
        if name.startswith(PREFIX) or name=='README-INSTALL.txt':
            dest=ROOT/'dist'/NAME/name; dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists(): assert dest.read_bytes()==data,('Staged artifact changed',name)
            else: dest.write_bytes(data)
    write_json(ROOT/'reports/low-window-mesa-backport-package.json',dict(status='PASS',build=BUILD,
        update=update,rollback=undo,nro_sha256=native['nro_sha256'],elf_sha256=native['elf_sha256'],
        driver_version=driver['version'],trial=1,trial_budget=2,baseline_zip_sha256=OLD_ZIP,
        baseline_preserved=sha(base)==OLD_ZIP,changed_runtime_paths=sorted(changed),
        rollback_restores_v12=True,
        game_files_changed=[],fex_adapter_unchanged=True,wine_objects_unchanged=True,
        dxvk_unchanged=True,graphics_presets_unchanged=True,shared_sdk_unchanged=True,
        target_resolution=[1280,720],hardware_tested=False,fps_gain_measured=False,
        reports={name:sha(ROOT/'reports'/name) for name in reports}))
    print('PACKAGED',update['path'],update['sha256'],flush=True)


if __name__=='__main__': main()
