"""Package the native CPU-work candidate; preserve all saved LSFG choices."""
from pathlib import Path
import hashlib
import json

from package_launcher_v2 import ROOT, host, sha, encode

LOCAL = ROOT / 'local/launcher-v4'
INLINE = ROOT / 'local/native-dxvk-inline-v1'
PREFIX = 'switch/sleepingdogs-fex/'
PRIOR = ROOT / 'dist/sd-launcher-v3-update'
PRIOR_MANIFEST = '406ca4de90849f180b282cd775c6905bc19e85a796a467d132e0bc8271833000'

INSTRUCTIONS = '''SLEEPING DOGS - LAUNCHER v4 / NATIVE INLINE COM

Tutup aplikasi sepenuhnya dari HOME. Salin HANYA folder switch/ utama ke
root kartu SD, pilih Replace. Tidak perlu menyalin start-game atau source.
Ini update untuk instalasi FEXTendo Sleeping Dogs yang sudah berjalan.

Target pengujian: FPS ASLI pada Light 1280x720, terutama adegan ramai.
Argumen binding kecil dikemas langsung dalam paket COM yang divalidasi
sekali. Ini mengurangi pemeriksaan memori berulang di Wine/native tanpa
menunda atau membuang draw. Filter binding luas dari v3 tidak dipakai.
Pengumpulan diagnostik native yang tidak memiliki laporan juga diperbaiki.
Saat Present menunggu, konteks deferred dapat meneruskan upload/rekaman;
operasi immediate, lifetime objek dan shutdown tetap diserialkan.

Pengaturan LSFG kamu tetap dipertahankan, termasuk ON/OFF dan motion.
Untuk membandingkan FPS asli, matikan sendiri melalui Settings bila perlu.
DXVK HUD tetap menghitung frame game. LSFG ON dapat menambah beban; hasil
ON dan OFF harus dibandingkan dalam sesi terpisah dengan kondisi sama.

Target 25-40 FPS belum terbukti pada Switch. Pengujian PC memeriksa
kebenaran transport, sumber build dan paket; bukan angka FPS perangkat.
Uji lokasi, arah kamera dan rute yang sama setelah loading selesai,
CPU 1728 / GPU 768 / RAM 1600 MHz. Sertakan bagian kerumunan dan berlari.
Kirim fex-runtime.log dan HKShip.exe_d3d11.log dari sesi baru.

Verifier penuh sekali setelah update, lalu memakai cache. Patch low-memory
aktif tetap wajib. Debug melalui Settings dan keyboard L+R+Left Stick
tetap tersedia. DisplaySettings.xml, game dan save tidak dibundel.

Opsional: comparison-compact/switch memasang proxy Compact v1 pada NRO v4
yang sama untuk membandingkan transport. Jangan copy bersama switch utama.
Untuk kembali ke kandidat inline, copy switch/ utama lagi.
- rollback-launcher-v2/switch: NRO + proxy sebelum eksperimen filter v3/v4,
  jika kandidat baru bermasalah. LSFG native pada v2 masih memiliki bypass
  yang sudah diketahui; ini rollback performa, bukan perbaikan LSFG.

Paket LSFG pribadi ikut disertakan sebagai dependensi yang sudah ada;
jangan distribusikan shader pack tersebut sebagai rilis publik.
Tidak ada ZIP. Detail audit dan batas pengujian: docs/launcher-v4.md.
'''


