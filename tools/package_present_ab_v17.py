"""Package a single DXGI sync-interval experiment for the existing v17 NRO.

Run with Python on the Windows workspace. This does not build or replace code.
"""
from pathlib import Path
import argparse
import json
import re
import zipfile

from port_common import ROOT, profile_config, sha, write_json
from package_native_v15 import archive, digest


PREFIX = 'switch/sleepingdogs-fex/'
TARGET = PREFIX + 'launcher/presets/stable/dxvk-3.1.1/dxvk.conf'
BASELINE = ROOT / 'local/buffer-reuse-validate-uzpwmdes' / TARGET
BASELINE_HASH = '5478173e15ed78a9663dd0807856661c15e9fcf3df03469eb38a0ff68492121d'
V17_ZIP = ROOT / 'dist/sleepingdogs-fex-v17-scheduler-update.zip'
V17_ZIP_HASH = 'bc9db64210b3e55e0ebc1dff3fcff1c55c95b0a0a132409d60749c51c2173b5c'
V17_NRO_HASH = '366e9d7c175b48654c0faf9200dc04da98b4a6e1ba85da0771c8b7318b917fbb'
RECIPE = 'source/native-v15-lsfg/tools/port_common.py'
RECIPE_HASH = 'ddd3a3d2a749befeee88ebbe2914c515595181f1a578d6a9bfae571e093c0c62'
LOG_HASH = '2a6219ff780b5d7e222898e914c3dd94d0a9ae7f652ff54a771f64d8734de024'


