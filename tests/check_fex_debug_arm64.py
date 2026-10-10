"""Run the actual guard emitter's AArch64 output in Unicorn (not a Python model)."""
from pathlib import Path
import hashlib
import json
import random
import struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'local/fex-debug-check'
LAYOUT = json.loads((DATA / 'layout.json').read_text())
CODE = (DATA / 'guard.bin').read_bytes()
RIP, ENTRY, TRAP, END, STATE, STACK = 0x4c0a8a, 0x1000000, 0x1001000, 0x1002000, 0x2000000, 0x3000000

def run(addresses, enabled, expected, rf=0, resume=0):
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    uc.mem_map(ENTRY, 0x3000); uc.mem_write(ENTRY, CODE)
    uc.mem_map(STATE, (LAYOUT['frame_size'] + 4095) & ~4095)
    uc.mem_map(STACK, 4096)
    frame = bytearray([0xa5] * LAYOUT['frame_size'])
    for i, a in enumerate(addresses): struct.pack_into('<I', frame, LAYOUT['address'] + i * 4, a)
    for field, value in [('enabled', enabled), ('hit', 0), ('resume_rip', resume)]:
        struct.pack_into('<I', frame, LAYOUT[field], value)
    struct.pack_into('<Q', frame, LAYOUT['signal'], TRAP)
    frame[LAYOUT['rf']] = rf
    before = bytes(frame); uc.mem_write(STATE, before)
    for i in range(29): uc.reg_write(UC_ARM64_REG_X0 + i, 0xabc00000 + i)
    uc.reg_write(UC_ARM64_REG_X29, 0xabc0001d)
    uc.reg_write(UC_ARM64_REG_X28, STATE); uc.reg_write(UC_ARM64_REG_LR, END)
    uc.reg_write(UC_ARM64_REG_SP, STACK + 2048)
    uc.reg_write(UC_ARM64_REG_NZCV, 0xb0000000)
    hit = []
    def on_code(uc, address, size, _):
        if address == TRAP: hit.append(address); uc.emu_stop()
    uc.hook_add(UC_HOOK_CODE, on_code)
    uc.emu_start(ENTRY, END, count=256)
    assert bool(hit) == bool(expected), (addresses, enabled, rf, resume)
    after = bytes(uc.mem_read(STATE, LAYOUT['frame_size']))
    assert struct.unpack_from('<I', after, LAYOUT['hit'])[0] == expected
    assert uc.reg_read(UC_ARM64_REG_NZCV) == 0xb0000000, 'Guest flags changed'
    for i in range(3, 28):
        assert uc.reg_read(UC_ARM64_REG_X0 + i) == 0xabc00000 + i, ('Guest/SRA register changed', i)
    assert uc.reg_read(UC_ARM64_REG_X29) == 0xabc0001d
    assert uc.reg_read(UC_ARM64_REG_X28) == STATE
    assert uc.reg_read(UC_ARM64_REG_LR) == END
    assert uc.reg_read(UC_ARM64_REG_SP) == STACK + 2048 + (32 if expected else 0)
    expected_bytes = bytearray(before)
    if resume == RIP: expected_bytes[LAYOUT['rf']] = 0
    if expected:
        struct.pack_into('<I', expected_bytes, LAYOUT['hit'], expected)
        struct.pack_into('<Q', expected_bytes, LAYOUT['rip'], RIP)
        # bool generated, SIGTRAP=5, x86 #DB=1, TRAP_HWBKPT=4, error=0, pad=0.
        struct.pack_into('<Q', expected_bytes, LAYOUT['fault'], 0x04010501)
    assert after == expected_bytes, 'Unexpected frame write or incorrect exception metadata'

cases = 0
for slot in range(4):
    addresses = [0x700000 + i for i in range(4)]; addresses[slot] = RIP
    for mask in range(16):
        run(addresses, mask, mask & (1 << slot)); cases += 1
run([RIP] * 4, 15, 15); cases += 1
run([RIP + 1] * 4, 15, 0); cases += 1
run([RIP] * 4, 15, 0, rf=1, resume=RIP); cases += 1
run([RIP] * 4, 15, 15, rf=0, resume=RIP); cases += 1
run([RIP + 1] * 4, 15, 0, rf=1, resume=RIP); cases += 1
# Shared cached code must follow the executing thread's current state.
for _ in range(4):
    for mask in (1, 0, 8, 0): run([RIP] * 4, mask, mask); cases += 1
random.seed(771)
for _ in range(100):
    addresses = [RIP if random.randrange(2) else random.randrange(0x100000000) for i in range(4)]
    mask = random.randrange(16)
    expected = sum(1 << i for i in range(4) if mask & (1 << i) and addresses[i] == RIP)
    run(addresses, mask, expected); cases += 1
report = {'passed': cases, 'dr7_decode_cases_in_cpp': 257,
          'guard_sha256': hashlib.sha256(CODE).hexdigest(), 'layout': LAYOUT,
          'checks': ['DR0-DR3', 'enable/disable/reprogram', 'simultaneous hits', 'RF once at resume RIP',
                     'shared code with different thread states', 'guest registers and NZCV preserved',
                     'only allowed frame writes', 'spill stack unwind on trap only', 'pre-instruction #DB metadata'],
          'hardware_tested': False}
(ROOT / 'reports/fex-debug-arm64-check.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
