"""Package the matching native/DXVK streaming update over the GPU-budget fix."""
from pathlib import Path
import argparse, hashlib, json, shutil, tempfile, zipfile
import pefile
from port_common import ROOT, sha, write_json
from package_named_pipe import PREFIX, archive, encode
from package_dxvk_memory import interfaces
from build_streaming_memory import FILES, ADAPTER_FILES
from build_dxvk_memory import manifest
from sleepingdogs_streaming_memory import apply_native, apply_dxvk, DXVK_FILES
from dxvk_runtime import release_files, effective_release


def executable_sections(data):
    pe = pefile.PE(data=data, fast_load=True)
    return [(s.Name, s.VirtualAddress, s.get_data()) for s in pe.sections if s.Characteristics & 0x20000000]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-streaming-memory-v1'))
    work = p.parse_args().work
    out = ROOT / 'dist/streaming-memory-fix'
    native = json.loads((out / 'native.json').read_text())
    build = json.loads((out / 'dxvk.json').read_text())
    staged = json.loads((out / 'staged.json').read_text())
    assert sha(out / 'sleepingdogs-fex.nro') == native['nro_sha256']
    assert sha(ROOT / 'local/symbols/sleepingdogs-streaming-memory.elf') == native['elf_sha256']
    assert sha(ROOT / 'tools/build_streaming_memory.py') == build['inputs']['builder_sha256']
    assert sha(ROOT / 'tools/sleepingdogs_streaming_memory.py') == build['inputs']['patch_sha256']
    assert manifest(work / 'dxvk/source') == build['source_files']
    for key, base in (('source_files', work / 'native-source'), ('adapter_files', work / 'fex-adapter')):
        for n, digest in native[key].items(): assert sha(base / n) == digest, n
    prior = ROOT / 'dist/sleepingdogs-fex-gpu-budget-fix.zip'
    assert sha(prior) == 'bca038f391c972eeb82b16e52fa3c373cca5fb0d67a704f987470fe87548cec8'
    with zipfile.ZipFile(prior) as z:
        old = {n:z.read(n) for n in z.namelist() if n not in ('README.txt','SHA256SUMS.txt')}
    previous_native = json.loads(old['source/gpu-budget-fix/native.json'])
    previous = Path('/home/blekjek/sleepingdogs-gpu-budget-v1')
    dxvk_base = Path('/home/blekjek/sleepingdogs-dxvk-memory-v2/source')
    assert manifest(dxvk_base) == build['inputs']['base']
    with tempfile.TemporaryDirectory() as temp:
        ns = Path(temp) / 'native'; ds = Path(temp) / 'dxvk'
        for n, digest in previous_native['source_files'].items():
            src = previous / 'native-source' / n; assert sha(src) == digest, n
            dst = ns / n; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
        apply_native(ns)
        for n in FILES: assert sha(ns / n) == native['source_files'][n], n
        for n in ADAPTER_FILES: assert sha(previous / 'fex-adapter' / n) == native['adapter_files'][n], n
        for n in DXVK_FILES:
            dst = ds / n; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(dxvk_base / n, dst)
        apply_dxvk(ds)
        for n in DXVK_FILES: assert sha(ds / n) == build['changed'][n], n
    checks = {}
    for name in ('streaming-host-check', 'streaming-binary-check'):
        check = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        assert check['status'] == 'PASS'
        for n, digest in check['sources'].items(): assert sha(ROOT / n) == digest, n
        checks[name] = check
    host = checks['streaming-host-check']; binary = checks['streaming-binary-check']
    assert binary['native_elf_sha256'] == native['elf_sha256']
    assert binary['dll_sha256'] == staged['files']['d3d11.dll']['sha256']
    for n, digest in host['compiled_native'].items(): assert sha(work / 'native-source/wine-nx-probe/source' / n) == digest
    for n, digest in host['compiled_dxvk']['candidate'].items(): assert build['source_files'][n] == digest
    entries = dict(old); changed = {PREFIX + 'sleepingdogs-fex.nro'}
    entries[PREFIX + 'sleepingdogs-fex.nro'] = (out / 'sleepingdogs-fex.nro').read_bytes()
    for name in ('direct-arena-fix','first-fault-trace','named-pipe-fix','dep-policy-fix',
                 'debug-cache-fix','thread-debug-fix','memory-budget-fix','compiler-memory-fix','gpu-budget-fix'):
        key = PREFIX + 'launcher/' + name + '.json'; receipt = json.loads(entries[key])
        receipt['nro_sha256'] = native['nro_sha256']
        receipt['additional_overlay'] = 'launcher/streaming-memory-fix.json'
        entries[key] = encode(receipt); changed.add(key)
    current = release_files()['dxvk-3.1.1']; managed = set(); interface_report = {}
    for name, data in current.items():
        assert hashlib.sha256(data).hexdigest() == staged['files'][name]['sha256']
        raw = (out / name).read_bytes(); assert hashlib.sha256(raw).hexdigest() == build['files'][name]['raw_sha256']
        assert executable_sections(raw) == executable_sections(data), name
        assert interfaces(data) == interfaces(old[PREFIX + 'drive_c/SleepingDogs/' + name]), name
        interface_report[name] = {'imports_exports_unchanged':True, 'stripped_executable_sections_identical':True,
                                  'sha256':staged['files'][name]['sha256']}
        targets = ['launcher/renderers/dxvk-3.1.1/' + name, 'drive_c/SleepingDogs/' + name]
        if name == 'd3d9.dll': targets.append('drive_c/dxvk/d3d9.dll')
        for relative in targets:
            key = PREFIX + relative; assert key in old
            entries[key] = data; changed.add(key); managed.add(key)
    key = PREFIX + 'launcher/dxvk-releases.json'; receipts = json.loads(old[key])
    release = effective_release('dxvk-3.1.1')
    receipts['dxvk-3.1.1'] = {'url':release['url'], 'archive_sha256':release['sha256'],
        'dlls':{n:m['sha256'] for n,m in staged['files'].items()}, 'patch':staged}
    entries[key] = encode(receipts); changed.add(key)
    key = PREFIX + 'launcher/dxvk-memory-fix.json'; entries[key] = encode(staged); changed.add(key)
    fw = json.loads(old['forwarder/build.json'])
    assert fw['sha256'] == '222269d0bc876b970a1a82a82890223909dd6811776232041e7b8966c4756781'
    assert hashlib.sha256(old['forwarder/' + fw['nsp']]).hexdigest() == fw['sha256']
    stream = {k:native[k] for k in ('build','nro_sha256','gpu_preallocation_bytes','large_reserve_bytes',
                                  'borrow_guard_bytes','threshold_bytes','hardware_tested')}
    stream.update(dxvk_dlls=receipts['dxvk-3.1.1']['dlls'], compatible_forwarder_sha256=fw['sha256'],
                  forwarder_reinstall_required_from_gpu_budget=False)
    entries[PREFIX + 'launcher/streaming-memory-fix.json'] = encode(stream)
    entries['README.txt'] = '''Sleeping Dogs FEXTendo - New Game / streaming memory v1

1. Tutup Sleeping Dogs/FEXTendo sepenuhnya dari HOME.
2. Timpa SELURUH folder switch dari ZIP ini ke root SD PALING AKHIR.
   NRO dan semua DLL renderer di drive_c serta launcher harus terpasang bersama.
3. Jika NSP GPU-budget sebelumnya sudah aktif, TIDAK perlu install ulang NSP.
   Untuk instalasi dari basis lama, install NSP dalam folder forwarder sekali.
   NSP yang disertakan identik dengan versi GPU-budget sebelumnya.
4. Buka Sleeping Dogs dari HOME, pilih DXVK 3.1.1 dan Launch Debug.
   Coba New Game sampai melewati loading menuju adegan 3D.

Cari penanda baru:
[SD-GPU-STREAM] v1 total_mib=256 large_mib=64 threshold_mib=2 borrow_guard_mib=16
[SD-DXVK-STREAM] v1 mapped > 2 MiB dedicated; no small suballocations

Log terakhir menunjukkan buffer 5 MiB gagal karena ruang GPU terpecah/hampir
penuh, lalu game menulis ke pointer kosong. DXVK kini memisahkan backing
buffer mapped besar; native menjaga bagian pool untuk buffer besar, dengan
peminjaman terbatas saat terdesak. Total pool tetap 256 MiB. FEX tetap Fastest.
Empat buffer compiler, arena game 1.000 MiB, dan patch sebelumnya dipertahankan.
File game/save/settings tidak ditimpa. ZIP tidak memuat data asli game.

Uji host/binari dan pemasangan paket lulus; gameplay Switch belum diuji.
Jika masih crash, kirim fex-runtime.log dan crash.log terbaru.
Rollback: sleepingdogs-fex-streaming-memory-rollback.zip, salin seluruh switch
saat aplikasi tertutup. Mengembalikan NRO GPU-budget dan DXVK sdmem1 bersama;
forwarder tetap sama dan tidak perlu diinstall ulang.
'''.encode()
    folder = 'source/streaming-memory-fix/'
    sources = ('src/sd_gpu_stream.h','tools/sleepingdogs_streaming_memory.py','tools/build_streaming_memory.py',
        'tools/stage_streaming_memory.py','tools/package_streaming_memory.py','tools/analyze_streaming_memory.py',
        'tools/sleepingdogs_overlay.py','tools/build_launcher.py','tools/dxvk_runtime.py','tools/verify_package.py',
        'tools/port_common.py','tests/streaming_gpu.c','tests/streaming_dxvk.cpp','tests/check_streaming_host.py',
        'tests/check_streaming_binary.py','tests/check_gpu_budget_binary.py','tests/native_heap_binary.py',
        'tests/check_dxvk_map_binary.py','tests/check_wow64_context_binary.py','tests/check_streaming_package.py',
        'tests/check_streaming_launcher.py','tests/check_renderer_package.py','vendor/f1-tools/check_renderer_package.py',
        'docs/streaming-memory-fix.md','reports/streaming-memory-analysis.json',
        'vendor/dxvk/dxvk-3.1.1-sdstream1.json','vendor/dxvk/DXVK-LICENSE','LICENSE')
    for n in sources: entries[folder + n] = (ROOT / n).read_bytes()
    for name, check in checks.items(): entries[folder + 'reports/' + name + '.json'] = encode(check)
    for name in ('native.json','dxvk.json','staged.json'): entries[folder + name] = (out / name).read_bytes()
    for n in FILES: entries[folder + 'native/' + n] = (work / 'native-source' / n).read_bytes()
    for n in ADAPTER_FILES: entries[folder + 'adapter/' + n] = (work / 'fex-adapter' / n).read_bytes()
    for n in DXVK_FILES:
        entries[folder + 'dxvk/' + n] = (work / 'dxvk/source' / n).read_bytes()
        entries[folder + 'dxvk-base/' + n] = (dxvk_base / n).read_bytes()
    for n, data in old.items():
        if n not in changed: assert entries[n] == data, n
    for n in entries:
        if '/drive_c/SleepingDogs/' in n: assert n in managed, n
        if n.lower().endswith('.nsp'): assert n == 'forwarder/' + fw['nsp'] and entries[n] == old[n]
        assert not n.lower().endswith(('.log','.keys','.exe','.big','.bix'))
        assert Path(n).name not in {'configuration.ini','fex-mode.txt','UserOptions.dat','selected.txt','renderer-choice.txt'}
    rollback = {n:old[n] for n in changed}
    rollback[PREFIX + 'launcher/streaming-memory-fix.json'] = encode({'rolled_back':True})
    rollback['README.txt'] = b'Close FEXTendo from HOME and copy the entire switch folder. Restores the previous GPU-budget NRO plus sdmem1 DXVK DLLs. Keep the existing GPU-budget forwarder; no NSP reinstall.\n'
    report = archive(ROOT / 'dist/sleepingdogs-fex-streaming-memory-fix.zip', entries)
    report['rollback'] = archive(ROOT / 'dist/sleepingdogs-fex-streaming-memory-rollback.zip', rollback)
    report.update(status='PASS', source_reconstruction='PASS', prior_payloads_preserved=True,
        nro_sha256=native['nro_sha256'], interfaces=interface_report, forwarder_unchanged=fw['sha256'],
        fex_unchanged=hashlib.sha256(entries[PREFIX + 'drive_c/windows/system32/libwow64fex.dll']).hexdigest(),
        original_game_excluded=True, hardware_tested=False)
    write_json(ROOT / 'reports/streaming-package.json', report)
    print(json.dumps({k:report[k] for k in ('path','sha256','bytes','files')}))


if __name__ == '__main__': main()
