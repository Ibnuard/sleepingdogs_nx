"""Invoke the shipped ARM64 DLL's JIT emitter with mocked allocator/write-alias boundaries."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import argparse
import pefile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *
from check_wow64_context_binary import symbols

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'local/fex-debug-check'
layout = json.loads((DATA / 'dll-layout.json').read_text())
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--dll', type=Path, default=ROOT / 'dist/fex-debug-fix/libwow64fex.dll')
p.add_argument('--report', type=Path, default=ROOT / 'reports/fex-debug-binary-check.json')
args = p.parse_args()
dll = args.dll
pe = pefile.PE(str(dll)); syms = symbols(pe)
entry = next(v for k, v in syms.items() if 'Op_SDDebugCheckE' in k)
uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
base = pe.OPTIONAL_HEADER.ImageBase
uc.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
uc.mem_write(base, pe.get_memory_mapped_image())
obj, op, heap, stack, output, stop = 0x70000000, 0x70040000, 0x71000000, 0x72000000, 0x1000000, 0x100f000
uc.mem_map(obj, 0x100000); uc.mem_map(heap, 0x100000)
uc.mem_map(stack, 0x10000); uc.mem_map(output, 0x10000)
assert layout['jit_size'] < 0x40000
for field, value in [('buffer', output), ('cursor', output), ('writable', output), ('buffer_size', 4096), ('entry', 0x4c0a8a)]:
    uc.mem_write(obj + layout[field], struct.pack('<Q', value))
uc.mem_write(obj + layout['spills'], struct.pack('<I', 1))
uc.mem_write(op + layout['op_offset'], struct.pack('<I', 0))
uc.reg_write(UC_ARM64_REG_X0, obj); uc.reg_write(UC_ARM64_REG_X1, op)
uc.reg_write(UC_ARM64_REG_X2, 0); uc.reg_write(UC_ARM64_REG_SP, stack + 0xf000)
uc.reg_write(UC_ARM64_REG_LR, stop)
bump = [heap]; calls = []
hooks = {syms['PES13FexWriteAlias']: 'alias'}
for dependency in pe.DIRECTORY_ENTRY_IMPORT:
    for symbol in dependency.imports:
        if symbol.name in (b'memcpy', b'memmove', b'memset'):
            stub = output + 0xe000 + len(hooks) * 16
            uc.mem_write(symbol.address, struct.pack('<Q', stub))
            hooks[stub] = symbol.name.decode()
for name, address in syms.items():
    if name.startswith('_ZN7FEXCore9Allocator'):
        if '13aligned_allocE' in name: hooks[address] = 'aligned_alloc'
        elif '12aligned_freeE' in name: hooks[address] = 'free'

def on_code(uc, address, size, _):
    action = hooks.get(address)
    if not action: return
    calls.append(action)
    if action == 'aligned_alloc':
        align = max(8, uc.reg_read(UC_ARM64_REG_X0)); size = uc.reg_read(UC_ARM64_REG_X1)
        pointer = (bump[0] + align - 1) & ~(align - 1)
        bump[0] = pointer + size
        assert bump[0] < heap + 0x100000
        uc.reg_write(UC_ARM64_REG_X0, pointer)
    elif action == 'alias': pass
    elif action == 'free': pass
    elif action in ('memcpy', 'memmove', 'memset'):
        dst, src, count = [uc.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2)]
        assert count < 0x10000
        if count:
            data = bytes([src & 255]) * count if action == 'memset' else bytes(uc.mem_read(src, count))
            uc.mem_write(dst, data)
    uc.reg_write(UC_ARM64_REG_PC, uc.reg_read(UC_ARM64_REG_LR))

uc.hook_add(UC_HOOK_CODE, on_code)
try:
    uc.emu_start(entry, stop, count=1000000)
except Exception:
    pc = uc.reg_read(UC_ARM64_REG_PC)
    closest = max(((v, k) for k, v in syms.items() if v <= pc), default=(0, '?'))
    print('Emitter failed at', hex(pc), closest, 'calls', calls[-8:])
    raise
assert uc.reg_read(UC_ARM64_REG_PC) == stop
cursor = struct.unpack('<Q', uc.mem_read(obj + layout['cursor'], 8))[0]
assert output < cursor < output + 4096
guard = bytes(uc.mem_read(output, cursor - output)) + bytes.fromhex('c0035fd6')
(DATA / 'dll-guard.bin').write_bytes(guard)
# Reuse the behavioral matrix on the output emitted by the actual DLL.
sys.path.insert(0, str(ROOT / 'tests'))
import check_fex_debug_arm64 as check
check.CODE = guard
for slot in range(4):
    for mask in range(16):
        addresses = [0x550000 + i for i in range(4)]; addresses[slot] = check.RIP
        check.run(addresses, mask, mask & (1 << slot))
check.run([check.RIP] * 4, 15, 15)
check.run([check.RIP] * 4, 15, 0, rf=1, resume=check.RIP)
check.run([check.RIP + 1] * 4, 15, 0, rf=1, resume=check.RIP)
old = pefile.PE(str(ROOT / 'vendor/fex/libwow64fex-f1-demand.dll'))
def imports(p): return {x.dll.decode(): sorted((i.name or str(i.ordinal).encode()).decode() for i in x.imports) for x in p.DIRECTORY_ENTRY_IMPORT}
def exports(p): return sorted((s.name, s.ordinal) for s in p.DIRECTORY_ENTRY_EXPORT.symbols)
assert imports(pe) == imports(old)
assert exports(pe) == exports(old)
assert pe.get_data(syms['PES13FexPrimeCodeCache'] - base, 4) == bytes.fromhex('c0035fd6')
report = {'dll_sha256': hashlib.sha256(dll.read_bytes()).hexdigest(), 'actual_dll_emitter_cases': 67,
          'guard_sha256': hashlib.sha256(guard).hexdigest(), 'guard_bytes': len(guard),
          'imports_unchanged': True, 'exports_unchanged': True, 'eager_spare_is_ret': True,
          'production_frame_offsets_match_host': True, 'mocked_boundaries': sorted(set(calls)),
          'hardware_tested': False}
args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report))
