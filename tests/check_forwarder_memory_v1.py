"""Validate the packed opt-in NSP and execute its forwarder with the v5 NRO.

The generic loader's contract is checked against the hardware-tested probe
NSPs. Horizon services are modeled by the existing ARM64 forwarder harness;
this does not boot the console or execute Sleeping Dogs gameplay.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from check_forwarder_startup_binary import Forwarder, NRO_PATH, ROOT
from port_common import PES, sha, write_json

OLD_NSP_SHA = '04607905b44c42e9a4825d255f745690b647d7d78b7ebe815a6c6b4c175ae929'
OLD_ELF_SHA = '569334bc424c07009b04b592bd31a61a90c9af1281c7bdea698c92b3cb760a1d'
NRO_SHA = '2ddb568038ec028f909070bee54abc50678a8fe7f77d330ec93cf9f7688dc146'
DESCRIPTOR_SHA = '6a4b404254f26c3b77a738213105989f38798b8abb231e97c1bcd7931f58fb8f'
PROBES = {
    'control': '756ad5e21fc02412a7e6155d454f9035be533605967ff7456c208e5f0a557d3f',
    'optin-a': 'ce9d58a38b8cffe0dbb3b1ea297d7b6043af66738a23332e4945179c3e63348e',
    'optin-b': '5b97337f2755e089a286ae10ddb41cbb3baab28f93307f926f0897b74da4c328',
}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--previous-work', type=Path, required=True)
    args = parser.parse_args()
    package = ROOT/'dist/sleepingdogs-fex-fextendo-memory-v1'
    fw = json.loads((package/'forwarder/build.json').read_text())
    assert fw['memory_abi'] == 'fxtmem-v1' and fw['title_id'] == '059a3db219b42000'
    assert fw['packed_exefs_verified'] and fw['builder_sha256'] == sha(ROOT/'forwarder/build_forwarder.py')
    assert fw['target'] == 'sdmc:'+NRO_PATH.decode()
    assert fw['elf_sha256'] == sha(args.work/'forwarder.elf') == OLD_ELF_SHA
    old = json.loads((ROOT/'reports/forwarder-startup-binary.json').read_text())
    assert fw['source_files'] == old['source_files']
    for name, digest in fw['source_files'].items():
        assert sha(args.work/'source'/name) == digest, name
    builder = module('sd_forwarder_builder', ROOT/'forwarder/build_forwarder.py')
    checks = module('nsp_checks', PES/'tools/build-fextendo-forwarder.py')
    npdm_checks = module('npdm_checks', PES/'tools/build-as39-probe.py')
    nsp = package/'forwarder'/fw['nsp']
    assert sha(nsp) == fw['sha256']
    ncas = checks.pfs_files(nsp.read_bytes())
    assert len(ncas) == 3
    for name, content in ncas.items():
        assert hashlib.sha256(content).hexdigest()[:32] == name.split('.')[0]
    exefs = builder.packed_exefs(ncas, checks)
    assert set(exefs) == {'main', 'main.npdm', 'fxtmem'}
    assert hashlib.sha256(exefs['main']).hexdigest() == fw['nso_sha256']
    assert exefs['fxtmem'] == builder.memory_descriptor()
    assert hashlib.sha256(exefs['fxtmem']).hexdigest() == fw['descriptor_sha256'] == DESCRIPTOR_SHA
    previous_nsp = args.previous_work/'hacbrewpack_nsp/059a3db219b42000.nsp'
    assert sha(previous_nsp) == OLD_NSP_SHA
    previous_exefs = builder.packed_exefs(checks.pfs_files(previous_nsp.read_bytes()), checks)
    assert set(previous_exefs) == {'main', 'main.npdm'}
    assert all(exefs[name] == data for name, data in previous_exefs.items())
    for name in ('control/control.nacp', 'control/icon_AmericanEnglish.dat',
                 'romfs/nextNroPath', 'romfs/nextArgv'):
        data = (args.work/name).read_bytes()
        assert data == (args.previous_work/name).read_bytes(), name
        assert any(data in nca for nca in ncas.values()), name
    print('PASS packed ExeFS adds only fxtmem; NSO, NPDM, identity, assets and target preserved', flush=True)

    npdm = exefs['main.npdm']
    parsed = npdm_checks.check_npdm(npdm, 39, 0x059a3db219b42000)
    assert (npdm[12] & 15) == 7 and not (npdm[12] & 0x20)  # no alias extra-size
    assert struct.unpack_from('<I', npdm, 0x14)[0] == 16*1024*1024
    aci, acid = struct.unpack_from('<I4xI', npdm, 0x70)
    assert (struct.unpack_from('<I', npdm, acid+0x20c)[0] >> 2) & 15 == 0  # application pool
    for offset, field in ((aci, 0x30), (acid, 0x230)):
        start, size = struct.unpack_from('<II', npdm, offset+field)
        caps = [c[0] for c in struct.iter_unpack('<I', npdm[offset+start:offset+start+size])]
        assert [c for c in caps if c & 0x3fff == 0x1fff] == [0x5fff]  # application type
    print('PASS actual NPDM: ARM64, 39-bit, application type/pool, 16 MiB resources, required SVCs', flush=True)
    for tag, digest in PROBES.items():
        probe = PES/'dist/fextendo-low-window-v1/forwarders'/f'FEXTendo-Memory-{tag}.nsp'
        assert sha(probe) == digest
        content = builder.packed_exefs(checks.pfs_files(probe.read_bytes()), checks)
        if tag == 'control':
            assert 'fxtmem' not in content
        else:
            assert content['fxtmem'] == exefs['fxtmem']
    print('PASS descriptor byte-identical to accepted OPTIN-A/B; absent from CONTROL and old Sleeping Dogs NSP', flush=True)

    nro_path = ROOT/'dist/low-window-sync-startup-fix/sleepingdogs-fex.nro'
    assert sha(nro_path) == fw['nro_sha256'] == NRO_SHA
    nro = nro_path.read_bytes()
    cases = []
    for label, rng in (('low_candidate_then_high', [0, 0x100000]), ('random_high_address', 0x4000000)):
        m = Forwarder(args.work/'forwarder.elf', nro, rng)
        lo, hi = (m.uq(m.symbols[n]) for n in ('fake_heap_start', 'fake_heap_end'))
        assert hi-lo == 16384 and m.bias <= lo < hi <= m.image_end
        m.call('loadNro', handoff=True)
        assert m.abort is None and m.handoff and m.alloc_calls == [32]
        reservation = m.uq(m.symbols['sd_forwarder_guest_reservation'])
        assert lo <= reservation < hi and m.uq(reservation+16) == 0x200000
        assert m.uq(reservation+24) == 0x100000000
        assert m.maps[0][1] >= 0x100000000
        assert m.handoff[3] == (1, m.heap+m.map_size, m.heap_size-m.map_size)
        assert m.cstr(m.handoff[0][1]) == b'sphaira 3.0.0; sleepingdogs-gpu-budget-v1 reserve=32MiB'
        m.vm.mem_write(m.symbols['g_nextArgv'], NRO_PATH+b'\0')
        m.call('loadNro', handoff=True)
        assert m.abort is None and m.handoff and len(m.maps) == 2 and len(m.unmaps) == 3
        assert m.uq(m.symbols['sd_forwarder_guest_reservation']) == reservation and m.alloc_calls == [32]
        assert m.call('__libnx_alloc', 32768) == 0 and m.abort is None
        spare = m.call('__libnx_alloc', 32)
        assert lo <= spare < hi
        m.call('__libnx_free', spare)
        assert m.uq(m.symbols['g_Reservations']) == reservation
        cases.append(dict(case=label, native_nro=hex(m.maps[0][1]), reload=True, private_heap_bytes=hi-lo))
        m.close()
        print('PASS linked ARM64 forwarder + v5 NRO: '+label+', reload and allocator bounds', flush=True)
    write_json(ROOT/'reports/forwarder-memory-v1.json', {
        'status': 'PASS', 'scope': __doc__, 'hardware_tested': False,
        'nsp_sha256': fw['sha256'], 'elf_sha256': fw['elf_sha256'], 'nro_sha256': NRO_SHA,
        'descriptor_sha256': DESCRIPTOR_SHA, 'abi': 'fxtmem-v1',
        'previous_nsp_sha256': OLD_NSP_SHA, 'exefs_added_only': ['fxtmem'],
        'forwarder_code_unchanged': True, 'npdm_assets_target_unchanged': True,
        'npdm': parsed, 'generic_probe_nsp_hashes': PROBES, 'arm64_cases': cases,
        'source_files': fw['source_files'], 'test_sha256': sha(Path(__file__)),
        'harness_sha256': sha(ROOT/'tests/check_forwarder_startup_binary.py'),
        'builder_sha256': sha(ROOT/'forwarder/build_forwarder.py')})


if __name__ == '__main__':
    main()
