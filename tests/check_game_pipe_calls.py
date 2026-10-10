"""Replay original DLL pipe-open routines read-only; model only imported APIs.

This verifies the dependency on named-pipe support and the actual flags/path.
It does not emulate the game's full Steam initialization or prove Switch boot.
"""
from pathlib import Path
import hashlib
import json
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDI, UC_X86_REG_ESP, UC_X86_REG_EIP

ROOT = Path(__file__).resolve().parents[1]
DLL = ROOT.parent / 'Sleeping Dogs/pandoraclient.dll'


def replay(start, succeed):
    pe = pefile.PE(str(DLL)); base = pe.OPTIONAL_HEADER.ImageBase
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    u.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    u.mem_write(base, pe.get_memory_mapped_image())
    for addr in (0x20000000, 0x21000000, 0x22000000, 0x23000000, 0x24000000): u.mem_map(addr, 0x10000)
    imports = {}; calls = []
    for d in pe.DIRECTORY_ENTRY_IMPORT:
        for i in d.imports:
            addr = 0x23000000 + len(imports) * 16
            imports[addr] = (i.name or str(i.ordinal).encode()).decode()
            u.mem_write(i.address, struct.pack('<I', addr))
    def words(addr, n): return struct.unpack('<' + 'I' * n, u.mem_read(addr, 4 * n))
    def string(addr):
        out = bytearray()
        while True:
            pair = bytes(u.mem_read(addr + len(out), 2))
            if pair == b'\0\0': return out.decode('utf-16-le')
            out.extend(pair)
    def hook(machine, addr, size, userdata):
        if addr not in imports: return
        name = imports[addr]; esp = u.reg_read(UC_X86_REG_ESP); ret = words(esp, 1)[0]
        pop = 0; value = 0
        if name == 'realloc':
            old, size = words(esp + 4, 2); assert not old and size <= 65536
            value = 0x22000000
        elif name in ('memcpy', 'memmove'):
            dest, src, size = words(esp + 4, 3)
            u.mem_write(dest, bytes(u.mem_read(src, size))); value = dest
        elif name == 'free': pass
        elif name in ('CreateNamedPipeW', 'CreateFileW'):
            count = 8 if name == 'CreateNamedPipeW' else 7
            args = words(esp + 4, count); path = string(args[0]); pop = 4 * count
            assert path == r'\\.\pipe\pandora_master_pipe'
            if name == 'CreateNamedPipeW': assert args[1:] == (0x40000003, 6, 255, 0, 0, 0, 0)
            else: assert args[1:] == (0xc0000000, 0, 0, 3, 0x40000000, 0)
            value = 0x104 if succeed else 0xffffffff
            calls.append({'api': name, 'path': path, 'arguments': list(args[1:]), 'return_handle': hex(value)})
        else: raise AssertionError('Unexpected import: ' + name)
        u.reg_write(UC_X86_REG_EAX, value)
        u.reg_write(UC_X86_REG_ESP, esp + 4 + pop)
        u.reg_write(UC_X86_REG_EIP, ret)
    u.hook_add(UC_HOOK_CODE, hook)
    sp = 0x20008000; u.mem_write(sp, struct.pack('<I', 0x24000000))
    u.reg_write(UC_X86_REG_ESP, sp); u.reg_write(UC_X86_REG_EDI, 0x21000000)
    u.emu_start(base + start, 0x24000000, count=10000)
    assert u.reg_read(UC_X86_REG_ESP) == sp + 4
    assert u.reg_read(UC_X86_REG_EAX) & 255 == int(succeed)
    assert words(0x21000008, 1)[0] == (0x104 if succeed else 0xffffffff)
    assert len(calls) == 1
    return {'entry_rva': hex(start), 'api_model_succeeded': succeed, 'caller_returned': int(succeed), 'calls': calls}


def main():
    result = {'dll_sha256': hashlib.sha256(DLL.read_bytes()).hexdigest(),
              'passed': 4, 'game_files_modified': False,
              'cases': [replay(rva, success) for rva in (0x33f0, 0x21770) for success in (False, True)],
              'limitations': 'Imported Win32 APIs and CRT allocation/copy are host models; full SteamAPI_Init and Switch boot are not tested.'}
    (ROOT / 'reports/game-pipe-call-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
