"""Run the actual ARM64 WoW64 DLL context thunk with mocked NT API boundaries."""
from pathlib import Path
import struct
import sys

import pefile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2,
    UC_ARM64_REG_X3, UC_ARM64_REG_X4, UC_ARM64_REG_X18, UC_ARM64_REG_X30,
    UC_ARM64_REG_SP, UC_ARM64_REG_PC)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import BASE, sha, write_json


def symbols(pe):
    data = pe.__data__
    table = pe.FILE_HEADER.PointerToSymbolTable
    count = pe.FILE_HEADER.NumberOfSymbols
    strings = table + 18 * count
    result = {}
    index = 0
    while index < count:
        offset = table + 18 * index
        raw = data[offset:offset + 8]
        value, section, kind, storage, aux = struct.unpack_from('<IhHBB', data, offset + 8)
        if raw[:4] == b'\0' * 4:
            start = strings + struct.unpack_from('<I', raw, 4)[0]
            name = data[start:data.find(b'\0', start)].decode()
        else:
            name = raw.rstrip(b'\0').decode()
        if section > 0:
            result[name] = pe.OPTIONAL_HEADER.ImageBase + pe.sections[section - 1].VirtualAddress + value
        index += 1 + aux
    return result


def run(pe, handle, *, software=True, query_error=0, suspend_error=0,
        context_error=0, stop_self=False):
    syms = symbols(pe)
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    base = pe.OPTIONAL_HEADER.ImageBase
    uc.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    uc.mem_write(base, pe.get_memory_mapped_image())
    heap, stubs, stop = 0x20000000, 0x21000000, 0x2100f000
    uc.mem_map(heap, 0x20000)
    uc.mem_map(stubs, 0x10000)
    args, info, teb, context = (heap + n for n in (0x1000, 0x2000, 0x3000, 0x4000))
    uc.mem_write(syms['wow64info'], struct.pack('<Q', info))
    uc.mem_write(info + 4, struct.pack('<I', 2 if software else 0))
    uc.mem_write(teb + 0x40, struct.pack('<QQ', 100, 4))
    uc.mem_write(args, struct.pack('<II', handle, context))
    uc.mem_write(context, struct.pack('<I', 0x10010))
    names = ['NtQueryInformationThread', 'RtlWow64SuspendThread', 'RtlWow64GetThreadContext', 'NtResumeThread']
    hooks = {}
    for n, name in enumerate(names):
        address = stubs + n * 0x100
        uc.mem_write(address, bytes.fromhex('c0035fd6'))  # ret
        uc.mem_write(syms['__imp_' + name], struct.pack('<Q', address))
        hooks[address] = name
    events, state = [], {'count': 3, 'self_suspend': False, 'get_handle': None}

    def hook(machine, address, size, unused):
        name = hooks.get(address)
        if not name:
            return
        thread = machine.reg_read(UC_ARM64_REG_X0)
        status = 0
        if name == 'NtQueryInformationThread':
            events.append('Q')
            assert machine.reg_read(UC_ARM64_REG_X1) == 0
            assert machine.reg_read(UC_ARM64_REG_X3) == 0x30
            assert machine.reg_read(UC_ARM64_REG_X4) == 0
            status = query_error
            if not status:
                out = machine.reg_read(UC_ARM64_REG_X2)
                machine.mem_write(out + 0x10, struct.pack('<QQ', 200 if thread == 0x88 else 100,
                                                        8 if thread == 0x48 else 4))
        elif name == 'RtlWow64SuspendThread':
            events.append('S')
            state['self_suspend'] = thread in (0xfffffffffffffffe, 0x44)
            if state['self_suspend'] and stop_self:
                machine.emu_stop()
                return
            status = suspend_error
            if not status:
                machine.mem_write(machine.reg_read(UC_ARM64_REG_X1), struct.pack('<I', state['count']))
                state['count'] += 1
        elif name == 'RtlWow64GetThreadContext':
            events.append('G')
            state['get_handle'] = thread
            assert machine.reg_read(UC_ARM64_REG_X1) == context
            assert machine.mem_read(context, 4) == struct.pack('<I', 0x10010)
            status = context_error
            if not status:
                machine.mem_write(context + 24, struct.pack('<I', 0x400))
        else:
            events.append('R')
            machine.mem_write(machine.reg_read(UC_ARM64_REG_X1), struct.pack('<I', state['count']))
            state['count'] -= 1
        machine.reg_write(UC_ARM64_REG_X0, status)

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.reg_write(UC_ARM64_REG_X0, args)
    uc.reg_write(UC_ARM64_REG_X18, teb)
    uc.reg_write(UC_ARM64_REG_X30, stop)
    uc.reg_write(UC_ARM64_REG_SP, heap + 0x1ff00)
    uc.emu_start(syms['wow64_NtGetContextThread'], stop, count=10000)
    state.update(events=''.join(events), status=uc.reg_read(UC_ARM64_REG_X0) & 0xffffffff,
                 returned=uc.reg_read(UC_ARM64_REG_PC) == stop)
    return state


def main():
    original = BASE / 'drive_c/windows/system32/wow64.dll'
    fixed = ROOT / 'dist/wow64-context-fix/wow64.dll'
    old, new = pefile.PE(str(original)), pefile.PE(str(fixed))
    assert new.FILE_HEADER.Machine == old.FILE_HEADER.Machine == 0xaa64
    export_names = lambda pe: {(s.ordinal, s.name, s.forwarder) for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
    assert export_names(new) == export_names(old)
    imports = lambda pe: {(d.dll.lower(), s.name, s.ordinal) for d in pe.DIRECTORY_ENTRY_IMPORT for s in d.imports}
    assert imports(new) == imports(old)
    before = run(old, 0xfffffffe, stop_self=True)
    assert before['self_suspend'] and not before['returned'] and before['events'] == 'S'
    cases = [
        ('self', 0xfffffffe, {}, 'G', 0),
        ('self-real-handle', 0x44, {}, 'QG', 0),
        ('other-thread', 0x48, {}, 'QSGR', 0),
        ('other-process-same-tid', 0x88, {}, 'QSGR', 0),
        ('invalid-handle', 0x48, {'query_error': 0xc0000008}, 'Q', 0xc0000008),
        ('suspend-refused', 0x48, {'suspend_error': 0xc00000bb}, 'QS', 0xc00000bb),
        ('context-error', 0x48, {'context_error': 0xc000000d}, 'QSGR', 0xc000000d),
        ('self-context-error', 0xfffffffe, {'context_error': 0xc000000d}, 'G', 0xc000000d),
        ('native-backend', 0x48, {'software': False}, 'G', 0),
    ]
    results = {}
    for name, handle, options, events, status in cases:
        result = run(new, handle, **options)
        assert result['returned'] and not result['self_suspend'], (name, result)
        assert result['events'] == events and result['status'] == status, (name, result)
        assert result['count'] == 3, (name, result)
        if name in ('self', 'self-real-handle'):
            assert result['get_handle'] == 0xfffffffffffffffe
        results[name] = result
    write_json(ROOT / 'reports/wow64-context-arm64-check.json', {
        'status': 'PASS', 'original_sha256': sha(original), 'fixed_sha256': sha(fixed),
        'original_self_suspend_reproduced': before, 'cases': results,
        'imports_and_exports_preserved': True, 'hardware_tested': False,
        'scope': 'Actual DLL ARM64 instructions, NT API call boundaries mocked by Unicorn'})
    print('PASS: shipped ARM64 DLL; original self-suspend reproduced, all 9 corrected cases pass, imports/exports preserved.')


if __name__ == '__main__':
    main()
