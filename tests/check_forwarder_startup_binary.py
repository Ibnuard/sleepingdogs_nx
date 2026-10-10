"""Execute the actual old/new ARM64 forwarders, including libnx and newlib.

Only Horizon services, memory-map syscalls and the RNG are modeled. Allocation,
reservation bookkeeping, ROMFS/NRO parsing and NRO handoff run from the linked
ELFs. This reproduces the old abort before verifying the repaired startup. It
does not substitute for a Switch boot or execute the game's NRO entrypoint.
"""
from pathlib import Path
import argparse
import io
import json
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_PROT_ALL, UC_PROT_NONE
from unicorn import arm64_const as arm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json

REG = [getattr(arm, f'UC_ARM64_REG_X{i}') for i in range(31)]
MASK = (1 << 64) - 1
ABORT_NO_ALLOC = 0x515b  # MAKERESULT(Module_HomebrewLoader, 40)
NRO_PATH = b'/switch/sleepingdogs-fex/sleepingdogs-fex.nro'


def romfs_fixture():
    """The two forwarder configuration files, with real libnx ROMFS structures."""
    files = bytearray()
    data = bytearray()
    names = (b'nextArgv', b'nextNroPath')
    for index, name in enumerate(names):
        size = (32 + len(name) + 3) & -4
        sibling = len(files) + size if index + 1 < len(names) else 0xffffffff
        record = struct.pack('<IIQQII', 0, sibling, len(data), len(NRO_PATH), 0xffffffff, len(name)) + name
        files.extend(record.ljust(size, b'\0'))
        data.extend(NRO_PATH)
    image = bytearray(0x300 + len(data))
    image[:80] = struct.pack('<10Q', 80, 0, 0, 0x80, 24, 0, 0, 0x100, len(files), 0x300)
    image[0x80:0x98] = struct.pack('<6I', 0, 0xffffffff, 0xffffffff, 0, 0xffffffff, 0)
    image[0x100:0x100 + len(files)] = files
    image[0x300:] = data
    return bytes(image)


