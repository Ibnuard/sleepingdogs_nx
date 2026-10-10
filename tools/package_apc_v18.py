"""Package verified v18 APC notification routing and the delivered v17 rollback.

Run in WSL after the host, linked ARM64 and inherited checks have passed.
"""
from pathlib import Path
import json
import zipfile

from port_common import ROOT, sha, write_json
from prepare_apc_v18 import NATIVE, BASE
from package_native_v15 import archive, digest, encode

PREFIX = 'switch/sleepingdogs-fex/'
SOURCE = 'source/apc-v18/'
NAME = 'sleepingdogs-fex-v18-apc-update'
OLD_ZIP = 'bc9db64210b3e55e0ebc1dff3fcff1c55c95b0a0a132409d60749c51c2173b5c'
OLD_NRO = '366e9d7c175b48654c0faf9200dc04da98b4a6e1ba85da0771c8b7318b917fbb'
OLD_ELF = '73a8dfde96b51a7c77da97b8223bf536c20ecee0174ae9319c54b78e8d709cf0'
LOG_REPORT = 'gameplay-v17-immediate-31ac6f92b1bd.json'
LOG_HASH = '31ac6f92b1bd4bdcb043adf6163ae32f9497e811ff68a44bfa7517189ed47e45'
REPORTS = ('apc-v18-host-check.json', 'apc-v18-binary.json',
    'apc-v18-native-check.json', 'apc-v18-diagnostic-binary.json',
    'apc-v18-direct-sync-binary.json', 'apc-v18-low-window-binary.json',
    'apc-v18-shader-binary.json')