def config_values(data):
    result = {}
    for line in data.decode('utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, value = map(str.strip, line.split('=', 1))
        assert key not in result, key
        result[key] = value
    return result


def readme(immediate):
    mode = 'IMMEDIATE test / syncInterval 0' if immediate else 'FIFO restore / syncInterval 1'
    expected = 'VK_PRESENT_MODE_IMMEDIATE_KHR' if immediate else 'VK_PRESENT_MODE_FIFO_KHR'
    value = '0' if immediate else '1'
    intro = ('Eksperimen satu variabel pada v17: hanya dxgi.syncInterval 1 menjadi 0.\n'
             if immediate else
             'Mengembalikan preset Stable standar ke dxgi.syncInterval 1.\n'
             'Ini bukan salinan konfigurasi khusus milik pengguna.\n')
    return (f'''Sleeping Dogs FEXTendo v17 - {mode}

{intro}Paket ini hanya berisi satu preset konfigurasi. Tetap gunakan NRO v17 yang
sudah berjalan baik. Tidak ada NRO atau DLL baru dan tidak ada frame generation.

Jika pernah mengubah preset ini sendiri, cadangkan file tersebut terlebih dahulu:
{TARGET}
Restore mengembalikan byte preset standar, bukan perubahan khusus pengguna.

1. Tutup FEXTendo sepenuhnya melalui HOME.
2. Ekstrak ZIP ini. Salin folder switch ke root SD dan timpa satu dxvk.conf itu.
3. Jalankan launcher, pilih DXVK 3.1.1 dan profil Stable (bukan Performance).
4. Gunakan Launch GUI, LSFG OFF, 1280x720, CPU 1728 / GPU 768 / RAM 1600 MHz.
   Pertahankan HUD, pengaturan game, rute, posisi dan arah kamera yang sama.
5. Lewati area tes sekali untuk pemanasan, lalu ukur di area yang sama.
6. Simpan fex-runtime.log sebelum membuka sesi berikutnya.

Konfirmasi dalam log:
[SD-SCHED-V17] mode=auto
dxgi.syncInterval = {value}
dxgi.maxFrameLatency = 2
dxvk.numCompilerThreads = 1
Present mode: {expected}

Jika marker/mode berbeda, konfigurasi tes belum terpakai. Launcher menerapkan
preset saat Play; tidak perlu mengedit drive_c/SleepingDogs/dxvk.conf sendiri.

Kedua ZIP menggunakan langkah yang sama. FIFO restore membatalkan eksperimen
IMMEDIATE sambil mempertahankan scheduler v17. IMMEDIATE meminta present tanpa
menunggu VBlank dan dapat menyebabkan tearing; seluruh fence tetap digunakan.
Belum ada hasil FPS dari eksperimen ini di Switch. Target 30 FPS belum terbukti.
''').encode('utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', type=Path,
        default=Path('C:/Users/Administrator/Pictures/pesnx/SS/08/fex-runtime.log'))
    args = parser.parse_args()
    assert sha(args.log) == LOG_HASH
    assert sha(V17_ZIP) == V17_ZIP_HASH
    assert sha(BASELINE) == BASELINE_HASH
    base = BASELINE.read_bytes()

    # The config has a delivered package receipt and still matches the recipe
    # included in the current v17 source package. Do not infer it from an old NRO.
    old_receipt = json.loads((ROOT / 'reports/fex-debug-package.json').read_text())
    assert old_receipt['payload_sha256'][TARGET] == BASELINE_HASH
    assert base == profile_config('stable', False).encode('utf-8')
    with zipfile.ZipFile(V17_ZIP) as z:
        assert z.testzip() is None
        assert digest(z.read(PREFIX + 'sleepingdogs-fex.nro')) == V17_NRO_HASH
        assert digest(z.read(RECIPE)) == RECIPE_HASH
        assert z.read(RECIPE) == (ROOT / 'tools/port_common.py').read_bytes()
    native = json.loads((ROOT / 'local/scheduler-v17/native.json').read_text())
    assert native['nro_sha256'] == V17_NRO_HASH
    assert sha(ROOT / 'local/scheduler-v17/sleepingdogs-fex.nro') == V17_NRO_HASH

    log = args.log.read_text(encoding='utf-8')
    assert '[SD-SCHED-V17] mode=auto' in log
    assert 'profile=stable renderer=dxvk-3.1.1 hud=Full' in log
    assert '[SD-LSFG-V15] configured off' in log
    assert 'Present mode: VK_PRESENT_MODE_FIFO_KHR' in log
    assert log.count('[WINE] info:  Effective configuration:') == 1
    effective = log.split('[WINE] info:  Effective configuration:', 1)[1]
    pairs = {}
    for line in effective.splitlines()[1:]:
        match = re.fullmatch(r'\[WINE\] info:    ([\w.]+) = (.*)', line)
        if not match:
            break
        key, value = match.groups()
        assert key not in pairs
        pairs[key] = value
    baseline_values = config_values(base)
    assert pairs == dict(baseline_values, **{'dxvk.hud': 'full'}), pairs

    before, after = b'dxgi.syncInterval = 1\n', b'dxgi.syncInterval = 0\n'
    assert base.count(before) == 1
    candidate = base.replace(before, after)
    assert candidate.replace(after, before) == base
    candidate_values = config_values(candidate)
    assert set(candidate_values) == set(baseline_values)
    changed = {k for k in candidate_values if candidate_values[k] != baseline_values[k]}
    assert changed == {'dxgi.syncInterval'}
    assert candidate_values['dxgi.maxFrameLatency'] == '2'
    assert candidate_values['dxvk.numCompilerThreads'] == '1'

    ROOT.joinpath('dist').mkdir(exist_ok=True)
    outputs = {}
    for label, data, filename, immediate in (
        ('test', candidate, 'sleepingdogs-fex-v17-present-immediate-test.zip', True),
        ('restore', base, 'sleepingdogs-fex-v17-present-fifo-restore.zip', False)):
        entries = {TARGET: data, 'README-INSTALL.txt': readme(immediate)}
        assert {n for n in entries if n.startswith('switch/')} == {TARGET}
        outputs[label] = archive(ROOT / 'dist' / filename, entries)
        with zipfile.ZipFile(outputs[label]['path']) as z:
            assert set(z.namelist()) == {TARGET, 'README-INSTALL.txt', 'SHA256SUMS.txt'}
            assert z.read(TARGET) == data

    assert sha(BASELINE) == BASELINE_HASH and sha(V17_ZIP) == V17_ZIP_HASH
    report = dict(status='PASS', experiment='v17-present-syncInterval-only',
        test=outputs['test'], restore=outputs['restore'], runtime_files=[TARGET],
        changed_config_keys=['dxgi.syncInterval'],
        baseline=dict(path=str(BASELINE), sha256=BASELINE_HASH,
            receipt='reports/fex-debug-package.json',
            source_archive=str(V17_ZIP), source_archive_sha256=V17_ZIP_HASH,
            recipe=RECIPE, recipe_sha256=RECIPE_HASH),
        candidate_config_sha256=digest(candidate),
        restore_config_sha256=digest(base),
        baseline_config=baseline_values, candidate_config=candidate_values,
        latest_log=dict(path=str(args.log), sha256=LOG_HASH,
            effective_configuration=pairs, baseline_matches_effective_configuration=True,
            launcher_appended_hud='full',
            clocks_mhz=dict(cpu=1728, gpu=768, ram=1600),
            clock_source='User confirmation; these values are not measured by the log parser'),
        baseline_nro_sha256=V17_NRO_HASH, nro_included=False, dlls_included=False,
        active_game_config_included=False, profile_selection_included=False,
        other_profiles_included=False, all_other_config_values_preserved=True,
        restores_standard_preset_exactly=True, restores_unknown_user_customizations=False,
        baseline_inputs_preserved=True, zip_crc_and_hash_manifests_verified=True,
        hardware_tested=False, fps_gain_measured=False,
        packager_sha256=sha(Path(__file__)), docs_sha256=sha(ROOT / 'docs/present-ab-v17.md'))
    write_json(ROOT / 'reports/present-ab-v17-package.json', report)
    print(json.dumps(dict(status='PASS', **outputs), indent=2))


if __name__ == '__main__':
    main()
