"""Run the compiled ARM64 preflight and native VA allocator with modeled SVCs.

The tiny code mapped to 0x400000 actually executes in Unicorn. This is not a
Horizon hardware test; kernel behavior, TLS, heap boundaries and SVC failures
are explicit fixtures, while the shipped ELF supplies all checked control flow.
"""
from pathlib import Path
import argparse,io,json,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_PROT_ALL,UC_PROT_NONE
from unicorn import arm64_const as arm
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
REG=[getattr(arm,f'UC_ARM64_REG_X{i}') for i in range(31)]
ELF=ROOT/'local/symbols/sleepingdogs-low-window.elf'

class Machine:
    def __init__(self,mode='good',elf_path=ELF):
        self.vm=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.mode=mode
        elf=ELFFile(io.BytesIO(elf_path.read_bytes()));self.bias=0x400000000
        self.symbols={s.name:self.bias+s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
        segments=[s for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
        low=min(s['p_vaddr'] for s in segments)&-4096
        high=max((s['p_vaddr']+s['p_memsz']+4095)&-4096 for s in segments)
        self.vm.mem_map(self.bias+low,high-low)
        for s in segments:self.vm.mem_write(self.bias+s['p_vaddr'],s.data())
        relr=elf.get_section_by_name('.relr.dyn')
        if relr:
            for r in relr.iter_relocations():
                at=self.bias+r['r_offset'];self.q(at,self.uq(at)+self.bias)
        self.stack=0x600000000;self.tls=0x610000000;self.stop=0x620000000;self.back=0x1200000000
        for p in (self.stack,self.tls,self.stop,self.back):self.vm.mem_map(p,65536)
        self.vm.reg_write(arm.UC_ARM64_REG_TPIDRRO_EL0,self.tls if mode!='low_tls' else 0x20000)
        self.depth=0;self.returned=False;self.freed=0;self.mapping=None;self.maps=0;self.executed=0
        self.alias_state=None;self.perm=0;self.logs=[];self.data_perms=[]
        names=('svcGetInfo','svcQueryMemory','envGetOwnProcessHandle','memalign','free','svcMapProcessCodeMemory',
            'svcSetProcessMemoryPermission','svcSetMemoryPermission','svcUnmapProcessCodeMemory',
            'mutexLock','mutexUnlock','mutexIsLockedByCurrentThread','__libnx_virtmem_rng',
            'armDCacheFlush','armICacheInvalidate','snprintf','wine_nx_runtime_trace','diagAbortWithResult')
        self.hooks={self.symbols[n]:n for n in names if n in self.symbols}
        self.code_hook=self.vm.hook_add(UC_HOOK_CODE,self.hook)
    def close(self):
        self.vm.hook_del(self.code_hook);self.vm=None
    def q(self,p,v):self.vm.mem_write(p,struct.pack('<Q',v))
    def uq(self,p):return struct.unpack('<Q',self.vm.mem_read(p,8))[0]
    def x(self,i):return self.vm.reg_read(REG[i])
    def ret(self,v=0):
        self.vm.reg_write(REG[0],v&((1<<64)-1));self.vm.reg_write(arm.UC_ARM64_REG_PC,self.x(30))
    def text(self,p):return bytes(self.vm.mem_read(p,224)).split(b'\0')[0].decode(errors='replace')
    def info(self,id):
        values={2:0x2000000000,3:0x1000000000,4:0x3000000000,5:0x200000000,
            6:3285*1024*1024,12:0x200000,13:0x8000000000-0x200000,
            14:0x1800000000,15:0x80000000,18:0x059a3db219b42000,28:0}
        if self.mode=='stock39':values.update({12:0x8000000,13:0x8000000000-0x8000000})
        if self.mode=='old32':values.update({12:0x200000,13:0x100000000-0x200000})
        if self.mode=='quota2g':values[6]=0x80000000
        if self.mode=='wrong_title':values[18]=0x0548eabb35576000
        if self.mode=='low_heap':values[4]=0x80000000
        return values.get(id,0)
    def hook(self,vm,pc,size,_):
        n=self.hooks.get(pc);x=self.x
        if pc==self.stop:self.returned=True;vm.emu_stop();return
        if pc==0x400000:self.executed+=1
        if n=='svcGetInfo':
            if self.mode=='query_fail':self.ret(1)
            else:self.q(x(0),self.info(x(1)));self.ret()
        elif n=='svcQueryMemory':
            at=x(2);kind=0;perm=0;base=at;length=0x8000000000-at
            if at<0x100000000:
                length=0x100000000-at
                if self.mode=='occupied':kind=9;length=4096
            if self.mapping and at==self.mapping:kind=8 if self.alias_state=='code' else 9;perm=self.perm;length=4096
            vm.mem_write(x(0),struct.pack('<QQIIIIII',base,length,kind,0,perm,0,0,0));vm.mem_write(x(1),bytes(4));self.ret()
        elif n=='envGetOwnProcessHandle':self.ret(0 if self.mode=='no_handle' else 42)
        elif n=='memalign':self.ret(0 if self.mode=='no_backing' else self.back)
        elif n=='free':assert not self.mapping;self.freed+=bool(x(0));self.ret()
        elif n=='svcMapProcessCodeMemory':
            assert x(0)==42 and x(2)==self.back and x(3)==4096 and self.depth==1
            if self.mode=='map_fail':self.ret(2);return
            self.mapping=x(1);self.maps+=1;self.alias_state='code';self.perm=0
            vm.mem_map(self.mapping,4096);vm.mem_write(self.mapping,bytes(vm.mem_read(self.back,4096)))
            vm.mem_protect(self.back,4096,UC_PROT_NONE);self.ret()
        elif n=='svcSetProcessMemoryPermission':
            assert self.alias_state=='code'
            if self.mode=='process_perm_fail':self.ret(3);return
            self.perm=x(3);self.alias_state='data' if self.perm==3 else 'code'
            vm.mem_protect(self.mapping,4096,self.perm);self.ret()
        elif n=='svcSetMemoryPermission':
            assert self.alias_state=='data';self.data_perms.append(x(2))
            if self.mode=='data_perm_fail':self.ret(4);return
            self.perm=x(2);vm.mem_protect(self.mapping,4096,self.perm);self.ret()
        elif n=='svcUnmapProcessCodeMemory':
            if self.mode=='unmap_fail':self.ret(5);return
            vm.mem_protect(self.back,4096,UC_PROT_ALL)
            vm.mem_write(self.back,bytes(vm.mem_read(self.mapping,4096)))
            vm.mem_unmap(self.mapping,4096);self.mapping=None;self.ret()
        elif n=='mutexLock':self.depth+=1;assert self.depth==1;self.ret()
        elif n=='mutexUnlock':assert self.depth==1;self.depth-=1;self.ret()
        elif n=='mutexIsLockedByCurrentThread':self.ret(self.depth==1)
        elif n=='__libnx_virtmem_rng':self.ret(0)
        elif n in ('armDCacheFlush','armICacheInvalidate'):self.ret()
        elif n=='snprintf':vm.mem_write(x(0),b'probe\0');self.ret(5)
        elif n=='wine_nx_runtime_trace':assert not self.depth;self.logs.append(self.text(x(0)));self.ret()
        elif n=='diagAbortWithResult':raise AssertionError(('unexpected abort',x(0)))
    def call(self,name,*args):
        self.returned=False;self.vm.reg_write(arm.UC_ARM64_REG_SP,self.stack+0xf000)
        self.vm.reg_write(REG[30],self.stop)
        for i,v in enumerate(args):self.vm.reg_write(REG[i],v)
        self.vm.emu_start(self.symbols[name],0,count=2000000)
        assert self.returned,(name,hex(self.vm.reg_read(arm.UC_ARM64_REG_PC)))
        return self.x(0)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf',type=Path,default=ELF)
    p.add_argument('--report',type=Path,default=ROOT/'reports/low-window-binary.json')
    args=p.parse_args()
    cases=[]
    for mode in ('good','stock39','old32','quota2g','wrong_title','low_heap','low_tls','query_fail','no_handle',
                 'occupied','no_backing','map_fail','process_perm_fail','data_perm_fail','unmap_fail'):
        m=Machine(mode,args.elf);m.call('sd_low_window_init');ok=m.call('sd_low_window_ready')
        assert bool(ok)==(mode=='good'),(mode,ok)
        if mode=='good':assert m.executed==1 and m.maps==2 and m.freed==2 and m.data_perms==[0,3] and not m.mapping
        if mode=='unmap_fail':assert m.mapping and m.freed==0
        if mode in ('stock39','old32','quota2g','wrong_title','low_heap','low_tls','query_fail','no_handle','occupied'):
            assert m.maps==0,mode
        maps=m.maps;m.call('sd_low_window_init');assert m.maps==maps
        assert m.depth==0
        cases.append(mode)
        m.close()
    print('PASS 15 ARM64 preflight/failure cases',flush=True)
    m=Machine(elf_path=args.elf);m.call('virtmemSetup')
    assert m.uq(m.symbols['g_AslrRegion'])==0x100000000
    m.call('virtmemLock')
    for name in ('virtmemFindAslr','virtmemFindCodeMemory','virtmemFindStack'):
        p=m.call(name,4096,4096);assert p>=0x100000000,name
    # RNG zero always misses the guard: this exercises the real exhaustive
    # fallback as well as random allocation, with the high native floor.
    m.call('virtmemUnlock');assert m.depth==0;m.close()
    for mode in ('stock39','old32'):
        m=Machine(mode,args.elf);m.call('virtmemSetup');assert m.uq(m.symbols['g_AslrRegion'])==m.info(12)
        m.close()
    report={'status':'PASS','elf_sha256':sha(args.elf),'hardware_tested':False,'scope':__doc__,
        'preflight_cases':cases,'rx_instructions_executed':True,'native_va_floor_and_fallback':True,
        'sources':{'tests/check_low_window_binary.py':sha(Path(__file__))}}
    write_json(args.report,report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
