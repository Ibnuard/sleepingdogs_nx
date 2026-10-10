"""Fresh complete install, managed renderer mismatch rejection, and rollback."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json,profile_config
from verify_package import verify
from dxvk_runtime import stage_renderers


def main():
    base=ROOT/'dist/sleepingdogs-fex-0.1.0-sd.zip'
    patch=ROOT/'dist/sleepingdogs-fex-dxvk-memory-fix.zip'
    rollback=ROOT/'dist/sleepingdogs-fex-dxvk-memory-rollback.zip'
    assert sha(base)=='b2e19d4f71994a9a0fd80be51f045ee3a5c4711780aa752667497d3b88eeddfa'
    folder=Path(tempfile.mkdtemp(prefix='dxvk-memory-validate-',dir=ROOT/'local')).resolve()
    prefix=folder/'switch/sleepingdogs-fex'
    managed={'drive_c/SleepingDogs/'+n for n in ('d3d9.dll','d3d11.dll','dxgi.dll')}
    def extract(archive):
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            if archive!=base:
                for line in z.read('SHA256SUMS.txt').decode().splitlines():
                    digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
            for name in z.namelist():
                if not name.startswith('switch/sleepingdogs-fex/') or name.endswith('/'):continue
                path=(folder/name).resolve();path.relative_to(folder)
                relative=path.relative_to(prefix).as_posix()
                if archive!=base and relative.startswith('drive_c/SleepingDogs/'):
                    assert relative in managed
                if path.exists():assert path.stat().st_nlink==1,'Never overwrite a linked game file'
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
    extract(base)
    prefs={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*')
           if p.is_file() and p.name in {'configuration.ini','selected.txt','fex-mode.txt','renderer-choice.txt'}}
    extract(patch)
    game=ROOT.parent/'Sleeping Dogs';linked=0
    original=sha(game/'HKShip.exe')
    for source in game.rglob('*'):
        if not source.is_file():continue
        target=prefix/'drive_c/SleepingDogs'/source.relative_to(game)
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True);os.link(source,target);linked+=1
    installed=verify(prefix)
    assert installed['nro_sha256']=='c368f044386a387e3190c2c230bbb586154b0d447046f4d35297f3d0b7e00936'
    assert sha(prefix/'drive_c/windows/system32/libwow64fex.dll')=='0ca926654078800bf272ba7ddf21af393fe363697151f8016a45b2e7fb75f198'
    assert (prefix/'launcher/fex-mode.txt').read_text().strip()=='fastest'
    for n,digest in prefs.items():assert sha(prefix/n)==digest,n
    failures=[]
    with zipfile.ZipFile(rollback) as z:
        for relative in ('drive_c/SleepingDogs/d3d11.dll','launcher/renderers/dxvk-3.1.1/dxgi.dll'):
            path=prefix/relative;current=path.read_bytes();assert path.stat().st_nlink==1
            try:
                path.write_bytes(z.read('switch/sleepingdogs-fex/'+relative))
                try:verify(prefix)
                except RuntimeError as exc:failures.append(str(exc))
                else:raise AssertionError('Mixed renderer accepted')
            finally:path.write_bytes(current)
    extract(rollback);rolled=verify(prefix)
    assert sha(prefix/'drive_c/SleepingDogs/d3d11.dll')=='598c56dce50a04adb9c2d6f134d380697b6ef1c5c3dcbf65a6de29e636710be7'
    assert sha(prefix/'drive_c/dxvk/d3d9.dll')=='2318b18d7b70538be4d12263fa701b8643636f098f517cea39a4bf4ea17c37bc'
    assert rolled['nro_sha256']==installed['nro_sha256']
    extract(patch);verify(prefix)
    # Normal future builds must select the same new set as the update ZIP.
    staging=folder/'default-staging';receipts=stage_renderers(staging,profile_config)
    for renderer,receipt in receipts.items():
        for name,digest in receipt['dlls'].items():
            assert sha(prefix/'launcher/renderers'/renderer/name)==digest
    assert sha(game/'HKShip.exe')==original==sha(prefix/'drive_c/SleepingDogs/HKShip.exe')
    report={'status':'PASS','install':installed,'rollback':rolled,'mismatch_rejections':failures,
        'validation_prefix':str(prefix),'game_hardlinks':linked,'original_game_sha256':original,
        'fastest_preserved':True,'preferences_preserved':list(prefs),'default_renderer_staging':'PASS',
        'patch_sha256':sha(patch),'rollback_sha256':sha(rollback),'hardware_tested':False}
    write_json(ROOT/'reports/dxvk-memory-package-check.json',report)
    print(json.dumps({k:report[k] for k in ('status','validation_prefix','game_hardlinks','mismatch_rejections','fastest_preserved','patch_sha256')}))


if __name__=='__main__':main()
