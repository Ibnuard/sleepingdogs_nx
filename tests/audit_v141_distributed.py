"""Audit the delivered v14.1 ZIP/NRO and its public loader route, not the user's SD."""
from pathlib import Path
import json
import struct
import sys
import zipfile
from elftools.elf.elffile import ELFFile
from check_v141_cache_binary import CacheIdentity
from check_low_window_binary import ROOT
from port_common import sha,write_json


def main():
    native=json.loads((ROOT/'dist/low-window-gm20b-cache-fix/native.json').read_text())
    receipt=json.loads((ROOT/'reports/low-window-gm20b-cache-fix-package.json').read_text())
    archive=ROOT/'dist/sleepingdogs-fex-low-window-gm20b-cache-fix.zip'
    nro=ROOT/'dist/low-window-gm20b-cache-fix/sleepingdogs-fex.nro'
    elf=ROOT/'local/symbols/sleepingdogs-low-window-v141.elf'
    assert sha(archive)==receipt['update']['sha256']
    assert sha(nro)==receipt['nro_sha256']==native['nro_sha256']
    assert sha(elf)==receipt['elf_sha256']==native['elf_sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')==nro.read_bytes()
    data=nro.read_bytes();segments=[]
    with elf.open('rb') as f:
        e=ELFFile(f)
        for i in range(3):
            off,length=struct.unpack_from('<II',data,0x20+8*i)
            segment=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']==off)
            raw=segment.data();skip=0x80 if i==0 else 0
            # elf2nro rewrites the initial NRO/header bytes; executable payload,
            # rodata and initialized data must otherwise be the linked ELF.
            assert data[off+skip:off+len(raw)]==raw[skip:]
            segments.append(dict(index=i,offset=off,nro_size=length,elf_file_size=len(raw),skipped_header_bytes=skip))
    layout=json.loads((ROOT/'dist/low-window-gm20b-cache-fix/layout.json').read_text())
    m=CacheIdentity(elf,layout)
    try:
        string=m.area+0x800;m.vm.mem_write(string,b'vkCreateInstance\0')
        proc=m.call('vkGetInstanceProcAddr',0,string)
        assert proc in (m.symbols['vkCreateInstance'],m.symbols['nvk_CreateInstance'])
        m.symbols['nvk_CreateInstance']=proc
        result=m.run()
        assert result['identities_match'] and result['pipeline_build_id']==native['cache_id']
        assert len(result['logs'])==1 and '[SD-NVK-V14.1]' in result['logs'][0]
    finally:m.close()
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in (
        Path(__file__),ROOT/'tests/check_v141_cache_binary.py',ROOT/'tests/check_low_window_binary.py')}
    report=dict(status='PASS',scope=__doc__,zip_sha256=sha(archive),nro_sha256=sha(nro),elf_sha256=sha(elf),
        segment_payloads_match=segments,public_loader_lookup_and_create=result,sources=sources,
        hardware_tested=False,deployed_nro_available=False,
        limitation='Fixture execution confirms the shipped loader reaches the corrected instance; '
                   'the trace sink is modeled. This does not explain the missing hardware-log marker '
                   'or prove what file is stored/launched on the SD.')
    write_json(ROOT/'reports/distributed-v141-audit.json',report)
    print('PASS distributed ZIP/NRO/ELF payload and public Vulkan loader cache-identity route',flush=True)


if __name__=='__main__':main()
