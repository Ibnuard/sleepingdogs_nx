"""Convert the user's Lossless Scaling 3.2.1 shaders, without executing its DLL.

Run with Windows Python (pefile). The compiler runs in WSL Ubuntu. Output is
personal runtime data derived exclusively from the supplied installation.
"""
from pathlib import Path
import argparse, hashlib, struct, subprocess, json
import pefile
from port_common import ROOT, sha, write_json

DLL_SHA='8b7dbc11b2ea544650af2ed4ffc92da3abd88ec5afa09c36484c060fbc848834'
WORK='/home/blekjek/sleepingdogs-lsfg-v15'

def fnv(data):
    h=2166136261
    for x in data: h=((h^x)*16777619)&0xffffffff
    return h

def wsl_path(path):
    p=Path(path).resolve().as_posix()
    return '/mnt/'+p[0].lower()+p[2:] if p[1:3]==':/' else p

def instructions(data):
    words=struct.unpack('<%dI'%(len(data)//4),data)
    assert words[0]==0x07230203 and words[4]==0
    pos=5
    while pos<len(words):
        n,op=words[pos]>>16,words[pos]&65535
        assert n and pos+n<=len(words)
        yield op,words[pos+1:pos+n]
        pos+=n

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('dll',type=Path)
    a=ap.parse_args()
    assert sha(a.dll)==DLL_SHA,'Only the audited 3.2.1 DLL layout is accepted'
    pe=pefile.PE(str(a.dll))
    resources={e.id:pe.get_data(e.directory.entries[0].data.struct.OffsetToData,
        e.directory.entries[0].data.struct.Size) for t in pe.DIRECTORY_ENTRY_RESOURCE.entries
        if t.id==10 for e in t.directory.entries}
    ids={256}|{i+p for i in range(257,279) for p in (0,23)}
    output=ROOT/'local/lsfg-shaders-v15'; output.mkdir(parents=True,exist_ok=True)
    for rid in sorted(ids):
        data=resources[rid];assert data[:4]==b'DXBC'
        (output/f'{rid}.dxbc').write_bytes(data)
    # No shell interpolation of user filenames; call the pinned converter directly.
    for rid in sorted(ids):
        subprocess.run(['wsl','-d','Ubuntu','--',WORK+'/lsfg_translate',
            wsl_path(output/f'{rid}.dxbc'),wsl_path(output/f'{rid}.spv')],check=True)
    payload=bytearray(b'SDLSFG15'+struct.pack('<II',1,len(ids))+bytes.fromhex(DLL_SHA))
    records=[]
    for rid in sorted(ids):
        data=(output/f'{rid}.spv').read_bytes()
        assert len(data)%4==0
        ins=list(instructions(data))
        assert any(op==15 and args[0]==5 for op,args in ins),'Not a compute shader'
        bindings=sorted(args[2] for op,args in ins if op==71 and args[1]==33)
        assert all(args[2]==0 for op,args in ins if op==71 and args[1]==34)
        # Same LSFG 3.1 shader IDs as the 1.0.0 registry, mapped to FP32 slots.
        payload+=struct.pack('<III',rid+98,len(data),fnv(data))+data
        records.append(dict(dll_resource=rid,backend_resource=rid+98,bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),bindings=bindings,
            capabilities=sorted(args[0] for op,args in ins if op==17)))
    target=output/'lsfg-3.1.sdp';target.write_bytes(payload)
    write_json(ROOT/'reports/lsfg-shader-conversion.json',dict(status='CONVERTED',
        source_dll_sha256=DLL_SHA,source_version='3.2.1.0',model='LSFG 3.1 FP32',
        pack_sha256=sha(target),shader_count=len(records),records=records,
        dll_executed=False,hardware_tested=False))
    print('Converted',len(records),'shaders:',target,sha(target))

if __name__=='__main__': main()
