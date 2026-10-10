"""Package the paired NRO/forwarder over the complete sdmem1 update."""
from pathlib import Path
import argparse
import json
import shutil
import tempfile
import zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode, PREFIX
from build_gpu_budget import FILES, ADAPTER_FILES
from sleepingdogs_gpu_budget import apply_native, apply_forwarder


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-gpu-budget-v1'))
    p.add_argument('--forwarder-work', type=Path, default=Path('/home/blekjek/sleepingdogs-gpu-forwarder-v1'))
    a = p.parse_args(); work = a.work; fw = a.forwarder_work
    out = ROOT / 'dist/gpu-budget-fix'; native = json.loads((out / 'native.json').read_text())
    forwarder = json.loads((out / 'forwarder/build.json').read_text())
    assert sha(out / 'sleepingdogs-fex.nro') == native['nro_sha256']
    assert forwarder['nro_sha256'] == native['nro_sha256']
    assert sha(out / 'forwarder' / forwarder['nsp']) == forwarder['sha256']
    assert forwarder['packed_payload_verified'] and forwarder['additional_heap_bytes'] == 67108864
    for key, base in (('source_files', work / 'native-source'), ('adapter_files', work / 'fex-adapter')):
        for n, digest in native[key].items(): assert sha(base / n) == digest, n
    for n, digest in forwarder['source_files'].items(): assert sha(fw / 'source' / n) == digest, n
    checks = {}
    for name in ('gpu-budget-host-check', 'gpu-budget-binary-check'):
        check = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        assert check['status'] == 'PASS'
        assert check['native_elf_sha256'] == native['elf_sha256']
        assert check['forwarder_elf_sha256'] == forwarder['elf_sha256']
        checks[name] = check
    prior = ROOT / 'dist/sleepingdogs-fex-dxvk-memory-fix.zip'
    assert sha(prior) == '8ecb9c7dd6cc5da92382cf3e8e74c552bdb37fb3bb0c203b7c439b6a8d43ba9e'
    with zipfile.ZipFile(prior) as z:
        old = {n: z.read(n) for n in z.namelist() if n not in ('README.txt', 'SHA256SUMS.txt')}
    before = json.loads(old['source/compiler-memory-fix/native.json'])
    previous = Path('/home/blekjek/sleepingdogs-compiler-memory-v2')
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp); ns = base / 'native'
        for n in FILES:
            if n.endswith('/sd_gpu_budget.h'): continue
            src = previous / 'native-source' / n
            assert sha(src) == before['source_files'][n], n
            dst = ns / n; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
        apply_native(ns)
        for n in FILES: assert sha(ns / n) == native['source_files'][n], n
        for n in ADAPTER_FILES:
            assert sha(previous / 'fex-adapter' / n) == native['adapter_files'][n], n
        fs = base / 'forwarder'; shutil.copytree(ROOT / 'forwarder/hbl/source', fs)
        apply_forwarder(fs)
        for n, digest in forwarder['source_files'].items(): assert sha(fs / n) == digest, n
    entries = dict(old); nro_key = PREFIX + 'sleepingdogs-fex.nro'; changed = {nro_key}
    entries[nro_key] = (out / 'sleepingdogs-fex.nro').read_bytes()
    for name in ('direct-arena-fix', 'first-fault-trace', 'named-pipe-fix', 'dep-policy-fix',
                 'debug-cache-fix', 'thread-debug-fix', 'memory-budget-fix', 'compiler-memory-fix'):
        key = PREFIX + 'launcher/' + name + '.json'; receipt = json.loads(entries[key])
        receipt['nro_sha256'] = native['nro_sha256']
        receipt['additional_overlay'] = 'launcher/gpu-budget-fix.json'
        if name in ('direct-arena-fix', 'memory-budget-fix'):
            receipt['gpu_preallocation_bytes'] = 268435456
        if name == 'memory-budget-fix': receipt['build'] = 'sleepingdogs-native-headroom-v2'
        entries[key] = encode(receipt); changed.add(key)
    paired = {k: native[k] for k in ('build', 'nro_sha256', 'gpu_preallocation_bytes',
        'fallback_gpu_preallocation_bytes', 'loader_required', 'minimum_heap_bytes', 'hardware_tested')}
    paired.update(forwarder_reinstall_required=True, forwarder_sha256=forwarder['sha256'])
    entries[PREFIX + 'launcher/gpu-budget-fix.json'] = encode(paired)
    entries['forwarder/' + forwarder['nsp']] = (out / 'forwarder' / forwarder['nsp']).read_bytes()
    entries['forwarder/build.json'] = encode(forwarder)
    entries['README.txt'] = '''Sleeping Dogs FEXTendo - GPU budget fix v1 (START/menu)

1. Tutup Sleeping Dogs/FEXTendo sepenuhnya dari HOME.
2. Timpa SELURUH folder switch dari ZIP ini ke root SD PALING AKHIR.
3. WAJIB install ulang forwarder/FEXTendo-SleepingDogs-32bit.nsp dari ZIP INI.
   Title ID dan target tetap sama. Tidak perlu menghapus game/save.
4. Buka Sleeping Dogs dari HOME, pilih DXVK 3.1.1 lalu Launch Debug.
   Log harus memuat:
   [SD-GPU-BUDGET] v1 paired_loader=1 ... target_mib=256 reserved_mib=256
   Jika paired_loader=0, forwarder lama masih aktif atau heap host terlalu kecil.
   NRO akan kembali ke cadangan 128 MiB agar tidak mengambil ruang kerja FEX.

Log terbaru sudah mencapai menu. Saat START, buffer GPU 5 MiB gagal karena
heap terfragmentasi; game mengabaikan E_OUTOFMEMORY dan menyalin ke NULL+0x40.
Forwarder baru menambahkan 64 MiB ke heap dari jatah proses yang belum dipakai,
tetap menyisakan setidaknya 32 MiB di luar heap. Pool GPU naik 128 -> 256 MiB,
menjaga backing GPU terpisah dari alokasi CPU. Batas total proses tidak berubah.
Fastest, empat buffer compiler, DXVK sdmem1 dan semua patch sebelumnya tetap.
File game/save/settings tidak ditimpa. Paket tidak menyertakan data game.

Uji host, allocator ARM64, forwarder ARM64, dan paket dijalankan; Switch belum.
Coba tekan START. Jika gagal, kirim fex-runtime.log dan crash.log terbaru.
Rollback: sleepingdogs-fex-gpu-budget-rollback.zip, salin switch dan install
forwarder lama di dalam ZIP rollback. Memulihkan kondisi sebelum patch ini.
'''.encode()
    folder = 'source/gpu-budget-fix/'
    for n in ('src/sd_gpu_budget.h', 'tools/sleepingdogs_gpu_budget.py', 'tools/build_gpu_budget.py',
        'tools/package_gpu_budget.py', 'tools/sleepingdogs_overlay.py', 'tools/build_launcher.py',
        'tools/verify_package.py', 'forwarder/build_forwarder.py', 'forwarder/package_sd.py', 'tests/check_gpu_budget_host.py',
        'tests/gpu_budget_host.c', 'tests/memory_gpu_arena.c', 'tests/check_gpu_budget_binary.py', 'tests/native_heap_binary.py',
        'tests/check_gpu_budget_package.py', 'docs/gpu-budget-fix.md',
        'reports/gpu-budget-analysis.json', 'LICENSE'):
        entries[folder + n] = (ROOT / n).read_bytes()
    for name, check in checks.items(): entries[folder + 'reports/' + name + '.json'] = encode(check)
    entries[folder + 'native.json'] = encode(native)
    for n in FILES: entries[folder + 'native/' + n] = (work / 'native-source' / n).read_bytes()
    for n in ADAPTER_FILES: entries[folder + 'adapter/' + n] = (work / 'fex-adapter' / n).read_bytes()
    for n in forwarder['source_files']: entries[folder + 'forwarder/' + n] = (fw / 'source' / n).read_bytes()
    for p in (ROOT / 'forwarder/licenses').rglob('*'):
        if p.is_file(): entries[folder + 'licenses/' + p.relative_to(ROOT / 'forwarder/licenses').as_posix()] = p.read_bytes()
    for n, data in old.items():
        if n not in changed: assert entries[n] == data, n
    # Every carried renderer/Wine/FEX DLL remains exactly as tested in sdmem1.
    for n in entries:
        assert not n.lower().endswith(('.log', '.keys', '.exe', '.big', '.bix'))
        assert Path(n).name not in {'configuration.ini', 'fex-mode.txt', 'UserOptions.dat', 'selected.txt', 'renderer-choice.txt'}
    report = archive(ROOT / 'dist/sleepingdogs-fex-gpu-budget-fix.zip', entries)
    rollback = {n: old[n] for n in changed}
    rollback[PREFIX + 'launcher/gpu-budget-fix.json'] = encode({'rolled_back': True})
    old_fw = ROOT / 'dist/forwarder/FEXTendo-SleepingDogs-32bit.nsp'
    assert sha(old_fw) == '445faf7b83ea1adb06cf0c2e156a29d870b4fa2d1a1ad0688caeb984b2ffd4b2'
    rollback['forwarder/' + old_fw.name] = old_fw.read_bytes()
    rollback['forwarder/build.json'] = (ROOT / 'dist/forwarder/build.json').read_bytes()
    rollback['README.txt'] = b'Close FEXTendo from HOME. Copy the complete switch folder and reinstall the old forwarder included here. Restores the previous native runtime; FEX and DXVK remain sdmem1.\n'
    report['rollback'] = archive(ROOT / 'dist/sleepingdogs-fex-gpu-budget-rollback.zip', rollback)
    report.update(status='PASS', source_reconstruction='PASS', prior_payloads_preserved=True,
        nro_sha256=native['nro_sha256'], forwarder_sha256=forwarder['sha256'], hardware_tested=False)
    write_json(ROOT / 'reports/gpu-budget-package.json', report)
    print(json.dumps({k: report[k] for k in ('path', 'sha256', 'bytes', 'files')}))


if __name__ == '__main__': main()
