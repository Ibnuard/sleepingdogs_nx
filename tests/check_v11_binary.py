"""Validate linked diagnostic entry points, ARM64 disabled/boundary guards and inherited regressions."""
from pathlib import Path
import gc
import importlib
import io
import json
import struct
import sys
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools')); sys.path.insert(0,str(ROOT/'tests'))
from port_common import sha,write_json
from check_low_window_binary import Machine

def diagnostics(elf_path):
    elf=ELFFile(io.BytesIO(elf_path.read_bytes()))
    syms={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols() if s['st_size']}
    section=elf.get_section_by_name('.text'); code=section.data(); base=section['sh_addr']
    for name in ('wine_nx_sd_diag_note','wine_nx_sd_diag_thread_map','sd_frame_diag'):
        assert name in syms,name
    s=syms['server_call_unlocked']; targets=[]
    for offset in range(0,s['st_size']-3,4):
        word=struct.unpack_from('<I',code,s['st_value']-base+offset)[0]
        if word & 0x7c000000 == 0x14000000:
            rel=word & 0x3ffffff
            if rel & 0x2000000: rel-=0x4000000
            targets.append(s['st_value']+offset+rel*4)
    assert syms['wine_nx_sd_diag_note']['st_value'] in targets,'Wine telemetry not linked'
    m=Machine('good',elf_path)
    cases=[]
    try:
        data=m.symbols['sd_frame_diag']; size=syms['sd_frame_diag']['st_size']
        for name,start,stop,begin,end in (
                ('disabled',0,0,100,200),('before-window',1000,2000,999,1001),
                ('at-deadline',1000,2000,1999,2000),('after-window',1000,2000,2000,2100),
                ('reversed-time',1000,2000,1500,1499)):
            m.vm.mem_write(data,bytes(size)); m.q(data,start); m.q(data+8,stop)
            before=bytes(m.vm.mem_read(data,size))
            m.call('wine_nx_sd_diag_note',0,begin,end,0,0,1)
            assert bytes(m.vm.mem_read(data,size))==before,name
            cases.append(name)
    finally: m.close()
    write_json(ROOT/'reports/low-window-v11-diagnostic-binary.json',dict(status='PASS',
        elf_sha256=sha(elf_path),compiled_cases=cases,wine_callback_linked=True,hardware_tested=False,
        sources={'tests/check_v11_binary.py':sha(Path(__file__))}))
    print('PASS:',len(cases),'real ARM64 diagnostic guards; Wine callback linked',flush=True)

def main():
    elf_path=ROOT/'local/symbols/sleepingdogs-low-window-v11.elf'
    diagnostics(elf_path); gc.collect()
    for module,report in (('check_direct_sync_binary','direct-sync-binary'),
            ('check_cpu_topology_binary','cpu-topology'),('check_sync_startup_binary','sync-startup-binary'),
            ('check_low_window_binary','binary'),('check_shader_binary','shader-binary')):
        m=importlib.import_module(module)
        original=m.write_json
        def redirected(path,value,_write=original,_report=report):
            return _write(ROOT/'reports'/('low-window-v11-'+_report+'.json'),value)
        m.write_json=redirected
        sys.argv=[module,'--elf',str(elf_path)]
        print('Checking',module,flush=True)
        try: m.main()
        finally: m.write_json=original
        gc.collect()

if __name__=='__main__': main()
