"""Exercise the unchanged FEX DLL's real DEP interval logic in ARM64 Unicorn."""
from pathlib import Path
import struct
import sys
import pefile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *
from check_wow64_context_binary import symbols
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json


def main():
    path=ROOT/'vendor/fex/libwow64fex-sd-debug.dll'
    assert sha(path)=='583ac0d48fd5c2e3e92f8844a23f85873064cc2b1f03a2e6b6a96d224d7de130'
    p=pefile.PE(str(path)); syms=symbols(p); base=p.OPTIONAL_HEADER.ImageBase
    uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM); uc.mem_map(base,(p.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
    uc.mem_write(base,p.get_memory_mapped_image())
    data,stub=0x20000000,0x21000000
    uc.mem_map(data,0x100000); uc.mem_map(stub,0x10000)
    obj,ctx,vt,lock,threads,out=(data+n for n in (0x1000,0x2000,0x3000,0x4000,0x5000,0x6000))
    def qwrite(a,*v): uc.mem_write(a,struct.pack('<'+'Q'*len(v),*v))
    # Offsets from the pinned DLL's compiled instructions; vectors have spare
    # capacity, keeping allocation outside the execute-policy algorithm.
    for off,buffer in ((0,data+0x10000),(0x18,data+0x20000),(0x68,data+0x30000)):
        qwrite(obj+off,buffer,buffer,buffer+0x1000)
    # One pre-existing executable image interval must survive policy toggles.
    qwrite(data+0x10000,0x400000,0x410000); qwrite(obj+8,data+0x10010)
    qwrite(obj+0x50,ctx,threads); qwrite(ctx,vt)
    hooks={stub:'mutex',stub+16:'invalidate',stub+32:'virtualquery'}
    hooks[syms['VirtualQuery']]='virtualquery'
    qwrite(vt+0xf8,stub); qwrite(vt+0xe8,stub+16)
    for name in ('PES13FexJitBegin','PES13FexJitEnd'):
        hooks[syms[name]]='noop'
    for name,address in syms.items():
        if name.startswith('_ZNSt3__119__shared_mutex_base') and any(t in name for t in ('4lockEv','6unlockEv','11lock_sharedEv','13unlock_sharedEv')):
            hooks[address]='noop'
    for dep in p.DIRECTORY_ENTRY_IMPORT:
        for imp in dep.imports:
            if imp.name==b'VirtualQuery': qwrite(imp.address,stub+32)
            elif imp.name in (b'memmove',b'memcpy',b'memset'):
                ptr=stub+0x100+16*len(hooks); qwrite(imp.address,ptr); hooks[ptr]=imp.name.decode()
    # Returned regions include the logged fault page, a read-only page,
    # no-access and reserved pages, plus the pre-existing RX image.
    regions=[(0,0x3a0000,0x10000,1),(0x3a0000,0x10000,0x1000,4),
        (0x3b0000,0x10000,0x1000,2),(0x3c0000,0x10000,0x1000,1),
        (0x3d0000,0x30000,0x2000,4),(0x400000,0x10000,0x1000,0x20)]
    invalidations=[]
    def hook(u,address,size,unused):
        action=hooks.get(address)
        if not action:return
        x=[u.reg_read(r) for r in (UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2)]
        result=0
        if action=='mutex': result=lock
        elif action=='invalidate': invalidations.append((x[1],x[2]))
        elif action=='virtualquery':
            r=next((r for r in regions if r[0]<=x[0]<r[0]+r[1]),None)
            if r:
                a,n,state,prot=r
                u.mem_write(x[1],struct.pack('<QQIIQIIII',a,a,prot,0,n,state,prot,0x20000,0));result=48
        elif action in ('memmove','memcpy','memset'):
            assert x[2]<0x10000
            u.mem_write(x[0],bytes([x[1]&255])*x[2] if action=='memset' else bytes(u.mem_read(x[1],x[2])))
            result=x[0]
        u.reg_write(UC_ARM64_REG_X0,result); u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
    uc.hook_add(UC_HOOK_CODE,hook)
    def call(name,arg):
        uc.reg_write(UC_ARM64_REG_X0,obj);uc.reg_write(UC_ARM64_REG_X1,arg)
        uc.reg_write(UC_ARM64_REG_X8,out);uc.reg_write(UC_ARM64_REG_LR,stub+0xf000)
        uc.reg_write(UC_ARM64_REG_SP,data+0xff000)
        try: uc.emu_start(syms[name],stub+0xf000,count=100000)
        except Exception:
            pc=uc.reg_read(UC_ARM64_REG_PC);print('PC',hex(pc),'LR',hex(uc.reg_read(UC_ARM64_REG_LR)),max(((v,k) for k,v in syms.items() if v<=pc),default=(0,'?')));raise
        assert uc.reg_read(UC_ARM64_REG_PC)==stub+0xf000
    notify='_ZN3FEX7Windows19InvalidationTracker31HandleProcessExecuteFlagsChangeEm'
    query='_ZN3FEX7Windows19InvalidationTracker20QueryExecutableRangeEy'
    def executable(a):
        uc.mem_write(out,b'\0'*24);call(query,a)
        return struct.unpack('<QQB',uc.mem_read(out,17))
    assert executable(0x3a4f78)==(0,0,0)
    call(notify,2)
    assert executable(0x3a4f78)==(0x3a0000,0x10000,1)
    assert executable(0x3b0000)==(0x3b0000,0x10000,0)
    assert executable(0x3c0000)==(0,0,0) and executable(0x3d0000)==(0,0,0)
    assert executable(0x400000)==(0x400000,0x10000,0)
    assert len(invalidations)==1
    call(notify,2); assert len(invalidations)==1
    call(notify,9)
    assert executable(0x3a4f78)==(0,0,0) and executable(0x3b0000)==(0,0,0)
    assert executable(0x400000)==(0x400000,0x10000,0)
    assert len(invalidations)==2
    write_json(ROOT/'reports/fex-dep-binary-check.json',{'status':'PASS','dll_sha256':sha(path),
        'scope':'Actual FEX ARM64 DEP interval code; virtual-memory/lock/invalidation endpoints mocked',
        'before_heap_executable':False,'after_disabled_heap_executable':True,'smc_tracking_retained':True,
        'readonly_promoted':True,'noaccess_and_reserved_excluded':True,'reenable_revokes_heap':True,
        'rx_image_preserved':True,'policy_change_invalidates_code':True,'same_policy_no_extra_invalidation':True,
        'hardware_tested':False,'sources':{'tests/check_fex_dep_binary.py':sha(Path(__file__))}})
    print('PASS actual FEX ARM64 DEP intervals: heap denied -> executable with SMC -> denied; RX preserved')
if __name__=='__main__':main()
