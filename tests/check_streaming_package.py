"""Fresh cumulative install, paired mismatch rejection and complete rollback/reinstall."""
from pathlib import Path
import hashlib, json, os, sys, tempfile, zipfile
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT / 'tools'))
from port_common import sha, write_json, profile_config
from verify_package import verify
from dxvk_runtime import stage_renderers


def main():
    base = ROOT / 'dist/sleepingdogs-fex-0.1.0-sd.zip'
    patch = ROOT / 'dist/sleepingdogs-fex-streaming-memory-fix.zip'
    rollback = ROOT / 'dist/sleepingdogs-fex-streaming-memory-rollback.zip'
    assert sha(base) == 'b2e19d4f71994a9a0fd80be51f045ee3a5c4711780aa752667497d3b88eeddfa'
    folder = Path(tempfile.mkdtemp(prefix='streaming-validate-',dir=ROOT / 'local')).resolve()
    prefix = folder / 'switch/sleepingdogs-fex'
    managed = {'drive_c/SleepingDogs/' + n for n in ('d3d9.dll','d3d11.dll','dxgi.dll')}
    def extract(archive):
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            if archive != base:
                for line in z.read('SHA256SUMS.txt').decode().splitlines():
                    digest,name = line.split('  ',1); assert hashlib.sha256(z.read(name)).hexdigest() == digest
            for name in z.namelist():
                if not name.startswith(('switch/sleepingdogs-fex/','forwarder/')) or name.endswith('/'): continue
                path = (folder / name).resolve(); path.relative_to(folder)
                if name.startswith('switch/'):
                    relative = path.relative_to(prefix).as_posix()
                    if archive != base and relative.startswith('drive_c/SleepingDogs/'): assert relative in managed
                if path.exists(): assert path.stat().st_nlink == 1, 'Never overwrite linked original data'
                path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(z.read(name))
    extract(base)
    prefs = {p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*')
        if p.is_file() and p.name in {'configuration.ini','selected.txt','fex-mode.txt','renderer-choice.txt'}}
    extract(patch)
    game = ROOT.parent / 'Sleeping Dogs'; original = sha(game / 'HKShip.exe'); linked = 0
    for source in game.rglob('*'):
        if not source.is_file(): continue
        target = prefix / 'drive_c/SleepingDogs' / source.relative_to(game)
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True); os.link(source,target); linked += 1
    installed = verify(prefix)
    native = json.loads((ROOT / 'dist/streaming-memory-fix/native.json').read_text())
    assert installed['nro_sha256'] == native['nro_sha256']
    stream = json.loads((prefix / 'launcher/streaming-memory-fix.json').read_text())
    fw = json.loads((folder / 'forwarder/build.json').read_text())
    assert sha(folder / 'forwarder' / fw['nsp']) == fw['sha256'] == stream['compatible_forwarder_sha256']
    assert fw['sha256'] == '222269d0bc876b970a1a82a82890223909dd6811776232041e7b8966c4756781'
    # The NSP is byte-identical; preserve its original build receipt, including
    # the NRO hash used when it was built. Its loader tag supports the new NRO.
    assert fw == json.loads((ROOT / 'dist/gpu-budget-fix/forwarder/build.json').read_text())
    assert sha(prefix / 'drive_c/windows/system32/libwow64fex.dll') == '0ca926654078800bf272ba7ddf21af393fe363697151f8016a45b2e7fb75f198'
    assert (prefix / 'launcher/fex-mode.txt').read_text().strip() == 'fastest'
    for n,digest in prefs.items(): assert sha(prefix / n) == digest, n
    failures = []
    with zipfile.ZipFile(rollback) as z:
        for relative in ('sleepingdogs-fex.nro','drive_c/SleepingDogs/d3d11.dll',
                         'launcher/renderers/dxvk-3.1.1/dxgi.dll','drive_c/dxvk/d3d9.dll'):
            path = prefix / relative; saved = path.read_bytes(); assert path.stat().st_nlink == 1
            try:
                path.write_bytes(z.read('switch/sleepingdogs-fex/' + relative))
                try: verify(prefix)
                except RuntimeError as exc: failures.append({'file':relative,'error':str(exc)})
                else: raise AssertionError('Mixed native/renderer accepted: ' + relative)
            finally: path.write_bytes(saved)
    extract(rollback); rolled = verify(prefix)
    assert rolled['nro_sha256'] == '3c22b793e5c367158ee019af66732a1f2c332d87a2aa7ec0790bf9887016241f'
    assert sha(prefix / 'drive_c/SleepingDogs/d3d11.dll') == 'c5fbfad3dbe00a814bb7e5ba25350a1ff69cb140b2f3b44e309599d238a3cbd4'
    assert sha(folder / 'forwarder' / fw['nsp']) == fw['sha256']
    extract(patch); verify(prefix)
    receipts = stage_renderers(folder / 'default-staging',profile_config)
    for renderer,receipt in receipts.items():
        for name,digest in receipt['dlls'].items():
            assert sha(prefix / 'launcher/renderers' / renderer / name) == digest
    assert sha(game / 'HKShip.exe') == original == sha(prefix / 'drive_c/SleepingDogs/HKShip.exe')
    for n,digest in prefs.items(): assert sha(prefix / n) == digest, n
    report = {'status':'PASS','install':installed,'rollback':rolled,'mismatch_rejections':failures,
        'validation_prefix':str(prefix),'game_hardlinks':linked,'original_game_sha256':original,
        'fastest_preserved':True,'preferences_preserved':list(prefs),'default_renderer_staging':'PASS',
        'forwarder_unchanged':fw['sha256'],'patch_sha256':sha(patch),'rollback_sha256':sha(rollback),
        'hardware_tested':False}
    write_json(ROOT / 'reports/streaming-package-check.json',report)
    print(json.dumps({k:report[k] for k in ('status','validation_prefix','game_hardlinks','mismatch_rejections','fastest_preserved','patch_sha256')}))


if __name__ == '__main__': main()
