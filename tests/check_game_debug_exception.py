"""Execute the original x86 call site and VEH to reproduce the reported failure.

No game file is changed. The negative case supplies the nonzero return observed
in the Switch log; the positive case delivers the architectural #DB to the game's
unaltered handler and resumes the same call site with its returned context.
"""
from pathlib import Path
import hashlib
import json
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT.parent / 'Sleeping Dogs/HKShip.exe'
EXPECTED = '3c2eaa260ee29dfb464a0321aa9c7dc74e343894b663fac4fdd11d40fab0bacc'
assert hashlib.sha256(GAME.read_bytes()).hexdigest() == EXPECTED
PE = pefile.PE(str(GAME))
BASE = PE.OPTIONAL_HEADER.ImageBase
TARGETS = [0x4c0a8a, 0x5b2e92, 0x61ce88, 0x68d35a]
ESP, EBP = 0x166fe70, 0x166fe98
REGS = [UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
        UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EFLAGS]

def u32(uc, at): return struct.unpack('<I', uc.mem_read(at, 4))[0]
def put(uc, at, value): uc.mem_write(at, struct.pack('<I', value))

def machine():
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, (PE.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    uc.mem_write(BASE, PE.get_memory_mapped_image())
    uc.mem_map(0x1660000, 0x10000)
    uc.mem_map(0x2000000, 0x10000)
    put(uc, 0x14bffa0, BASE); put(uc, 0x14bffa4, 0xce036a)
    uc.mem_write(ESP, bytes.fromhex('12345678') * 12)
    put(uc, ESP, 0xfffffffe)
    put(uc, 0x166fe8c, 0x166ff40); put(uc, 0x166fe90, 0xfb5cf8)
    uc.reg_write(UC_X86_REG_ESP, ESP); uc.reg_write(UC_X86_REG_EBP, EBP)
    uc.reg_write(UC_X86_REG_EFLAGS, 0x246)
    return uc

def veh(uc, address, code=0x80000004):
    ctx, rec, ptr, stack, stop = 0x2000100, 0x2000400, 0x2000600, 0x2008000, 0x2009000
    saved = {r: uc.reg_read(r) for r in REGS}
    put(uc, rec, code); put(uc, rec + 12, address)
    put(uc, ptr, rec); put(uc, ptr + 4, ctx)
    put(uc, ctx + 0xb0, saved[UC_X86_REG_EAX])
    put(uc, ctx + 0xb8, address); put(uc, ctx + 0xc4, saved[UC_X86_REG_ESP])
    put(uc, stack, stop); put(uc, stack + 4, ptr)
    uc.reg_write(UC_X86_REG_ESP, stack)
    uc.emu_start(0xb74470, stop, count=200)
    handled = uc.reg_read(UC_X86_REG_EAX)
    for r, v in saved.items(): uc.reg_write(r, v)
    if handled == 0xffffffff:
        uc.reg_write(UC_X86_REG_EAX, u32(uc, ctx + 0xb0))
        uc.reg_write(UC_X86_REG_ESP, u32(uc, ctx + 0xc4))
        uc.reg_write(UC_X86_REG_EIP, u32(uc, ctx + 0xb8))
    return handled

def constructor(deliver):
    uc = machine(); before = bytes(uc.mem_read(ESP, EBP - ESP))
    def stop_at_target(uc, address, size, _):
        if address == TARGETS[0]: uc.emu_stop()
    hook = uc.hook_add(UC_HOOK_CODE, stop_at_target)
    uc.emu_start(0x7d469a, 0x7d46cd, count=40)
    uc.hook_del(hook)
    assert uc.reg_read(UC_X86_REG_EIP) == TARGETS[0]
    assert u32(uc, uc.reg_read(UC_X86_REG_ESP)) == 0x7d46af
    if deliver:
        assert veh(uc, TARGETS[0]) == 0xffffffff
    else:
        uc.reg_write(UC_X86_REG_EAX, 1)  # Observed nonzero return, not a simulated checker body.
        uc.reg_write(UC_X86_REG_ESP, ESP)
        uc.reg_write(UC_X86_REG_EIP, 0x7d46af)
    uc.emu_start(uc.reg_read(UC_X86_REG_EIP), 0x7d46cd if deliver else 0x7d46cc, count=200)
    if deliver:
        assert bytes(uc.mem_read(ESP, EBP - ESP)) == before
        assert uc.reg_read(UC_X86_REG_EIP) == 0x7d46cd
    else:
        assert bytes(uc.mem_read(ESP + 4, EBP - ESP - 4)) == bytes(EBP - ESP - 4)
        assert u32(uc, ESP) == 0xfffffffe
        assert u32(uc, 0x166fe90) == 0  # The null SEH responsible for the later recursion.

constructor(False); constructor(True)
for target in TARGETS:
    uc = machine(); put(uc, ESP, 0x7d46af)
    assert veh(uc, target) == 0xffffffff
    assert uc.reg_read(UC_X86_REG_EIP) == 0x7d46af
    assert uc.reg_read(UC_X86_REG_ESP) == ESP + 4
    assert uc.reg_read(UC_X86_REG_EAX) == 0
for code, address in [(0xc0000005, TARGETS[0]), (0x80000004, BASE - 1)]:
    assert veh(machine(), address, code) == 0
report = {'passed': 8, 'game_sha256': EXPECTED, 'game_modified': False,
          'negative': 'Observed nonzero return reproduces stack erasure, null SEH and return-to-fffffffe',
          'positive': 'Original VEH handles #DB at all four addresses; original call site preserves stack',
          'hardware_boot_test': False}
path = ROOT / 'reports/game-debug-exception-check.json'
path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
