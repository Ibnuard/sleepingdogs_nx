"""Replay native context sets, shipped x86 RaiseException, and the post-frame game site.

Actual ARM64 ELF and x86 PE instructions execute in Unicorn. Only native TLS/
CPU-area lookup, logging, memcpy and the NT exception boundary are substituted.
The checker body is not emulated: the negative case supplies a nonzero return,
then executes the original destructive branch. No game file is modified.
"""
from pathlib import Path
import struct
import sys
import pefile
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_ARCH_X86, UC_MODE_ARM, UC_MODE_32, UC_HOOK_CODE
from unicorn.arm64_const import *
from unicorn.x86_const import *
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json
from check_game_debug_exception import machine, veh, u32, put, EXPECTED, TARGETS

SIZE = 0x2cc
DEBUG = struct.pack('<6I', *TARGETS, 0xffff0ff9, 0x155)


class Native:
    DATA = 0x60000000
    TEB = DATA + 0x1000
    TEB32 = TEB + 0x4000
    CPU = DATA + 0x8000
    SAVED = CPU + 4
    INPUT = DATA + 0x9000
    STOP = DATA + 0xff000

    def __init__(self, path):
        self.uc = u = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        with path.open('rb') as f:
            e = ELFFile(f)
            self.syms = {s.name: s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols()}
            segs = [s for s in e.iter_segments() if s['p_type'] == 'PT_LOAD']
            start = min(s['p_vaddr'] for s in segs) & ~4095
            end = max(s['p_vaddr'] + s['p_memsz'] for s in segs)
            u.mem_map(start, ((end + 4095) & ~4095) - start)
            for s in segs: u.mem_write(s['p_vaddr'], s.data())
        u.mem_map(self.DATA, 0x100000)
        names = ('NtCurrentTeb', 'get_cpu_area', 'horizon_trace', 'memcpy', 'memmove')
        hooks = {self.syms[n]: n for n in names}
        self.area = self.SAVED
        def hook(u, address, size, unused):
            name = hooks.get(address)
            if name is None: return
            result = 0
            if name == 'NtCurrentTeb': result = self.TEB
            elif name == 'get_cpu_area':
                assert u.reg_read(UC_ARM64_REG_X0) == 0x14c
                result = self.area
            elif name in ('memcpy', 'memmove'):
                dst, src, length = [u.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2)]
                assert length <= SIZE
                u.mem_write(dst, bytes(u.mem_read(src, length))); result = dst
            u.reg_write(UC_ARM64_REG_X0, result)
            u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_LR))
        u.hook_add(UC_HOOK_CODE, hook)

    def set(self, incoming, saved=None, cache=None, *, handle=0xfffffffffffffffe,
            length=SIZE, machine=0x14c, cpu=True, area=True, context=True, wow=True, alias=False):
        u = self.uc
        saved = saved if saved is not None else b'\xa5' * SIZE
        cache = cache if cache is not None else b'\x5a' * 0x1000
        u.mem_write(self.TEB, bytes(0x2000))
        u.mem_write(self.TEB + 0x1488, struct.pack('<Q', self.CPU if cpu else 0))
        u.mem_write(self.TEB + 0x180c, struct.pack('<i', 0x4000 if wow else 0))
        u.mem_write(self.TEB + 0x48, struct.pack('<Q', 4))
        u.mem_write(self.CPU, struct.pack('<HH', 0x20, machine))
        u.mem_write(self.SAVED, incoming if alias else saved)
        u.mem_write(self.INPUT, incoming)
        u.mem_write(self.TEB32, cache)
        self.area = self.SAVED if area else 0
        u.reg_write(UC_ARM64_REG_X0, handle)
        u.reg_write(UC_ARM64_REG_X1, (self.SAVED if alias else self.INPUT) if context else 0)
        u.reg_write(UC_ARM64_REG_X2, length)
        u.reg_write(UC_ARM64_REG_SP, self.DATA + 0xef000)
        u.reg_write(UC_ARM64_REG_LR, self.STOP)
        u.emu_start(self.syms['set_thread_wow64_context'], self.STOP, count=20000)
        assert u.reg_read(UC_ARM64_REG_PC) == self.STOP
        return {'status': u.reg_read(UC_ARM64_REG_X0) & 0xffffffff,
                'saved': bytes(u.mem_read(self.SAVED, SIZE)),
                'teb32': bytes(u.mem_read(self.TEB32, 0x1000)),
                'cpu_flags': struct.unpack('<H', u.mem_read(self.CPU, 2))[0]}


