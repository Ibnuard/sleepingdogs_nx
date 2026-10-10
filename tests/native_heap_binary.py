"""Execute real newlib malloc/free/memalign and F1 fallback ARM64 instructions.

Only the bounded sbrk provider, recursive lock and diagnostic I/O are modeled.
No free list or allocator result is manufactured. NvMap is not hardware-tested.
"""
from pathlib import Path
import argparse, hashlib, io, json, random, struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm64_const as arm

def reg(i):return getattr(arm, f'UC_ARM64_REG_X{i}')

class Heap:
    plans={}
    def __init__(self, data, start=0x80000000, capacity=8*1024*1024):
        self.vm=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        if id(data) not in self.plans:
            elf=ELFFile(io.BytesIO(data))
            bias=0x1000000 if elf.header['e_type']=='ET_DYN' else 0
            symbols={s.name:bias+s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
            segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
            relr=elf.get_section_by_name('.relr.dyn')
            rels=[r['r_offset'] for r in relr.iter_relocations()] if relr else []
            self.plans[id(data)]=(data,bias,symbols,segments,rels)
        _,bias,self.symbols,segments,rels=self.plans[id(data)]
        low=min(va for va,_,_ in segments)&-4096
        high=max((va+n+4095)&-4096 for va,n,_ in segments)
        self.vm.mem_map(bias+low,high-low)
        for va,_,contents in segments:self.vm.mem_write(bias+va,contents)
        for offset in rels:
            p=bias+offset;self.q(p,self.uq(p)+bias)
        self.data=0x50000000;self.stack=0x51000000;self.stop=0x52000000
        for a in (self.data,self.stack,self.stop):self.vm.mem_map(a,0x10000)
        self.vm.mem_map(0x80000000,32*1024*1024)
        self.start=start;self.brk=start;self.cap=start+capacity
        self.depth=0;self.arena_depth=0;self.peak_depth=0;self.returned=False;self.growth=[]
        self.hooks={self.symbols[n]:n for n in ('__getreent','__malloc_lock','__malloc_unlock',
             '_sbrk_r','snprintf','wine_nx_runtime_trace','__errno','__errno_location','memcpy','memmove','memset','mutexLock','mutexUnlock')
             if n in self.symbols}
        self.code_hook=self.vm.hook_add(UC_HOOK_CODE,self.hook)
    def close(self):self.vm.hook_del(self.code_hook)
    def q(self,p,v):self.vm.mem_write(p,struct.pack('<Q',v&0xffffffffffffffff))
    def uq(self,p):return struct.unpack('<Q',self.vm.mem_read(p,8))[0]
    def ret(self,v=0):
        self.vm.reg_write(reg(0),v&0xffffffffffffffff)
        self.vm.reg_write(arm.UC_ARM64_REG_PC,self.vm.reg_read(reg(30)))
    def hook(self,vm,pc,n,user):
        name=self.hooks.get(pc);x=lambda i:vm.reg_read(reg(i))
        if pc==self.stop:self.returned=True;vm.emu_stop()
        elif name=='__getreent':self.ret(self.data)
        elif name in ('__errno','__errno_location'):self.ret(self.data)
        elif name=='__malloc_lock':
            self.depth+=1;self.peak_depth=max(self.peak_depth,self.depth);self.ret()
        elif name=='__malloc_unlock':
            assert self.depth>0;self.depth-=1;self.ret()
        elif name=='mutexLock':
            self.arena_depth+=1;assert self.arena_depth==1;self.ret()
        elif name=='mutexUnlock':
            assert self.arena_depth==1;self.arena_depth-=1;self.ret()
        elif name=='_sbrk_r':
            n=x(1);n=n if n<2**63 else n-2**64
            self.growth.append(n)
            if self.brk+n>self.cap or self.brk+n<self.start:
                vm.mem_write(x(0),struct.pack('<I',12));self.ret(-1)
            else:old=self.brk;self.brk+=n;self.ret(old)
        elif name in ('memcpy','memmove'):
            vm.mem_write(x(0),bytes(vm.mem_read(x(1),x(2))));self.ret(x(0))
        elif name=='memset':vm.mem_write(x(0),bytes([x(1)&255])*x(2));self.ret(x(0))
        elif name in ('snprintf','wine_nx_runtime_trace'):
            assert self.depth==self.arena_depth==0,'Diagnostics while holding allocator lock';self.ret()
    def call(self,name,*args):
        self.returned=False
        self.vm.reg_write(arm.UC_ARM64_REG_SP,self.stack+0xf000)
        self.vm.reg_write(reg(30),self.stop)
        for i,v in enumerate(args):self.vm.reg_write(reg(i),v&0xffffffffffffffff)
        self.vm.emu_start(self.symbols[name],0,count=5000000)
        assert self.returned and self.depth==self.arena_depth==0,(name,self.depth,self.arena_depth)
        return self.vm.reg_read(reg(0))
    def malloc(self,n):return self.call('_malloc_r',self.data,n)
    def free(self,p):self.call('_free_r',self.data,p)
    def align(self,a,n,new=False):
        return self.call('wine_nx_f1_gpu_memalign',a,n) if new else self.call('_memalign_r',self.data,a,n)
    def info(self):
        self.vm.reg_write(reg(8),self.data+0x2000)
        self.call('_mallinfo_r',self.data)
        return struct.unpack('<10Q',self.vm.mem_read(self.data+0x2000,80))
    def seal(self):
        self.cap=self.brk
        top=self.uq(self.symbols['__malloc_av_']+16);n=self.uq(top+8)&-4
        # Leave the required 32-byte top, and occupy all other tail space.
        return self.malloc(n-32-8) if n>=64 else 0
    def stats(self):return struct.unpack('<8Q',self.vm.mem_read(self.symbols['f1_gpu_heap_stats'],64))

def matrix(data):
    results=[]
    for alignment in (4096,65536,2*1024*1024):
        for size in (65536,65537,393216,1398144):
            for prefix in (0,32,4096,alignment-16):
                if prefix>=alignment:continue
                for tail in (0,16,32,112):
                    # The first returned malloc address has this residue.
                    start=0x80000000+((-prefix-16)%alignment)
                    m=Heap(data,start,16*1024*1024)
                    donor=m.malloc(prefix+size+tail)
                    assert donor and (donor+prefix)%alignment==0
                    guard=m.malloc(1024);assert guard
                    m.vm.mem_write(guard,b'LIVE'*256);end=m.seal()
                    m.free(donor);before=m.info();old=m.align(alignment,size)
                    # Larger trailing pieces may already satisfy newlib's
                    # worst-case request. Only count actual rejected fits.
                    if old:m.free(old);m.close();continue
                    ptr=m.align(alignment,size,True)
                    assert ptr and ptr%alignment==0,(alignment,size,prefix,tail,m.info(),m.stats())
                    assert donor<=ptr and ptr+size<=donor+prefix+size+tail+8
                    m.vm.mem_write(ptr,b'G'*size)
                    assert bytes(m.vm.mem_read(guard,1024))==b'LIVE'*256
                    m.free(ptr)
                    assert before==m.info(),('free/coalescing/accounting',before,m.info())
                    assert m.peak_depth>=1 and m.stats()[1]==1
                    results.append({'alignment':alignment,'size':size,'prefix':prefix,'tail':tail})
                    m.close()
    return results

def churn(data):
    m=Heap(data,capacity=4*1024*1024);rng=random.Random(2013);live=[]
    baseline=m.info()
    for i in range(3500):
        if live and rng.randrange(3)==0:
            j=rng.randrange(len(live));p,n,tag=live.pop(j)
            assert bytes(m.vm.mem_read(p,min(n,64)))==tag*min(n,64)
            m.free(p)
        else:
            n=rng.choice([32,80,224,4096,61440,65536,65537,131072])
            a=rng.choice([16,4096,65536]);p=m.align(a,n,True)
            if p:
                assert not p%a
                assert all(p+n<=q or q+z<=p for q,z,_ in live)
                tag=bytes([i%251]);m.vm.mem_write(p,tag*min(n,64));live.append((p,n,tag))
        if i%100==0:
            for p,n,tag in live:assert bytes(m.vm.mem_read(p,min(n,64)))==tag*min(n,64)
    for p,n,tag in live:
        assert bytes(m.vm.mem_read(p,min(n,64)))==tag*min(n,64);m.free(p)
    # Trim may contract sbrk. All arena bytes should be free again.
    info=m.info();assert info[7]==0,(baseline,info)
    assert m.stats()[1]>0,m.stats()
    report={'iterations':3500,'stats':m.stats(),'final_mallinfo':info};m.close();return report

def edge_cases(data):
    m=Heap(data)
    for a,n in ((0,1),(24,123),(4096,2**64-1),(2**63,2**63)):
        assert not m.align(a,n,True)
    p=m.align(65536,65536,True);assert p and not m.stats()[0]
    m.vm.mem_write(p,b'KEEP');m.cap=m.brk
    assert not m.align(65536,32*1024*1024,True)
    assert bytes(m.vm.mem_read(p,4))==b'KEEP';m.free(p)
    m.close();return True

def top_and_realloc(data):
    m=Heap(data,start=0x8000fff0)
    m.q(m.symbols['__malloc_trim_threshold'],2**63)
    p=m.malloc(65536);m.free(p);m.cap=m.brk
    before=m.info();assert not m.align(65536,65536)
    p=m.align(65536,65536,True);assert p and p%65536==0
    m.vm.mem_write(p,b'CONTENT'*100)
    q=m.call('_realloc_r',m.data,p,4096);assert q
    assert bytes(m.vm.mem_read(q,700))==b'CONTENT'*100
    m.free(q);assert before==m.info()
    p=m.call('_calloc_r',m.data,17,1024);assert p
    assert bytes(m.vm.mem_read(p,17408))==bytes(17408)
    m.free(p);assert before==m.info()
    m.close();return True

def main():
    p=argparse.ArgumentParser();p.add_argument('elf',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();data=a.elf.read_bytes()
    cases=matrix(data);print('PASS: real ARM64 newlib rejected fitting chunks; F1 recovered and coalesced',len(cases),flush=True)
    mixed=churn(data);print('PASS: mixed newlib/GPU allocation churn and live data integrity',flush=True)
    edge_cases(data);top_and_realloc(data)
    print('PASS: wilderness/top recovery, realloc/calloc compatibility, overflow, invalid alignment and true exhaustion',flush=True)
    report={'passed':True,'hardware_tested':False,'elf_sha256':hashlib.sha256(data).hexdigest(),
            'regressions':cases,'churn':mixed,'kernel_model':'bounded sbrk; NvMap hardware unavailable'}
    a.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
