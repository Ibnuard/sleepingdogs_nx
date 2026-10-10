"""Package the tested v15 native/LSFG candidate and exact v14.1 renderer rollback.

Run in the owned WSL build workspace; never modifies the shared SDK or baselines.
"""
from pathlib import Path
import copy,gzip,hashlib,io,json,tarfile,zipfile
from port_common import ROOT,sha,write_json
from build_lsfg_backend import WORK
from prepare_lsfg_native import NATIVE
from build_dxvk_memory import manifest

PREFIX='switch/sleepingdogs-fex/'
SOURCE='source/native-v15-lsfg/'
NAME='sleepingdogs-fex-v15-native-lsfg-update'
OLD_ZIP='bae4c47ba6ad9825bdaacbf149aaacac54c3fd5a4d6824e5d14bf47f6d94fd58'
OLD_NRO='69021fdc43afcef9aed9713e50f5bb5a1a5e8865f3e842bab9fb636cb5d39f71'
OLD_DLLS={
    'd3d9.dll':'5e44fa7c97dcce1c5fddc68a633c8715a49e522b53281ee78bc3e84c8617bcf1',
    'd3d11.dll':'1fb6368e856271d15b7ad8974f7e5af3dea88f3f59ea2374935ae835b8450650',
    'dxgi.dll':'0058cf2e7d6488d1f2f457db7d73a02938eff20e8e2568a9d855d72edbbde3a6'}
REPORTS=('native-v15-host-check.json','dxvk-native-v15-host-check.json',
    'dxvk-native-v15-binary-check.json','lsfg-assets-check.json','lsfg-headless-check.json',
    'lsfg-present-check.json','lsfg-launcher-check.json','lsfg-native-check.json',
    'lsfg-v15-diagnostic-binary.json','lsfg-v15-direct-sync-binary.json',
    'lsfg-v15-low-window-binary.json','lsfg-v15-shader-binary.json')


def encode(value):return (json.dumps(value,indent=2)+'\n').encode()
def digest(data):return hashlib.sha256(data).hexdigest()


def stable_tar(files,prefix):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w',format=tarfile.PAX_FORMAT) as tar:
        for name,data in sorted(files.items()):
            assert not name.startswith('/') and '..' not in Path(name).parts
            info=tarfile.TarInfo(prefix+'/'+name);info.size=len(data);info.mode=0o644
            tar.addfile(info,io.BytesIO(data))
    return gzip.compress(buf.getvalue(),compresslevel=6,mtime=0)


def source_tree(path):
    files={}
    for p in sorted(path.rglob('*')):
        relative=p.relative_to(path)
        if '.git' in relative.parts or '__pycache__' in relative.parts or not p.is_file():continue
        assert not p.is_symlink(),p
        files[relative.as_posix()]=p.read_bytes()
    assert files
    return files


def archive(path,entries):
    assert 'SHA256SUMS.txt' not in entries
    payload=dict(entries)
    payload['SHA256SUMS.txt']=''.join(f'{digest(data)}  {name}\n' for name,data in sorted(entries.items())).encode()
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,(2026,10,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;z.writestr(info,data)
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist())==len(set(z.namelist())) and z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            expected,name=line.split('  ',1);assert digest(z.read(name))==expected,name
    return dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,files=len(payload))


