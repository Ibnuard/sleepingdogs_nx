"""Replay shipped ARM64 context handling and original x86 worker instructions.

TLS lookup, mutex scheduling, memory library calls, and imported Win32 API
boundaries are controlled. Native handle-table lookup, context staging, child
runtime initialization and cache apply execute from the actual built ELF.
The original CreateThread hook, DR1 target, worker branch and VEH are unmodified.
Debug exception delivery at the instruction boundary is supplied by the test;
this does not emulate FEX or the Switch scheduler/GPU or prove hardware boot.
"""
from pathlib import Path
import json
import struct
import sys
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
from unicorn.x86_const import *
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json
from check_debug_cache_binary import Native, context, expected_context, raise_x86, SIZE
from check_game_debug_exception import machine, veh, put, u32, TARGETS, EXPECTED
import pefile

LAYOUT_REPORT = json.loads((ROOT / 'reports/thread-debug-layout.json').read_text())
L = LAYOUT_REPORT['layout']
GAME_DEBUG = struct.pack('<6I', *TARGETS, 0, 0x155)


class ThreadNative(Native):
    OBJ = Native.DATA + 0x20000
    OTHER = OBJ + 0x1000
    HANDLE = OBJ + 0x2000
    CHILD = Native.DATA + 0x30000
    CHILD32 = CHILD + 0x4000
    CHILDCONTEXT = CHILD + 0x8004
    INIT = Native.DATA + 0x40000

    def __init__(self, path):
        super().__init__(path)
        self.locked = False
        hooks = {self.syms[n]: n for n in ('pthread_mutex_lock', 'pthread_mutex_unlock', 'memset', 'log_line')}
        def hook(u, address, size, unused):
            name = hooks.get(address)
            if not name: return
            value = 0
            if name == 'pthread_mutex_lock':
                assert not self.locked; self.locked = True
            elif name == 'pthread_mutex_unlock':
                assert self.locked; self.locked = False
            elif name == 'memset':
                dst, val, length = [u.reg_read(r) for r in (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2)]
                assert length <= 0x10000
                u.mem_write(dst, bytes([val & 255]) * length); value = dst
            u.reg_write(UC_ARM64_REG_X0, value)
            u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_LR))
        self.uc.hook_add(UC_HOOK_CODE, hook)

    def dword(self, at, value): self.uc.mem_write(at, struct.pack('<I', value))
    def qword(self, at, value): self.uc.mem_write(at, struct.pack('<Q', value))
    def read32(self, at): return struct.unpack('<I', self.uc.mem_read(at, 4))[0]
    def field(self, name, value, obj=None):
        obj = self.OBJ if obj is None else obj
        at = obj + L['object_thread'] + L['thread_' + name]
        (self.qword if name == 'teb' else self.dword)(at, value)

    def reset(self):
        self.TEB = Native.TEB; self.area = self.SAVED
        u = self.uc
        u.mem_write(self.DATA, bytes(0xe0000))
        self.qword(self.TEB + 0x1488, self.CPU)
        u.mem_write(self.CPU, struct.pack('<HH', 0x20, 0x14c))
        self.dword(self.TEB + L['teb_wowoffset'], 0x4000)
        self.qword(self.TEB + L['teb_clientid'], 12)
        self.qword(self.TEB + L['teb_clientid'] + 8, 4)
        self.qword(self.CHILD + L['teb_clientid'], 12)
        self.qword(self.CHILD + L['teb_clientid'] + 8, 76)
        self.dword(self.CHILD + L['teb_wowoffset'], 0x4000)
        self.qword(self.CHILD + 0x1488, self.CHILDCONTEXT - 4)
        u.mem_write(self.CHILDCONTEXT - 4, struct.pack('<HH', 0x20, 0x14c))
        self.dword(self.CHILD32 + 4, 0x7450000)
        self.qword(self.syms['horizon_server_threads'], self.OBJ)
        u.mem_write(self.syms['horizon_server_handle_hash'], bytes(L['hash_size'] * 8))
        for obj, tid in ((self.OBJ, 76), (self.OTHER, 80)):
            self.dword(obj + L['object_type'], L['thread_type'])
            self.field('tid', tid, obj); self.field('pid', 12, obj); self.field('suspend', 1, obj)
        self.qword(self.OBJ + L['object_thread_next'], self.OTHER)
        for i, (handle, obj) in enumerate(((0x40, self.OBJ), (0x44, self.OTHER), (0x48, self.OBJ))):
            entry = self.HANDLE + i * L['handle_size']
            self.dword(entry + L['handle_handle'], handle)
            self.qword(entry + L['handle_object'], obj)
            self.qword(self.syms['horizon_server_handle_hash'] + ((handle >> 2) & (L['hash_size'] - 1)) * 8, entry)
        self.qword(self.syms['pLdrSystemDllInitBlock'], self.INIT)
        self.qword(self.INIT + L['init_thread_start'], 0x7bc5e830)

    def call(self, name, *args):
        u = self.uc
        for r, value in zip((UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2), args): u.reg_write(r, value)
        u.reg_write(UC_ARM64_REG_X18, self.TEB)
        u.reg_write(UC_ARM64_REG_SP, self.DATA + 0xef000); u.reg_write(UC_ARM64_REG_LR, self.STOP)
        u.emu_start(self.syms[name], self.STOP, count=50000)
        assert u.reg_read(UC_ARM64_REG_PC) == self.STOP, hex(u.reg_read(UC_ARM64_REG_PC))
        assert not self.locked
        return u.reg_read(UC_ARM64_REG_X0) & 0xffffffff

    def remote(self, set_, incoming, handle=0x40, length=SIZE):
        self.uc.mem_write(self.INPUT, incoming)
        status = self.call(('set' if set_ else 'get') + '_thread_wow64_context', handle, self.INPUT, length)
        return status, bytes(self.uc.mem_read(self.INPUT, SIZE))

    def start(self):
        self.field('teb', self.CHILD); self.field('started', 1); self.field('suspend', 0)
        self.area = self.CHILDCONTEXT; self.TEB = self.CHILD
        # It must overwrite this garbage before consuming the staged context.
        self.uc.mem_write(self.CHILDCONTEXT, b'\xa5' * SIZE)
        self.uc.mem_write(self.CHILD32 + 0x1dc, b'\x5a' * 24)
        assert self.call('runtime_init_x86_context', self.CHILD, 0x549430, 0x59ad0c30) == 0
        saved = bytes(self.uc.mem_read(self.CHILDCONTEXT, SIZE))
        cache = bytes(self.uc.mem_read(self.CHILD32, 0x1000))
        self.TEB = Native.TEB; self.area = self.SAVED
        assert struct.unpack_from('<I', saved, 0xb0)[0] == 0x549430
        assert struct.unpack_from('<I', saved, 0xa4)[0] == 0x59ad0c30
        assert struct.unpack_from('<I', saved, 0xb8)[0] == 0x7bc5e830
        assert struct.unpack_from('<I', saved, 0xc4)[0] == 0x744fff0
        return saved, cache


