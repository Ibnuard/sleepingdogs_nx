"""Package the tested FEX #DB fix cumulatively, without game data or stale logs."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile

from port_common import ROOT, APPROVED, sha, write_json

PREFIX = 'switch/sleepingdogs-fex/'
FIX = 'source/fex-debug-fix/'

def encoded(value): return (json.dumps(value, indent=2) + '\n').encode()

def archive(path, entries):
    sums = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(entries.items())}
    entries = dict(entries)
    entries['SHA256SUMS.txt'] = ''.join(f'{digest}  {name}\n' for name, digest in sums.items()).encode()
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist())) == len(entries)
        for name, digest in sums.items(): assert hashlib.sha256(z.read(name)).hexdigest() == digest
    return {'zip': path.name, 'sha256': sha(path), 'bytes': path.stat().st_size,
            'files': len(entries), 'payload_sha256': sums}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-fex-debug-v1'))
    a = p.parse_args()
    build = ROOT / 'dist/fex-debug-fix'
    receipt = json.loads((build / 'build.json').read_text())
    dll = build / 'libwow64fex.dll'
    digest = sha(dll)
    assert digest == receipt['dll_sha256']
    binary = json.loads((ROOT / 'reports/fex-debug-binary-check.json').read_text())
    assert binary['dll_sha256'] == digest and binary['actual_dll_emitter_cases'] == 67
    assert binary['imports_unchanged'] and binary['exports_unchanged'] and binary['eager_spare_is_ret']
    assert json.loads((ROOT / 'reports/fex-debug-arm64-check.json').read_text())['passed'] == 185
    assert json.loads((ROOT / 'reports/game-debug-exception-check.json').read_text())['passed'] == 8
    inputs = receipt['inputs']
    assert sha(ROOT / 'tools/sleepingdogs_fex_debug.py') == inputs['patch']
    for name, expected in inputs['new_sources'].items(): assert sha(ROOT / 'src' / name) == expected
    for name, expected in receipt['source_changes'].items(): assert sha(a.work / 'source' / name) == expected
    for name, expected in receipt['adapter_files'].items(): assert sha(a.work / 'adapter' / name) == expected
    # Host bridge ABI bytes are identical to the approved source.
    assert receipt['adapter_files']['horizon_host.h'] == inputs['approved']['src/fex/horizon_host.h']

    prior = ROOT / 'dist/sleepingdogs-fex-first-fault-trace.zip'
    assert sha(prior) == 'cd67712e08ae212e6d0274884ca67fd7f04037d197388ed72af429edfe6a7a73'
    with zipfile.ZipFile(prior) as z:
        entries = {n: z.read(n) for n in z.namelist() if n not in ('README.txt', 'SHA256SUMS.txt')}
    previous = dict(entries)
    entries[PREFIX + 'drive_c/windows/system32/libwow64fex.dll'] = dll.read_bytes()
    policy = {'method': 'Pinned FEX source rebuild with per-thread x86 execution breakpoints',
              'sha256': digest, 'previous_sha256': receipt['base_dll_sha256'],
              'initial_jit_cache_bytes': 134217728, 'eager_spare_disabled': True,
              'profile': 'fastest', 'hardware_tested': False, 'debug_register_build': receipt}
    entries[PREFIX + 'launcher/fex-memory-policy.json'] = encoded(policy)
    entries[PREFIX + 'launcher/fex-debug-fix.json'] = encoded(receipt)
    entries['README.txt'] = '''Sleeping Dogs FEXTendo - x86 execution-breakpoint fix v1

1. Tutup Sleeping Dogs/FEXTendo sepenuhnya dari HOME.
2. Ekstrak ZIP, lalu salin folder switch ke root SD dan timpa file lama.
3. Buka dengan forwarder Sleeping Dogs 32-bit yang sama; tidak perlu install ulang NSP.
4. Pilih Launch Debug. Log harus memuat:
   [SD-DB] execution-breakpoints v1 DR0-DR3 per-thread
   [SD-DB] arm ...
   [SD-DB] hit ...
5. Jika masih gagal, ambil fex-runtime.log dan crash.log terbaru dari
   switch/sleepingdogs-fex/ setelah percobaan tersebut.

Patch kumulatif: FEX baru + NRO diagnostik/memori + WoW64 self-context + renderer.
Fastest tetap aktif. Save/config pengguna dan file game tidak disertakan.
Paket runtime/ready tetap diperlukan sebagai basis; timpa patch ini paling akhir.
Jangan hanya menyalin NRO: perbaikan baru ada di drive_c/windows/system32/libwow64fex.dll.

Log sebelumnya menunjukkan breakpoint x86 dilewati, lalu kode startup menghapus
stack dan handler SEH. FEX kini mengirim #DB ke handler asli game sebelum instruksi.
Pengujian host dan emulasi DLL ARM64 lolos; boot/gameplay di Switch belum dikonfirmasi.
Penanda SD-FIRSTFAULT pertama bisa merekam exception breakpoint yang normal;
gunakan penanda SD-DB dan akhir log untuk menilai percobaan ini.

Rollback DLL: timpa switch/ dari sleepingdogs-fex-debug-register-rollback.zip.
Detail sumber dan pengujian: source/fex-debug-fix/docs/debug-register-fix.md.
'''.encode()
    for relative in ('tools/build_fex_debug.py', 'tools/sleepingdogs_fex_debug.py',
                     'tools/package_fex_debug.py', 'tools/port_common.py',
                     'src/sd_fex_debug.h', 'src/sd_fex_debug_emit.inc', 'src/sd_fex_debug_module.inc',
                     'tests/build_fex_debug_check.py', 'tests/fex_debug_emitter.cpp', 'tests/fex_debug_layout.cpp',
                     'tests/check_fex_debug_arm64.py', 'tests/check_fex_debug_binary.py',
                     'tests/check_wow64_context_binary.py', 'tests/check_game_debug_exception.py',
                     'docs/debug-register-fix.md', 'reports/fex-debug-arm64-check.json',
                     'reports/fex-debug-binary-check.json', 'reports/game-debug-exception-check.json'):
        entries[FIX + relative] = (ROOT / relative).read_bytes()
    entries[FIX + 'build.json'] = encoded(receipt)
    entries[FIX + 'prepared.json'] = (a.work / 'prepared.json').read_bytes()
    # Every approved FEX overlay plus the final changed source and all adapter files.
    names = set(receipt['source_changes'])
    names.update(n[len('generated/fex/'):] for n in inputs['approved'] if n.startswith('generated/fex/'))
    for name in sorted(names): entries[FIX + 'generated/fex/' + name] = (a.work / 'source' / name).read_bytes()
    for name in receipt['adapter_files']: entries[FIX + 'adapter/' + name] = (a.work / 'adapter' / name).read_bytes()
    licenses = APPROVED / 'licenses/FEX'
    for path in sorted(licenses.rglob('*')):
        if path.is_file(): entries[FIX + 'licenses/FEX/' + path.relative_to(licenses).as_posix()] = path.read_bytes()
    assert FIX + 'licenses/FEX/LICENSE' in entries
    for name, data in previous.items(): assert entries[name] == data, name
    for name in entries:
        assert not name.lower().endswith(('.log', '.keys', '.nsp', '.exe'))
        assert '/drive_c/SleepingDogs/' not in name
    nro_hash = hashlib.sha256(entries[PREFIX + 'sleepingdogs-fex.nro']).hexdigest()
    assert nro_hash == '5caf68ad45598cc1a3d461eeeec1f043f5c62d9a8da1e43ae4b91d232d68843f'
    output = ROOT / 'dist/sleepingdogs-fex-debug-register-fix.zip'
    report = archive(output, entries)
    old = ROOT / 'vendor/fex/libwow64fex-f1-demand.dll'
    assert sha(old) == receipt['base_dll_sha256']
    rollback = {PREFIX + 'drive_c/windows/system32/libwow64fex.dll': old.read_bytes(),
                PREFIX + 'launcher/fex-memory-policy.json': (ROOT / 'vendor/fex/libwow64fex-f1-demand.json').read_bytes(),
                PREFIX + 'launcher/fex-debug-fix.json': encoded({'rolled_back': True, 'dll_sha256': sha(old)}),
                'README.txt': b'Close FEXTendo from HOME, then overwrite the switch folder on SD. Restores the previous FEX DLL; other fixes remain.\n'}
    report['rollback'] = archive(ROOT / 'dist/sleepingdogs-fex-debug-register-rollback.zip', rollback)
    # Stage the tested DLL for subsequent normal builds without replacing the old fallback.
    shutil.copy2(dll, ROOT / 'vendor/fex/libwow64fex-sd-debug.dll')
    write_json(ROOT / 'vendor/fex/libwow64fex-sd-debug.json', policy)
    report.update({'nro_unchanged_from_diagnostic': nro_hash, 'dll_sha256': digest,
                   'previous_patch_members_preserved': len(previous), 'game_boot_confirmed': False})
    write_json(ROOT / 'reports/fex-debug-package.json', report)
    print(json.dumps({k: report[k] for k in ('zip', 'sha256', 'bytes', 'files', 'dll_sha256')}))

if __name__ == '__main__': main()
