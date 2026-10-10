"""Package the corrected v14 trial, preserving runtime configuration and v13 rollback."""
from pathlib import Path
import difflib
import hashlib
import json
import zipfile
from port_common import ROOT,sha,write_json
from build_mesa_cache_v141 import WORK,DEST,BUILD,BUILD_ID,VERSION,OLD_LIB,OLD_ELF,OLD_NRO,OLD_ZIP,FILE,PHYSICAL,V13,V14
from build_mesa_backport import archive_members

NAME='sleepingdogs-fex-low-window-gm20b-cache-fix'
PREFIX='switch/sleepingdogs-fex/'
SOURCE='source/low-window-gm20b-cache-fix/'
V13_ZIP='43e233720d7f48d0ec320a77c836af085917a00cfc0ddc0d23e469b190dee9c5'
V13_NRO='635728655ee1fbf11ce7d882882e61b561825567b79f2929cf653691bbf681a6'


def encode(value):return (json.dumps(value,indent=2)+'\n').encode()


def archive(path,entries):
    assert 'SHA256SUMS.txt' not in entries
    payload=dict(entries)
    payload['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(d).hexdigest()}  {n}\n'
        for n,d in sorted(entries.items())).encode()
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for n,d in sorted(payload.items()):z.writestr(n,d)
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist())==len(set(z.namelist())) and z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            h,n=line.split('  ',1);assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    return dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,files=len(payload))


