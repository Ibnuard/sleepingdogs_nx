"""Fresh cumulative install, paired-runtime rejection, preservation and rollback."""
from pathlib import Path
import hashlib,json,os,sys,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
from verify_package import verify

def main():
    base=ROOT/'dist/sleepingdogs-fex-0.1.0-sd.zip'
    patch=ROOT/'dist/sleepingdogs-fex-scene-memory-fix.zip'
    rollback=ROOT/'dist/sleepingdogs-fex-scene-memory-rollback.zip'
    prior=ROOT/'dist/sleepingdogs-fex-gpu-pressure-fix.zip'
    assert sha(base)=='b2e19d4f71994a9a0fd80be51f045ee3a5c4711780aa752667497d3b88eeddfa'
    folder=Path(tempfile.mkdtemp(prefix='scene-memory-validate-',dir=ROOT/'local')).resolve()
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
                if path.exists():assert path.stat().st_nlink==1,'Never overwrite original hardlinked game data'
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
    native=json.loads((ROOT/'dist/scene-memory-fix/native.json').read_text())
    fex=json.loads((ROOT/'dist/scene-memory-fix/fex.json').read_text())
    assert installed['nro_sha256']==native['nro_sha256']
    fw=json.loads((folder/'forwarder/build.json').read_text())
    assert sha(folder/'forwarder'/fw['nsp'])==fw['sha256']=='222269d0bc876b970a1a82a82890223909dd6811776232041e7b8966c4756781'
    dll=prefix/'drive_c/windows/system32/libwow64fex.dll'
    assert sha(dll)==fex['dll_sha256']
    with zipfile.ZipFile(prior) as z:
        for name in z.namelist():
            if name.startswith('switch/sleepingdogs-fex/') and name.endswith('.dll') and name!=dll.relative_to(folder).as_posix():
                assert sha(folder/name)==hashlib.sha256(z.read(name)).hexdigest(),name
    failures=[]
    def reject(path,data,label):
        assert path.stat().st_nlink==1
        saved=path.read_bytes()
        try:
            path.write_bytes(data)
            try:verify(prefix)
            except RuntimeError as exc:failures.append({'case':label,'message':str(exc)})
            else:raise AssertionError('Accepted invalid pair: '+label)
        finally:path.write_bytes(saved)
    with zipfile.ZipFile(rollback) as z:
        reject(prefix/'sleepingdogs-fex.nro',z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro'),'old NRO/new FEX')
        reject(dll,z.read('switch/sleepingdogs-fex/drive_c/windows/system32/libwow64fex.dll'),'old FEX/new NRO')
    for name in ('compiler-memory-fix','scene-memory-fix'):
        path=prefix/'launcher'/(name+'.json');wrong=json.loads(path.read_text());wrong['compile_slots']=4
        reject(path,json.dumps(wrong).encode(),name+' wrong workspace count')
    extract(rollback);rolled=verify(prefix)
    assert rolled['nro_sha256']=='6b1c87d99b5182af103dde9495ebae033774ad9cd02b4b2f6c930434c7742905'
    assert sha(dll)=='0ca926654078800bf272ba7ddf21af393fe363697151f8016a45b2e7fb75f198'
    extract(patch);verify(prefix)
    for n,digest in prefs.items():assert sha(prefix/n)==digest,n
    assert (prefix/'launcher/fex-mode.txt').read_text().strip()=='fastest'
    assert sha(game/'HKShip.exe')==original==sha(prefix/'drive_c/SleepingDogs/HKShip.exe')
    report={'status':'PASS','install':installed,'rollback':rolled,'mismatch_rejections':failures,
        'validation_prefix':str(prefix),'game_hardlinks':linked,'original_game_sha256':original,
        'other_dlls_preserved':True,'fastest_preserved':True,'preferences_preserved':list(prefs),
        'forwarder_unchanged':fw['sha256'],'patch_sha256':sha(patch),'rollback_sha256':sha(rollback),
        'hardware_tested':False,'sources':{n:sha(ROOT/n) for n in ('tests/check_scene_memory_package.py','tools/verify_package.py')}}
    write_json(ROOT/'reports/scene-package-check.json',report)
    print(json.dumps({k:report[k] for k in ('status','validation_prefix','game_hardlinks','mismatch_rejections','patch_sha256')}))

if __name__=='__main__':main()
