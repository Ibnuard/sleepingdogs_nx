"""Fresh install, mismatched renderer rejection, unchanged settings and rollback."""
from pathlib import Path
import hashlib, json, os, sys, tempfile, zipfile
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json
from verify_package import verify


def main():
    base = ROOT / 'dist/sleepingdogs-fex-0.1.0-sd.zip'
    patch = ROOT / 'dist/sleepingdogs-fex-buffer-reuse-fix.zip'
    rollback = ROOT / 'dist/sleepingdogs-fex-buffer-reuse-rollback.zip'
    prior = ROOT / 'dist/sleepingdogs-fex-scene-memory-fix.zip'
    assert sha(base) == 'b2e19d4f71994a9a0fd80be51f045ee3a5c4711780aa752667497d3b88eeddfa'
    folder = Path(tempfile.mkdtemp(prefix='buffer-reuse-validate-', dir=ROOT / 'local')).resolve()
    prefix = folder / 'switch/sleepingdogs-fex'; game_prefix = 'drive_c/SleepingDogs/'
    managed = {base_path + n for n in ('d3d9.dll','d3d11.dll','dxgi.dll')
               for base_path in (game_prefix, 'launcher/renderers/dxvk-3.1.1/')}
    managed.add('drive_c/dxvk/d3d9.dll')
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
                    if archive != base and relative.startswith(game_prefix): assert relative in managed
                if path.exists(): assert path.stat().st_nlink == 1, 'Never overwrite original hardlinked game data'
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(z.read(name))
    extract(base)
    prefs = {p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()
             and (p.name in {'configuration.ini','selected.txt','fex-mode.txt','renderer-choice.txt'} or p.suffix == '.conf')}
    extract(patch)
    game = ROOT.parent / 'Sleeping Dogs'; original = sha(game / 'HKShip.exe'); linked = 0
    for source in game.rglob('*'):
        if not source.is_file(): continue
        target = prefix / game_prefix / source.relative_to(game)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True); os.link(source,target); linked += 1
    installed = verify(prefix)
    assert installed['nro_sha256'] == 'de0a9ea83adcdf8e68a1b0cd3d8383af50e911ec99e7e43149ddadb98367b0f7'
    fex = prefix / 'drive_c/windows/system32/libwow64fex.dll'
    assert sha(fex) == '48b169a80966676100c7b361343072766973809a80727cb2fcfe8bb33a300024'
    fw = json.loads((folder / 'forwarder/build.json').read_text())
    assert sha(folder / 'forwarder' / fw['nsp']) == fw['sha256'] == '222269d0bc876b970a1a82a82890223909dd6811776232041e7b8966c4756781'
    with zipfile.ZipFile(prior) as z:
        for name in z.namelist():
            if name.startswith('switch/sleepingdogs-fex/') and name.endswith('.dll'):
                relative = name.removeprefix('switch/sleepingdogs-fex/')
                if relative not in managed: assert sha(folder / name) == hashlib.sha256(z.read(name)).hexdigest(),name
    failures = []
    def reject(path,data,label):
        assert path.stat().st_nlink == 1
        saved = path.read_bytes()
        try:
            path.write_bytes(data)
            try: verify(prefix)
            except RuntimeError as exc: failures.append({'case':label,'message':str(exc)})
            else: raise AssertionError('Accepted invalid renderer update: ' + label)
        finally: path.write_bytes(saved)
    with zipfile.ZipFile(rollback) as z:
        for relative in (game_prefix + 'd3d11.dll', 'launcher/renderers/dxvk-3.1.1/dxgi.dll'):
            reject(prefix / relative, z.read('switch/sleepingdogs-fex/' + relative), 'stale ' + relative)
    receipt_path = prefix / 'launcher/buffer-reuse-fix.json'
    wrong = json.loads(receipt_path.read_text()); wrong['max_idle_bytes'] = 33554432
    reject(receipt_path, json.dumps(wrong).encode(), 'wrong cache budget')
    extract(rollback); rolled = verify(prefix)
    assert rolled['nro_sha256'] == installed['nro_sha256']
    with zipfile.ZipFile(prior) as z:
        for relative in managed:
            assert sha(prefix / relative) == hashlib.sha256(z.read('switch/sleepingdogs-fex/' + relative)).hexdigest(), relative
    extract(patch); verify(prefix)
    for name,digest in prefs.items(): assert sha(prefix / name) == digest,name
    assert (prefix / 'launcher/fex-mode.txt').read_text().strip() == 'fastest'
    assert sha(game / 'HKShip.exe') == original == sha(prefix / game_prefix / 'HKShip.exe')
    assert sha(fex) == '48b169a80966676100c7b361343072766973809a80727cb2fcfe8bb33a300024'
    report = {'status':'PASS','install':installed,'rollback':rolled,'mismatch_rejections':failures,
        'validation_prefix':str(prefix),'game_hardlinks':linked,'original_game_sha256':original,
        'other_dlls_preserved':True,'fastest_preserved':True,'preferences_preserved':list(prefs),
        'forwarder_unchanged':fw['sha256'],'patch_sha256':sha(patch),'rollback_sha256':sha(rollback),
        'hardware_tested':False,'sources':{n:sha(ROOT / n) for n in ('tests/check_buffer_reuse_package.py','tools/verify_package.py')}}
    write_json(ROOT / 'reports/buffer-reuse-package-check.json', report)
    print(json.dumps({k:report[k] for k in ('status','validation_prefix','game_hardlinks','mismatch_rejections','patch_sha256')}))


if __name__ == '__main__': main()