def context(flags, debug=DEBUG):
    data = bytearray(bytes(range(256)) * 3)[:SIZE]
    struct.pack_into('<I', data, 0, flags)
    data[4:28] = debug
    return bytes(data)


def expected_context(incoming, saved):
    flags = struct.unpack_from('<I', incoming)[0]
    out = bytearray(saved)
    groups = {1: [(0xb4, 0xcc)], 2: [(0x9c, 0xb4)], 4: [(0x8c, 0x9c)],
              8: [(0x1c, 0x8c)], 16: [(4, 28)], 32: [(0xcc, SIZE)]}
    for bit, spans in groups.items():
        if flags & bit:
            for begin, end in spans: out[begin:end] = incoming[begin:end]
    for bit, offsets in ((1, (0xbc, 0xc8)), (4, (0x8c, 0x90, 0x94, 0x98))):
        if flags & bit:
            for offset in offsets: out[offset + 2:offset + 4] = bytes(2)
    return bytes(out)


def raise_x86(pe, cache, code=0x406d1388):
    u = Uc(UC_ARCH_X86, UC_MODE_32); base = pe.OPTIONAL_HEADER.ImageBase
    u.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    u.mem_write(base, pe.get_memory_mapped_image())
    u.mem_map(0, 0x1000)  # Flat FS fixture; FS:[0x18] resolves to this TEB.
    u.mem_map(0x2000000, 0x20000)
    teb, rec, stack = 0x2001000, 0x2003000, 0x201f000
    u.mem_write(teb, cache); put(u, 0x18, teb)
    put(u, rec, code); put(u, rec + 16, 4)
    put(u, rec + 20, 0x1000); put(u, rec + 24, 0x120741c); put(u, rec + 28, 0x48)
    put(u, stack, 0x7b013049); put(u, stack + 4, rec)
    u.reg_write(UC_X86_REG_ESP, stack); u.reg_write(UC_X86_REG_EBP, stack + 0x20)
    exports = {s.name.decode(): base + s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
    def stop(u, address, size, unused):
        if address == exports['NtRaiseException']: u.emu_stop()
    u.hook_add(UC_HOOK_CODE, stop)
    u.emu_start(exports['RtlRaiseException'], exports['NtRaiseException'], count=20000)
    assert u.reg_read(UC_X86_REG_EIP) == exports['NtRaiseException']
    sp = u.reg_read(UC_X86_REG_ESP)
    assert u32(u, sp + 4) == rec and u32(u, sp + 12) == 1
    return bytes(u.mem_read(u32(u, sp + 8), SIZE))


def post_frame(deliver):
    u = machine(); esp, ebp = 0x166f670, 0x166f698
    u.mem_write(esp, b'\xa5' * (ebp - esp))
    put(u, esp, 0x3a4f78)
    put(u, 0x166f68c, 0x166f6c8); put(u, 0x166f690, 0xf70708)
    u.reg_write(UC_X86_REG_ESP, esp); u.reg_write(UC_X86_REG_EBP, ebp)
    before = bytes(u.mem_read(esp, ebp - esp))
    def stop(u, address, size, unused):
        if address == TARGETS[0]: u.emu_stop()
    hook = u.hook_add(UC_HOOK_CODE, stop)
    u.emu_start(0xb2373b, 0xb2376d, count=100); u.hook_del(hook)
    assert u.reg_read(UC_X86_REG_EIP) == TARGETS[0]
    assert u32(u, u.reg_read(UC_X86_REG_ESP)) == 0xb2374f
    if deliver:
        assert veh(u, TARGETS[0]) == 0xffffffff
    else:
        # Nonzero return observed after the missing #DB; no substitute checker.
        u.reg_write(UC_X86_REG_EAX, 1)
        u.reg_write(UC_X86_REG_ESP, esp); u.reg_write(UC_X86_REG_EIP, 0xb2374f)
    end = 0xb2376d if deliver else 0x3a4f78
    u.emu_start(u.reg_read(UC_X86_REG_EIP), end, count=200)
    assert u.reg_read(UC_X86_REG_EIP) == end
    if deliver: assert bytes(u.mem_read(esp, ebp - esp)) == before
    else:
        assert bytes(u.mem_read(esp + 4, ebp - esp - 4)) == bytes(ebp - esp - 4)
        assert u32(u, 0x166f690) == 0
    return {'breakpoint_delivered': deliver, 'eip': hex(end), 'stack_preserved': deliver}


def main():
    oldpath = ROOT / 'local/symbols/sleepingdogs-dep-policy.elf'
    newpath = ROOT / 'local/symbols/sleepingdogs-debug-cache.elf'
    ntdll = ROOT / 'local/dep-validate-vtqq0uwp/switch/sleepingdogs-fex/drive_c/windows/syswow64/ntdll.dll'
    pe = pefile.PE(str(ntdll)); old, new = Native(oldpath), Native(newpath)
    # Reproduce the actual failure across both architectures, with shipped ntdll.
    flows = {}
    for label, binary in (('old', old), ('new', new)):
        arm = binary.set(context(0x10010), cache=bytes(0x1000))
        assert arm['saved'][4:28] == DEBUG
        exception = raise_x86(pe, arm['teb32'])
        assert struct.unpack_from('<I', exception)[0] == 0x1003f
        applied = binary.set(exception, saved=arm['saved'], cache=arm['teb32'])
        enabled = applied['saved'][4:28] == DEBUG
        assert enabled == (label == 'new')
        if label == 'old': assert applied['saved'][4:28] == bytes(24)
        flows[label] = {'exception_debug': struct.unpack_from('<6I', exception, 4), **post_frame(enabled)}
    # All 64 context-group combinations: no unrequested register/cache writes.
    for flags in range(64):
        incoming = context(0x10000 | flags); saved = b'\xa5' * SIZE
        result = new.set(incoming, saved=saved)
        assert result['status'] == 0
        assert result['saved'] == expected_context(incoming, saved), flags
        expected = bytearray(b'\x5a' * 0x1000)
        if flags & 16: expected[0x1dc:0x1f4] = DEBUG
        assert result['teb32'] == expected, flags
        assert result['cpu_flags'] == (0x21 if flags & 1 else 0x20)
    error_cases = [(dict(length=SIZE - 1), 0xc0000004), (dict(handle=0x44), 0xc0000002),
        (dict(machine=0xaa64), 0xc000000d), (dict(cpu=False), 0xc000000d),
        (dict(area=False), 0xc000000d), (dict(context=False), 0xc000000d)]
    for options, status in error_cases:
        r = new.set(context(0x10010), **options)
        assert r['status'] == status and r['saved'] == b'\xa5' * SIZE
        assert r['teb32'] == b'\x5a' * 0x1000 and r['cpu_flags'] == 0x20
    r = new.set(context(0x1007f))
    assert r['status'] == 0xc00000bb and r['saved'] == b'\xa5' * SIZE and r['teb32'] == b'\x5a' * 0x1000
    r = new.set(context(0x10010, bytes(24)))
    assert r['status'] == 0 and r['saved'][4:28] == bytes(24) and r['teb32'][0x1dc:0x1f4] == bytes(24)
    r = new.set(context(0x10010), wow=False)
    assert r['status'] == 0 and r['saved'][4:28] == DEBUG and r['teb32'] == b'\x5a' * 0x1000
    incoming = context(0x1003f); r = new.set(incoming, alias=True)
    assert r['status'] == 0 and r['saved'] == expected_context(incoming, incoming)
    assert r['teb32'][0x1dc:0x1f4] == DEBUG
    # The fix applies to software exceptions generally, not just thread naming.
    for code in (0xe06d7363, 0x12345678):
        assert raise_x86(pe, r['teb32'], code)[4:28] == DEBUG
    write_json(ROOT / 'reports/debug-cache-binary-check.json', {'status': 'PASS',
        'elf_sha256': sha(newpath), 'prior_elf_sha256': sha(oldpath), 'guest_ntdll_sha256': sha(ntdll),
        'game_sha256': EXPECTED, 'game_modified': False, 'flows': flows,
        'context_group_combinations': 64, 'additional_edge_cases': 12,
        'prior_game_debug_regressions': 8, 'hardware_tested': False,
        'scope': __doc__, 'sources': {n: sha(ROOT / n) for n in
            ('tests/check_debug_cache_binary.py', 'tests/check_game_debug_exception.py')}})
    print('PASS old register loss reproduced; new cache survives actual x86 RaiseException; post-frame stack preserved')
    print('PASS 64 context combinations, 12 edge cases, 8 earlier game-handler regressions')

if __name__ == '__main__': main()
