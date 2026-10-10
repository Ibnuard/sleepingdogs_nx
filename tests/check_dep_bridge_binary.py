"""Replay actual shipped ARM64 WoW64 thunks; mock only external NT/CPU APIs."""
from pathlib import Path
import struct
import sys
import pefile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *
from check_wow64_context_binary import symbols, run as context_run
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha, write_json


def run(pe, *, initial=False, handle=0xffffffff, flags=2, length=4, info_null=False,
        set_error=0, query_error=0, identity_error=0, backend=True, policy=1, info_class=34):
    syms=symbols(pe); uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM); base=pe.OPTIONAL_HEADER.ImageBase
    uc.mem_map(base,(pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
    uc.mem_write(base,pe.get_memory_mapped_image())
    heap,stubs=0x20000000,0x21000000; stop=stubs+0xf000
    uc.mem_map(heap,0x20000); uc.mem_map(stubs,0x10000)
    args,info,teb=heap+0x1000,heap+0x2000,heap+0x3000
    uc.mem_write(args,struct.pack('<IIII',handle,info_class,0 if info_null else info,length))
    uc.mem_write(info,struct.pack('<I',flags)); uc.mem_write(teb+0x40,struct.pack('<QQ',100,4))
    state={'policy':policy,'backend_flags':1,'notified':[],'events':[],'locks':0}
    hooks={}
    names=('NtSetInformationProcess','NtQueryInformationProcess','RtlAcquireSRWLockExclusive',
           'RtlReleaseSRWLockExclusive','notify','__wine_dbg_header')
    for i,name in enumerate(names):
        address=stubs+i*0x100; hooks[address]=name
        uc.mem_write(address,bytes.fromhex('c0035fd6'))
        if '__imp_'+name in syms: uc.mem_write(syms['__imp_'+name],struct.pack('<Q',address))
    if 'pBTCpuNotifyProcessExecuteFlagsChange' in syms:
        uc.mem_write(syms['pBTCpuNotifyProcessExecuteFlagsChange'],struct.pack('<Q',stubs+4*0x100 if backend else 0))
    def hook(u,address,size,unused):
        name=hooks.get(address)
        if not name: return
        x=[u.reg_read(r) for r in (UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3)]
        status=0
        if name=='NtSetInformationProcess':
            state['events'].append('S'); assert x[1]==info_class
            assert x[0]==(0xffffffffffffffff if handle==0xffffffff else handle)
            status=set_error or (0xc0000004 if length!=4 else 0xc0000005 if info_null else 0)
            if not status and handle in (0xffffffff,0x44): state['policy']=struct.unpack('<I',u.mem_read(x[2],4))[0]
        elif name=='NtQueryInformationProcess':
            if x[1]==0:
                state['events'].append('I'); status=identity_error; assert x[3]==0x30
                if not status: u.mem_write(x[2]+0x20,struct.pack('<Q',100 if handle==0x44 else 200))
            else:
                state['events'].append('Q'); assert x[1]==34 and x[3]==4 and x[0]==0xffffffffffffffff
                status=query_error
                if not status: u.mem_write(x[2],struct.pack('<I',state['policy']))
        elif name=='notify':
            state['events'].append('N'); assert state['locks']==1
            state['backend_flags']=x[0]; state['notified'].append(x[0])
        elif name=='RtlAcquireSRWLockExclusive': state['locks']+=1; assert state['locks']==1
        elif name=='RtlReleaseSRWLockExclusive': state['locks']-=1; assert state['locks']==0
        elif name=='__wine_dbg_header': status=0xffffffff
        u.reg_write(UC_ARM64_REG_X0,status)
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.reg_write(UC_ARM64_REG_X0,args); uc.reg_write(UC_ARM64_REG_X18,teb)
    uc.reg_write(UC_ARM64_REG_SP,heap+0x1f000); uc.reg_write(UC_ARM64_REG_LR,stop)
    entry=syms['sd_wow64_sync_execute_flags' if initial else 'wow64_NtSetInformationProcess']
    try: uc.emu_start(entry,stop,count=50000)
    except Exception:
        pc=uc.reg_read(UC_ARM64_REG_PC)
        print('Failure PC',hex(pc),'LR',hex(uc.reg_read(UC_ARM64_REG_LR)), 'nearest',max(((v,k) for k,v in syms.items() if v<=pc),default=(0,'?')),state)
        raise
    assert uc.reg_read(UC_ARM64_REG_PC)==stop and not state['locks']
    state['status']=uc.reg_read(UC_ARM64_REG_X0)&0xffffffff
    state['events']=''.join(state['events'])
    return state


def main():
    oldpath=ROOT/'dist/wow64-context-fix/wow64.dll'; newpath=ROOT/'dist/dep-policy-fix/wow64.dll'
    old=pefile.PE(str(oldpath)); new=pefile.PE(str(newpath))
    before=run(old); assert before['policy']==2 and before['backend_flags']==1 and before['events']=='S'
    cases=[('initial',dict(initial=True,policy=2),'QN',[2],None),
        ('self-disable',{},'SQN',[2],0),('self-enable',dict(flags=9),'SQN',[9],0),
        ('self-real',dict(handle=0x44),'SIQN',[2],0),('remote',dict(handle=0x88),'SI',[],0),
        ('denied',dict(set_error=0xc0000022,info_null=True),'S',[],0xc0000022),
        ('bad-size',dict(length=3),'S',[],0xc0000004),('null-buffer',dict(info_null=True),'S',[],0xc0000005),
        ('query-error',dict(query_error=0xc0000001),'SQ',[],0),
        ('identity-error',dict(handle=0x44,identity_error=0xc0000008),'SI',[],0),
        ('backend-absent',dict(backend=False),'S',[],0),
        ('initial-backend-absent',dict(initial=True,backend=False),'',[],None),
        ('initial-query-error',dict(initial=True,query_error=0xc0000001),'Q',[],None),
        ('other-information-class',dict(info_class=5),'S',[],0)]
    results={}
    for name,options,events,notifications,status in cases:
        result=run(new,**options)
        assert result['events']==events and result['notified']==notifications,(name,result)
        if status is not None: assert result['status']==status,(name,result)
        results[name]=result
    context_cases=[(0xfffffffe,{},'G'),(0x44,{},'QG'),(0x48,{},'QSGR'),(0x88,{},'QSGR'),
        (0x48,{'query_error':0xc0000008},'Q'),(0x48,{'suspend_error':0xc00000bb},'QS'),
        (0x48,{'context_error':0xc000000d},'QSGR'),(0xfffffffe,{'context_error':0xc000000d},'G'),
        (0x48,{'software':False},'G')]
    for handle,options,events in context_cases:
        result=context_run(new,handle,**options)
        assert result['returned'] and not result['self_suspend'] and result['count']==3 and result['events']==events
    exports=lambda p:{(s.ordinal,s.name,s.forwarder) for s in p.DIRECTORY_ENTRY_EXPORT.symbols}
    assert exports(old)==exports(new)
    deps=lambda p:{d.dll.lower() for d in p.DIRECTORY_ENTRY_IMPORT}
    assert deps(old)==deps(new)
    assert new.FILE_HEADER.Machine==0xaa64
    write_json(ROOT/'reports/dep-bridge-binary-check.json',{'status':'PASS','dll_sha256':sha(newpath),
        'prior_dll_sha256':sha(oldpath),'prior_policy_desync_reproduced':before,'cases':results,
        'context_regression_cases':9,'export_abi_preserved':True,'dependency_dlls_unchanged':True,
        'hardware_tested':False,'scope':'Actual ARM64 WoW64 DLL; external NT/CPU APIs mocked',
        'sources':{'tests/check_dep_bridge_binary.py':sha(Path(__file__))}})
    print('PASS actual WoW64 ARM64 DLL: original desync reproduced; 14 DEP cases and 9 context regressions')
if __name__=='__main__': main()
