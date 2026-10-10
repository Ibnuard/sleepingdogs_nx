"""Install/rollback the paired update without modifying linked original game data."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json
from verify_package import verify


def main():
    base = ROOT / 'dist/sleepingdogs-fex-0.1.0-sd.zip'
    patch = ROOT / 'dist/sleepingdogs-fex-gpu-budget-fix.zip'
    rollback = ROOT / 'dist/sleepingdogs-fex-gpu-budget-rollback.zip'
    assert sha(base) == 'b2e19d4f71994a9a0fd80be51f045ee3a5c4711780aa752667497d3b88eeddfa'
    folder = Path(tempfile.mkdtemp(prefix='gpu-budget-validate-', dir=ROOT / 'local')).resolve()
    prefix = folder / 'switch/sleepingdogs-fex'
    managed = {'drive_c/SleepingDogs/' + n for n in ('d3d9.dll', 'd3d11.dll', 'dxgi.dll')}
    def extract(archive):
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            if archive != base:
                for line in z.read('SHA256SUMS.txt').decode().splitlines():
                    digest, name = line.split('  ', 1)
                    assert hashlib.sha256(z.read(name)).hexdigest() == digest
            for name in z.namelist():
                if not name.startswith(('switch/sleepingdogs-fex/', 'forwarder/')) or name.endswith('/'): continue
                path = (folder / name).resolve(); path.relative_to(folder)
                if name.startswith('switch/'):
                    relative = path.relative_to(prefix).as_posix()
                    if archive != base and relative.startswith('drive_c/SleepingDogs/'): assert relative in managed
                if path.exists(): assert path.stat().st_nlink == 1, 'Never overwrite a linked game file'
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(z.read(name))
    extract(base)
    prefs = {p.relative_to(prefix).as_posix(): sha(p) for p in prefix.rglob('*')
             if p.is_file() and p.name in {'configuration.ini', 'selected.txt', 'fex-mode.txt', 'renderer-choice.txt'}}
    extract(patch)
    game = ROOT.parent / 'Sleeping Dogs'; original = sha(game / 'HKShip.exe'); linked = 0
    for source in game.rglob('*'):
        if not source.is_file(): continue
        target = prefix / 'drive_c/SleepingDogs' / source.relative_to(game)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True); os.link(source, target); linked += 1
    installed = verify(prefix)
    native = json.loads((ROOT / 'dist/gpu-budget-fix/native.json').read_text())
    fw = json.loads((folder / 'forwarder/build.json').read_text())
    assert fw['nro_sha256'] == installed['nro_sha256'] == native['nro_sha256']
    assert sha(folder / 'forwarder' / fw['nsp']) == fw['sha256']
    previous_fw = json.loads((ROOT / 'dist/forwarder/build.json').read_text())
    for field in ('title_id', 'target', 'capabilities', 'address_space'):
        assert fw[field] == previous_fw[field]
    assert fw['additional_heap_bytes'] == 67108864 and fw['packed_payload_verified']
    assert sha(prefix / 'drive_c/windows/system32/libwow64fex.dll') == '0ca926654078800bf272ba7ddf21af393fe363697151f8016a45b2e7fb75f198'
    assert (prefix / 'launcher/fex-mode.txt').read_text().strip() == 'fastest'
    for n, digest in prefs.items(): assert sha(prefix / n) == digest, n
    failures = []
    nr = prefix / 'sleepingdogs-fex.nro'; saved = nr.read_bytes(); assert nr.stat().st_nlink == 1
    with zipfile.ZipFile(rollback) as z:
        try:
            nr.write_bytes(z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro'))
            try: verify(prefix)
            except RuntimeError as exc: failures.append(str(exc))
            else: raise AssertionError('Old NRO accepted with new receipts')
        finally: nr.write_bytes(saved)
    extract(rollback); rolled = verify(prefix)
    assert rolled['nro_sha256'] == 'c368f044386a387e3190c2c230bbb586154b0d447046f4d35297f3d0b7e00936'
    assert sha(folder / 'forwarder' / fw['nsp']) == previous_fw['sha256']
    assert sha(prefix / 'drive_c/SleepingDogs/d3d11.dll') == 'c5fbfad3dbe00a814bb7e5ba25350a1ff69cb140b2f3b44e309599d238a3cbd4'
    extract(patch); verify(prefix)
    assert sha(game / 'HKShip.exe') == original == sha(prefix / 'drive_c/SleepingDogs/HKShip.exe')
    write_json(ROOT / 'reports/gpu-budget-package-check.json', {'status': 'PASS',
        'install': installed, 'rollback': rolled, 'mismatch_rejections': failures,
        'forwarder_identity_preserved': True, 'forwarder_sha256': fw['sha256'],
        'validation_prefix': str(prefix), 'game_hardlinks': linked, 'original_game_sha256': original,
        'fastest_preserved': True, 'preferences_preserved': list(prefs),
        'patch_sha256': sha(patch), 'rollback_sha256': sha(rollback), 'hardware_tested': False})
    print(json.dumps({'status': 'PASS', 'validation_prefix': str(prefix), 'linked_game_files': linked,
        'mixed_nro_rejected': failures, 'install_rollback_reinstall': 'PASS', 'fastest_preserved': True}))


if __name__ == '__main__': main()