def main():
    previous=ROOT/'dist/sleepingdogs-fex-low-window-gm20b-shaders.zip'
    v13=ROOT/'dist/sleepingdogs-fex-low-window-mesa-backport.zip'
    assert sha(previous)==OLD_ZIP and sha(v13)==V13_ZIP
    with zipfile.ZipFile(previous) as z:
        assert z.testzip() is None
        entries={n:z.read(n) for n in z.namelist() if n.startswith((PREFIX,'source/'))}
    original=dict(entries)
    with zipfile.ZipFile(v13) as z:
        assert z.testzip() is None
        old13={n:z.read(n) for n in z.namelist() if n.startswith(PREFIX)}
    assert hashlib.sha256(original[PREFIX+'sleepingdogs-fex.nro']).hexdigest()==OLD_NRO
    assert hashlib.sha256(old13[PREFIX+'sleepingdogs-fex.nro']).hexdigest()==V13_NRO
    native=json.loads((DEST/'native.json').read_text())
    assert native['build']==BUILD and native['cache_id']==BUILD_ID and native['version']==VERSION
    assert native['baseline_reproduced'] and native['baseline_elf_sha256']==OLD_ELF
    assert native['script_sha256']==sha(ROOT/'tools/build_mesa_cache_v141.py')
    for n,h in native['inputs'].items():assert sha(Path(n))==h,n
    for n,h in native['replaced_objects'].items():assert sha(Path(n))==h,n
    for n,h in json.loads((WORK/'dependencies.json').read_text()).items():assert sha(Path(n))==h,n
    assert sha(WORK/'dependencies.json')==native['dependencies_sha256']
    assert sha(WORK/'compile.json')==native['compile_sha256']
    assert sha(WORK/'library/libvulkan.a')==native['library_sha256']
    assert sha(V14/'library/libvulkan.a')==OLD_LIB
    excluded={Path(n).name for n in native['replaced_objects']}
    keep=lambda rows:[(r['name'],r['sha256']) for r in rows if r['name'] not in excluded]
    before=keep(archive_members(V14/'library/libvulkan.a'))
    after=keep(archive_members(WORK/'library/libvulkan.a'))
    assert before==after and len(after)==native['preserved_driver_member_count']==1831
    assert hashlib.sha256(json.dumps(after).encode()).hexdigest()==native['preserved_driver_members_sha256']
    compile=json.loads((WORK/'compile.json').read_text())
    for recipe in compile['recipes'].values():
        assert recipe['command'].count('-DNVK_BUILD_ID_OVERRIDE="'+BUILD_ID+'"')==1
    assert sha(WORK/'source'/PHYSICAL)==sha(V14/'source'/PHYSICAL)
    tests={}
    for n in ('low-window-v141-cache-binary.json','low-window-v141-runtime-binary.json'):
        r=json.loads((ROOT/'reports'/n).read_text());assert r['status']=='PASS'
        for p,h in r['sources'].items():assert sha(ROOT/p)==h,p
        tests[n]=r
    cache=tests['low-window-v141-cache-binary.json']
    assert cache['negative_control_detected'] and cache['cache_fix_verified']
    assert cache['native_receipt_sha256']==sha(DEST/'native.json')
    assert cache['cases']['v141']['elf_sha256']==native['elf_sha256']
    runtime=tests['low-window-v141-runtime-binary.json']
    assert runtime['elf_sha256']==native['elf_sha256']
    for label,h in runtime['reports'].items():
        n='low-window-v141-'+label+'.json';assert sha(ROOT/'reports'/n)==h
        tests[n]=json.loads((ROOT/'reports'/n).read_text())
    nro=DEST/'sleepingdogs-fex.nro'
    assert sha(nro)==native['nro_sha256']
    assert sha(ROOT/'local/symbols/sleepingdogs-low-window-v141.elf')==native['elf_sha256']
    entries[PREFIX+nro.name]=nro.read_bytes();changed={PREFIX+nro.name}
    for n,data in list(entries.items()):
        if n.startswith(PREFIX) and n.endswith('.json'):
            value=json.loads(data)
            if value.get('nro_sha256')==OLD_NRO:
                value.update(nro_sha256=native['nro_sha256'],additional_overlay=BUILD,hardware_tested=False,
                             active_driver_build_id=BUILD_ID,active_driver_version=VERSION)
                entries[n]=encode(value);changed.add(n)
    identity=PREFIX+'launcher/gm20b-cache-fix.json'
    assert identity not in original
    entries[identity]=encode(dict(build=BUILD,trial=2,trial_budget=2,correction_of='v14',
        nro_sha256=native['nro_sha256'],driver_version=VERSION,driver_build_id=BUILD_ID,
        disk_and_pipeline_identity_consistent=True,compiler_unchanged_from_v14=True,
        dxvk='3.1.1-sdbatch1',target_resolution=[1280,720],
        fex_origin='AndroSwitch Project / Ibnuard; own pes13-fex port using FEX-Emu',
        hardware_tested=False,fps_gain_measured=False))
    changed.add(identity)
    runtime_entries={n:d for n,d in entries.items() if n.startswith(PREFIX)}
    for n,data in runtime_entries.items():
        if n not in changed:assert data==original[n],n
    # Roll back to the previously hardware-tested v13, including every original
    # receipt. Neutralize the two metadata-only files that did not exist in v13.
    rollback={n:d for n,d in old13.items() if runtime_entries.get(n)!=d}
    added=set(runtime_entries)-set(old13)
    assert added=={identity,PREFIX+'launcher/gm20b-shaders.json'}
    for n in added:
        rollback[n]=encode(dict(build='sleepingdogs-v13',rolled_back=True,nro_sha256=V13_NRO,
            driver_version='26.2.2-sdv13-zcull-ubo'))
    restored=dict(runtime_entries);restored.update(rollback)
    assert all(restored[n]==d for n,d in old13.items())
    assert all(json.loads(restored[n])['rolled_back'] for n in added)
    entries['README-INSTALL.txt']='''Sleeping Dogs FEXTendo v14.1: correction of v14 cache invalidation, trial 2.
Target remains 1280x720. No hardware FPS result for this correction yet.
Close FEXTendo from HOME. Copy the entire switch folder to the SD root and overwrite.
Use DXVK 3.1.1, Performance, Launch GUI, 1280x720 and the same clocks.
First launch recompiles GPU shaders under a fresh cache ID. Warm the route once.
Save that log, restart the app, then compare the same route/scene after warm-up.
Expected marker: [SD-NVK-V14.1] instance/disk cache_id=1e3909c6aaf647614822cc8a3ee58d9e99a9e3e1
Existing cache files can remain. The v11 runtime and v14 shader-policy banners remain.
The rollback-v13 ZIP restores v13 runtime/receipts. Game/save files are not included.
Read source/low-window-gm20b-cache-fix/docs/low-window-gm20b-cache-fix.md for the v14 correction.
Older source folders are historical records; their v14 cache-isolation claim is superseded.
'''.encode()
    paths=['tools/build_mesa_cache_v141.py','tools/package_cache_v141.py','tools/port_common.py',
           'tools/build_mesa_backport.py','tools/build_mesa_shader_v14.py','tools/analyze_gameplay_v14.py',
           'tools/analyze_frame_diagnostics.py','tools/analyze_gameplay_v11.py',
           'tests/check_v141_cache_binary.py','tests/check_v141_runtime_binary.py','tests/check_low_window_binary.py',
           'tests/check_direct_sync_binary.py','tests/check_shader_binary.py','tests/check_v11_binary.py',
           'docs/low-window-gm20b-cache-fix.md']
    for n in paths:entries[SOURCE+n]=(ROOT/n).read_bytes()
    for name in ('native.json','layout.json'):entries[SOURCE+name]=(DEST/name).read_bytes()
    for name in ('compile.json','dependencies.json','layout.c'):entries[SOURCE+name]=(WORK/name).read_bytes()
    patch=[]
    for n,base in ((FILE,V13),(PHYSICAL,V14)):
        a=(base/'source'/n).read_text();b=(WORK/'source'/n).read_text()
        entries[SOURCE+'mesa/'+n]=b.encode();entries[SOURCE+'mesa-base/'+n]=a.encode()
        patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),'a/'+n,'b/'+n))
    entries[SOURCE+'sleepingdogs-v141-cache-trace.patch']=''.join(patch).encode()
    entries[SOURCE+'mesa/docs/license.rst']=(V13/'source/docs/license.rst').read_bytes()
    for n in tests:entries[SOURCE+'reports/'+n]=(ROOT/'reports'/n).read_bytes()
    for n in ('gameplay-v14-performance-analysis.json','gameplay-v14-efbe9428c2ad.json'):
        entries[SOURCE+'reports/'+n]=(ROOT/'reports'/n).read_bytes()
    assert all(not n.lower().endswith(('.exe','.nsp','.keys','.kip','.log','.big','.bix')) for n in entries)
    rollback['README-INSTALL.txt']=b'Close FEXTendo from HOME, copy the entire switch folder to SD root and overwrite. Restores v13 runtime/receipts and its cache identity. Game/save files are unchanged. New shader caches may remain on SD.\n'
    update=archive(ROOT/'dist'/(NAME+'.zip'),entries)
    undo=archive(ROOT/'dist'/(NAME+'-rollback-v13.zip'),rollback)
    for n,d in entries.items():
        if n.startswith(PREFIX) or n=='README-INSTALL.txt':
            path=ROOT/'dist'/NAME/n;path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():assert path.read_bytes()==d,n
            else:path.write_bytes(d)
    assert sha(previous)==OLD_ZIP and sha(v13)==V13_ZIP
    report=dict(status='PASS',build=BUILD,correction_of='v14',trial=2,trial_budget=2,
        update=update,rollback=undo,nro_sha256=native['nro_sha256'],elf_sha256=native['elf_sha256'],
        driver_version=VERSION,driver_build_id=BUILD_ID,baseline_zip_sha256=OLD_ZIP,baseline_preserved=True,
        changed_runtime_paths=sorted(changed),rollback_restores_v13=True,game_files_changed=[],
        preserved_driver_member_count=1831,compiler_unchanged_from_v14=True,
        wine_objects_unchanged=True,fex_adapter_unchanged=True,dxvk_unchanged=True,graphics_presets_unchanged=True,
        target_resolution=[1280,720],hardware_tested=False,fps_gain_measured=False,
        packager_sha256=sha(Path(__file__)),reports={n:sha(ROOT/'reports'/n) for n in tests})
    write_json(ROOT/'reports/low-window-gm20b-cache-fix-package.json',report)
    print('PACKAGED',update['path'],update['sha256'],flush=True)


if __name__=='__main__':main()