def main():
    assert sha(PRIOR / 'SHA256SUMS.txt') == PRIOR_MANIFEST
    prior = {}
    for line in (PRIOR / 'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert sha(PRIOR / name) == digest, name
        prior[name] = digest
    build = json.loads((LOCAL / 'build.json').read_text())
    inline = json.loads((INLINE / 'build.json').read_text())
    checks = {name: json.loads((LOCAL / name).read_text()) for name in ('test.json', 'binary-test.json')}
    guest = json.loads((INLINE / 'guest-test.json').read_text())
    native = json.loads((INLINE / 'host-test.json').read_text())
    scope = json.loads((INLINE / 'scope-test.json').read_text())
    overlap = json.loads((ROOT / 'local/native-dxvk-present-overlap-v1/test.json').read_text())
    runtime = json.loads((ROOT / 'local/launcher-v4-runtime/test.json').read_text())
    assert all(r['status'] == 'PASS' for r in (*checks.values(), guest, native, scope, overlap, runtime))
    assert sha(LOCAL / 'sleepingdogs-fex.nro') == build['nro_sha256'] == checks['binary-test.json']['nro_sha256']
    assert sha(host(build['elf'])) == build['elf_sha256'] == checks['binary-test.json']['elf_sha256']
    assert sha(INLINE / 'sdndx4.dll') == inline['proxy_sha256'] == guest['proxy_sha256']
    assert sha(INLINE / 'build.json') == build['compact_build_receipt_sha256']
    assert native['candidate_sources'] == guest['source_files'] == inline['source_files']
    assert sha(INLINE / 'sd-native-dxvk-h4-test.exe') == inline['client_sha256']
    assert inline['present_deferred_overlap'] and native['present_deferred_overlap']
    for flag in ('real_deferred_upload_during_blocked_present',
                 'concurrent_inline_scopes_while_present_active',
                 'immediate_and_global_calls_waited',
                 'same_swapchain_present_and_release_waited',
                 'native_foreign_deferred_worker_nested_dispatch_rejected',
                 'native_present_inside_explicit_enter_keeps_gate'):
        assert native[flag], flag
    assert native['live_interfaces'] == native['live_maps'] == 0
    assert native['validated_range_scope'] == scope
    for name, digest in overlap['production_sources'].items():
        assert sha(ROOT / name) == digest, name
    assert checks['test.json']['source_files'] == build['source_files']
    for group in ('source_files', 'builder_sources'):
        for name, digest in build[group].items():
            assert sha(ROOT / name) == digest, name
    for name, digest in inline['source_files'].items():
        assert sha(INLINE / name) == digest, name
    assert runtime['overlay_sha256'] == sha(ROOT / 'tools/launcher_v4_runtime.py')
    assert runtime['tests_sha256'] == sha(ROOT / 'tools/test_launcher_v4_runtime.py')

    entries = {}

    def put(name, source=None, data=None):
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        entries[name] = Path(source).read_bytes() if source else data

    # Reuse known runtime assets and unchanged license/backend source files.
    for name in prior:
        if name.startswith((PREFIX, 'licenses/', 'source/')):
            put(name, PRIOR / name)
    catalog = json.loads((LOCAL / 'catalog.json').read_text())
    assert sha(LOCAL / 'catalog.json') == build['runtime_catalog_sha256']
    for entry in catalog:
        source = host(entry['source'])
        assert source.stat().st_size == entry['bytes'] and sha(source) == entry['sha256'], entry['path']
        put(PREFIX + entry['path'], source)
    put(PREFIX + 'sleepingdogs-fex.nro', LOCAL / 'sleepingdogs-fex.nro')
    put(PREFIX + 'drive_c/SleepingDogs/sdndx4.dll', INLINE / 'sdndx4.dll')
    put(PREFIX + 'drive_c/sd-native-dxvk-h4-test.exe', INLINE / 'sd-native-dxvk-h4-test.exe')
    # The original build receipt has this legacy filename; update its contents.
    marker = dict(build='launcher-v4', proxy='native-dxvk-inline-v1',
                  nro_sha256=build['nro_sha256'], proxy_sha256=inline['proxy_sha256'],
                  saved_lsfg_preserved=True, hardware_tested=False)
    put(PREFIX + 'launcher/build-v2.json', data=encode(marker))
    for name in ('run-native-com-test.txt', 'launcher/debug-launch.txt'):
        put(PREFIX + name, data=b'0\n')
    put(PREFIX + 'launcher/renderer-choice.txt', data=b'2\n')
    old_proxy = ROOT / 'local/native-dxvk-compact-v1/sdndx4.dll'
    assert sha(old_proxy) == '3d2154bb29f4735e8d6818deeb95c2b9554dc3e7177780199a15cdb7514bd3dd'
    compiled_catalog = host('/home/blekjek/sleepingdogs-launcher-v4/source/system_catalog.h').read_text()
    assert sha(old_proxy) in compiled_catalog and inline['proxy_sha256'] in compiled_catalog
    for name in ('drive_c/SleepingDogs/sdndx4.dll', 'launcher/renderers/dxvk-native-h4/sdndx4.dll'):
        put('comparison-compact/' + PREFIX + name, old_proxy)
    old_nro = ROOT / 'dist/sd-launcher-v2-update' / PREFIX / 'sleepingdogs-fex.nro'
    assert sha(old_nro) == '5f8dfae7208fef6450489f97b1135bb4e90e2c57933a02003d2467e67c7b9677'
    put('rollback-launcher-v2/' + PREFIX + 'sleepingdogs-fex.nro', old_nro)
    for name in ('drive_c/SleepingDogs/sdndx4.dll', 'launcher/renderers/dxvk-native-h4/sdndx4.dll'):
        put('rollback-launcher-v2/' + PREFIX + name, old_proxy)
    put('rollback-launcher-v2/' + PREFIX + 'run-native-com-test.txt', data=b'0\n')

    for folder in ('src/launcher', 'src/native_dxvk_com', 'src/native_dxvk'):
        for p in (ROOT / folder).rglob('*'):
            if p.is_file():
                put('source/' + p.relative_to(ROOT).as_posix(), p)
    for p in (ROOT / 'tools').glob('*.py'):
        if any(word in p.name for word in ('launcher_v4', 'native_dxvk_inline', 'native_dxvk_present_overlap')):
            put('source/tools/' + p.name, p)
    for p in (ROOT / 'tests').glob('*'):
        if p.is_file() and any(word in p.name for word in ('inline', 'present_overlap')):
            put('source/tests/' + p.name, p)
    for name, digest in inline['source_files'].items():
        put('generated/inline/' + name, INLINE / name)
    for name, digest in build['generated_sources'].items():
        source = host('/home/blekjek/sleepingdogs-launcher-v4/' + name)
        assert sha(source) == digest, name
        put('generated/launcher/' + name, source)
    for name in ('lsfg.h', 'lsfg_config.h', 'sd_lsfg_pack.hpp'):
        put('generated/launcher/source/' + name, PRIOR / 'generated/launcher/source' / name)
    for name in ('LICENSE', 'THIRD_PARTY.md', 'docs/launcher-v4.md'):
        put(name, ROOT / name)
    for folder, label, names in (
        (LOCAL, 'launcher', ('build.json', 'test.json', 'binary-test.json', 'catalog.json')),
        (INLINE, 'inline', ('build.json', 'guest-test.json', 'host-test.json', 'scope-test.json')),
        (ROOT / 'local/native-dxvk-present-overlap-v1', 'present-overlap', ('test.json',)),
        (ROOT / 'local/launcher-v4-runtime', 'runtime', ('test.json',))):
        for name in names:
            put('reports/' + label + '-' + name, folder / name)
    validation = dict(
        status='PASS', build='launcher-v4', hardware_tested=False, game_fps_measured=False,
        nro_sha256=build['nro_sha256'], proxy_sha256=inline['proxy_sha256'],
        native=dict(checks=native['checks'], pixels_verified=native['pixels_verified'],
                    present_calls=native['present_calls'], concurrent_reference_pairs=native['concurrent_reference_pairs'],
                    inline_permission_cases=native['inline_permission_cases'],
                    overlapped_gpu_readback_bytes=native['overlapped_gpu_readback_bytes'],
                    live_interfaces=0, live_maps=0,
                    scope=native['scope']),
        pe32=dict(methods=guest['methods'], array_lengths=guest['array_lengths'],
                  mutated_bindings=guest['mutated_bindings'], scope='Actual PE32 wrappers with a modeled native endpoint.'),
        range_scope=scope, present_gate=overlap['gate_scenarios'],
        runtime_policy_cases=runtime['checks'], launcher_results=checks['test.json']['results'],
        arm64_heap_cases=len(checks['binary-test.json']['actual_arm64_heap_cases']),
        unresolved_strong_symbols=checks['binary-test.json']['unresolved_strong_symbols'],
        candidate_sources=inline['source_files'], builder_sources=build['builder_sources'],
        receipts={name: sha(ROOT / name) for name in (
            'local/launcher-v4/build.json', 'local/launcher-v4/test.json', 'local/launcher-v4/binary-test.json',
            'local/native-dxvk-inline-v1/build.json', 'local/native-dxvk-inline-v1/guest-test.json',
            'local/native-dxvk-inline-v1/host-test.json', 'local/native-dxvk-inline-v1/scope-test.json',
            'local/native-dxvk-present-overlap-v1/test.json', 'local/launcher-v4-runtime/test.json')})
    put('reports/validation.json', data=encode(validation))
    put('reports/latest-game.json', ROOT / 'reports/launcher-v3-game-499c25d436b6.json')
    # No LSFG logic changed: tie its previous real Vulkan validation to exact
    # hashes of the candidate sources, rather than claiming a new GPU test.
    lsfg = json.loads((ROOT / 'local/launcher-v3/lsfg-test.json').read_text())
    assert lsfg['status'] == 'PASS' and lsfg['validation_errors'] == 0
    unchanged = {}
    for name in ('source/lsfg.cpp', 'source/osk.cpp'):
        old = '/home/blekjek/sleepingdogs-launcher-v3/' + name
        new = host('/home/blekjek/sleepingdogs-launcher-v4/' + name)
        assert sha(new) == lsfg['source_files'][old]
        unchanged[name] = sha(new)
    adapter = ROOT / 'src/launcher/lsfg_vulkan.cpp'
    assert sha(adapter) == lsfg['source_files']['/mnt/d/Dev/Switch/SwitchHub/sleepingdogs-fex/src/launcher/lsfg_vulkan.cpp']
    unchanged['src/launcher/lsfg_vulkan.cpp'] = sha(adapter)
    put('reports/lsfg-unchanged-validation.json', data=encode(dict(
        status='PASS', scope='Reused v3 real Vulkan validation; exact generating source hashes unchanged.',
        sources=unchanged, previous_test_sha256=sha(ROOT / 'local/launcher-v3/lsfg-test.json'),
        validation_errors=0, generated_sessions=lsfg['generated_sessions'], new_gpu_test=False)))
    put('README.txt', data=INSTRUCTIONS.encode())
    game = [n[len(PREFIX + 'drive_c/SleepingDogs/'):] for n in entries if n.startswith(PREFIX + 'drive_c/SleepingDogs/')]
    assert set(game) <= {'d3d11.dll', 'dxgi.dll', 'sdndx4.dll'}, game
    assert not any(n.endswith(('lsfg.txt', 'lsfg.txt.old', 'native-performance-counters.txt')) for n in entries)
    assert not any(n.lower().endswith(('.zip', '.rar')) for n in entries)
    digest = lambda data: hashlib.sha256(data).hexdigest()
    put('SHA256SUMS.txt', data=''.join(digest(data) + '  ' + name + '\n' for name, data in sorted(entries.items())).encode())
    out = ROOT / 'dist/sd-launcher-v4-update'
    if out.exists():
        assert {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()} == set(entries), 'Keep prior deliveries immutable'
        for name, data in entries.items():
            assert (out / name).read_bytes() == data, name
    else:
        for name, data in entries.items():
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    for name, data in entries.items():
        assert sha(out / name) == digest(data), name
    (ROOT / 'reports/launcher-v4-validation.json').write_bytes(encode(validation))
    result = dict(status='PASS', path=str(out), files=len(entries), bytes=sum(len(x) for x in entries.values()),
                  all_hashes_verified=True, nro_sha256=build['nro_sha256'], proxy_sha256=inline['proxy_sha256'],
                  manifest_sha256=sha(out / 'SHA256SUMS.txt'), saved_lsfg_preserved=True,
                  zip_created=False, game_data_included=False, hardware_tested=False, game_fps_measured=False)
    (ROOT / 'reports/launcher-v4-folder.json').write_bytes(encode(result))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
