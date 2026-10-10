"""Run direct-dispatch guards in the shipped ARM64 ELF and verify client linkage.

Blocking and concurrent object semantics are covered by the separate sanitizer
host test. This test executes real compiled fallback branches with modeled TLS/SVCs.
"""
from pathlib import Path
import argparse
import io
import json
import re
import struct
import sys
from elftools.elf.elffile import ELFFile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from port_common import ROOT, sha, write_json
from check_low_window_binary import Machine


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf',type=Path,default=ROOT/'local/symbols/sleepingdogs-low-window-v10.elf')
    a=p.parse_args()
    elf=ELFFile(io.BytesIO(a.elf.read_bytes()))
    syms={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols() if s['st_size']}
    section=elf.get_section_by_name('.text'); code=section.data(); start=section['sh_addr']
    def branches(name):
        s=syms[name]; offset=s['st_value']-start
        result=[]
        for at in range(0,s['st_size']-3,4):
            w=struct.unpack_from('<I',code,offset+at)[0]
            if w & 0x7c000000 == 0x14000000:
                rel=w & 0x3ffffff
                if rel & 0x2000000: rel-=0x4000000
                result.append(s['st_value']+at+rel*4)
        return result
    dest=syms['horizon_server_sync_call']['st_value']
    route=['server_call_unlocked']
    targets=branches(route[0])
    if dest not in targets:
        via=[n for n,s in syms.items() if s['st_value'] in targets and s['st_info']['type']=='STT_FUNC'
             and s['st_shndx']==syms['server_call_unlocked']['st_shndx'] and dest in branches(n)]
        assert via,'Direct sync not reachable from Wine client'
        route.append(via[0])
    route.append('horizon_server_sync_call')
    for n in ('horizon_fast_sync_enabled','horizon_server_profile_enabled','wine_nx_sd_sync_snapshot','wine_nx_sd_sync_calls'):
        assert n in syms,n
    source=(ROOT/'local/direct-sync-v10-source/dlls/ntdll/unix/horizon.c').read_text()
    req=int(re.search(r'^#define HORIZON_REQ_EVENT_OP\s+(\d+)',source,re.M)[1])
    cases=[]
    m=Machine('good',a.elf)
    try:
        buffer=m.back; reply=buffer+4096; payload=buffer+8192
        for mode in (0,1,2):
            m.vm.mem_write(m.symbols['horizon_fast_sync_enabled'],struct.pack('<I',mode))
            checks=[('null_tid',0,buffer,payload,0,reply,0,req,0,0),
                    ('null_message',1,0,payload,0,reply,0,req,0,0),
                    ('null_reply',1,buffer,payload,0,0,0,req,0,0),
                    ('mismatched_payload',1,buffer,payload,0,reply,0,req,1,0),
                    ('missing_payload',1,buffer,0,1,reply,0,req,1,0),
                    ('missing_reply_payload',1,buffer,payload,0,reply,0,req,0,1),
                    ('unsupported_request',1,buffer,payload,0,reply,0,0x7fffffff,0,0)]
            if mode==0: checks.append(('valid_mode_off',1,buffer,payload,0,reply,0,req,0,0))
            for label,tid,message,data,size,out,extra,opcode,request_size,reply_size in checks:
                m.vm.mem_write(buffer,struct.pack('<III',opcode,request_size,reply_size)+bytes(116))
                m.vm.mem_write(reply,b'\xaa'*128)
                assert m.call('horizon_server_sync_call',tid,message,data,size,out,extra)==0,(mode,label)
                assert bytes(m.vm.mem_read(reply,128))==b'\xaa'*128,(mode,label)
                cases.append(dict(mode=mode,case=label,reply_untouched=True))
    finally: m.close()
    report=dict(status='PASS',scope=__doc__,hardware_tested=False,elf_sha256=sha(a.elf),
        linked_route=route,compiled_cases=cases,sources={'tests/check_direct_sync_binary.py':sha(Path(__file__)),
        'tests/check_low_window_binary.py':sha(ROOT/'tests/check_low_window_binary.py')})
    write_json(ROOT/'reports/low-window-v10-direct-sync-binary.json',report)
    print('PASS:',len(cases),'real ARM64 dispatch fallback/validation cases; linked route:',route,flush=True)


if __name__=='__main__': main()
