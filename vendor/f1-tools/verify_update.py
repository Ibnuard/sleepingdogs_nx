"""Verify GPU heap recovery update against the shipped 0.1.27 parent."""
from pathlib import Path
import hashlib, json, sys, zipfile
from verify_package import inspect_nro, inventory, ROOT
from dxvk_runtime import release_files

def digest(data):return hashlib.sha256(data).hexdigest()

def verify(archive, parent, manifest):
    assert digest(parent.read_bytes()) == manifest['archive_sha256']
    with zipfile.ZipFile(parent) as old, zipfile.ZipFile(archive) as new:
        assert old.testzip() is None and new.testzip() is None
        added = set()
        allowed = {'switch/f1-fex/f1-fex.nro','UPDATE.txt','SHA256SUMS.txt'} | added
        assert set(new.namelist()) == set(old.namelist()) | added
        assert len(new.namelist()) == len(set(new.namelist()))
        changed=[]
        for name in new.namelist():
            data=new.read(name)
            if name not in old.namelist() or data!=old.read(name):changed.append(name)
            if name in manifest['files'] and name not in allowed:
                assert digest(data)==manifest['files'][name],name
            assert not name.endswith(('F1_2013.exe','configuration.ini','selected.txt','renderer-choice.txt',
                                      'crash.log','fex-runtime.log','.xml'))
            if name.endswith('.conf'):assert b'\r' not in data,name
        assert set(changed)==allowed,changed
        assert new.read('switch/f1-fex/launcher/fex-mode.txt') == b'fastest\n'
        for line in new.read('SHA256SUMS.txt').decode().splitlines():
            value,name=line.split('  ',1)
            assert digest(new.read(name))==value,name
        nro=new.read('switch/f1-fex/f1-fex.nro')
        meta=inspect_nro(nro,expected_title='F1 2013 - FEXTendo',expected_version='0.1.28')
        assert b'switch/pes13-fex' not in nro and 'switch/pes13-fex'.encode('utf-16le') not in nro
        for label in (b'/F1_2013/F1_2013.exe',b'400000-15ed000',b'FEXTendo / F1 2013',
            b'Launch Debug',b'Graphics',b'Keyboard',b'f1-fextendo-0.1.28-memory-map',b'[F1-MEMMAP]',b'report-memory-mb.txt',b'[F1-MEMBUDGET]',b'[F1-VKDEVICE]',b'circuit-memory-v5',
            b'[F1-GPU-ARENA]', b'source=ordinary-heap', b'[F1-GPU-SCAN]', b'protected=1', b'FEX compiler stopped', b'[F1-GPU-HEAP]', b'[F1-GPU-HEAP-STATS]', b'[F1-GPU-NVMAP]',
            b'[F1-CODE-MEM]', b'eager_spare=off',b'1280x720 fullscreen',
            b'[F1-NATIVE-STACKS]',b'[F1-NATIVE-STACK-RECOVER]',
            b'[F1-SCRATCH-RESERVE]',b'[F1-VKMEM-STATS]',b'scratch_released=',
            b'[F1-STATE] guest-exited',b'[F1-FEX-MODE]',b'[F1-RUST-HEAP]',b'[F1-SCRATCH-RECOVER]',b'[F1-SCRATCH-PAGES]',b'[F1-VIRTMEM]',b'[F1-PAGES]',b'[F1-VKMEM]',b'[F1-GUEST]',b'[F1-GUEST-FRAME]',b'[F1-GUEST-STACK]',
            b'[F1-SCRATCH]',b'[F1-AUDIO]',b'[F1-GRAPHICS]',b'.pre-0.1.27.bak',
            b'[F1-RESTART]',b'[F1-MODES]',b'last-game-return.bin',b'fex-runtime-previous.log',
            b'Game stopped',b'circuit-memory-v5.txt',b'[F1-THREAD-RECOVER]',b'Cannot start game worker',
            b'WINEDLLOVERRIDES=d3d9,d3d11,dxgi=n,b',b'guest-process-exit',b'unhandled-native-exception'):
            assert label in nro,label
        assert b'/PES13/pes2013.exe' not in nro
        from f1_fex_spare import patch
        original=ROOT.parent/'pes13-nx/local/production-input-fix/approved/switch/pes13-fex/drive_c/windows/system32/libwow64fex.dll'
        expected,policy=patch(original.read_bytes())
        assert new.read('switch/f1-fex/drive_c/windows/system32/libwow64fex.dll')==expected
        assert json.loads(new.read('switch/f1-fex/launcher/fex-memory-policy.json'))==policy
        for renderer,files in release_files().items():
            for name,data in files.items():
                assert new.read('switch/f1-fex/launcher/renderers/'+renderer+'/'+name)==data
        receipt=json.loads(new.read('switch/f1-fex/launcher/dxvk-3.1.1-f1mem2.json'))
        assert digest(new.read('switch/f1-fex/launcher/dxvk-3.1.1-f1mem2.patch'))==receipt['patch_sha256']
        assert new.read('switch/f1-fex/launcher/dxvk-3.1.1-f1mem2.json')==(ROOT/'vendor/dxvk/dxvk-3.1.1-f1mem2.json').read_bytes()
    game=ROOT/'F1 2013'
    exe_hash=digest((game/'F1_2013.exe').read_bytes())
    assert exe_hash==manifest['build_inputs']['game_exe_sha256']
    files=inventory(game)
    assert len(files)==5589 and sum(files.values())==11296904761
    return {'passed':True,'hardware_tested':False,'nro_metadata':meta,'nro_sha256':digest(nro),
            'game_exe_sha256':exe_hash,'game_files':len(files),'game_bytes':sum(files.values()),
            'changed_archive_entries':changed,'parent_zip_sha256':manifest['archive_sha256'],
            'unchanged_other_wine_dlls_and_presets':True,'fex_mode':'fastest',
            'fex_memory_policy':policy,'resolution_restoration':'1280x720 fullscreen with circuit memory profile v5, once',
            'dxvk_patched':'3.1.1-f1mem2','dxvk_async_unchanged':True,
            'dependency_audit':json.loads((ROOT/'debug/0.1.20-thread-memory/dependencies-0.1.21.json').read_text())}

if __name__=='__main__':
    archive,parent=map(Path,sys.argv[1:3])
    report=verify(archive,parent,json.loads(parent.with_name(parent.stem+'-manifest.json').read_text()))
    print(json.dumps(report,indent=2))
