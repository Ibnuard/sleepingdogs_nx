"""Execute shipping x86 DXVK cache, allocation dispatch and retirement code.

SRW locks, diagnostics, fresh Vulkan allocation and final Vulkan destruction
are modeled. Reference-count transitions at the caller boundary are explicit.
"""
from pathlib import Path
import json,struct,sys
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_EDX,UC_X86_REG_ESP,UC_X86_REG_EIP
from check_wow64_context_binary import symbols
from check_dxvk_map_binary import MapReplay
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
M=1048576;L=json.loads((ROOT/'local/recycle-layout.json').read_text())
DLL=ROOT/'dist/buffer-reuse-fix/x32/d3d11.dll'

class Replay:
    def __init__(self):
        self.pe=pefile.PE(str(DLL));self.syms=symbols(self.pe);self.vm=Uc(UC_ARCH_X86,UC_MODE_32)
        base=self.pe.OPTIONAL_HEADER.ImageBase;self.vm.mem_map(base,(self.pe.OPTIONAL_HEADER.SizeOfImage+4095)&-4096)
        self.vm.mem_write(base,self.pe.get_memory_mapped_image());self.vm.mem_map(0x20000000,0x1000000)
        self.vm.mem_map(0x22000000,0x10000);self.vm.mem_map(0x23000000,4096);self.vm.mem_map(0x24000000,16*M)
        self.a=0x20000000;self.heap=0x20010000;self.req=0x20020000;self.info=0x20021000;self.output=0x20022000
        self.types=[self.a+L['types']+i*L['type_size'] for i in range(2)]
        for t in self.types:self.d(t+L['type_heap'],self.heap);self.d(t+L['type_usage'],1)
        self.d(self.heap+L['heap_types'],3)
        for i in range(16):self.d(self.a+L['type_masks']+i*4,3)
        self.deleted=[];self.fresh=0;self.depth=0;self.next=0
        self.lock=self.syms['_AcquireSRWLockExclusive@4'];self.unlock=self.syms['_ReleaseSRWLockExclusive@4']
        self.logger=self.symbol('DxvkMemoryAllocator14logStreamCache')
        self.destructor=self.symbol('DxvkResourceAllocationD2Ev')
        self.allocate=self.symbol('DxvkMemoryAllocator20allocateDeviceMemory')
        self.vm.hook_add(UC_HOOK_CODE,self.hook)
    def symbol(self,fragment):
        hits=[v for n,v in self.syms.items() if fragment in n and n.startswith('__ZN') and '$_' not in n]
        assert len(hits)==1,(fragment,hits);return hits[0]
    def d(self,p,v):self.vm.mem_write(p,struct.pack('<I',v&0xffffffff))
    def q(self,p,v):self.vm.mem_write(p,struct.pack('<Q',v&0xffffffffffffffff))
    def u(self,p):return struct.unpack('<I',self.vm.mem_read(p,4))[0]
    def uq(self,p):return struct.unpack('<Q',self.vm.mem_read(p,8))[0]
    def ret(self,v=0,pop=0):
        sp=self.vm.reg_read(UC_X86_REG_ESP);self.vm.reg_write(UC_X86_REG_EAX,v)
        self.vm.reg_write(UC_X86_REG_EIP,self.u(sp));self.vm.reg_write(UC_X86_REG_ESP,sp+4+pop)
    def hook(self,vm,pc,size,unused):
        if pc==self.lock:self.depth+=1;assert self.depth==1;self.ret(pop=4)
        elif pc==self.unlock:assert self.depth==1;self.depth-=1;self.ret(pop=4)
        elif pc==self.logger:self.ret(pop=12)
        elif pc==self.destructor:
            p=vm.reg_read(UC_X86_REG_ECX);assert p not in self.deleted;self.deleted.append(p);self.ret()
        elif pc==self.allocate:
            # Every fresh Vulkan request fails, just as a fragmented exhausted
            # native heap would. A cache hit must bypass this boundary entirely.
            self.fresh+=1;vm.mem_write(vm.reg_read(UC_X86_REG_ECX),bytes(L['device_memory_size']));self.ret(pop=20)
    def call(self,fragment,*args,sret=False):
        sp=0x2200f000;args=([self.a]+list(args)) if sret else list(args)
        self.vm.mem_write(sp,struct.pack('<'+'I'*(len(args)+1),0x23000000,*args))
        self.vm.reg_write(UC_X86_REG_ESP,sp);self.vm.reg_write(UC_X86_REG_ECX,self.output if sret else self.a)
        self.vm.emu_start(self.symbol(fragment),0x23000000,count=1000000)
        assert self.vm.reg_read(UC_X86_REG_EIP)==0x23000000 and self.vm.reg_read(UC_X86_REG_ESP)==sp+4+4*len(args)
        assert not self.depth
        return self.u(self.output) if sret else self.vm.reg_read(UC_X86_REG_EAX)
    def stats(self,type=0):
        t=self.types[type]+L['type_stats'];return self.uq(t+L['stats_allocated']),self.uq(t+L['stats_used'])
    def create(self,size=5*M,type=0):
        p=0x20030000+self.next*256;self.next+=1;t=self.types[type]
        self.d(p+L['flags'],0x83);self.d(p+L['count'],0)
        self.d(p+L['type'],t);self.d(p+L['allocator'],self.a)
        self.q(p+L['memory'],100+self.next);self.q(p+L['buffer'],200+self.next);self.q(p+L['size'],size)
        self.d(p+L['map'],0x24000000);allocated,used=self.stats(type)
        self.q(t+L['type_stats']+L['stats_allocated'],allocated+size);self.q(t+L['type_stats']+L['stats_used'],used+size)
        return p
    def retire(self,p):
        self.d(p+L['count'],0);self.call('DxvkMemoryAllocator14freeAllocation',p)
    def take(self,size=5*M,types=1,cookie=123,handle=0x7fffffff):
        self.q(self.req+L['req_bytes'],size);self.q(self.req+L['req_alignment'],256);self.d(self.req+L['req_types'],types)
        self.q(self.info+L['info_cookie'],cookie);self.d(self.info+L['info_properties'],3)
        self.d(self.info+L['info_handle'],handle)
        return self.call('DxvkMemoryAllocator14allocateMemory',self.req,self.info,sret=True)