class Forwarder:
    def __init__(self, path, nro, rng=0):
        self.vm = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.bias = 0x400000000
        elf = ELFFile(io.BytesIO(path.read_bytes()))
        self.symbols = {s.name: self.bias + s['st_value']
                        for s in elf.get_section_by_name('.symtab').iter_symbols()}
        segments = [s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        self.image_end = self.bias + max((s['p_vaddr'] + s['p_memsz'] + 4095) & -4096 for s in segments)
        self.vm.mem_map(self.bias, self.image_end - self.bias)
        for s in segments:
            self.vm.mem_write(self.bias + s['p_vaddr'], s.data())
        relr = elf.get_section_by_name('.relr.dyn')
        if relr:
            for r in relr.iter_relocations():
                at = self.bias + r['r_offset']
                self.q(at, self.uq(at) + self.bias)
        self.stack, self.tls, self.stop = 0x1800000000, 0x1900000000, 0x1a00000000
        self.heap = 0x3000000000
        self.heap_size = 0xc6000000
        self.nro = nro
        self.nro_size = struct.unpack_from('<I', nro, 0x18)[0]
        bss_size = struct.unpack_from('<I', nro, 0x38)[0]
        self.map_size = (self.nro_size + bss_size + 4095) & -4096
        for p in (self.stack, self.tls, self.stop):
            self.vm.mem_map(p, 65536)
        self.vm.mem_map(self.heap, max(self.map_size, (len(nro) + 4095) & -4096))
        self.vm.reg_write(arm.UC_ARM64_REG_TPIDRRO_EL0, self.tls)
        self.rng = [rng] if isinstance(rng, int) else list(rng)
        self.rng_calls = 0
        self.romfs = romfs_fixture()
        self.mapping = None
        self.maps, self.unmaps, self.alloc_calls, self.heap_growth = [], [], [], []
        self.abort, self.handoff, self.returned = None, None, False
        names = ('svcGetInfo', 'svcQueryMemory', '__libnx_virtmem_rng',
                 'fsOpenDataStorageByCurrentProcess', 'fsStorageRead', 'fsStorageClose',
                 'fsOpenSdCardFileSystem', 'fsFsOpenFile', 'fsFileRead', 'fsFileClose', 'fsFsClose',
                 'svcBreak', 'svcMapProcessCodeMemory', 'svcSetProcessMemoryPermission',
                 'svcUnmapProcessCodeMemory', 'svcSetThreadCoreMask', 'randomGet64',
                 'nroEntrypointTrampoline', 'diagAbortWithResult', '__libnx_alloc', '_sbrk_r')
        self.hooks = {self.symbols[n]: n for n in names if n in self.symbols}
        self.hook_id = self.vm.hook_add(UC_HOOK_CODE, self.hook)
        self.call('envSetup', 0, 42, 0)
        self.call('newlibSetup')
        self.call('hosversionSet', 0x80160500)
        self.call('__libnx_initheap')
        self.call('virtmemSetup')
        self.q(self.symbols['g_heapAddr'], self.heap)
        self.q(self.symbols['g_heapSize'], self.heap_size)
        self.vm.mem_write(self.symbols['g_procHandle'], struct.pack('<I', 43))
        self.vm.mem_write(self.symbols['g_savedTls'], bytes(self.vm.mem_read(self.tls + 0x100, 0x100)))

    def close(self):
        self.vm.hook_del(self.hook_id)
        self.vm = None

    def q(self, p, value):
        self.vm.mem_write(p, struct.pack('<Q', value))

    def uq(self, p):
        return struct.unpack('<Q', self.vm.mem_read(p, 8))[0]

    def x(self, index):
        return self.vm.reg_read(REG[index])

    def ret(self, value=0):
        self.vm.reg_write(REG[0], value & MASK)
        self.vm.reg_write(arm.UC_ARM64_REG_PC, self.x(30))

    def cstr(self, p):
        return bytes(self.vm.mem_read(p, 256)).split(b'\0', 1)[0]

    def hook(self, vm, pc, size, _):
        if pc == self.stop:
            self.returned = True
            vm.emu_stop()
            return
        n, x = self.hooks.get(pc), self.x
        if n == '__libnx_alloc':
            self.alloc_calls.append(x(0))  # Observe; execute the REAL allocator.
        elif n == '_sbrk_r':
            self.heap_growth.append(x(1))  # Observe; execute the REAL heap bounds.
        elif n == 'svcGetInfo':
            values = {0: 15, 2: 0x2000000000, 3: 0x1000000000, 4: self.heap,
                      5: 0x200000000, 6: 3285 * 1024 * 1024, 12: 0x200000,
                      13: 0x8000000000 - 0x200000, 14: self.stack, 15: 0x80000000, 28: 0}
            assert x(1) in values, ('unexpected info', x(1))
            self.q(x(0), values[x(1)])
            self.ret()
        elif n == 'svcQueryMemory':
            at = x(2)
            regions = [(self.bias, self.image_end, 3),
                       (self.stack, self.stack + 65536, 5),
                       (self.tls, self.tls + 65536, 5),
                       (self.heap, self.heap + self.heap_size, 5)]
            if self.mapping:
                regions.append((self.mapping, self.mapping + self.map_size, 8))
            base, end, kind = 0, 0x8000000000, 0
            for lo, hi, region_kind in sorted(regions):
                if lo <= at < hi:
                    base, end, kind = lo, hi, region_kind
                    break
                if hi <= at:
                    base = hi
                elif lo > at:
                    end = lo
                    break
            vm.mem_write(x(0), struct.pack('<QQIIIIII', base, end - base, kind, 0, 3 if kind else 0, 0, 0, 0))
            vm.mem_write(x(1), bytes(4))
            self.ret()
        elif n == '__libnx_virtmem_rng':
            value = self.rng[min(self.rng_calls, len(self.rng) - 1)]
            self.rng_calls += 1
            self.ret(value)
        elif n == 'fsStorageRead':
            data = self.romfs[x(1):x(1) + x(3)]
            assert len(data) == x(3)
            vm.mem_write(x(2), data)
            self.ret()
        elif n == 'fsFsOpenFile':
            assert self.cstr(x(1)) == NRO_PATH
            self.ret()
        elif n == 'fsFileRead':
            assert x(1) == 0 and x(2) == self.heap and x(3) == self.heap_size
            vm.mem_write(x(2), self.nro)
            self.q(x(5), len(self.nro))
            self.ret()
        elif n in ('fsOpenDataStorageByCurrentProcess', 'fsStorageClose', 'fsOpenSdCardFileSystem',
                   'fsFileClose', 'fsFsClose', 'svcBreak', 'svcSetThreadCoreMask'):
            self.ret()
        elif n == 'svcMapProcessCodeMemory':
            assert x(0) == 43 and x(2) == self.heap and x(3) == self.map_size
            assert 0x100000000 <= x(1) < 0x8000000000 - self.map_size
            assert not self.mapping
            self.mapping = x(1)
            self.maps.append(tuple(x(i) for i in range(4)))
            # The forwarder may not read its source heap after mapping it away.
            vm.mem_protect(self.heap, self.map_size, UC_PROT_NONE)
            self.ret()
        elif n == 'svcSetProcessMemoryPermission':
            assert x(0) == 43 and self.mapping <= x(1) < self.mapping + self.map_size
            assert x(1) + x(2) <= self.mapping + self.map_size
            self.ret()
        elif n == 'svcUnmapProcessCodeMemory':
            assert x(0) == 43 and self.mapping
            assert x(1) - self.mapping == x(2) - self.heap
            self.unmaps.append(tuple(x(i) for i in range(4)))
            vm.mem_protect(x(2), x(3), UC_PROT_ALL)
            if len(self.unmaps) % 3 == 0:
                self.mapping = None
            self.ret()
        elif n == 'randomGet64':
            self.ret(0x987654321)
        elif n == 'nroEntrypointTrampoline':
            assert x(1) == MASK and x(2) == self.mapping
            entries = {}
            p = x(0)
            for i in range(32):
                key, flags, first, second = struct.unpack('<IIQQ', vm.mem_read(p + 24 * i, 24))
                entries[key] = (flags, first, second)
                if key == 0:
                    break
            else:
                raise AssertionError('Unterminated NRO config')
            self.handoff = entries
            vm.emu_stop()
        elif n == 'diagAbortWithResult':
            self.abort = x(0)
            vm.emu_stop()

    def call(self, name, *args, handoff=False):
        self.abort, self.returned, self.handoff = None, False, None
        self.vm.reg_write(arm.UC_ARM64_REG_SP, self.stack + 0xf000)
        self.vm.reg_write(REG[30], self.stop)
        for i, value in enumerate(args):
            self.vm.reg_write(REG[i], value)
        self.vm.emu_start(self.symbols[name], 0, count=2000000)
        assert self.returned or self.abort is not None or (handoff and self.handoff), (name, hex(self.vm.reg_read(arm.UC_ARM64_REG_PC)))
        return self.x(0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old-work', type=Path, required=True)
    p.add_argument('--new-work', type=Path, required=True)
    args = p.parse_args()
    nro_path = ROOT / 'dist/low-window-fix/sleepingdogs-fex.nro'
    nro = nro_path.read_bytes()
    old_elf, new_elf = args.old_work / 'forwarder.elf', args.new_work / 'forwarder.elf'
    old = Forwarder(old_elf, nro)
    old.call('loadNro', handoff=True)
    assert old.abort == ABORT_NO_ALLOC and old.alloc_calls == [32] and not old.maps
    old.close()
    print('PASS old full loadNro reproduces allocator abort 0x515b before mapping', flush=True)
    cases = []
    for label, rng in (('low_candidate_then_high', [0, 0x100000]), ('random_high_address', 0x4000000)):
        m = Forwarder(new_elf, nro, rng)
        lo, hi = (m.uq(m.symbols[n]) for n in ('fake_heap_start', 'fake_heap_end'))
        assert hi - lo == 16384 and m.bias <= lo < hi <= m.image_end
        assert hi < m.heap
        m.call('loadNro', handoff=True)
        assert m.abort is None and m.handoff and m.alloc_calls == [32]
        assert m.rng_calls >= (2 if label == 'low_candidate_then_high' else 1)
        reservation = m.uq(m.symbols['sd_forwarder_guest_reservation'])
        assert lo <= reservation and reservation + 32 <= hi
        assert m.uq(reservation + 16) == 0x200000 and m.uq(reservation + 24) == 0x100000000
        assert m.handoff[3] == (1, m.heap + m.map_size, m.heap_size - m.map_size)
        assert m.handoff[10][1] == 43
        assert m.cstr(m.handoff[0][1]) == b'sphaira 3.0.0; sleepingdogs-gpu-budget-v1 reserve=32MiB'
        # The NRO returns with a next-load request; its old mappings are removed.
        # The reservation must stay valid in the forwarder's private BSS heap.
        m.vm.mem_write(m.symbols['g_nextArgv'], NRO_PATH + b'\0')
        m.call('loadNro', handoff=True)
        assert m.abort is None and m.handoff and len(m.maps) == 2 and len(m.unmaps) == 3
        assert m.alloc_calls == [32] and m.uq(m.symbols['sd_forwarder_guest_reservation']) == reservation
        assert m.uq(reservation + 24) == 0x100000000
        # Exhaustion must return NULL through the actual newlib allocator, not
        # abort or grow into the application heap. The reservation survives.
        assert m.call('__libnx_alloc', 32768) == 0 and m.abort is None
        assert m.uq(reservation + 16) == 0x200000
        spare = m.call('__libnx_alloc', 32)
        assert lo <= spare and spare + 32 <= hi
        m.call('__libnx_free', spare)
        assert m.uq(m.symbols['g_Reservations']) == reservation
        assert m.heap_growth
        cases.append({'mode': label, 'maps': len(m.maps), 'unmaps': len(m.unmaps),
                      'first_nro_address': hex(m.maps[0][1]), 'private_heap_bytes': hi - lo,
                      'reservation_address': hex(reservation), 'allocation_failure_and_free': 'PASS'})
        m.close()
        print(f'PASS {label}: startup, reload, real allocator bounds/free', flush=True)
    # The packed forwarder must use the same NPDM, icon, metadata and target.
    for name in ('exefs/main.npdm', 'control/control.nacp', 'control/icon_AmericanEnglish.dat',
                 'romfs/nextNroPath', 'romfs/nextArgv'):
        assert (args.old_work / name).read_bytes() == (args.new_work / name).read_bytes(), name
    fw = json.loads((ROOT / 'dist/low-window-startup-fix/forwarder/build.json').read_text())
    assert sha(new_elf) == fw['elf_sha256'] and sha(nro_path) == fw['nro_sha256']
    for name, digest in fw['source_files'].items():
        assert sha(args.new_work / 'source' / name) == digest
    nsp = ROOT / 'dist/low-window-startup-fix/forwarder' / fw['nsp']
    assert sha(nsp) == fw['sha256'] and (args.new_work / 'exefs/main').read_bytes() in nsp.read_bytes()
    write_json(ROOT / 'reports/forwarder-startup-binary.json', {
        'status': 'PASS', 'hardware_tested': False, 'scope': __doc__,
        'old_elf_sha256': sha(old_elf), 'elf_sha256': sha(new_elf),
        'nro_sha256': sha(nro_path), 'nsp_sha256': sha(nsp),
        'old_abort_result': hex(ABORT_NO_ALLOC), 'allocation_functions_emulated_from_elf': True,
        'npdm_nacp_icon_target_unchanged': True, 'cases': cases,
        'source_files': fw['source_files'], 'test_sha256': sha(Path(__file__))})


if __name__ == '__main__':
    main()
