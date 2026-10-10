"""Execute the shipped ARM64 decoder setup/loop with real x86 decoding."""
from pathlib import Path
import json
import struct
import sys
import pefile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'pes13-nx/tests'))
sys.path.insert(0, str(ROOT / 'tools'))
from fex_scratch import ScratchModel, VTABLE, DISOWN
from fex_alloc import PARAM, STUBS, reg
from port_common import sha, write_json
L = json.loads((ROOT / 'local/compiler-memory-layout.json').read_text())
DLL = ROOT / 'dist/compiler-memory-fix/libwow64fex.dll'


class DecoderModel(ScratchModel):
    def hook(self, vm, pc, size, user):
        if hasattr(self, 'entries') and pc not in self.entries and not STUBS <= pc < STUBS + 0x10000:
            return
        symbol = getattr(self, 'by_address', {}).get(pc, '')
        if 'Config5Value' in symbol and '11GetIfExists' in symbol:
            vm.reg_write(reg(0), vm.reg_read(reg(1))); self.host_return(); return
        super().hook(vm, pc, size, user)

    def __init__(self):
        super().__init__(DLL)
        self.entries = set(self.symbols.values())
        self.ctx = PARAM + 0x5000; self.decoder = PARAM + 0x6000
        self.thread = 0x30000000; self.frame = 0x30004000; self.gdt = 0x30006000
        self.vm.mem_map(self.thread, 0x10000)
        self.writeq(self.ctx, self.symbols['_ZTVN7FEXCore7Context11ContextImplE'] + 16)
        self.writeq(self.ctx + L['ctx_maxinst'], 500)
        self.vm.mem_write(self.ctx + L['ctx_multiblock'], b'\1')
        self.pool = self.ctx + L['ctx_pool']
        self.writeq(self.pool, self.symbols[VTABLE] + 16)
        for offset in (8, 32):
            self.writeq(self.pool + offset, self.pool + offset)
            self.writeq(self.pool + offset + 8, self.pool + offset)
        self.writeq(self.thread + L['thread_ctx'], self.ctx)
        self.writeq(self.thread + L['thread_frame'], self.frame)
        self.writeq(self.frame + L['segments'], self.gdt)
        self.invoke(self.method('DecoderC2E'), self.decoder, self.thread)
        assert not self.trapped
        self.code = 0x400000; self.vm.mem_map(self.code, 0x100000)
        self.vm.mem_write(self.code, b'\x90' * 0x100000)
        self.writeq(self.decoder + L['range_base'], self.code)
        self.writeq(self.decoder + L['range_end'], self.code + 0x100000)

    def setup(self, maximum, code=None, pc=None):
        if code is not None: self.vm.mem_write(self.code, code)
        self.pc = pc or self.code
        self.invoke(self.method('Decoder30SetupDecode'), self.decoder, self.thread, self.pc, maximum)
        assert not self.trapped
        n = maximum or 500
        assert self.readq(self.decoder + L['capacity']) == min(max(1, n), 65536)
        p = self.readq(self.decoder + L['buffer'])
        assert p
        return p

    def decode(self, pause=0):
        self.invoke(self.method('Decoder10DecodeLoop'), self.decoder, self.pc, pause)
        assert not self.trapped
        n = self.readq(self.decoder + L['decoded'])
        assert n <= self.readq(self.decoder + L['capacity'])
        return n

    def release(self):
        self.invoke(DISOWN, self.decoder + L['pool'])
        assert not self.trapped


def main():
    m = DecoderModel(); checks = []
    for n in (1, 2, 31, 32, 33, 127, 499, 500, 501, 512, 513, 1024):
        p = m.setup(n)
        got = m.decode()
        assert got == n, (n, got)
        m.release(); checks.append(n)
    large = (2048, 65535, 65536, 65537, 2**64-1)
    for n in large:
        m.setup(n); m.release()
    # The normal Fastest path really requests 64 KiB, rather than simply using
    # the beginning of an 8 MiB allocation. Observe the native ABI callback.
    compact = DecoderModel(); p = compact.setup(0)
    assert compact.native_regions[p] == 65536
    tail = p + 500*128; canary = b'\xa5' * (65536 - 500*128)
    compact.vm.mem_write(tail, canary)
    assert compact.decode(73) == 73
    assert compact.vm.mem_read(compact.decoder + L['paused'], 1) == b'\1'
    assert compact.decode() == 500
    assert bytes(compact.vm.mem_read(tail, len(canary))) == canary
    compact.release()
    for code in (b'\x75\x02\x90\x90' * 600, b'\x90' * 499 + b'\x0f\x0b' + b'\x90' * 800):
        p = compact.setup(500, code)
        compact.vm.mem_write(tail, canary)
        assert 0 < compact.decode() <= 500
        assert bytes(compact.vm.mem_read(tail, len(canary))) == canary
        compact.release()
    # Force an already-full continuation: check precedes every decoder write,
    # including paths that bypass the loop's regular end-of-instruction test.
    compact.setup(500, b'\x90' * 2000)
    compact.writeq(compact.decoder + L['decoded'], 500)
    compact.vm.mem_write(tail, canary)
    assert compact.decode() == 500
    assert bytes(compact.vm.mem_read(tail, len(canary))) == canary
    compact.release()
    game = ROOT.parent / 'Sleeping Dogs/HKShip.exe'
    pe = pefile.PE(str(game)); image = pe.get_memory_mapped_image()
    compact.vm.mem_map(compact.code + 0x100000, ((len(image)+4095)&-4096)-0x100000)
    compact.vm.mem_write(compact.code, image)
    compact.writeq(compact.decoder + L['range_end'], compact.code+len(image))
    game_checks = []
    for pc in (compact.code + pe.OPTIONAL_HEADER.AddressOfEntryPoint, 0x549430, 0x5b2e92, 0x9b2ad0):
        compact.setup(500, pc=pc); compact.vm.mem_write(tail, canary)
        n = compact.decode(); assert 0 < n <= 500
        assert bytes(compact.vm.mem_read(tail, len(canary))) == canary
        compact.release(); game_checks.append({'pc': hex(pc), 'instructions': n})
    report = {'status': 'PASS', 'dll_sha256': sha(DLL), 'actual_decoder_limits': checks,
        'large_setup_limits': list(large), 'fastest_native_request': 65536,
        'pause_resume': True, 'multiblock_and_invalid': True, 'prewrite_capacity_guard': True,
        'buffer_tail_canaries': True, 'original_game_sha256': sha(game), 'actual_game_code': game_checks,
        'entry_bytes': L['entry_size'], 'hardware_tested': False,
        'boundaries': 'NT memory, container heap, locks, clock and config getters modeled; actual DLL x86 decoder executes'}
    write_json(ROOT / 'reports/compiler-decoder-binary-check.json', report)
    print(json.dumps(report))

if __name__ == '__main__': main()
