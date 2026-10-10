"""Package trial two with v13 rollback; verify every runtime and source entry."""
from pathlib import Path
import difflib
import hashlib
import json
import zipfile
from port_common import ROOT,sha,write_json
from build_mesa_shader_v14 import WORK,PREVIOUS,FILES,prepare,REFERENCE_SHA
from build_shader_runtime_v14 import OLD_ZIP,OLD_NRO,OLD_ELF,BUILD,DEST

NAME='sleepingdogs-fex-low-window-gm20b-shaders'
PREFIX='switch/sleepingdogs-fex/'
SOURCE='source/low-window-gm20b-shaders/'


def encode(value):return (json.dumps(value,indent=2)+'\n').encode()


def archive(path,entries):
    entries=dict(entries)
    entries['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n'
        for name,data in sorted(entries.items())).encode()
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in sorted(entries.items()):z.writestr(name,data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            h,n=line.split('  ',1);assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    return dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,files=len(entries))


def main():
    prepared=prepare()
    previous=ROOT/'dist/sleepingdogs-fex-low-window-mesa-backport.zip'
    assert sha(previous)==OLD_ZIP
    with zipfile.ZipFile(previous) as z:
        assert z.testzip() is None
        entries={n:z.read(n) for n in z.namelist() if n.startswith((PREFIX,'source/'))}
    original=dict(entries)
    native=json.loads((DEST/'native.json').read_text());driver=json.loads((DEST/'driver.json').read_text())
    assert native['build']==BUILD and native['baseline_elf_sha256']==OLD_ELF and native['baseline_reproduced']
    assert native['script_sha256']==sha(ROOT/'tools/build_shader_runtime_v14.py')
    assert driver['builder_sha256']==sha(ROOT/'tools/build_mesa_shader_v14.py')
    assert native['driver_build_sha256']==sha(DEST/'driver.json')==sha(WORK/'build.json')
    assert sha(Path(driver['library']))==native['candidate_vulkan_sha256']==driver['library_sha256']
    for n,h in native['inputs'].items():assert sha(Path(n))==h,n
    for n,h in json.loads((WORK/'c-dependencies.json').read_text()).items():assert sha(Path(n))==h,n
    for n,e in driver['explicit_link_objects'].items():assert sha(Path(e['path']))==e['sha256'],n
    tests={}
    for n in ('mesa-v14-shader-host.json','low-window-v14-runtime-binary.json'):
        r=json.loads((ROOT/'reports'/n).read_text());assert r['status']=='PASS'
        for p,h in r['sources'].items():assert sha(ROOT/p)==h,p
        tests[n]=r
    assert tests['mesa-v14-shader-host.json']['changed_sources']==prepared['changed']
    assert native['host_test_sha256']==sha(ROOT/'reports/mesa-v14-shader-host.json')
    assert tests['low-window-v14-runtime-binary.json']['elf_sha256']==native['elf_sha256']
    for label,h in tests['low-window-v14-runtime-binary.json']['reports'].items():
        n='low-window-v14-'+label+'.json';assert sha(ROOT/'reports'/n)==h
        tests[n]=json.loads((ROOT/'reports'/n).read_text())
    nro=DEST/'sleepingdogs-fex.nro';assert sha(nro)==native['nro_sha256']
    assert sha(ROOT/'local/symbols/sleepingdogs-low-window-v14.elf')==native['elf_sha256']
    rollback={PREFIX+nro.name:original[PREFIX+nro.name]}
    assert hashlib.sha256(rollback[PREFIX+nro.name]).hexdigest()==OLD_NRO
    entries[PREFIX+nro.name]=nro.read_bytes();changed={PREFIX+nro.name}
    for n,data in list(entries.items()):
        if n.startswith(PREFIX) and n.endswith('.json'):
            value=json.loads(data)
            if value.get('nro_sha256')==OLD_NRO:
                rollback[n]=data
                value.update(nro_sha256=native['nro_sha256'],additional_overlay=BUILD,hardware_tested=False)
                entries[n]=encode(value);changed.add(n)
    identity=PREFIX+'launcher/gm20b-shaders.json'
    assert identity not in original
    entries[identity]=encode(dict(build=BUILD,trial=2,trial_budget=2,
        nro_sha256=native['nro_sha256'],driver_version=driver['version'],driver_build_id=driver['build_id'],
        policy=driver['policy'],dxvk='3.1.1-sdbatch1',target_resolution=[1280,720],
        fex_origin='AndroSwitch Project / Ibnuard; own pes13-fex port using FEX-Emu',
        hardware_tested=False,fps_gain_measured=False))
    rollback[identity]=encode(dict(build='sleepingdogs-v13',rolled_back=True,nro_sha256=OLD_NRO,
        driver_version='26.2.2-sdv13-zcull-ubo'))
    changed.add(identity)
    for n,data in entries.items():
        if n.startswith(PREFIX) and n not in changed:assert data==original[n],n
        assert not n.lower().endswith(('.exe','.nsp','.keys','.kip','.log','.big','.bix'))
    restored={n:d for n,d in entries.items() if n.startswith(PREFIX)}
    restored.update(rollback)
    for n,data in original.items():
        if n.startswith(PREFIX):assert restored[n]==data,('rollback mismatch',n)
    assert json.loads(restored[identity])['rolled_back']
    readme='''Sleeping Dogs FEXTendo v14 — trial 2 of 2. Target 720p; FPS unmeasured on hardware.
Close FEXTendo from HOME. Copy the entire switch folder to the SD root and overwrite.
Use DXVK 3.1.1, Performance, Launch GUI, 1280x720. Keep the same clocks for comparison.
The GPU shader cache identity changes: warm the route once, then measure it again.
Expected log marker: [SD-NVK-V14] shader compiler SM53. The old runtime banner remains v11.
Rollback ZIP restores the tested v13 runtime. Game and save files are not included.
See source/low-window-gm20b-shaders/docs/low-window-gm20b-shaders.md for evidence and limits.
'''
    entries['README-INSTALL.txt']=readme.encode()
    scripts=['tools/build_mesa_shader_v14.py','tools/build_shader_runtime_v14.py','tools/package_shader_v14.py',
             'tools/port_common.py','tools/build_mesa_backport.py','tools/analyze_gameplay_v13.py',
             'tools/analyze_gameplay_v12.py','tools/analyze_gameplay_v11.py','tools/analyze_frame_diagnostics.py',
             'tests/check_mesa_shader_v14.py','tests/check_v14_runtime_binary.py','tests/check_v11_binary.py',
             'tests/check_direct_sync_binary.py','tests/check_low_window_binary.py','tests/check_shader_binary.py',
             'docs/low-window-gm20b-shaders.md','docs/v13-dxvk-research.md']
    for n in scripts:entries[SOURCE+n]=(ROOT/n).read_bytes()
    # Carry the pinned reference used by the preparer, including attribution;
    # only our six selected/adapted source changes are applied to the build.
    reference=ROOT/'local/research-v14/mesa-switch-nfsmw.patch';assert sha(reference)==REFERENCE_SHA
    entries[SOURCE+'local/research-v14/mesa-switch-nfsmw.patch']=reference.read_bytes()
    for n in prepared['source_files']:entries[SOURCE+'mesa/'+n]=(WORK/'source'/n).read_bytes()
    patch=[]
    for n in FILES:
        before=(PREVIOUS/'source'/n).read_text();after=(WORK/'source'/n).read_text()
        entries[SOURCE+'mesa-base/'+n]=before.encode()
        patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),'a/'+n,'b/'+n))
    entries[SOURCE+'sleepingdogs-v14-shader.patch']=''.join(patch).encode()
    entries[SOURCE+'mesa/docs/license.rst']=(PREVIOUS/'source/docs/license.rst').read_bytes()
    entries[SOURCE+'native.json']=encode(native);entries[SOURCE+'driver.json']=encode(driver)
    for n in ('prepared.json','c-dependencies.json','c-recipes.json','rust.json'):
        entries[SOURCE+n]=(WORK/n).read_bytes()
    for n in ('shader.rs','nir.c'):entries[SOURCE+'tests/generated/'+n]=(WORK/'tests'/n).read_bytes()
    for n,r in tests.items():entries[SOURCE+'reports/'+n]=encode(r)
    for n in ('gameplay-v13-performance-analysis.json','gameplay-v13-1fdd9558041b.json'):
        entries[SOURCE+'reports/'+n]=(ROOT/'reports'/n).read_bytes()
    rollback['README-INSTALL.txt']=b'Close FEXTendo from HOME. Copy the entire switch folder to the SD root and overwrite. Restores v13 NRO and receipts, including its compiler/cache identity. Game and save files are unchanged.\n'
    update=archive(ROOT/'dist'/(NAME+'.zip'),entries)
    undo=archive(ROOT/'dist'/(NAME+'-rollback.zip'),rollback)
    for n,data in entries.items():
        if n.startswith(PREFIX) or n=='README-INSTALL.txt':
            p=ROOT/'dist'/NAME/n;p.parent.mkdir(parents=True,exist_ok=True)
            if p.exists():assert p.read_bytes()==data,n
            else:p.write_bytes(data)
    assert sha(previous)==OLD_ZIP
    report=dict(status='PASS',build=BUILD,trial=2,trial_budget=2,update=update,rollback=undo,
        nro_sha256=native['nro_sha256'],elf_sha256=native['elf_sha256'],driver_version=driver['version'],
        driver_build_id=driver['build_id'],baseline_zip_sha256=OLD_ZIP,baseline_preserved=True,
        changed_runtime_paths=sorted(changed),rollback_restores_v13=True,game_files_changed=[],
        wine_objects_unchanged=True,fex_adapter_unchanged=True,dxvk_unchanged=True,graphics_presets_unchanged=True,
        target_resolution=[1280,720],hardware_tested=False,fps_gain_measured=False,
        packager_sha256=sha(Path(__file__)),reports={n:sha(ROOT/'reports'/n) for n in tests})
    write_json(ROOT/'reports/low-window-gm20b-shaders-package.json',report)
    print('PACKAGED',update['path'],update['sha256'],flush=True)


if __name__=='__main__':main()