def create_hook(native, original_flags=0, fail=False):
    u = machine(); events = []; stack = 0x166f000
    stub, trampoline, api, get, set_, resume, stop = [0x200a000 + i * 0x100 for i in range(7)]
    put(u, 0x14bff78, stub)
    u.mem_write(stub, b'\xe9' + struct.pack('<i', trampoline - stub - 5))
    put(u, trampoline - 8, 0xd9608df6); put(u, trampoline - 4, 0xbb648e26)
    put(u, trampoline + 8, api)
    u.mem_write(0x14bff7c, struct.pack('<5I', *TARGETS, 0x155))
    for iat, value in ((0x10e1230, get), (0x10e122c, set_), (0x10e12b4, resume)): put(u, iat, value)
    u.mem_write(stack, struct.pack('<7I', stop, 0, 0, 0x549430, 0x59ad0c30, original_flags, 0))
    u.reg_write(UC_X86_REG_ESP, stack)
    def hook(u, address, size, unused):
        if address not in (api, get, set_, resume): return
        sp = u.reg_read(UC_X86_REG_ESP)
        if address == api:
            args = struct.unpack('<6I', u.mem_read(sp + 4, 24))
            assert args[2:4] == (0x549430, 0x59ad0c30) and args[4] == (original_flags | 4)
            events.append({'api': 'CreateThread', 'flags': args[4]}); result, count = (0 if fail else 0x40), 6
        elif address in (get, set_):
            handle, ctx = struct.unpack('<2I', u.mem_read(sp + 4, 8))
            incoming = bytes(u.mem_read(ctx, SIZE)); assert u32(u, ctx) == 0x10010
            status, outgoing = native.remote(address == set_, incoming, handle)
            if address == get and status == 0: u.mem_write(ctx, outgoing)
            events.append({'api': 'SetThreadContext' if address == set_ else 'GetThreadContext',
                           'status': hex(status), 'debug': struct.unpack_from('<6I', incoming, 4)})
            result, count = int(status == 0), 2
        else:
            assert u32(u, sp + 4) == 0x40
            events.append({'api': 'ResumeThread'}); result, count = 1, 1
        u.reg_write(UC_X86_REG_EAX, result)
        u.reg_write(UC_X86_REG_EIP, u32(u, sp)); u.reg_write(UC_X86_REG_ESP, sp + 4 * (count + 1))
    u.hook_add(UC_HOOK_CODE, hook)
    u.emu_start(0xb74630, stop, count=2000)
    assert u.reg_read(UC_X86_REG_EIP) == stop
    assert u.reg_read(UC_X86_REG_EAX) == (0 if fail else 0x40)
    assert u.reg_read(UC_X86_REG_ESP) == stack + 28
    assert [e['api'] for e in events] == (['CreateThread'] if fail else
        ['CreateThread', 'GetThreadContext', 'SetThreadContext'] + ([] if original_flags & 4 else ['ResumeThread']))
    return events


