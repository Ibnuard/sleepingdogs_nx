"""Execute the original game/Wine wait path to validate the diagnostic frame offset."""
from pathlib import Path
import json
import struct
import sys
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json


def main():
    game=ROOT.parent/'Sleeping Dogs/HKShip.exe'
    kernelbase=ROOT.parent/'pes13-nx/local/production-input-fix/approved/switch/pes13-fex/drive_c/windows/syswow64/kernelbase.dll'
    assert sha(game)=='3c2eaa260ee29dfb464a0321aa9c7dc74e343894b663fac4fdd11d40fab0bacc'
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    loaded=[]
    for path in (game,kernelbase):
        pe=pefile.PE(str(path));loaded.append(pe)
        uc.mem_map(pe.OPTIONAL_HEADER.ImageBase,(pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095)
        uc.mem_write(pe.OPTIONAL_HEADER.ImageBase,pe.get_memory_mapped_image())
    def put(address,value): uc.mem_write(address,struct.pack('<I',value))
    def u32(address): return struct.unpack('<I',uc.mem_read(address,4))[0]
    wait=next(e for e in loaded[1].DIRECTORY_ENTRY_EXPORT.symbols if e.name==b'WaitForSingleObject')
    assert wait.address+loaded[1].OPTIONAL_HEADER.ImageBase==0x7b05e420 and wait.forwarder is None
    signatures={0xbb6f30:'8b016aff50ff15c4110e01c3',0xbb8730:'8b4cbe7851',0x7b05e420:'66905589e556'}
    for address,hex_bytes in signatures.items():
        assert bytes(uc.mem_read(address,len(bytes.fromhex(hex_bytes))))==bytes.fromhex(hex_bytes)
    uc.mem_map(0x1660000,0x10000);uc.mem_map(0x30000000,0x10000);uc.mem_map(0x2000000,0x1000)
    # Loader/API fixtures in emulator memory only: bind the game's IAT to the
    # actual kernelbase function and stop at its native NtWait import boundary.
    put(0x10e11c4,0x7b05e420);put(0x7b0942fc,0x2000000)
    queue,slot,obj,handle=0x30001000,2,0x30002000,0x6d4ffff0
    put(queue+0x78+slot*4,obj);put(obj,handle)
    uc.reg_write(UC_X86_REG_ESP,0x166f200);uc.reg_write(UC_X86_REG_EBP,0x166f700)
    uc.reg_write(UC_X86_REG_ESI,queue);uc.reg_write(UC_X86_REG_EDI,slot)
    uc.emu_start(0xbb8730,0x2000000,count=200)
    esp,ebp=uc.reg_read(UC_X86_REG_ESP),uc.reg_read(UC_X86_REG_EBP)
    assert u32(esp+4)==handle and u32(esp+8)==0 and u32(esp+12)==0
    assert u32(ebp+4)==0xbb6f3b and u32(ebp-4)==queue
    assert uc.reg_read(UC_X86_REG_EDI)==slot
    assert u32(u32(ebp-4)+0x78+slot*4)==obj and u32(obj)==handle
    report=dict(status='PASS',game_sha256=sha(game),kernelbase_sha256=sha(kernelbase),
                game_modified=False,hardware_tested=False,
                test_sha256=sha(Path(__file__)),
                signatures={hex(a):v for a,v in signatures.items()},
                observation='Original game queue -> semaphore wrapper -> original kernelbase WaitForSingleObject: EBP-4 preserves queue ESI, EDI preserves slot; invalid handle is loaded from the semaphore object.',
                limitation='Fixture supplies the already-invalid object value. It validates capture layout, not the origin of corruption or a freeze fix.')
    write_json(ROOT/'reports/low-window-sync-guest-frame.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
