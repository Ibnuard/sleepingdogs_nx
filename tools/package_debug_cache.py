"""Cumulative cache-fix ZIP; no game files, logs, settings or old payload rewrites."""
from pathlib import Path
import argparse
import json
import tempfile
import zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode, PREFIX
from build_debug_cache import FILES
from sleepingdogs_named_pipe import apply as apply_pipes
from sleepingdogs_debug_cache import apply as apply_cache
from sleepingdogs_fault_trace import apply as apply_faults


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-debug-cache-v1'))
    p.add_argument('--memory-work', type=Path, default=Path('/home/blekjek/sleepingdogs-direct-arena-v2'))
    a = p.parse_args(); source = a.work / 'native-source'; out = ROOT / 'dist/debug-cache-fix'
    native = json.loads((out / 'native.json').read_text())
    assert sha(out / 'sleepingdogs-fex.nro') == native['nro_sha256']
    for n, digest in native['source_files'].items(): assert sha(source / n) == digest, n
    reports = ('debug-cache-host-check', 'debug-cache-binary-check', 'first-fault-host-check')
    for name in reports:
        check = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        assert check['status'] == 'PASS', name
        for n, digest in check.get('sources', {}).items(): assert sha(ROOT / n) == digest, n
        if name == 'debug-cache-binary-check': assert check['elf_sha256'] == native['elf_sha256']
    prior = ROOT / 'dist/sleepingdogs-fex-dep-policy-fix.zip'
    assert sha(prior) == '1e120b777329d04713a170306b71a926fc86e2acc26a4378f771fbbed14bbe76'
    with zipfile.ZipFile(prior) as z:
        previous = {n: z.read(n) for n in z.namelist() if n not in ('README.txt', 'SHA256SUMS.txt')}
    # Reconstruct the exact compilation units from the immutable arena build.
    seed = ('dlls/ntdll/unix/horizon.c', 'dlls/ntdll/unix/file.c',
        'dlls/ntdll/unix/signal_arm64.c', 'dlls/ntdll/signal_i386.c',
        'dlls/ntdll/unix/horizon_wow64.h', 'wine-nx-probe/source/runtime.c',
        'wine-nx-probe/source/f1_crash.c')
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp)
        for n in seed:
            target = expected / n; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((a.memory_work / 'native-source' / n).read_bytes())
        apply_pipes(expected); apply_cache(expected); apply_faults(expected)
        for n in set(seed + FILES + ('dlls/ntdll/unix/sd_named_pipe.h', 'dlls/ntdll/unix/sd_named_pipe.inc')):
            assert (expected / n).read_bytes() == (source / n).read_bytes(), n
    old_build = json.loads(previous['source/named-pipe-fix/build.json'])
    for n, digest in old_build['memory_sources_unchanged'].items(): assert sha(source / n) == digest, n
    entries = dict(previous)
    receipts = ('direct-arena-fix', 'first-fault-trace', 'named-pipe-fix', 'dep-policy-fix')
    changed = {PREFIX + 'sleepingdogs-fex.nro', *(PREFIX + 'launcher/' + n + '.json' for n in receipts)}
    entries[PREFIX + 'sleepingdogs-fex.nro'] = (out / 'sleepingdogs-fex.nro').read_bytes()
    for name in receipts:
        key = PREFIX + 'launcher/' + name + '.json'; rec = json.loads(entries[key])
        rec['nro_sha256'] = native['nro_sha256']; rec['additional_overlay'] = 'launcher/debug-cache-fix.json'
        if name == 'first-fault-trace':
            rec.update(build='sleepingdogs-post-frame-fault-v3', skip_thread_name_exceptions=True,
                max_backtrace_warning_lines=128, source_files=native['source_files'])
        entries[key] = encode(rec)
    entries[PREFIX + 'launcher/debug-cache-fix.json'] = encode(native)
    entries['README.txt'] = '''Sleeping Dogs FEXTendo - TEB debug cache v1

1. Tutup Sleeping Dogs/FEXTendo dari HOME.
2. Timpa SELURUH folder switch dari ZIP ini ke root SD. Pasang PALING AKHIR
   setelah paket basis/ready dan patch lama.
3. Buka forwarder yang sama, lalu Launch Debug. NSP tidak perlu diinstall ulang.
4. Cari [SD-TEB-DEBUG] build=v1 dan [SD-TEB-DEBUG] sync di fex-runtime.log.
5. Jika masih gagal, kirim fex-runtime.log DAN crash.log terbaru dari
   switch/sleepingdogs-fex/ setelah percobaan tersebut.

Log DEP terbaru memperlihatkan register breakpoint hilang saat RaiseException
untuk penamaan thread Havok. Wine x86 membaca cache debug TEB yang belum ikut
diperbarui oleh native WoW64. Cache kosong itu menimpa breakpoint FEX; kode game
kemudian menghapus stack/SEH dan kembali ke alamat heap. Patch menyinkronkan
cache setelah SetContext berhasil; penghapusan breakpoint yang diminta tetap
dihormati. File game tidak diubah.

Kumulatif: perbaikan DEP, named pipe, FEX breakpoint, arena, self-context dan
renderer tetap disertakan. Fastest tetap; save dan pilihan launcher tidak ditimpa.
Uji host/binary lulus, tetapi menu/gameplay masih perlu diuji pada Switch.
Rollback: sleepingdogs-fex-debug-cache-rollback.zip memulihkan runtime DEP.
'''.encode()
    files = ('src/sd_wow64_debug_cache.h', 'src/sd_fault_trace.inc', 'src/sd_fault_wine_log.h',
        'tools/sleepingdogs_debug_cache.py', 'tools/sleepingdogs_overlay.py',
        'tools/sleepingdogs_fault_trace.py', 'tools/build_debug_cache.py', 'tools/package_debug_cache.py',
        'tools/build_launcher.py', 'tools/verify_package.py',
        'tests/debug_cache.c', 'tests/check_debug_cache.py', 'tests/check_debug_cache_binary.py',
        'tests/check_game_debug_exception.py', 'tests/fault_trace.c', 'tests/check_fault_trace.py',
        'reports/debug-cache-analysis.json', 'docs/debug-cache-fix.md', 'LICENSE')
    folder = 'source/debug-cache-fix/'
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
    report = archive(ROOT / 'dist/sleepingdogs-fex-debug-cache-fix.zip', entries)
    rollback = {n: previous[n] for n in changed}
    rollback[PREFIX + 'launcher/debug-cache-fix.json'] = encode({'rolled_back': True})
    rollback['README.txt'] = b'Close FEXTendo from HOME; overwrite switch/ on SD. Restores the DEP-policy runtime.\n'
    report['rollback'] = archive(ROOT / 'dist/sleepingdogs-fex-debug-cache-rollback.zip', rollback)
    report.update(cumulative=True, source_reconstruction='PASS', checksums_verified=True,
        prior_payloads_preserved=True, memory_sources_unchanged=True, all_pe_dlls_unchanged=True,
        nro_sha256=native['nro_sha256'], hardware_tested=False, game_boot_confirmed=False)
    write_json(ROOT / 'reports/debug-cache-package.json', report)
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
