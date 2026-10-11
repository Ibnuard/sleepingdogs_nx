"""Check the user's PE32 game's static graphics imports against the built proxies.

This does not execute the game or prove dynamically requested COM coverage.
Only hashes and import names are recorded; no game bytes are distributed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-h4-v7'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class PE32:
    def __init__(self,path):
        self.path=Path(path);self.data=self.path.read_bytes()
        if self.data[:2]!=b'MZ':raise ValueError('Missing DOS header')
        pe=self.u32(0x3c)
        if self.data[pe:pe+4]!=b'PE\0\0' or self.u16(pe+4)!=0x14c or self.u16(pe+24)!=0x10b:
            raise ValueError('Requires i386 PE32')
        optional=pe+24;self.image_base=self.u32(optional+28)
        self.header_bytes=self.u32(optional+60)
        count=min(self.u32(optional+92),16);self.directories=[]
        for i in range(count):self.directories.append(struct.unpack_from('<II',self.data,optional+96+i*8))
        section_start=optional+self.u16(pe+20);self.sections=[]
        for i in range(self.u16(pe+6)):
            start=section_start+i*40
            size,rva,raw_size,raw=struct.unpack_from('<IIII',self.data,start+8)
            self.sections.append((rva,size,raw,raw_size))
    def u16(self,offset):return struct.unpack_from('<H',self.data,offset)[0]
    def u32(self,offset):return struct.unpack_from('<I',self.data,offset)[0]
    def offset(self,rva,length=1):
        if rva<self.header_bytes and rva+length<=min(self.header_bytes,len(self.data)):return rva
        for base,_,raw,raw_size in self.sections:
            relative=rva-base
            if relative>=0 and relative+length<=raw_size and raw+relative+length<=len(self.data):return raw+relative
        raise ValueError(f'Unbacked RVA {rva:x} in {self.path.name}')
    def string(self,rva):
        start=self.offset(rva);end=self.data.find(b'\0',start,min(start+4096,len(self.data)))
        if end<0:raise ValueError('Unterminated PE name')
        return self.data[start:end].decode('ascii')
    def directory(self,n):return self.directories[n] if n<len(self.directories) else (0,0)
    def imports(self):
        result=[]
        for mode,index,stride in [('normal',1,20),('delay',13,32)]:
            rva,size=self.directory(index)
            if not rva:continue
            for i in range(4096):
                if i*stride+stride>size:raise ValueError('No import descriptor terminator')
                raw=self.offset(rva+i*stride,stride)
                desc=struct.unpack_from('<'+'I'*(stride//4),self.data,raw)
                if not any(desc):break
                if mode=='normal':lookup,_,_,name,iat=desc;lookup=lookup or iat
                else:
                    attrs,name,_,iat,lookup,_,_,_=desc
                    if not attrs&1:
                        name-=self.image_base;lookup-=self.image_base
                dll=self.string(name);functions=[]
                for j in range(65536):
                    value=self.u32(self.offset(lookup+j*4,4))
                    if not value:break
                    if value&0x80000000:functions.append({'ordinal':value&0xffff})
                    else:functions.append({'name':self.string(value+2)})
                else:raise ValueError('No thunk terminator')
                result.append(dict(dll=dll,kind=mode,functions=functions))
            else:raise ValueError('Import table exceeds limit')
        return result
    def exports(self):
        rva,size=self.directory(0)
        if not rva:return {},set()
        raw=self.offset(rva,40);base,count,names,functions,names_rva,ordinals=struct.unpack_from('<IIIIII',self.data,raw+16)
        valid={base+i for i in range(count) if self.u32(self.offset(functions+i*4,4))}
        named={}
        for i in range(names):
            name=self.string(self.u32(self.offset(names_rva+i*4,4)))
            ordinal=base+self.u16(self.offset(ordinals+i*2,2))
            named[name]=ordinal
        return named,valid

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,default=ROOT.parent/'Sleeping Dogs/HKShip.exe')
    args=parser.parse_args();game=PE32(args.game);imports=game.imports();graphics=[];missing=[]
    for detail in imports:
        dll=detail['dll'].lower()
        if dll not in ('d3d11.dll','dxgi.dll'):continue
        path=LOCAL/dll;exports,ordinals=PE32(path).exports()
        for function in detail['functions']:
            if ('name' in function and function['name'] not in exports) or ('ordinal' in function and function['ordinal'] not in ordinals):
                missing.append(dict(dll=dll,**function))
        graphics.append(dict(**detail,proxy_sha256=sha(path),proxy_exports=exports))
    receipt=dict(status='PASS' if graphics and not missing else 'FAIL',game_name=args.game.name,game_sha256=sha(args.game),
                 game_bytes=len(game.data),game_machine='i386',graphics_imports=graphics,missing_graphics_exports=missing,
                 imported_dlls=[dict(dll=x['dll'],kind=x['kind'],functions=len(x['functions'])) for x in imports],
                 static_imports_only=True,dynamic_com_coverage_proven=False,game_data_included=False,
                 runner_sha256=sha(__file__),hardware_tested=False,game_integration_tested=False,game_fps_measured=False)
    LOCAL.mkdir(parents=True,exist_ok=True);(LOCAL/'game-imports.json').write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
    print(json.dumps(receipt,indent=2));raise SystemExit(0 if receipt['status']=='PASS' else 1)

if __name__=='__main__':main()