def main():
    baseline = ROOT / 'dist/sleepingdogs-fex-v17-scheduler-update.zip'
    assert sha(baseline) == OLD_ZIP
    with zipfile.ZipFile(baseline) as z:
        assert z.testzip() is None and len(z.namelist()) == len(set(z.namelist()))
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            expected, name = line.split('  ', 1)
            assert digest(z.read(name)) == expected, name
        original = {n: z.read(n) for n in z.namelist()
                    if n.startswith((PREFIX, 'source/'))}
    assert digest(original[PREFIX + 'sleepingdogs-fex.nro']) == OLD_NRO
    previous = json.loads(original['source/scheduler-v17/native.json'])
    assert previous['nro_sha256'] == OLD_NRO and previous['elf_sha256'] == OLD_ELF

    local = ROOT / 'local/apc-v18'
    native = json.loads((local / 'native.json').read_text())
    prepared = json.loads((local / 'prepared.json').read_text())
    baseline_prepared = json.loads((ROOT / 'local/scheduler-v17/prepared.json').read_text())
    assert native['status'] == 'BUILT' and native['baseline_reproduced']
    assert native['baseline_nro_sha256'] == OLD_NRO
    assert native['baseline_elf_sha256'] == OLD_ELF
    for key in ('scheduler_unchanged', 'fex_engine_unchanged', 'dxvk_unchanged',
                'mesa_unchanged', 'lsfg_unchanged'):
        assert native[key], key
    for key in ('driver_cache_id', 'driver_library_sha256', 'backend_library_sha256'):
        assert native[key] == previous[key], key
    for name, expected in native['inputs'].items():
        assert sha(name) == expected, name
    for name, expected in prepared['input_sha256'].items():
        assert expected == baseline_prepared['files'][name]
        assert sha(BASE / name) == expected, name
    for name, expected in prepared['files'].items():
        assert sha(NATIVE / name) == expected, name
    assert sha(NATIVE / 'dlls/ntdll/unix/sd_apc_notify_v18.h') == sha(
        ROOT / 'src/low_window/sd_apc_notify_v18.h')
    nro = local / 'sleepingdogs-fex.nro'
    assert sha(nro) == native['nro_sha256']
    assert sha(ROOT / 'local/symbols/sleepingdogs-apc-v18.elf') == native['elf_sha256']
    reports = {n: json.loads((ROOT / 'reports' / n).read_text()) for n in REPORTS}
    assert all(r['status'] == 'PASS' for r in reports.values())
    assert reports['apc-v18-host-check.json']['source_files'] == prepared['files']
    checked_sources = {}
    for report in reports.values():
        for name, expected in report.get('sources', {}).items():
            assert sha(ROOT / name) == expected, name
            checked_sources[name] = expected
    for name in REPORTS[1:]:
        assert reports[name]['elf_sha256'] == native['elf_sha256'], name
    assert reports['apc-v18-native-check.json']['nro_sha256'] == native['nro_sha256']
    assert reports['apc-v18-native-check.json']['nro_matches_elf']
    layout = json.loads((local / 'apc-layout.json').read_text())
    assert layout['build_elf_sha256'] == native['elf_sha256']
    assert layout['linked_into_runtime'] is False
    assert layout['object_sha256'] == sha(local / 'apc-layout.o')
    assert layout['probe_sha256'] == sha(local / 'apc-layout.c')
    assert layout['production_sha256'] == prepared['files']['dlls/ntdll/unix/horizon.c']
    for name, expected in layout['production_dependencies'].items():
        assert sha(name) == expected, name
    tested_layout = reports['apc-v18-binary.json']['layout']
    assert tested_layout['metadata_sha256'] == sha(local / 'apc-layout.json')
    for key in ('object_sha256', 'probe_sha256', 'production_sha256'):
        assert tested_layout[key] == layout[key], key
    contract = reports['apc-v18-binary.json']['reachable_input_contract']
    for key, name in (('disassembly_sha256', 'apc-notifier-disassembly.txt'),
                      ('caller_evidence_sha256', 'apc-notifier-caller.txt')):
        assert contract[key] == layout[key] == sha(local / name), name
    assert contract['host_report_sha256'] == sha(ROOT / 'reports/apc-v18-host-check.json')
    analysis = json.loads((ROOT / 'reports' / LOG_REPORT).read_text())
    assert analysis['status'] == 'ANALYZED' and analysis['sha256'] == LOG_HASH

    entries = dict(original)
    rollback = {PREFIX + nro.name: original[PREFIX + nro.name]}
    entries[PREFIX + nro.name] = nro.read_bytes()
    changed = [PREFIX + nro.name]
    for name, data in original.items():
        if not name.startswith(PREFIX) or not name.endswith('.json'):
            continue
        obj = json.loads(data)
        if obj.get('nro_sha256') == OLD_NRO:
            obj.update(nro_sha256=native['nro_sha256'], additional_overlay=native['build'],
                       hardware_tested=False, fps_gain_measured=False)
            entries[name] = encode(obj)
            rollback[name] = data
            changed.append(name)
    identity = PREFIX + 'launcher/apc-v18.json'
    entries[identity] = encode(dict(build=native['build'], nro_sha256=native['nro_sha256'],
        inherited_build='sleepingdogs-v17-scheduler', target_resolution=[1280, 720],
        default_apc_targeted_wake=True, setting='apc-targeted-wake.txt',
        required_sync_mode=2, scheduler_v17_preserved=True,
        accepted_user_apc_queued_wake='target thread only',
        legacy_router_and_shared_broadcast_preserved=True,
        driver_cache_id=native['driver_cache_id'], hardware_tested=False, fps_gain_measured=False))
    rollback[identity] = encode(dict(build='sleepingdogs-v17-scheduler', rolled_back=True,
        nro_sha256=OLD_NRO, apc_targeted_queued_wake_available=False))
    changed.append(identity)

    for name in prepared['files']:
        entries[SOURCE + 'native/' + name] = (NATIVE / name).read_bytes()
    files = ('tools/prepare_apc_v18.py', 'tools/build_apc_v18.py',
        'tools/package_apc_v18.py', 'src/low_window/sd_apc_notify_v18.h',
        'tests/check_apc_v18.py', 'tests/check_apc_v18_binary.py',
        'tests/extract_apc_v18_layout.py', 'tests/check_lsfg_native_binary.py',
        'docs/apc-v18.md')
    for name in files:
        entries[SOURCE + name] = (ROOT / name).read_bytes()
    for name in checked_sources:
        entries[SOURCE + name] = (ROOT / name).read_bytes()
    # Include any separate host fixtures as well as the named entry points.
    for path in (ROOT / 'tests').glob('*apc*v18*'):
        if path.is_file() and path.suffix in ('.py', '.c', '.h'):
            entries[SOURCE + 'tests/' + path.name] = path.read_bytes()
    for name in ('native.json', 'prepared.json', 'v18.patch',
                 'apc-layout.json', 'apc-layout.o', 'apc-layout.c', 'apc-layout.log',
                 'apc-notifier-disassembly.txt', 'apc-notifier-caller.txt'):
        entries[SOURCE + name] = (local / name).read_bytes()
    for name in REPORTS:
        entries[SOURCE + 'reports/' + name] = (ROOT / 'reports' / name).read_bytes()
    entries[SOURCE + 'reports/latest-v17-immediate-log-analysis.json'] = (
        ROOT / 'reports' / LOG_REPORT).read_bytes()
    entries['README-INSTALL.txt'] = '''Sleeping Dogs FEXTendo v18 - APC notification candidate

Tutup FEXTendo sepenuhnya melalui HOME. Salin seluruh folder switch dari ZIP
ke root SD dan timpa file yang disertakan. Paket tidak menimpa preset atau
preferensi; pengaturan Stable/IMMEDIATE dari tes terakhir tetap digunakan.

Tes: DXVK 3.1.1, Stable, Launch GUI, LSFG OFF, 1280x720.
Gunakan CPU 1728 / GPU 768 / RAM 1600 MHz, HUD dan pengaturan game yang sama.
Lewati area sekali untuk pemanasan lalu bandingkan rute, posisi dan kamera sama.
Simpan fex-runtime.log sebelum membuka sesi berikutnya.

Pastikan log mencatat runtime 0.1.0-v18-apc serta:
[SD-APC-V18] enabled=1 active=1
[SD-SCHED-V17] mode=auto
Untuk perbandingan dengan tes terakhir: dxgi.syncInterval = 0 dan
Present mode: VK_PRESENT_MODE_IMMEDIATE_KHR.

v18 membatasi notifikasi antrean APC biasa ke waiter milik thread tujuan.
Callback APC, hasil wait, deadline, broadcast legacy dan scheduler v17 tetap.
Counter unrelated_candidates_skipped adalah kandidat, bukan waktu yang dihemat
atau jumlah kenaikan FPS. Dampak hardware belum diuji; 30 FPS belum terbukti.

A/B pada NRO yang sama: buat switch/sleepingdogs-fex/apc-targeted-wake.txt
berisi angka 0 dan newline, tutup dari HOME, lalu jalankan ulang. Log menjadi
enabled=0 active=0 dan memakai rute notifikasi v17. Hapus file atau isi 1 lalu
restart penuh untuk mengaktifkan lagi. Jangan ubah auto-affinity.txt untuk tes ini.

ZIP rollback-v17 mengembalikan NRO v17 yang sudah dikirim serta metadata yang
diubah. Preset IMMEDIATE/FIFO, preferensi, save dan data game tidak disertakan.
Detail: source/apc-v18/docs/apc-v18.md
'''.encode('utf-8')
    rollback['README-INSTALL.txt'] = '''Tutup FEXTendo sepenuhnya melalui HOME.
Salin folder switch dari ZIP ini ke root SD untuk mengembalikan NRO v17 yang
sudah dikirim dan metadata terkait. v17 mengabaikan apc-targeted-wake.txt.
Scheduler v17 tetap aktif sesuai pilihan sebelumnya. Preset IMMEDIATE/FIFO,
preferensi, save dan data game tidak diubah oleh paket rollback ini.
'''.encode('utf-8')

    runtime = {n: d for n, d in entries.items() if n.startswith(PREFIX)}
    old_runtime = {n: d for n, d in original.items() if n.startswith(PREFIX)}
    assert set(runtime) == set(old_runtime) | {identity}
    assert all(n == PREFIX + nro.name or n.endswith('.json') for n in changed)
    assert all(n in changed or d == old_runtime[n] for n, d in runtime.items())
    assert not any(n.endswith(('.txt', '.conf')) or '/presets/' in n for n in runtime)
    restored = dict(runtime)
    restored.update({n: d for n, d in rollback.items() if n.startswith(PREFIX)})
    assert all(restored[n] == d for n, d in old_runtime.items())
    assert digest(restored[PREFIX + nro.name]) == OLD_NRO
    assert json.loads(restored[identity])['rolled_back']

    update = archive(ROOT / 'dist' / (NAME + '.zip'), entries)
    undo = archive(ROOT / 'dist/sleepingdogs-fex-v18-rollback-v17.zip', rollback)
    staged = ROOT / 'dist' / NAME
    for name, data in {**runtime, 'README-INSTALL.txt': entries['README-INSTALL.txt']}.items():
        dest = staged / name
        assert dest.resolve().is_relative_to(staged.resolve())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    assert sha(baseline) == OLD_ZIP
    write_json(ROOT / 'reports/apc-v18-package.json', dict(status='PASS',
        build=native['build'], update=update, rollback=undo,
        nro_sha256=native['nro_sha256'], elf_sha256=native['elf_sha256'],
        baseline_zip_sha256=OLD_ZIP, baseline_nro_sha256=OLD_NRO,
        baseline_elf_sha256=OLD_ELF, baseline_preserved=True,
        rollback_restores_v17=True, runtime_changed=changed,
        preference_files_included=False, presets_included=False,
        current_user_present_mode_preserved=True,
        scheduler_unchanged=True, fex_engine_unchanged=True,
        dxvk_unchanged=True, mesa_unchanged=True, lsfg_unchanged=True,
        hardware_tested=False, fps_gain_measured=False,
        source_log_sha256=LOG_HASH, source_analysis_sha256=sha(ROOT / 'reports' / LOG_REPORT),
        test_reports={n: sha(ROOT / 'reports' / n) for n in REPORTS},
        runtime_files={n: digest(d) for n, d in runtime.items()},
        packager_sha256=sha(Path(__file__)), docs_sha256=sha(ROOT / 'docs/apc-v18.md')))
    print(json.dumps(dict(status='PASS', update=update, rollback=undo), indent=2), flush=True)


if __name__ == '__main__':
    main()
