"""Execute the delivered ARM64 PE functions, including fallback, in Unicorn.

No function hooks or substituted conversion code. Instruction counts are not
cycles and the emulator is not a Switch gameplay or whole-FEX execution test.
"""
from pathlib import Path
import hashlib,json,random,struct
import pefile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *

ROOT=Path(__file__).resolve().parents[1];LOCAL=ROOT/'local/sd-fex-context-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def symbols(path):
    pe=pefile.PE(str(path));data=path.read_bytes();table=pe.FILE_HEADER.PointerToSymbolTable
    strings=table+18*pe.FILE_HEADER.NumberOfSymbols;result={};i=0
    while i<pe.FILE_HEADER.NumberOfSymbols:
        record=data[table+i*18:table+(i+1)*18];raw,value,section,kind,storage,aux=struct.unpack('<8sIhHBB',record)
        if raw[:4]==b'\0'*4:
            at=strings+struct.unpack_from('<I',raw,4)[0];end=data.index(0,at);name=data[at:end].decode()
        else:name=raw.rstrip(b'\0').decode()
        if section>0:result[name]=pe.OPTIONAL_HEADER.ImageBase+pe.sections[section-1].VirtualAddress+value
        i+=1+aux
    return pe,result

class Runner:
    def __init__(self,path):
        pe,self.symbols=symbols(path);self.uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        image=pe.get_memory_mapped_image();base=pe.OPTIONAL_HEADER.ImageBase
        self.uc.mem_map(base,(len(image)+4095)&~4095);self.uc.mem_write(base,image)
        self.uc.mem_map(0x30000000,0x4000);self.uc.mem_map(0x31000000,0x1000)
    def call(self,fn,values,top,control,reduced,count=False):
        uc=self.uc;data=b''.join(struct.pack('<QQ',*x) for x in values)
        memory=b'\xa5'*0x1000;uc.mem_write(0x30000000,memory);uc.mem_write(0x30001000,data)
        uc.mem_write(0x30002000,b'\x6b'*0x2000)
        for i in range(29):uc.reg_write(UC_ARM64_REG_X0+i,0xcafee000+i)
        uc.reg_write(UC_ARM64_REG_X29,0xcafee01d)
        for i in range(8,16):uc.reg_write(UC_ARM64_REG_Q0+i,(0x1234<<64)|i)
        for reg,value in [(UC_ARM64_REG_X0,0x30000080),(UC_ARM64_REG_X1,0x30001000),(UC_ARM64_REG_X2,top<<11),
                          (UC_ARM64_REG_X3,control),(UC_ARM64_REG_X4,reduced),(UC_ARM64_REG_SP,0x30003f00),(UC_ARM64_REG_LR,0x31000000)]:uc.reg_write(reg,value)
        if fn=='PES13FexExportX87':uc.reg_write(UC_ARM64_REG_X3,reduced)
        instructions=[0]
        def step(*_):instructions[0]+=1
        hook=uc.hook_add(UC_HOOK_CODE,step) if count else None
        try:uc.emu_start(self.symbols[fn],0x31000000,count=20000)
        finally:
            if hook is not None:uc.hook_del(hook)
        assert uc.reg_read(UC_ARM64_REG_PC)==0x31000000,('did not return',fn)
        out=bytes(uc.mem_read(0x30000000,0x1000))
        assert out[:128]==memory[:128] and out[256:]==memory[256:],('out of bounds write',fn)
        assert bytes(uc.mem_read(0x30001000,len(data)))==data,'input changed'
        assert uc.reg_read(UC_ARM64_REG_SP)==0x30003f00
        assert uc.reg_read(UC_ARM64_REG_X18)==0xcafee012,'Wine TEB x18 clobbered'
        for i in range(19,29):assert uc.reg_read(UC_ARM64_REG_X0+i)==0xcafee000+i,('callee register',i)
        assert uc.reg_read(UC_ARM64_REG_X29)==0xcafee01d
        for i in range(8,16):assert uc.reg_read(UC_ARM64_REG_Q0+i)&((1<<64)-1)==i,('SIMD preserved low half',i)
        return out[128:256],instructions[0]

def expand(bits):
    sign=(bits>>48)&0x8000;exp=(bits>>52)&2047;frac=bits&((1<<52)-1)
    if exp==2047:return ((1<<63)|(frac<<11),sign|32767)
    if exp:return ((1<<63)|(frac<<11),sign|(exp+15360))
    if not frac:return (0,sign)
    shift=64-frac.bit_length();return (frac<<shift,sign|(15372-shift))

def main():
    build=json.loads((LOCAL/'build.json').read_text());a=LOCAL/'baseline-libwow64fex.dll';b=LOCAL/'libwow64fex.dll'
    assert sha(a)==build['baseline_sha256'] and sha(b)==build['dll_sha256']
    old,new=Runner(a),Runner(b);rand=random.Random(77144);checks=0
    edges=[0,1,0xfffffffffffff,0x10000000000000,0x7fefffffffffffff,0x7ff0000000000000,0x7ff0000000000001,0x8000000000000000]
    rows=[[expand(x) for x in edges],[expand(rand.getrandbits(64)) for _ in range(8)]]
    for i in range(120):
        rows.append([expand(rand.getrandbits(64)) if i&1 else (rand.getrandbits(64),rand.getrandbits(64)) for _ in range(8)])
    for values in rows:
        for top in range(8):
            for reduced in range(2):
                for mode in range(4):
                    control=0x37f|(mode<<10)
                    for fn in ('PES13FexImportX87','PES13FexExportX87'):
                        x,_=old.call(fn,values,top,control,reduced);y,_=new.call(fn,values,top,control,reduced)
                        assert x==y,(fn,values,top,control,reduced);checks+=1
    counts={}
    for name,values in [('normal',[expand(0x3ff8000000000000+i*(1<<48)) for i in range(8)]),
        ('zero',[expand((i&1)<<63) for i in range(8)]),('special',[expand(x) for x in edges]),
        ('general80',[(0x8000000000000400+i,0x3fff) for i in range(8)])]:
        # Fresh engines ensure previously cached translation blocks cannot
        # bypass a newly installed instruction hook in Unicorn.
        counts[name]={label:Runner(path).call('PES13FexImportX87',values,3,0x37f,1,True)[1] for label,path in [('old',a),('new',b)]}
        assert all(n>0 for n in counts[name].values())
    report=dict(status='PASS',differential_calls=checks,actual_pe_functions=True,substituted_functions=False,callee_saved_and_x18_verified=True,
        source_sha256=sha(__file__),build_receipt_sha256=sha(LOCAL/'build.json'),baseline_sha256=sha(a),dll_sha256=sha(b),
        representative_import_instruction_counts=counts,hardware_tested=False,game_fps_measured=False,
        scope='Unicorn executes the ARM64 PE import/export routines from both DLLs. Register/stack/byte canaries; no Wine callback, suspend or gameplay emulation. Instruction counts are not hardware time.')
    (LOCAL/'arm64-test.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
