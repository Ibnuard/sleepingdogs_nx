"""Cumulative suspended-thread context update, preserving previous PE payloads."""
from pathlib import Path
import argparse
import json
import tempfile
import zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode, PREFIX
from build_thread_debug import FILES
from sleepingdogs_thread_debug import apply


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-thread-debug-v1'))
    p.add_argument('--previous-work', type=Path, default=Path('/home/blekjek/sleepingdogs-debug-cache-v1'))
    a = p.parse_args(); source = a.work / 'native-source'; out = ROOT / 'dist/thread-debug-fix'
    native = json.loads((out / 'native.json').read_text())
    assert sha(out / 'sleepingdogs-fex.nro') == native['nro_sha256']
    for n, digest in native['source_files'].items(): assert sha(source / n) == digest, n
    reports = ('thread-debug-host-check', 'thread-debug-binary-check')
    for name in reports:
        check = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        assert check['status'] == 'PASS', name
        for n, digest in check.get('sources', {}).items(): assert sha(ROOT / n) == digest, n
        if name == 'thread-debug-binary-check': assert check['elf_sha256'] == native['elf_sha256']
    prior = ROOT / 'dist/sleepingdogs-fex-debug-cache-fix.zip'
    assert sha(prior) == 'b1de337278859f888e43c6197021c7424f9c5766a40bd259970259191b9b1bcd'
    with zipfile.ZipFile(prior) as z:
        previous = {n: z.read(n) for n in z.namelist() if n not in ('README.txt', 'SHA256SUMS.txt')}
    old_native = json.loads(previous['source/debug-cache-fix/native.json'])
    for n, digest in old_native['source_files'].items():
        assert sha(a.previous_work / 'native-source' / n) == digest, n
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp)
        for n in FILES:
            old = a.previous_work / 'native-source' / n
            if not old.is_file():
                assert Path(n).name in ('sd_thread_debug.h', 'sd_thread_debug.inc'); continue
            target = expected / n; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(old.read_bytes())
        apply(expected)
        for n in FILES: assert (expected / n).read_bytes() == (source / n).read_bytes(), n
    old_pipes = json.loads(previous['source/named-pipe-fix/build.json'])
    for n, digest in old_pipes['memory_sources_unchanged'].items(): assert sha(source / n) == digest, n
    for n in ('file.c', 'sd_named_pipe.h', 'sd_named_pipe.inc', 'horizon_wow64.h', 'sd_wow64_debug_cache.h'):
        rel = 'dlls/ntdll/unix/' + n
        assert sha(source / rel) == sha(a.previous_work / 'native-source' / rel), n
    entries = dict(previous)
    receipts = ('direct-arena-fix', 'first-fault-trace', 'named-pipe-fix', 'dep-policy-fix', 'debug-cache-fix')
    changed = {PREFIX + 'sleepingdogs-fex.nro', *(PREFIX + 'launcher/' + n + '.json' for n in receipts)}
    entries[PREFIX + 'sleepingdogs-fex.nro'] = (out / 'sleepingdogs-fex.nro').read_bytes()
    for name in receipts:
        key = PREFIX + 'launcher/' + name + '.json'; rec = json.loads(entries[key])
        rec['nro_sha256'] = native['nro_sha256']; rec['additional_overlay'] = 'launcher/thread-debug-fix.json'
        entries[key] = encode(rec)
    entries[PREFIX + 'launcher/thread-debug-fix.json'] = encode(native)
    entries['README.txt'] = '''Sleeping Dogs FEXTendo - suspended-thread debug context v1

1. Tutup Sleeping Dogs/FEXTendo dari HOME.
2. Timpa SELURUH folder switch dari ZIP ini ke root SD. Pasang PALING AKHIR
   setelah paket basis/ready dan patch lama.
3. Buka forwarder yang sama, lalu Launch Debug. NSP tidak perlu dipasang ulang.
4. Cari [SD-THREAD-DEBUG] build=v1 dan [SD-THREAD-DEBUG] apply tid=...
   di fex-runtime.log. Thread game juga seharusnya mendapat [SD-DB] arm.
5. Jika masih gagal, kirim fex-runtime.log DAN crash.log terbaru dari
   switch/sleepingdogs-fex/ setelah percobaan tersebut.

Game membuat thread dengan CREATE_SUSPENDED, memasang debug context pada
handle thread baru, lalu ResumeThread. Runtime sebelumnya hanya menerima
context untuk thread sendiri. Patch menyimpan permintaan debug-only di objek
thread selama suspend, lalu menerapkannya ke CPU context dan cache TEB setelah
inisialisasi CPU, sebelum WoW64/FEX berjalan. Context thread yang sudah berjalan
tetap ditolak sampai ada mekanisme sinkronisasi yang mendukungnya.

Kumulatif: cache exception, DEP, named pipe, FEX breakpoint, arena,
self-context dan renderer tetap disertakan. Fastest tetap. File game, save dan
pilihan launcher tidak diubah. Uji host dan instruksi biner lulus; boot/menu
dan gameplay masih perlu diuji pada Switch.
Rollback: sleepingdogs-fex-thread-debug-rollback.zip memulihkan runtime cache v1.
'''.encode()
    files = ('src/sd_thread_debug.h', 'src/sd_thread_debug.inc', 'src/sd_wow64_debug_cache.h',
        'tools/sleepingdogs_thread_debug.py', 'tools/sleepingdogs_overlay.py',
        'tools/build_thread_debug.py', 'tools/package_thread_debug.py',
        'tools/build_launcher.py', 'tools/verify_package.py',
        'tests/thread_debug.c', 'tests/check_thread_debug.py', 'tests/check_thread_debug_binary.py',
        'tests/extract_thread_layout.py', 'reports/thread-debug-layout.json',
        'tests/check_debug_cache_binary.py', 'tests/check_game_debug_exception.py',
        'reports/thread-debug-analysis.json', 'docs/thread-debug-fix.md', 'LICENSE')
    folder = 'source/thread-debug-fix/'
    for n in files: entries[folder + n] = (ROOT / n).read_bytes()
    for name in reports: entries[folder + 'reports/' + name + '.json'] = (ROOT / 'reports' / (name + '.json')).read_bytes()
    entries[folder + 'native.json'] = encode(native)
    for n in FILES: entries[folder + 'generated/' + n] = (source / n).read_bytes()
    for n, data in previous.items():
        if n not in changed: assert entries[n] == data, n
    for n in entries:
        assert not n.lower().endswith(('.log', '.keys', '.nsp', '.exe', '.big', '.bix'))
        assert Path(n).name not in {'configuration.ini', 'fex-mode.txt', 'UserOptions.dat', 'selected.txt', 'renderer-choice.txt'}
        assert '/drive_c/SleepingDogs/' not in n
    report = archive(ROOT / 'dist/sleepingdogs-fex-thread-debug-fix.zip', entries)
    rollback = {n: previous[n] for n in changed}
    rollback[PREFIX + 'launcher/thread-debug-fix.json'] = encode({'rolled_back': True})
    rollback['README.txt'] = b'Close FEXTendo from HOME; overwrite switch/ on SD. Restores the TEB debug-cache v1 runtime.\n'
    report['rollback'] = archive(ROOT / 'dist/sleepingdogs-fex-thread-debug-rollback.zip', rollback)
    report.update(cumulative=True, source_reconstruction='PASS', checksums_verified=True,
        prior_payloads_preserved=True, memory_sources_unchanged=True, all_pe_dlls_unchanged=True,
        nro_sha256=native['nro_sha256'], hardware_tested=False, game_boot_confirmed=False)
    write_json(ROOT / 'reports/thread-debug-package.json', report)
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