def main():
    m=Replay();p=m.create();m.retire(p);assert m.stats()==(5*M,0)
    assert m.uq(m.a+L['cache_bytes'])==5*M and not m.deleted
    for i in range(256):
        assert m.take(cookie=i+1)==p and m.u(p+L['count'])==1 and m.uq(p+L['cookie'])==i+1
        assert m.stats()==(5*M,5*M);m.retire(p)
    assert not m.fresh and m.uq(m.a+L['hits'])==256
    assert not m.take(6*M) and not m.take(5*M,2) and not m.take(handle=1) and m.stats()==(5*M,0)
    q=m.take();assert q==p
    assert not m.call('DxvkMemoryAllocator21cacheStreamAllocation',q),'Live allocation was cached'
    assert not m.take(),'Live allocation was lent to another command'
    m.retire(q);m.call('DxvkMemoryAllocator22drainStreamAllocations',m.heap)
    assert m.deleted==[p] and m.stats()==(0,0) and not m.uq(m.a+L['cache_bytes'])
    caps=Replay();ptrs=[caps.create(n*M) for n in (4,5,6,7,8,9)]
    for p in ptrs:caps.retire(p)
    assert caps.uq(caps.a+L['cache_bytes'])==15*M and len(caps.deleted)==3
    caps.call('DxvkMemoryAllocator22drainStreamAllocations',caps.heap);assert len(caps.deleted)==6 and caps.stats()==(0,0)
    # Keep the existing Map contract: real failure remains HRESULT, with no
    # invented storage; successful mappings still retain their command refs.
    for size in (65536,5*M,9*M):
        x=MapReplay(DLL);before=x.state();assert x.call(size)==0x8007000e and x.state()==before
        assert bytes(x.vm.mem_read(x.output,12))==bytes(12) and not x.faults
    x=MapReplay(DLL);x.fail=False;assert x.call()==0
    assert x.u(x.output)==x.storage and x.u(x.queue+0x4c)==x.allocation and x.q(x.dxbuf+8)==2
    report={'status':'PASS','dll_sha256':sha(DLL),'actual_x86_reuse_cycles':256,'exact_size_and_type':True,
        'live_allocation_refused':True,'cache_bounds_and_destruction':True,'allocation_accounting':True,
        'map_failure_and_success_ownership':True,'scope':__doc__,'hardware_tested':False,
        'sources':{n:sha(ROOT/n) for n in ('tests/check_recycle_binary.py','tests/recycle_layout.cpp',
        'tests/build_recycle_layout.py','tests/check_dxvk_map_binary.py','tests/check_wow64_context_binary.py','local/recycle-layout.json')}}
    write_json(ROOT/'reports/recycle-binary-check.json',report);print(json.dumps(report))

if __name__=='__main__':main()
