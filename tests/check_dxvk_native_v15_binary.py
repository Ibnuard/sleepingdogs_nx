"""Run actual PE32 v15 functions and check imports/exports against v12."""
from pathlib import Path
import json,tarfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
from check_dxvk_batch_binary import Replay
from package_dxvk_memory import interfaces

def main():
    archive=ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.tar.gz'
    receipt=json.loads((ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.json').read_text())
    assert sha(archive)==receipt['archive_sha256']
    with tarfile.open(archive) as tar:base=tar.extractfile('dxvk-3.1.1-sdrecycle1/x32/d3d11.dll').read()
    folder=ROOT/'local/dxvk-native-v15';dll=folder/'d3d11.dll';build=json.loads((folder/'build.json').read_text())
    original,off,on=Replay(base,False),Replay(dll.read_bytes(),True),Replay(dll.read_bytes(),True)
    cases=0
    for maximum in range(4):
        for kind in range(4):
            for pending in (0,1,2,4,9):
                for chunks in (0,1,3,6,11,12,20,23,24,25,40):
                    for cost in (0,1499,1500):
                        for item,enabled in ((original,False),(off,False),(on,True)):
                            item.init(enabled,maximum);item.notify(100,30)
                        a=original.consider(kind,100+chunks,30-pending,cost)
                        b=off.consider(kind,100+chunks,30-pending,cost)
                        c=on.consider(kind,100+chunks,30-pending,cost)
                        assert a==b and (not c or a)
                        if kind<2 or pending<2 or chunks>=24 or cost>=1500 or kind>maximum:assert a==c
                        cases+=1
    on.init(True);on.notify(20,10)
    assert on.consider(2,23,8,10)==0 and on.consider(1,23,8,10)==0
    assert on.consider(1,23,9,10)==1
    on.notify(23,11);assert on.consider(0,24,9,10)==1
    abi={}
    for name,meta in build['files'].items():
        path=folder/name;assert sha(path)==meta['sha256']
        old=ROOT/'local/dxvk-native-v15-baseline'/name
        assert interfaces(path.read_bytes())==interfaces(old.read_bytes()),name
        abi[name]={'interfaces_unchanged':True,'sha256':sha(path)}
    write_json(ROOT/'reports/dxvk-native-v15-binary-check.json',dict(status='PASS',cases=cases,
        dll_sha256=sha(dll),readback_progress=True,explicit_flush_preserved=True,interfaces=abi,
        hardware_tested=False))
    print('PASS PE32 v15 tracker cases=',cases,'interfaces unchanged')

if __name__=='__main__':main()