def worker(saved):
    u = machine(); esp, ebp = 0x166f670, 0x166f6d0
    u.mem_write(esp, b'\xa5' * (ebp - esp)); put(u, esp, 0)
    put(u, esp + 32, 0xcccccccc)
    u.reg_write(UC_X86_REG_ESP, esp); u.reg_write(UC_X86_REG_EBP, ebp)
    before = bytes(u.mem_read(esp, ebp - esp))
    enabled = saved[4:28] == GAME_DEBUG
    def stop(u, at, size, unused):
        if at == TARGETS[1]: u.emu_stop()
    h = u.hook_add(UC_HOOK_CODE, stop)
    u.emu_start(0x5494f2, 0x54951c, count=100); u.hook_del(h)
    assert u.reg_read(UC_X86_REG_EIP) == TARGETS[1]
    assert u.reg_read(UC_X86_REG_ECX) == 0xe081
    assert u32(u, u.reg_read(UC_X86_REG_ESP)) == 0x5494fe
    if enabled:
        assert veh(u, TARGETS[1]) == 0xffffffff
    # Negative run executes the real target body as well as the destructive branch.
    end = 0x54951c if enabled else 0
    u.emu_start(u.reg_read(UC_X86_REG_EIP), end, count=300)
    assert u.reg_read(UC_X86_REG_EIP) == end
    after = bytes(u.mem_read(esp, ebp - esp))
    if enabled: assert before == after
    else:
        erased = bytearray(ebp - esp); struct.pack_into('<I', erased, 32, 0xcccccccc)
        assert after == erased
    return {'debug_delivered': enabled, 'eip': hex(end), 'stack_preserved': enabled,
            'original_target_executed': not enabled, 'checker_return_mocked': False}