def main():
    baseline=ROOT/'dist/sleepingdogs-fex-v14.1-update.zip'
    assert sha(baseline)==OLD_ZIP
    with zipfile.ZipFile(baseline) as z:
        assert z.testzip() is None
        original={n:z.read(n) for n in z.namelist() if n.startswith((PREFIX,'source/'))}
    assert digest(original[PREFIX+'sleepingdogs-fex.nro'])==OLD_NRO
    native=json.loads((ROOT/'local/lsfg-native-v15/native.json').read_text())
    build=json.loads((ROOT/'local/dxvk-native-v15/build.json').read_text())
    assert native['baseline_reproduced'] and native['baseline_nro_sha256']==OLD_NRO
    assert manifest(Path('/home/blekjek/sleepingdogs-dxvk-native-v15/source'))==build['source_files']
    assert sha(WORK/'portlibs/lib/liblsfg-vk.a')==native['backend_library_sha256']
    for name,expected in native['inputs'].items():assert sha(name)==expected,name
    prepared=json.loads((WORK/'native-prepared.json').read_text())
    for name,expected in prepared['files'].items():assert sha(NATIVE/name)==expected,name
    nro=ROOT/'local/lsfg-native-v15/sleepingdogs-fex.nro'
    assert sha(nro)==native['nro_sha256']
    assert sha(ROOT/'local/symbols/sleepingdogs-lsfg-v15.elf')==native['elf_sha256']
    tests={name:json.loads((ROOT/'reports'/name).read_text()) for name in REPORTS}
    assert all(r['status']=='PASS' for r in tests.values())
    assert tests['lsfg-native-check.json']['nro_sha256']==native['nro_sha256']
    assert tests['lsfg-native-check.json']['elf_sha256']==native['elf_sha256']
    assert tests['dxvk-native-v15-binary-check.json']['dll_sha256']==build['files']['d3d11.dll']['sha256']
    assert tests['dxvk-native-v15-host-check.json']['candidate_sources']==build['changes']
    assert tests['lsfg-present-check.json']['bridge_sha256']==sha(NATIVE/'wine-nx-probe/source/lsfg.cpp')
    geometry=tests['native-v15-host-check.json']
    assert geometry['helper_sha256']==sha(ROOT/'tools/sd_fullscreen_extent.h')
    assert geometry['window_sha256']==sha(NATIVE/'dlls/win32u/window.c')
    assert geometry['vulkan_sha256']==sha(NATIVE/'dlls/win32u/vulkan.c')

    entries=dict(original);rollback={n:d for n,d in original.items() if n.startswith(PREFIX)}
    entries[PREFIX+nro.name]=nro.read_bytes()
    for name,data in list(entries.items()):
        if name.startswith(PREFIX) and name.endswith('.json'):
            obj=json.loads(data)
            if obj.get('nro_sha256')==OLD_NRO:
                obj.update(nro_sha256=native['nro_sha256'],additional_overlay=native['build'],hardware_tested=False)
                entries[name]=encode(obj)
    dlls={};old_dlls={};managed=set()
    for name,meta in build['files'].items():
        path=ROOT/'local/dxvk-native-v15'/name;old=ROOT/'local/dxvk-native-v15-baseline'/name
        assert sha(path)==meta['sha256'] and sha(old)==OLD_DLLS[name]
        dlls[name]=path.read_bytes();old_dlls[name]=old.read_bytes()
        targets=['launcher/renderers/dxvk-3.1.1/'+name,'drive_c/SleepingDogs/'+name]
        if name=='d3d9.dll':targets.append('drive_c/dxvk/'+name)
        for rel in targets:
            entries[PREFIX+rel]=dlls[name];rollback[PREFIX+rel]=old_dlls[name];managed.add(PREFIX+rel)
    receipts=json.loads((ROOT/'local/buffer-reuse-validate-uzpwmdes/switch/sleepingdogs-fex/launcher/dxvk-releases.json').read_text())
    archives={}
    for version,files,target in (('sdbatch2',dlls,entries),('sdbatch1',old_dlls,rollback)):
        renderer=stable_tar({'x32/'+n:d for n,d in files.items()},'dxvk-3.1.1-'+version)
        archive_name='dxvk-3.1.1-'+version+'.tar.gz';archives[archive_name]=digest(renderer)
        receipt=copy.deepcopy(receipts)
        receipt['dxvk-3.1.1']=dict(build='sleepingdogs-dxvk-'+version,
            url='https://github.com/doitsujin/dxvk/tree/b1a1c99ab52b687cf950d62c88bc2fa316b41663',
            archive_sha256=digest(renderer),dlls={n:digest(d) for n,d in files.items()},
            patch=dict(build='sleepingdogs-dxvk-'+version,option='d3d11.sdSubmissionBatching',
                       max_deferred_hint_chunks=24 if version=='sdbatch2' else 12,hardware_tested=False))
        target[PREFIX+'launcher/dxvk-releases.json']=encode(receipt)
        target[SOURCE+archive_name]=renderer
    batching=json.loads(entries[PREFIX+'launcher/dxvk-submit-batching.json'])
    batching.update(build='sleepingdogs-dxvk-sdbatch2',dlls={n:digest(d) for n,d in dlls.items()},
        native_runtime=native['build'],max_deferred_hint_chunks=24,fps_gain_measured=False)
    entries[PREFIX+'launcher/dxvk-submit-batching.json']=encode(batching)
    identity=PREFIX+'launcher/native-v15-lsfg.json'
    entries[identity]=encode(dict(build=native['build'],nro_sha256=native['nro_sha256'],
        dxvk='3.1.1-sdbatch2',target_resolution=[1280,720],lsfg_default_enabled=False,
        lsfg_performance=True,lsfg_motion_default=0.25,fex_origin='own pes13-fex-derived port',
        driver_cache_id=native['driver_cache_id'],hardware_tested=False,fps_gain_measured=False))
    rollback[identity]=encode(dict(build='sleepingdogs-v14.1',rolled_back=True,nro_sha256=OLD_NRO,dxvk='3.1.1-sdbatch1'))
    pack=ROOT/'local/lsfg-shaders-v15/lsfg-3.1.sdp'
    assert sha(pack)==tests['lsfg-assets-check.json']['pack_sha256']==tests['lsfg-headless-check.json']['pack_sha256']
    entries[PREFIX+'lsfg/lsfg-3.1.sdp']=pack.read_bytes()

    # Include modified open-source components, their licenses and local recipes.
    for label,path in (('lsfg-backend',WORK/'backend'),('dxbc-converter',WORK/'dxbc'),
                       ('dxvk-sdbatch2',Path('/home/blekjek/sleepingdogs-dxvk-native-v15/source'))):
        files=source_tree(path);payload=stable_tar(files,label)
        entries[SOURCE+label+'-source.tar.gz']=payload
        entries[SOURCE+label+'-source-files.json']=encode({n:digest(d) for n,d in files.items()})
    for folder,path in (('native',NATIVE),('horizon-recipe',WORK/'recipe'),
                        ('horizon-upstream',ROOT/'local/research-lsfg/switch-dev'),
                        ('autorun-upstream',ROOT/'local/research-lsfg/autorun')):
        for name,data in source_tree(path).items():entries[SOURCE+folder+'/'+name]=data
    for group in ('tools','tests'):
        for path in (ROOT/group).iterdir():
            if path.is_file() and path.suffix in ('.py','.c','.cpp','.h','.hpp','.S'):
                entries[SOURCE+group+'/'+path.name]=path.read_bytes()
    for name in REPORTS+('lsfg-shader-conversion.json','lsfg-backend-build.json','gameplay-v11-e0004d2a7fe4.json'):
        entries[SOURCE+'reports/'+name]=(ROOT/'reports'/name).read_bytes()
    for name,path in (('native.json',ROOT/'local/lsfg-native-v15/native.json'),
        ('dxvk-build.json',ROOT/'local/dxvk-native-v15/build.json'),('native-prepared.json',WORK/'native-prepared.json'),
        ('sleepingdogs-lsfg-v15.patch',ROOT/'local/research-lsfg/sleepingdogs-lsfg-v15.patch'),
        ('docs/native-v15-lsfg.md',ROOT/'docs/native-v15-lsfg.md'),
        ('licenses/lsfg-vk-GPLv3.md',WORK/'backend/LICENSE.md'),
        ('licenses/DXBC-zlib.md',WORK/'dxbc/LICENSE.md'),
        ('licenses/DXVK-zlib.txt',Path('/home/blekjek/sleepingdogs-dxvk-native-v15/source/LICENSE'))):
        entries[SOURCE+name]=path.read_bytes()
    entries['README-INSTALL.txt']=b'''Sleeping Dogs FEXTendo v15 - native FPS candidate + optional LSFG
Close FEXTendo from HOME. Merge the entire switch folder into the SD root.
Copy all included files, including DXVK DLLs, not only the NRO.
Test first: DXVK 3.1.1 / Performance / Launch GUI / 1280x720 / LSFG OFF.
Use the same clocks, route, camera and graphics settings. Warm the route once.
Save fex-runtime.log before restarting. Native FPS gain and 30 FPS are unmeasured.
Confirm: [SD-NATIVE-V15] swapchain=1280x720 host=1280x720 extra_scale=0
Confirm: [SD-DXVK-BATCH] v2 and [SD-LSFG-V15] configured off.
Optional LSFG: Settings > Frame Generation > LSFG 2x, motion resolution 25%.
Performance mode is fixed ON. First install defaults OFF; existing choices persist.
LSFG adds display frames and GPU cost; it does not accelerate game simulation.
The rollback-v14.1 ZIP restores the prior NRO and sdbatch1 renderer DLLs.
This is an update to the existing installation. No game assets or saves included.
Details, test limits and sources: source/native-v15-lsfg/docs/native-v15-lsfg.md
'''
    rollback['README-INSTALL.txt']=b'''Close FEXTendo from HOME. Merge the entire switch folder into the SD root.
Restores the exact v14.1 NRO, its metadata and DXVK 3.1.1-sdbatch1 DLLs.
Game files, saves and settings remain. LSFG data/cache may remain unused on SD.
'''

    runtime={n:d for n,d in entries.items() if n.startswith(PREFIX)}
    allowed={n for n in original if n.startswith(PREFIX)}|managed|{
        identity,PREFIX+'launcher/dxvk-releases.json',PREFIX+'lsfg/lsfg-3.1.sdp'}
    assert set(runtime)==allowed
    assert all('/drive_c/' not in n or n in managed for n in runtime)
    assert not any(n.endswith(('lsfg.txt','UserOptions.dat','settings.txt','dxvk.conf')) for n in runtime)
    restored=dict(runtime);restored.update({n:d for n,d in rollback.items() if n.startswith(PREFIX)})
    assert all(restored[n]==d for n,d in original.items() if n.startswith(PREFIX))
    for n in managed:assert restored[n]==old_dlls[Path(n).name]
    assert json.loads(restored[identity])['rolled_back']
    assert all(not n.lower().endswith(('.exe','.nsp','.keys','.kip','.big','.bix','.log')) for n in entries)
    update=archive(ROOT/'dist'/(NAME+'.zip'),entries)
    undo=archive(ROOT/'dist'/'sleepingdogs-fex-v15-rollback-v14.1.zip',rollback)
    for name,data in entries.items():
        if name.startswith(PREFIX) or name=='README-INSTALL.txt':
            path=ROOT/'dist'/NAME/name;path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():assert path.read_bytes()==data,name
            else:path.write_bytes(data)
    assert sha(baseline)==OLD_ZIP
    write_json(ROOT/'reports/native-v15-package.json',dict(status='PASS',build=native['build'],
        update=update,rollback=undo,nro_sha256=native['nro_sha256'],elf_sha256=native['elf_sha256'],
        baseline_preserved=True,rollback_restores_nro_and_dlls=True,managed_dll_copies=len(managed),
        preserved_game_assets=True,preserved_saves=True,preserved_settings=True,lsfg_default_enabled=False,
        native_fps_changes=['720p borderless geometry','bounded DXVK automatic submission batching'],
        driver_cache_id=native['driver_cache_id'],fex_unchanged=True,dxvk_updated=True,
        renderer_archives=archives,runtime_files={n:digest(d) for n,d in runtime.items()},
        reports={n:sha(ROOT/'reports'/n) for n in REPORTS},packager_sha256=sha(Path(__file__)),
        hardware_tested=False,fps_gain_measured=False))
    print('PACKAGED',update,undo,flush=True)


if __name__=='__main__':main()
