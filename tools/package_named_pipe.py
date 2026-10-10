"""Explicit cumulative update list; user logs/extracted game files never enter the ZIP."""
from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import zipfile

from port_common import ROOT, sha, write_json
from sleepingdogs_named_pipe import apply as apply_pipes
from sleepingdogs_fault_trace import apply as apply_faults

PREFIX = 'switch/sleepingdogs-fex/'
SOURCE = 'source/named-pipe-fix/'


def encode(data): return (json.dumps(data, indent=2) + '\n').encode()


def archive(path, entries):
    entries = dict(entries)
    entries['SHA256SUMS.txt'] = ''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n'
                                       for name, data in sorted(entries.items())).encode()
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, data in sorted(entries.items()): z.writestr(name, data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest, name = line.split('  ', 1); assert hashlib.sha256(z.read(name)).hexdigest() == digest
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path), 'files': len(entries)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--memory-work', type=Path, required=True)
    a = p.parse_args()
    build = ROOT / 'dist/named-pipe-fix'
    receipt = json.loads((build / 'build.json').read_text())
    source = a.work / 'native-source'; memory = a.memory_work / 'native-source'
    tests = json.loads((ROOT / 'reports/named-pipe-check.json').read_text())
    assert tests['passed_groups'] == 13 and tests['objects_remaining'] == 0
    for n, digest in tests['sources'].items(): assert sha(ROOT / n) == digest, n
    assert json.loads((ROOT / 'reports/game-pipe-call-check.json').read_text())['passed'] == 4
    for n, digest in receipt['source_files'].items(): assert sha(source / n) == digest, n
    nro = build / 'sleepingdogs-fex.nro'; assert sha(nro) == receipt['nro_sha256']
    # Reconstruct from the previous memory build, before diagnostics, so overlay
    # order is identical to the new isolated build. Check the actual compiled C.
    seed = ('dlls/ntdll/unix/horizon.c', 'dlls/ntdll/unix/file.c',
            'dlls/ntdll/unix/signal_arm64.c', 'wine-nx-probe/source/runtime.c', 'wine-nx-probe/source/f1_crash.c')
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp)
        for n in seed:
            target = expected / n; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((memory / n).read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
        apply_pipes(expected); apply_faults(expected)
        for n in receipt['source_files']:
            assert (expected / n).read_text(encoding='utf-8') == (source / n).read_text(encoding='utf-8'), n
    memory_files = ('dlls/ntdll/unix/virtual.c', 'dlls/ntdll/unix/sd_guest_view.inc',
                    'dlls/ntdll/unix/sd_guest_arena.h', 'wine-nx-probe/source/sd_guest_arena.c',
                    'wine-nx-probe/source/sd_guest_arena.h', 'wine-nx-probe/source/f1_gpu_arena.h')
    for n in memory_files: assert sha(source / n) == sha(memory / n), n
    receipt['final_host_tests'] = tests
    receipt['compiled_overlay_reconstructed'] = True
    receipt['memory_sources_unchanged'] = {n: sha(source / n) for n in memory_files}
    write_json(build / 'build.json', receipt)
    previous_path = ROOT / 'dist/sleepingdogs-fex-debug-register-fix.zip'
    assert sha(previous_path) == 'd9b7e66c6fc8b9c488c0b0e7443d903eafea01d46a265ab132bc82edd7fe3cbd'
    with zipfile.ZipFile(previous_path) as z:
        previous = {n: z.read(n) for n in z.namelist() if n not in ('README.txt', 'SHA256SUMS.txt')}
    entries = dict(previous)
    entries[PREFIX + nro.name] = nro.read_bytes()
    arena = json.loads(entries[PREFIX + 'launcher/direct-arena-fix.json'])
    arena['nro_sha256'] = receipt['nro_sha256']; arena['additional_overlay'] = 'launcher/named-pipe-fix.json'
    entries[PREFIX + 'launcher/direct-arena-fix.json'] = encode(arena)
    trace = json.loads(entries[PREFIX + 'launcher/first-fault-trace.json'])
    trace['nro_sha256'] = receipt['nro_sha256']; trace['additional_overlay'] = 'launcher/named-pipe-fix.json'
    entries[PREFIX + 'launcher/first-fault-trace.json'] = encode(trace)
    entries[PREFIX + 'launcher/named-pipe-fix.json'] = encode({n: receipt[n] for n in
        ('build', 'kind', 'nro_sha256', 'base_nro_sha256', 'hardware_tested', 'game_boot_confirmed',
         'fex_dll_sha256', 'fex_profile', 'unsupported', 'memory_fix_preserved', 'game_exe_or_dll_modified')})
    entries['README.txt'] = '''Sleeping Dogs FEXTendo - local named-pipe compatibility v1

1. Tutup Sleeping Dogs/FEXTendo sepenuhnya dari HOME.
2. Ekstrak ZIP, salin SELURUH folder switch ke root SD, lalu timpa file lama.
3. Buka forwarder Sleeping Dogs 32-bit yang sama. Tidak perlu install ulang NSP.
4. Pilih Launch Debug. Cari [SD-PIPE] local named pipes v1, lalu create/listen/open.
5. Jika masih gagal, kirim fex-runtime.log dan crash.log terbaru dari
   switch/sleepingdogs-fex/ setelah percobaan itu.

Log terbaru melewati breakpoint dan alokasi arena, kemudian SteamAPI_Init gagal
dan game menjalankan exit(1). Runtime lama belum menyediakan named pipe lokal
yang dipakai DLL pendamping game. Patch ini menambahkan transport tersebut,
termasuk completion event/IOCP dan penanganan IOSB WoW64.

Kumulatif: NRO named-pipe + memory/first-fault trace, FEX debug-register DLL,
WoW64 self-context dan renderer. Fastest tetap berlaku. Save dan konfigurasi
pilihan pengguna tidak ditimpa; game EXE/DLL tidak disertakan atau diubah.
Paket runtime/ready tetap menjadi basis. Timpa patch ini PALING AKHIR.

ASan/UBSan, replay dua fungsi DLL asli, build NRO dan checksum paket diuji di host.
Belum terverifikasi boot/menu/gameplay di Switch. Log sebelumnya belum merekam
status syscall pipe secara langsung; penanda baru akan memperjelas tahap ini.
Rincian batas dukungan: source/named-pipe-fix/docs/named-pipe-fix.md.
Rollback: sleepingdogs-fex-named-pipe-rollback.zip (NRO diagnostik sebelumnya).
'''.encode()
    for n in ('src/sd_named_pipe.h', 'src/sd_named_pipe.inc', 'tools/sleepingdogs_named_pipe.py',
              'tools/sleepingdogs_overlay.py', 'tools/build_named_pipe.py', 'tools/build_launcher.py',
              'tools/package_named_pipe.py', 'tools/verify_package.py', 'tools/port_common.py',
              'tests/named_pipe.c', 'tests/check_named_pipe.py', 'tests/check_game_pipe_calls.py',
              'reports/named-pipe-check.json', 'reports/game-pipe-call-check.json',
              'reports/named-pipe-fault-analysis.json', 'docs/named-pipe-fix.md', 'LICENSE'):
        entries[SOURCE + n] = (ROOT / n).read_bytes()
    entries[SOURCE + 'build.json'] = encode(receipt)
    for n in receipt['source_files']: entries[SOURCE + 'generated/' + n] = (source / n).read_bytes()
    changes = {PREFIX + nro.name, PREFIX + 'launcher/direct-arena-fix.json', PREFIX + 'launcher/first-fault-trace.json'}
    for n, data in previous.items():
        if n not in changes: assert entries[n] == data, n
    forbidden = {'fex-runtime.log', 'crash.log', 'configuration.ini', 'fex-mode.txt', 'UserOptions.dat',
                 'selected.txt', 'renderer-choice.txt', 'report-memory-mb.txt'}
    for n in entries:
        assert Path(n).name not in forbidden and not n.lower().endswith(('.log', '.keys', '.nsp', '.exe', '.big', '.bix'))
        assert '/drive_c/SleepingDogs/' not in n
    output = ROOT / 'dist/sleepingdogs-fex-named-pipe-fix.zip'
    report = archive(output, entries)
    rollback = {n: previous[n] for n in changes}
    rollback[PREFIX + 'launcher/named-pipe-fix.json'] = encode({'rolled_back': True})
    rollback['README.txt'] = b'Close FEXTendo from HOME, then overwrite switch/ on SD. Restores the prior diagnostic NRO; the tested FEX DLL remains.\n'
    report['rollback'] = archive(ROOT / 'dist/sleepingdogs-fex-named-pipe-rollback.zip', rollback)
    report.update({'checksums_verified': True, 'cumulative': True, 'nsp_reinstall_required': False,
                   'compiled_overlay_reconstruction': 'PASS', 'unchanged_prior_payloads_verified': True,
                   'nro_sha256': receipt['nro_sha256'], 'fex_dll_sha256': receipt['fex_dll_sha256'],
                   'hardware_tested': False, 'game_boot_confirmed': False})
    write_json(ROOT / 'reports/named-pipe-package.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
