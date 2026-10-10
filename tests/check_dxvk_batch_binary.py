"""Execute the shipped PE32 flush tracker, including the disabled fallback."""
from pathlib import Path
import json
import struct
import sys
import tarfile
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_ESP
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from port_common import sha, write_json
from check_wow64_context_binary import symbols


class Replay:
    def __init__(self, data, candidate):
        self.pe = pefile.PE(data=data)
        self.syms = symbols(self.pe)
        self.vm = Uc(UC_ARCH_X86, UC_MODE_32)
        base = self.pe.OPTIONAL_HEADER.ImageBase
        self.vm.mem_map(base, (self.pe.OPTIONAL_HEADER.SizeOfImage+4095)&-4096)
        self.vm.mem_write(base, self.pe.get_memory_mapped_image())
        self.vm.mem_map(0x20000000, 0x20000)
        self.obj, self.sp, self.stop = 0x20000000, 0x20010000, 0x2001f000
        self.candidate = candidate

    def symbol(self, fragment):
        hits = {v for n,v in self.syms.items() if fragment in n and n.startswith('__ZN')}
        assert len(hits) == 1, (fragment, hits)
        return hits.pop()

    def call(self, fragment, arguments):
        address = self.symbol(fragment)
        self.vm.mem_write(self.sp, struct.pack('<I', self.stop)+arguments)
        self.vm.reg_write(UC_X86_REG_ESP, self.sp)
        self.vm.reg_write(UC_X86_REG_ECX, self.obj)
        self.vm.emu_start(address, self.stop, count=10000)
        assert self.vm.reg_read(UC_X86_REG_ESP) == self.sp+4+len(arguments)
        return self.vm.reg_read(UC_X86_REG_EAX)&255

    def init(self, enabled, maximum=3):
        self.vm.mem_write(self.obj, bytes(256))
        self.call('GpuFlushTrackerC2', struct.pack('<II', maximum, enabled)
                  if self.candidate else struct.pack('<I', maximum))

    def notify(self, chunk, submitted):
        self.call('GpuFlushTracker11notifyFlush', struct.pack('<QQ', chunk, submitted))

    def consider(self, kind, chunk, completed, cost):
        return self.call('GpuFlushTracker13considerFlush', struct.pack('<IQIQ', kind, chunk, completed, cost))


def main():
    receipt = json.loads((ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.json').read_text())
    archive = ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.tar.gz'
    assert sha(archive) == receipt['archive_sha256']
    with tarfile.open(archive) as tar:
        old_data = tar.extractfile('dxvk-3.1.1-sdrecycle1/x32/d3d11.dll').read()
    import hashlib
    assert hashlib.sha256(old_data).hexdigest() == receipt['files']['d3d11.dll']['sha256']
    dll = ROOT/'dist/dxvk-batch/x32/d3d11.dll'
    new_data = dll.read_bytes()
    build = json.loads((ROOT/'dist/dxvk-batch/build.json').read_text())
    assert sha(dll) == build['files']['d3d11.dll']['sha256']
    original, off, on = Replay(old_data, False), Replay(new_data, True), Replay(new_data, True)
    cases = 0
    for maximum in range(4):
        for kind in range(4):
            for pending in (0, 1, 2, 4, 9):
                for chunks in (0, 1, 3, 6, 11, 12, 19, 20, 40):
                    for cost in (0, 1499, 1500):
                        original.init(False, maximum); off.init(False, maximum); on.init(True, maximum)
                        for replay in (original, off, on): replay.notify(100, 30)
                        a = original.consider(kind, 100+chunks, 30-pending, cost)
                        b = off.consider(kind, 100+chunks, 30-pending, cost)
                        c = on.consider(kind, 100+chunks, 30-pending, cost)
                        assert a == b, (maximum, kind, pending, chunks, cost, a, b)
                        assert not c or a
                        if kind < 2 or pending < 2 or chunks >= 12 or cost >= 1500 or kind > maximum:
                            assert a == c
                        cases += 1
    on.init(True); on.notify(20, 10)
    assert on.consider(2, 23, 8, 10) == 0
    assert on.consider(1, 23, 8, 10) == 0
    assert on.consider(1, 23, 9, 10) == 1
    on.notify(23, 11)
    assert on.consider(0, 24, 9, 10) == 1
    write_json(ROOT/'reports/dxvk-batch-binary.json', dict(status='PASS', cases=cases,
        readback_progress=True, explicit_flush_preserved=True, disabled_matches_shipped_baseline=True,
        dll_sha256=sha(dll), baseline_dll_sha256=hashlib.sha256(old_data).hexdigest(),
        execution='Unicorn x86 PE32, actual shipping functions; no function-boundary mocks',
        hardware_tested=False, sources={n:sha(ROOT/n) for n in
            ('tests/check_dxvk_batch_binary.py','tests/check_wow64_context_binary.py')}))
    print('PASS shipping PE32 tracker cases=', cases, flush=True)


if __name__ == '__main__': main()
