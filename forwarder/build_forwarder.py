"""Build the pinned Sphaira HOME forwarder, using an existing local keyset."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import PES, APP_ID, TITLE, VERSION, sha, write_json
from sleepingdogs_gpu_budget import apply_forwarder
from f1_overlay import exact, replace_function
sys.path.insert(0, str(PES / 'tools'))
from nro_assets import inspect_nro

NRO_PATH = f'/switch/{APP_ID}/{APP_ID}.nro'
TITLE_ID = 0x0500000000000000 | (int.from_bytes(
    hashlib.sha256((NRO_PATH * 2).encode()).digest()[:8], 'little') & 0x00FFFFFFFFFFF000)
PACKER_REV = '745b16ecfc9ce055743067d200572204cb2aac6c'


def memory_descriptor():
    """Private FEXTendo memory ABI v1, read from ExeFS before process creation."""
    return struct.pack('<8sIIIIQ', b'FXTMEM\0\0', 1, 32, 1, 0, 0)


def packed_exefs(ncas, checks):
    """Locate the actual ExeFS directory, not a matching byte string in an NCA."""
    matches = []
    for nca in ncas.values():
        at = 0
        while True:
            at = nca.find(b'PFS0', at)
            if at < 0:
                break
            try:
                files = checks.pfs_files(nca[at:])
                if 'main.npdm' in files:
                    matches.append(files)
            except (AssertionError, ValueError, struct.error, UnicodeError):
                pass
            at += 4
    if len(matches) != 1:
        raise RuntimeError('Cannot identify the packaged ExeFS')
    return matches[0]


def run(command, **kwargs):
    subprocess.run([str(p) for p in command], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keys', type=Path, required=True)
    parser.add_argument('--nro', type=Path, required=True)
    parser.add_argument('--work', type=Path, default=Path.home() / 'sleepingdogs-gpu-forwarder-v1')
    parser.add_argument('--packer-repo', type=Path, default=Path.home() / 'sleepingdogs-forwarder-tools/hacbrewpack')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/gpu-budget-fix/forwarder')
    parser.add_argument('--low-window', action='store_true', help='39-bit NPDM for the patched AMS kernel/loader')
    parser.add_argument('--fextendo-memory-v1', action='store_true',
                        help='Opt in through ExeFS fxtmem for FEXTendo Memory v1; implies --low-window')
    args = parser.parse_args()
    if args.fextendo_memory_v1:
        args.low_window = True
    work, repo, out = args.work.resolve(), args.packer_repo.resolve(), args.output.resolve()
    if work.exists():
        raise RuntimeError('Choose a fresh forwarder work directory')
    for p in ('exefs', 'romfs', 'control'):
        (work / p).mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    if not (repo / '.git').exists():
        repo.mkdir(parents=True, exist_ok=True)
        run(['git', 'init', '-q', repo])
        run(['git', '-C', repo, 'remote', 'add', 'origin', 'https://github.com/rlaphoenix/hacBrewPack.git'])
        run(['git', '-C', repo, 'fetch', '--depth', '1', 'origin', PACKER_REV])
        run(['git', '-C', repo, 'checkout', '--detach', '-q', 'FETCH_HEAD'])
    revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != PACKER_REV:
        raise RuntimeError('Unreviewed forwarder packer revision')
    if subprocess.check_output(['git', '-C', str(repo), 'diff', 'HEAD', '--'], text=True).strip():
        raise RuntimeError('Modified forwarder packer source')
    if not (repo / 'hacbrewpack').is_file():
        shutil.copy2(repo / 'config.mk.template', repo / 'config.mk')
        run(['make', '-C', repo, 'CC=cc', '-j', '4'])

    blob = args.nro.read_bytes()
    metadata = inspect_nro(blob, expected_title=TITLE, expected_version=VERSION)
    size = struct.unpack_from('<I', blob, 0x18)[0]
    icon_off, icon_len, nacp_off, nacp_len = struct.unpack_from('<4Q', blob, size + 8)
    icon = blob[size + icon_off:size + icon_off + icon_len]
    nacp = bytearray(blob[size + nacp_off:size + nacp_off + nacp_len])
    nacp[0x3025:0x3028] = bytes((0, 0, 1))
    nacp[0x30f1:0x30f4] = bytes(3)
    for offset in (0x3080, 0x3088, 0x3090, 0x3098, 0x3148, 0x3150, 0x3158, 0x3160):
        struct.pack_into('<Q', nacp, offset, 0)
    (work / 'control/icon_AmericanEnglish.dat').write_bytes(icon)
    (work / 'control/control.nacp').write_bytes(nacp)
    for name in ('nextNroPath', 'nextArgv'):
        (work / 'romfs' / name).write_text(NRO_PATH)
    hbl = ROOT / 'forwarder/hbl'
    # Confirm the vendored loader matches the approved PES source snapshot.
    original = PES / 'local/production-input-fix/approved/source/forwarder/hbl/source'
    for p in (hbl / 'source').iterdir():
        if sha(p) != sha(original / p.name):
            raise RuntimeError(f'Changed pinned loader source: {p.name}')
    patched = work / 'source'
    if patched.exists():
        raise RuntimeError('Choose a fresh forwarder work directory')
    shutil.copytree(hbl / 'source', patched)
    apply_forwarder(patched)
    if args.low_window:
        p = patched / 'main.c'
        text = p.read_text()
        text = exact(text, '#include "sd_gpu_budget.h"', '#include "sd_gpu_budget.h"\n#include "sd_forwarder_low.inc"')
        text = exact(text, '    void* map_addr = virtmemFindCodeMemory(total_size, 0);',
            '    void* map_addr = sd_forwarder_find_native(total_size);')
        text = replace_function(text, 'void __libnx_initheap(void)',
            '#include "sd_forwarder_heap.inc"')
        text = exact(text, '''// stub alloc calls as they're not used (saves 4KiB).
void* __libnx_alloc(size_t size) {
    diagAbortWithResult(MAKERESULT(Module_HomebrewLoader, 40));
}

void* __libnx_aligned_alloc(size_t alignment, size_t size) {
    diagAbortWithResult(MAKERESULT(Module_HomebrewLoader, 41));
}

void __libnx_free(void* p) {
    diagAbortWithResult(MAKERESULT(Module_HomebrewLoader, 43));
}''', '''// Use libnx's normal allocation functions with our private BSS heap.
// The guest-window reservation must never live in g_heapAddr (the NRO heap).''')
        p.write_text(text)
        for name in ('sd_forwarder_low.inc', 'sd_forwarder_heap.inc'):
            shutil.copy2(ROOT / 'src/low_window' / name, patched / name)
    config = json.loads((hbl / 'base.json').read_text())
    config.update(name='SleepingDogs', address_space_type=3 if args.low_window else 2, title_id=hex(TITLE_ID),
                  title_id_range_min=hex(TITLE_ID), title_id_range_max=hex(TITLE_ID))
    if args.low_window:
        config['system_resource_size'] = '0x1000000'
    write_json(work / 'forwarder.json', config)
    sdk = Path('/opt/devkitpro')
    env = dict(os.environ, DEVKITPRO=str(sdk))
    cc = sdk / 'devkitA64/bin/aarch64-none-elf-gcc'
    common = ['-O2', '-march=armv8-a+crc', '-mtune=cortex-a57', '-ffixed-x18', '-fPIE',
              '-ffunction-sections', '-fdata-sections', '-D__SWITCH__',
              '-DVERSION="3.0.0"', '-isystem', sdk / 'libnx/include']
    objects = []
    for name in ('main.c', 'trampoline.s'):
        obj = work / (name + '.o')
        run([cc, *common, '-c', patched / name, '-o', obj], env=env)
        objects.append(obj)
    run([cc, *common, '-specs=' + str(sdk / 'libnx/switch.specs'), '-Wl,-wrap,exit',
         *objects, '-L' + str(sdk / 'libnx/lib'), '-lnx', '-o', work / 'forwarder.elf'], env=env)
    run([sdk / 'tools/bin/elf2nso', work / 'forwarder.elf', work / 'exefs/main'])
    run([sdk / 'tools/bin/npdmtool', work / 'forwarder.json', work / 'exefs/main.npdm'])
    if args.fextendo_memory_v1:
        (work / 'exefs/fxtmem').write_bytes(memory_descriptor())
    spec = importlib.util.spec_from_file_location('base_forwarder', PES / 'tools/build-fextendo-forwarder.py')
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    checks.TITLE_ID = TITLE_ID
    npdm = (work / 'exefs/main.npdm').read_bytes()
    if args.low_window:
        assert (npdm[12] >> 1) & 7 == 3, 'Expected real 39-bit NPDM'
        assert struct.unpack_from('<I', npdm, 0x14)[0] == 16 * 1024 * 1024
        # The inherited decoder fixes the old AS mode but checks the complete
        # capability tables. Check the real mode above, normalize only that
        # field for the existing table checker; packaged NPDM stays unchanged.
        normalized = bytearray(npdm)
        normalized[12] = (normalized[12] & ~14) | 4
        capabilities = checks.check_npdm(normalized)
    else:
        capabilities = checks.check_npdm(npdm)

    # Read only for local packaging; neither keys nor packer stdout enter output.
    selected = {}
    for line in args.keys.read_text().splitlines():
        key, separator, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if separator and key in ('header_key', 'key_area_key_application_00'):
            length = 64 if key == 'header_key' else 32
            if not re.fullmatch('[0-9a-fA-F]{' + str(length) + '}', value):
                raise RuntimeError('Invalid required packing key')
            selected[key] = value
    if len(selected) != 2:
        raise RuntimeError('Keyset lacks required local packing keys')
    with tempfile.TemporaryDirectory(prefix='sleepingdogs-pack-') as temporary:
        keyfile = Path(temporary) / 'keys.dat'
        keyfile.write_text(''.join(f'{k} = {v}\n' for k, v in selected.items()))
        keyfile.chmod(0o600)
        packed = subprocess.run([str(repo / 'hacbrewpack'), '--keyset', str(keyfile),
            '--titleid', f'{TITLE_ID:016x}', '--nologo', '--nopatchnacplogo', '--plaintext', '--keepncadir'],
            cwd=work, capture_output=True, text=True)
        if packed.returncode:
            raise RuntimeError(f'Forwarder packer failed with status {packed.returncode}; output suppressed to protect keys')
    payload = (work / 'hacbrewpack_nsp' / f'{TITLE_ID:016x}.nsp').read_bytes()
    entries = checks.pfs_files(payload)
    if len(entries) != 3:
        raise RuntimeError('Unexpected NSP layout')
    for name, content in entries.items():
        if hashlib.sha256(content).hexdigest()[:32] != name.split('.')[0]:
            raise RuntimeError('Invalid NCA content ID')
    exefs = packed_exefs(entries, checks)
    expected_exefs = {'main', 'main.npdm'} | ({'fxtmem'} if args.fextendo_memory_v1 else set())
    assert set(exefs) == expected_exefs, 'Unexpected ExeFS entries'
    for name in expected_exefs:
        assert exefs[name] == (work / 'exefs' / name).read_bytes(), name
    if args.fextendo_memory_v1:
        assert exefs['fxtmem'] == memory_descriptor()
    # --plaintext leaves payload sections readable. Verify actual packed bytes,
    # including the NPDM and icon, rather than trusting only staging files.
    for part in ('exefs/main', 'exefs/main.npdm', 'control/control.nacp', 'control/icon_AmericanEnglish.dat', 'romfs/nextNroPath'):
        if not any((work / part).read_bytes() in nca for nca in entries.values()):
            raise RuntimeError(f'Packed NSP does not contain the expected {part}')
    destination = out / ('FEXTendo-SleepingDogs-39bit-FEXTendoMemory-v1.nsp' if args.fextendo_memory_v1 else
                         'FEXTendo-SleepingDogs-39bit-LowWindow-StartupFix.nsp' if args.low_window else
                         'FEXTendo-SleepingDogs-32bit.nsp')
    destination.write_bytes(payload)
    shutil.copy2(work / 'forwarder.json', out / 'forwarder.json')
    shutil.copytree(ROOT / 'forwarder/licenses', out / 'licenses', dirs_exist_ok=True)
    report = {'nsp': destination.name, 'sha256': sha(destination), 'bytes': len(payload),
              'title': metadata['title'], 'version': metadata['version'],
              'title_id': f'{TITLE_ID:016x}', 'target': 'sdmc:' + NRO_PATH,
              'address_space': '39-bit low-window' if args.low_window else '32-bit no-alias', 'capabilities': capabilities,
              'system_resource_bytes': 16 * 1024 * 1024 if args.low_window else 0,
              'native_nro_above_4g': args.low_window,
              'private_bookkeeping_heap_bytes': 16 * 1024 if args.low_window else 0,
              'low_window_overlay': 'sleepingdogs-forwarder-startup-v2' if args.low_window else None,
              'nro_sha256': sha(args.nro), 'packer_commit': PACKER_REV,
              'loader_commit': '72a94b905816de24817594109fb012a8f7107d8c',
              'loader_overlay': 'sleepingdogs-gpu-budget-v1',
              'full_application_reserve_bytes': 33554432,
              'previous_reserve_bytes': 100663296,
              'additional_heap_bytes': 67108864,
              'source_files': {p.name: sha(p) for p in sorted(patched.iterdir()) if p.is_file()},
              'elf_sha256': sha(work / 'forwarder.elf'),
              'nso_sha256': sha(work / 'exefs/main'),
              'memory_abi': 'fxtmem-v1' if args.fextendo_memory_v1 else None,
              'descriptor_sha256': hashlib.sha256(exefs['fxtmem']).hexdigest() if args.fextendo_memory_v1 else None,
              'exefs_files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(exefs.items())},
              'packed_exefs_verified': True,
              'builder_sha256': sha(Path(__file__)),
              'packed_payload_verified': True, 'hardware_tested': False}
    write_json(out / 'build.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
