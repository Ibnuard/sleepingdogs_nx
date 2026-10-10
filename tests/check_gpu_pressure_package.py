"""Fresh install, exact runtime preservation, mixed-NRO rejection and rollback."""
from pathlib import Path
import hashlib,json,os,sys,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
from verify_package import verify


def main():
    base=ROOT/'dist/sleepingdogs-fex-0.1.0-sd.zip'
    patch=ROOT/'dist/sleepingdogs-fex-gpu-pressure-fix.zip'
    rollback=ROOT/'dist/sleepingdogs-fex-gpu-pressure-rollback.zip'
    assert sha(base)=='b2e19d4f71994a9a0fd80be51f045ee3a5c4711780aa752667497d3b88eeddfa'
    folder=Path(tempfile.mkdtemp(prefix='gpu-pressure-validate-',dir=ROOT/'local')).resolve()
    prefix=folder/'switch/sleepingdogs-fex'
    managed={'drive_c/SleepingDogs/'+n for n in ('d3d9.dll','d3d11.dll','dxgi.dll')}
    def extract(archive):
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            if archive!=base:
                for line in z.read('SHA256SUMS.txt').decode().splitlines():
                    digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
            for name in z.namelist():
                if not name.startswith(('switch/sleepingdogs-fex/','forwarder/')) or name.endswith('/'):continue
                path=(folder/name).resolve();path.relative_to(folder)
                if name.startswith('switch/'):
                    relative=path.relative_to(prefix).as_posix()
                    if archive!=base and relative.startswith('drive_c/SleepingDogs/'):assert relative in managed
                if path.exists():assert path.stat().st_nlink==1,'Never overwrite linked original data'
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
    extract(base)
    prefs={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()
        and p.name in {'configuration.ini','selected.txt','fex-mode.txt','renderer-choice.txt'}}
    extract(patch)
    game=ROOT.parent/'Sleeping Dogs';original=sha(game/'HKShip.exe');linked=0
    for source in game.rglob('*'):
        if not source.is_file():continue
        target=prefix/'drive_c/SleepingDogs'/source.relative_to(game)
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True);os.link(source,target);linked+=1
    installed=verify(prefix)
    native=json.loads((ROOT/'dist/gpu-pressure-fix/native.json').read_text())
    assert installed['nro_sha256']==native['nro_sha256']
    fw=json.loads((folder/'forwarder/build.json').read_text())
    assert sha(folder/'forwarder'/fw['nsp'])==fw['sha256']=='222269d0bc876b970a1a82a82890223909dd6811776232041e7b8966c4756781'
    fex=prefix/'drive_c/windows/system32/libwow64fex.dll'
    assert sha(fex)=='0ca926654078800bf272ba7ddf21af393fe363697151f8016a45b2e7fb75f198'
    with zipfile.ZipFile(ROOT/'dist/sleepingdogs-fex-streaming-memory-fix.zip') as z:
        for name in z.namelist():
            if name.startswith('switch/sleepingdogs-fex/') and name.endswith('.dll'):
                assert sha(folder/name)==hashlib.sha256(z.read(name)).hexdigest(),name
    failures=[];nro=prefix/'sleepingdogs-fex.nro';saved=nro.read_bytes();assert nro.stat().st_nlink==1
    with zipfile.ZipFile(rollback) as z:
        try:
            nro.write_bytes(z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro'))
            try:verify(prefix)
            except RuntimeError as exc:failures.append(str(exc))
            else:raise AssertionError('Mixed old NRO/new receipts accepted')
        finally:nro.write_bytes(saved)
    # The new pressure receipt itself must reject a mismatched native hash.
    receipt=prefix/'launcher/gpu-pressure-fix.json';saved=receipt.read_bytes()
    try:
        wrong=json.loads(saved);wrong['nro_sha256']='0'*64;receipt.write_text(json.dumps(wrong))
        try:verify(prefix)
        except RuntimeError as exc:failures.append(str(exc))
        else:raise AssertionError('Invalid pressure receipt accepted')
    finally:receipt.write_bytes(saved)
    extract(rollback);rolled=verify(prefix)
    assert rolled['nro_sha256']=='9a5ef65f646fef4582bb0493573aaadc6c1e51c167de86bff2090f38cb0d0a8f'
    extract(patch);verify(prefix)
    for n,digest in prefs.items():assert sha(prefix/n)==digest,n
    assert (prefix/'launcher/fex-mode.txt').read_text().strip()=='fastest'
    assert sha(game/'HKShip.exe')==original==sha(prefix/'drive_c/SleepingDogs/HKShip.exe')
    report={'status':'PASS','install':installed,'rollback':rolled,'mismatch_rejections':failures,
        'validation_prefix':str(prefix),'game_hardlinks':linked,'original_game_sha256':original,
        'dlls_preserved':True,'fastest_preserved':True,'preferences_preserved':list(prefs),
        'forwarder_unchanged':fw['sha256'],'patch_sha256':sha(patch),'rollback_sha256':sha(rollback),
        'hardware_tested':False}
    write_json(ROOT/'reports/gpu-pressure-package-check.json',report)
    print(json.dumps({k:report[k] for k in ('status','validation_prefix','game_hardlinks','mismatch_rejections','patch_sha256')}))


if __name__=='__main__':main()