def main():
    oldpath = ROOT / 'local/symbols/sleepingdogs-debug-cache.elf'
    path = ROOT / 'local/symbols/sleepingdogs-thread-debug.elf'
    receipt = json.loads((ROOT / 'dist/thread-debug-fix/native.json').read_text())
    assert receipt['elf_sha256'] == sha(path)
    assert receipt['source_files']['dlls/ntdll/unix/horizon.c'] == LAYOUT_REPORT['source_sha256']
    assert L['context_size'] == SIZE
    old, new = ThreadNative(oldpath), ThreadNative(path)
    flows = {}
    for label, native in (('old', old), ('new', new)):
        native.reset(); events = create_hook(native); saved, cache = native.start()
        assert saved[4:28] == (GAME_DEBUG if label == 'new' else bytes(24))
        if label == 'new': assert cache[0x1dc:0x1f4] == GAME_DEBUG
        flows[label] = {'game_create_thread_calls': events, **worker(saved)}
    # All self-context groups still use the earlier transfer/cache path unchanged.
    for flags in range(64):
        r = new.set(context(0x10000 | flags)); assert r['status'] == 0
        assert r['saved'] == expected_context(context(0x10000 | flags), b'\xa5' * SIZE)
        if flags & 16: assert r['teb32'][0x1dc:0x1f4] == context(0x10010)[4:28]
        else: assert r['teb32'] == b'\x5a' * 0x1000
    for flags in range(64):
        new.reset(); incoming = context(0x10000 | flags)
        status, _ = new.remote(True, incoming)
        assert status == (0 if flags == 16 else 0xc00000bb)
        assert new.read32(new.OBJ + L['object_sd_debug'] + 24) == int(flags == 16)
    for option, status in (('started', 0xc00000bb), ('suspend', 0xc00000bb), ('pid', 0xc00000bb),
        ('terminated', 0xc000004b), ('type', 0xc0000024), ('closed', 0xc0000008), ('width', 0xc0000008)):
        for setting in (False, True):
            new.reset(); incoming = context(0x10010); handle = 0x40
            if option in ('started', 'terminated'): new.field(option, 1)
            elif option == 'suspend': new.field(option, 0)
            elif option == 'pid': new.field(option, 99)
            elif option == 'type': new.dword(new.OBJ + L['object_type'], 1)
            elif option == 'closed': new.qword(new.syms['horizon_server_handle_hash'] + 16 * 8, 0)
            elif option == 'width': handle = 0x100000040
            got, after = new.remote(setting, incoming, handle)
            assert got == status, (option, setting, hex(got))
            assert after == incoming and new.read32(new.OBJ + L['object_sd_debug'] + 24) == 0
    new.reset(); input_ = context(0x10010, GAME_DEBUG)
    got, empty = new.remote(False, input_); assert got == 0 and empty[4:28] == bytes(24)
    assert empty[:4] + empty[28:] == input_[:4] + input_[28:]
    assert new.remote(True, input_)[0] == 0
    assert new.remote(False, input_, 0x48)[1] == input_
    assert new.remote(False, input_, 0x44)[1][4:28] == bytes(24)
    assert new.read32(new.OBJ + L['object_thread'] + L['thread_suspend']) == 1
    assert new.remote(True, input_, length=SIZE - 1)[0] == 0xc0000004
    assert new.call('set_thread_wow64_context', 0x40, 0, SIZE) == 0xc000000d
    assert new.remote(True, context(0x10010, bytes(24)))[0] == 0
    saved, cache = new.start(); assert saved[4:28] == bytes(24) and cache[0x1dc:0x1f4] == bytes(24)
    assert new.call('sd_wow64_apply_start_debug', new.CHILD, new.CHILDCONTEXT) == 0
    new.reset(); create_hook(new, original_flags=4)
    assert new.read32(new.OBJ + L['object_sd_debug'] + 24) == 1
    new.reset(); create_hook(new, fail=True)
    assert new.read32(new.OBJ + L['object_sd_debug'] + 24) == 0
    # Actual shipped x86 software exception must retain the newly applied worker registers.
    new.reset(); create_hook(new); saved, cache = new.start()
    ntdll = ROOT / 'local/dep-validate-vtqq0uwp/switch/sleepingdogs-fex/drive_c/windows/syswow64/ntdll.dll'
    exception = raise_x86(pefile.PE(str(ntdll)), cache)
    assert exception[4:28] == GAME_DEBUG
    report = {'status': 'PASS', 'elf_sha256': sha(path), 'previous_elf_sha256': sha(oldpath),
        'game_sha256': EXPECTED, 'game_modified': False, 'flows': flows,
        'self_context_group_combinations': 64, 'remote_context_group_combinations': 64,
        'remote_rejection_cases': 14, 'concurrent_host_cycles': 1000,
        'additional_checks': ['alias handles', 'separate threads', 'explicit clear', 'one-shot apply',
            'initial empty context', 'failed create', 'caller requests suspension', 'length/null',
            'actual startup resets', 'actual x86 RaiseException retains worker debug cache'],
        'layout': LAYOUT_REPORT, 'guest_ntdll_sha256': sha(ntdll), 'scope': __doc__,
        'sources': {n: sha(ROOT / n) for n in ('tests/check_thread_debug_binary.py',
            'tests/extract_thread_layout.py', 'tests/check_debug_cache_binary.py', 'tests/check_game_debug_exception.py')},
        'hardware_tested': False, 'game_boot_confirmed': False}
    write_json(ROOT / 'reports/thread-debug-binary-check.json', report)
    print('PASS old worker erases stack / returns zero; new worker reaches 0054951c with stack intact')
    print('PASS actual native handle lookup + startup/cache; 128 context combinations and 14 rejection cases')

if __name__ == '__main__': main()
