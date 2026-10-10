"""Validate cumulative install, mismatch rejection, and paired rollback."""
from pathlib import Path
import json
import os
import sys
import tempfile
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha, write_json
from verify_package import verify

base=ROOT/'dist/sleepingdogs-fex-0.1.0-sd.zip'
patch=ROOT/'dist/sleepingdogs-fex-compiler-memory-fix.zip'
rollback=ROOT/'dist/sleepingdogs-fex-compiler-memory-rollback.zip'
assert sha(base)=='b2e19d4f71994a9a0fd80be51f045ee3a5c4711780aa752667497d3b88eeddfa'
folder=Path(tempfile.mkdtemp(prefix='compiler-memory-validate-',dir=ROOT/'local')).resolve()
prefix=folder/'switch/sleepingdogs-fex'
def extract(archive):
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for n in z.namelist():
            if not n.startswith('switch/') or n.endswith('/'): continue
            path=(folder/n).resolve(); path.relative_to(folder)
            assert '..' not in Path(n).parts
            # Never write any linked original game file.
            assert not ('drive_c/SleepingDogs/' in n and path.exists())
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(z.read(n))
extract(base); extract(patch)
game=ROOT.parent/'Sleeping Dogs'; linked=0
for source in game.rglob('*'):
    if not source.is_file(): continue
    target=prefix/'drive_c/SleepingDogs'/source.relative_to(game)
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True); os.link(source,target); linked+=1
installed=verify(prefix)
assert (prefix/'launcher/fex-mode.txt').read_text().strip()=='fastest'
native=json.loads((ROOT/'dist/compiler-memory-fix/native.json').read_text())
assert installed['nro_sha256']==native['nro_sha256']
failures=[]
with zipfile.ZipFile(rollback) as z:
    for name in ('sleepingdogs-fex.nro','drive_c/windows/system32/libwow64fex.dll'):
        target=prefix/name; current=target.read_bytes()
        try:
            target.write_bytes(z.read('switch/sleepingdogs-fex/'+name))
            try: verify(prefix)
            except RuntimeError as exc: failures.append(str(exc))
            else: raise AssertionError('Mixed runtime accepted: '+name)
        finally: target.write_bytes(current)
extract(rollback)
rolled_back=verify(prefix)
assert rolled_back['nro_sha256']=='b2e525d647c583b15432186928a318ebf80efb921fd6f88e94efe978b1b1d79d'
assert sha(prefix/'drive_c/windows/system32/libwow64fex.dll')=='583ac0d48fd5c2e3e92f8844a23f85873064cc2b1f03a2e6b6a96d224d7de130'
# Restore the validated new pair in this isolated inspection directory.
extract(patch)
assert sha(prefix/'sleepingdogs-fex.nro')==native['nro_sha256']
assert sha(prefix/'drive_c/SleepingDogs/HKShip.exe')==native['game']['sha256']
write_json(ROOT/'reports/compiler-memory-package-check.json', {'status':'PASS','install':installed,
    'rollback':rolled_back,'mismatch_rejections':failures,'game_hardlinks':linked,'validation_prefix':str(prefix),
    'fastest_preserved':True,'original_game_sha256':sha(game/'HKShip.exe'),
    'patch_sha256':sha(patch),'rollback_sha256':sha(rollback),'hardware_tested':False})
print(json.dumps({'status':'PASS','prefix':str(prefix),'game_hardlinks':linked,'mismatch_rejections':failures,
                  'rollback':'PASS','fastest':True,'patch_sha256':sha(patch)}))
