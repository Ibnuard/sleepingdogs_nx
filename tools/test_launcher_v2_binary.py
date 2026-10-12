"""Audit linked symbols and execute the real ARM64 pre-main heap gate."""
from pathlib import Path
import hashlib,io,json,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X30,UC_ARM64_REG_PC,UC_ARM64_REG_SP
from launcher_v2_overlay import ROOT
from package_launcher_v2 import host

LOCAL=ROOT/'local/launcher-v2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    build=json.loads((LOCAL/'build.json').read_text());path=host(build['elf']);data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==build['elf_sha256']
    vm=Uc(UC_ARCH_ARM64,UC_MODE_ARM);symbols={};load=[]
    with io.BytesIO(data) as f:
        elf=ELFFile(f);table=elf.get_section_by_name('.symtab');undefined=[]
        for s in table.iter_symbols():
            if s.name and s.entry['st_shndx']=='SHN_UNDEF' and s.entry['st_info']['bind']!='STB_WEAK':undefined.append(s.name)
            elif s.name:symbols[s.name]=s.entry['st_value']
        assert not undefined,undefined
        for p in elf.iter_segments():
            if p['p_type']=='PT_LOAD':load.append((p['p_vaddr'],p['p_memsz'],p.data()))
    low=min(p[0] for p in load)&~4095;high=max(p[0]+p[1] for p in load);vm.mem_map(low,(high-low+4095)&~4095)
    for address,size,data in load:vm.mem_write(address,data)
    required=['__libnx_initheap','__wrap_vkGetInstanceProcAddr','__wrap_vkGetDeviceProcAddr','sd_keyboard_present_gate',
        'fx_keyboard_input_blocked','fx_osk_frame_visible','fx_osk_frame_presented','fx_osk_frame_reject',
        'sd_lsfg_present','sd_lsfg_create_device','sd_lsfg_create_chain','sd_lsfg_intercept','wine_nx_lsfg_present','wine_nx_sd_com_wow64_unix_funcs','vkGetInstanceProcAddr','nvk_CreateDevice','D3D11CreateDevice']
    for name in required:assert symbols.get(name),name
    stack=0x7000000000;stop=stack+0x100000;vm.mem_map(stack,0x101000)
    default=struct.unpack('<Q',vm.mem_read(symbols['__nx_heap_size'],8))[0] or 256*1024*1024
    cases=[];current={}
    def ret(value=0):vm.reg_write(UC_ARM64_REG_X0,value);vm.reg_write(UC_ARM64_REG_PC,vm.reg_read(UC_ARM64_REG_X30))
    def hook(vm,pc,size,user):
        if pc==stop:vm.emu_stop();return
        if pc==symbols.get('svcGetInfo'):
            i=current['queries'];current['queries']+=1;assert i<4
            current['query_types'].append(vm.reg_read(UC_ARM64_REG_X1))
            vm.mem_write(vm.reg_read(UC_ARM64_REG_X0),struct.pack('<Q',current['values'][i]));ret(current.get('query_fail',0) if i==0 else 0)
        elif pc==symbols.get('envHasHeapOverride'):ret(current.get('override',0)!=0)
        elif pc==symbols.get('envGetHeapOverrideAddr'):ret(0x7100000000)
        elif pc==symbols.get('envGetHeapOverrideSize'):ret(current['override'])
        elif pc==symbols.get('svcSetHeapSize'):
            n=vm.reg_read(UC_ARM64_REG_X1);current['sizes'].append(n)
            if n>current.get('limit',4*1024**3):ret(1)
            else:vm.mem_write(vm.reg_read(UC_ARM64_REG_X0),struct.pack('<Q',0x7100000000));ret()
        elif pc==symbols.get('envGetExitFuncPtr'):ret(0)
        elif pc==symbols.get('__nx_exit'):current['exited']=True;vm.emu_stop()
    vm.hook_add(UC_HOOK_CODE,hook)
    good=[0x200000,0x7fffe00000,0xda000000,0x059a3db219b42000]
    specs=[('patched',{},[default]),('unpatched',{'values':[0x80000000,0x7f80000000,*good[2:]]},[128*1024**2]),
        ('wrong-title',{'values':[*good[:3],good[3]+1]},[128*1024**2]),
        ('query-failed',{'query_fail':1},[128*1024**2]),
        ('small-applet',{'values':[*good[:2],40*1024**2,good[3]],'limit':40*1024**2},[128*1024**2,64*1024**2,32*1024**2]),
        ('loader-owned',{'override':64*1024**2},[]),
        ('no-memory',{'query_fail':1,'limit':0},[n*1024**2 for n in (128,64,32,16,8,4,2)])]
    for name,options,sizes in specs:
        current.clear();current.update(values=good,queries=0,query_types=[],sizes=[],exited=False);current.update(options)
        vm.reg_write(UC_ARM64_REG_SP,stop-32);vm.reg_write(UC_ARM64_REG_X30,stop)
        vm.emu_start(symbols['__libnx_initheap'],stop,count=200000)
        assert current['queries']==4 and current['sizes']==sizes,(name,current)
        assert current['exited']==(name=='no-memory'),(name,current)
        cases.append(dict(name=name,sizes=sizes,exited=current['exited'],query_types=current['query_types']))
    # The actual closed-keyboard branch must return without any SDK call.
    vm.reg_write(UC_ARM64_REG_SP,stop-32);vm.reg_write(UC_ARM64_REG_X30,stop)
    vm.emu_start(symbols['sd_keyboard_present_gate'],stop,count=200)
    assert vm.reg_read(UC_ARM64_REG_PC)==stop
    report=dict(status='PASS',elf_sha256=build['elf_sha256'],nro_sha256=build['nro_sha256'],required_symbols=required,
        unresolved_strong_symbols=undefined,actual_arm64_heap_cases=cases,closed_keyboard_gate_executed=True,
        hardware_tested=False,scope='Actual linked ARM64 heap policy under Unicorn; modeled svc/env APIs. No physical mapping or GPU test.')
    (LOCAL/'binary-test.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':'PASS','heap_cases':len(cases),'symbols':len(required)}))
if __name__=='__main__':main()
