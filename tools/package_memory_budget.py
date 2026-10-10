"""Cumulative native memory budget update; previous PE payloads stay byte-identical."""
from pathlib import Path
import argparse
import json
import tempfile
import zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode, PREFIX
from build_memory_budget import FILES, ADAPTER_FILES
from sleepingdogs_memory_budget import apply


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-memory-budget-v1'))
    p.add_argument('--previous-work', type=Path, default=Path('/home/blekjek/sleepingdogs-thread-debug-v1'))
    a = p.parse_args(); source = a.work / 'native-source'; adapter = a.work / 'fex-adapter'
    out = ROOT / 'dist/memory-budget-fix'
    native = json.loads((out / 'native.json').read_text())
    assert sha(out / 'sleepingdogs-fex.nro') == native['nro_sha256']
    for names, tree in (('source_files', source), ('adapter_files', adapter)):
        for n, digest in native[names].items(): assert sha(tree / n) == digest, n
    reports = ('memory-budget-host-check', 'memory-budget-binary-check')
    for name in reports:
        check = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        assert check['status'] == 'PASS', name
        for n, digest in check.get('sources', {}).items(): assert sha(ROOT / n) == digest, n
        for n, digest in check.get('compiled_sources', {}).items():
            assert native['source_files']['wine-nx-probe/source/' + n] == digest, n
        if name == 'memory-budget-binary-check': assert check['elf_sha256'] == native['elf_sha256']
    prior = ROOT / 'dist/sleepingdogs-fex-thread-debug-fix.zip'
    assert sha(prior) == '3b40a40a23bc0408d421f26cd9169a5db396c83db77f19e76759267da91c286b'
    with zipfile.ZipFile(prior) as z:
        previous = {n: z.read(n) for n in z.namelist() if n not in ('README.txt', 'SHA256SUMS.txt')}
    old_native = json.loads(previous['source/thread-debug-fix/native.json'])
    for n, digest in old_native['source_files'].items():
        assert sha(a.previous_work / 'native-source' / n) == digest, n
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / 'source'; expected_adapter = Path(tmp) / 'adapter'
        expected_adapter.mkdir()
        for n in FILES:
            target = expected / n; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((a.previous_work / 'native-source' / n).read_bytes())
        for n in ADAPTER_FILES:
            (expected_adapter / n).write_bytes((a.previous_work / 'fex-adapter' / n).read_bytes())
        apply(expected, expected_adapter)
        for n in FILES: assert (expected / n).read_bytes() == (source / n).read_bytes(), n
        for n in ADAPTER_FILES: assert (expected_adapter / n).read_bytes() == (adapter / n).read_bytes(), n
    old_pipes = json.loads(previous['source/named-pipe-fix/build.json'])
    for n, digest in old_pipes['memory_sources_unchanged'].items():
        if n != 'wine-nx-probe/source/f1_gpu_arena.h': assert sha(source / n) == digest, n
    for n in ('file.c', 'sd_named_pipe.h', 'sd_named_pipe.inc', 'horizon_wow64.h',
              'sd_wow64_debug_cache.h', 'sd_thread_debug.inc', 'signal_arm64.c', 'horizon.c'):
        rel = 'dlls/ntdll/unix/' + n
        assert sha(source / rel) == sha(a.previous_work / 'native-source' / rel), n
    entries = dict(previous)
    receipts = ('direct-arena-fix', 'first-fault-trace', 'named-pipe-fix', 'dep-policy-fix',
                'debug-cache-fix', 'thread-debug-fix')
    changed = {PREFIX + 'sleepingdogs-fex.nro', *(PREFIX + 'launcher/' + n + '.json' for n in receipts)}
    entries[PREFIX + 'sleepingdogs-fex.nro'] = (out / 'sleepingdogs-fex.nro').read_bytes()
    for name in receipts:
        key = PREFIX + 'launcher/' + name + '.json'; rec = json.loads(entries[key])
        rec['nro_sha256'] = native['nro_sha256']; rec['additional_overlay'] = 'launcher/memory-budget-fix.json'
        if name == 'direct-arena-fix': rec['gpu_preallocation_bytes'] = 134217728
        entries[key] = encode(rec)
    entries[PREFIX + 'launcher/memory-budget-fix.json'] = encode(native)
    entries['README.txt'] = '''Sleeping Dogs FEXTendo - native memory headroom v1

1. Tutup Sleeping Dogs/FEXTendo dari HOME.
2. Timpa SELURUH folder switch dari ZIP ini ke root SD. Pasang PALING AKHIR
   setelah paket basis/ready dan patch lama.
3. Buka forwarder yang sama, lalu Launch Debug. NSP tidak perlu dipasang ulang.
4. Cari [SD-MEMORY-BUDGET] build=v1 gpu_reserve_mib=128 di fex-runtime.log.
5. Jika masih gagal, kirim fex-runtime.log DAN crash.log terbaru dari
   switch/sleepingdogs-fex/ setelah percobaan tersebut.

Log baru sudah melewati worker yang sebelumnya gagal. Kini heap umum kehabisan
ruang untuk thread dan compiler FEX, sementara snapshot GPU masih menyimpan
sekitar 149 MiB cadangan kosong. Prealokasi GPU dikurangi 256 -> 128 MiB:
128 MiB kembali tersedia bagi heap umum. Ini bukan batas total alokasi GPU;
fallback GPU biasa tetap tersedia. Arena data game 1000 MiB tetap.

Thread SDK kecil, termasuk server Wine 128 KiB, kini dapat memakai slot stack
1 MiB yang masih idle setelah OOM. Kapasitas stack, TLS/reent, kepemilikan dan
karantina pada kegagalan unmap tetap dipertahankan. Jika scratch masih gagal,
log mencatat heap, GPU dan stack pada titik kegagalan.

Fastest dan ukuran workspace compiler tetap. Semua DLL serta patch thread,
cache exception, DEP, pipe dan arena sebelumnya tetap disertakan. Tidak
mengubah file game, save atau pilihan launcher.
Uji host/biner dan paket lulus; boot/menu/gameplay tetap perlu diuji di Switch.
Rollback: sleepingdogs-fex-memory-budget-rollback.zip memulihkan thread-debug v1.
'''.encode()
    files = ('tools/sleepingdogs_memory_budget.py', 'tools/sleepingdogs_overlay.py',
        'tools/build_memory_budget.py', 'tools/package_memory_budget.py', 'tools/build_launcher.py',
        'tools/verify_package.py', 'tests/memory_native_stacks.c', 'tests/memory_gpu_arena.c',
        'tests/check_memory_budget.py', 'tests/check_memory_budget_binary.py', 'tests/native_heap_binary.py',
        'reports/memory-budget-analysis.json', 'docs/memory-budget-fix.md', 'LICENSE')
    folder = 'source/memory-budget-fix/'
    for n in files: entries[folder + n] = (ROOT / n).read_bytes()
    for name in reports: entries[folder + 'reports/' + name + '.json'] = (ROOT / 'reports' / (name + '.json')).read_bytes()
    entries[folder + 'native.json'] = encode(native)
    for n in FILES: entries[folder + 'generated/' + n] = (source / n).read_bytes()
    for n in ADAPTER_FILES: entries[folder + 'adapter/' + n] = (adapter / n).read_bytes()
    for n, data in previous.items():
        if n not in changed: assert entries[n] == data, n
    for n in entries:
        assert not n.lower().endswith(('.log', '.keys', '.nsp', '.exe', '.big', '.bix'))
        assert Path(n).name not in {'configuration.ini', 'fex-mode.txt', 'UserOptions.dat', 'selected.txt', 'renderer-choice.txt'}
        assert '/drive_c/SleepingDogs/' not in n
    report = archive(ROOT / 'dist/sleepingdogs-fex-memory-budget-fix.zip', entries)
    rollback = {n: previous[n] for n in changed}
    rollback[PREFIX + 'launcher/memory-budget-fix.json'] = encode({'rolled_back': True})
    rollback['README.txt'] = b'Close FEXTendo from HOME; overwrite switch/ on SD. Restores the thread-debug v1 runtime.\n'
    report['rollback'] = archive(ROOT / 'dist/sleepingdogs-fex-memory-budget-rollback.zip', rollback)
    report.update(cumulative=True, source_reconstruction='PASS', checksums_verified=True,
        prior_payloads_preserved=True, guest_memory_sources_unchanged=True, all_pe_dlls_unchanged=True,
        nro_sha256=native['nro_sha256'], hardware_tested=False, game_boot_confirmed=False)
    write_json(ROOT / 'reports/memory-budget-package.json', report)
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
