"""Package and verify the standalone native DXVK Horizon diagnostic.

Includes exact probe/DXVK sources, Mesa overlays, build evidence and notices.
The local prepared Mesa/SDK baselines remain prerequisites for rebuilding.
"""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'local/native-dxvk-probe-v1'
PREFIX = 'switch/sd-dxvk-native-probe/'
NAME = 'sd-dxvk-native-probe-horizon-v1'

INSTRUCTIONS = '''FEXTendo Native DXVK Horizon Probe v1 / H1

Tes renderer ARM64 mandiri. Sleeping Dogs belum memakai renderer ini.
Tidak ada data game, Wine/FEX guest, LSFG atau benchmark FPS game di paket ini.

1. Salin folder switch/ dari ZIP ke root SD.
2. Buka hbmenu dalam application/full-memory mode: tahan R saat membuka
   sebuah game dari HOME, lalu jalankan "FEXTendo Native DXVK Probe".
   Akses hbmenu melalui Album/applet mode tidak didukung oleh tes ini.
3. Gunakan kondisi referensi yang sama jika tersedia:
   OLED handheld, CPU 1728 / GPU 768 / RAM 1600 MHz. Program tidak mengubah clock.
4. Tes membuat device D3D11 FL11_0, menguji buffer Map/Unmap dan readback
   seluruh 921600 pixel hasil shader 1280x720. Setelah itu, bila berhasil,
   layar biru muncul selama 300 Present(1,0), sekitar 5 detik pada 60 Hz.
   Selesai tes kembali ke hbmenu. Tombol PLUS membatalkan saat tahap present.
5. Ambil file dari SD: switch/sd-dxvk-native-probe/result.json, probe.log,
   stderr.log dan sd-dxvk-native-probe_d3d11.log.

PASS harus berasal dari result.json pada Switch. Receipt BUILT/PASS di source/
adalah pemeriksaan build/host, bukan hasil hardware. RUNNING berarti tes belum
selesai (misalnya hang/crash); probe.log terakhir menunjukkan tahap terakhir.
Jika libnx gagal membuat window sebelum main(), file log bisa belum terbentuk.
Log dan probe.conf di folder diagnostik ini ditulis ulang saat setiap tes.

NRO hanya ditempatkan di folder sd-dxvk-native-probe. Runtime Sleeping Dogs
tidak perlu diubah untuk tes ini. Folder source/ dan notices/ untuk developer;
cukup folder switch/ yang disalin ke SD.

Sources: https://github.com/Ibnuard/sleepingdogs_nx/tree/experiment/native-dxvk-probe-v1
Record: source/project/docs/native-dxvk-probe-v1.md
Rebuild still needs the prepared local Mesa/SDK inputs documented there.
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def archive(path, entries):
    sums = ''.join(f'{digest(data)}  {name}\n' for name, data in sorted(entries.items()))
    payload = dict(entries, **{'SHA256SUMS.txt': sums.encode()})
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for name, data in sorted(payload.items()):
            assert not name.startswith('/') and '..' not in Path(name).parts, name
            info = zipfile.ZipInfo(name, (2026, 10, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, data)
    with zipfile.ZipFile(path) as package:
        assert len(package.namelist()) == len(set(package.namelist()))
        assert package.testzip() is None
        for line in package.read('SHA256SUMS.txt').decode().splitlines():
            expected, name = line.split('  ', 1)
            assert digest(package.read(name)) == expected, name
        switch_files = [name for name in package.namelist() if name.startswith('switch/')]
        assert switch_files == [PREFIX + 'sd-dxvk-native-probe.nro'], switch_files
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size,
                files=len(payload), all_member_hashes_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1'))
    args = parser.parse_args()
    native = json.loads((EVIDENCE / 'horizon-executable.json').read_text())
    assert native['status'] == 'BUILT'
    assert native['elf_audit']['status'] == native['nro_audit']['status'] == 'PASS'
    assert not any(native[key] for key in ('game_integration', 'guest_execution', 'hardware_tested', 'fps_gain_measured'))
    assert sha(native['nro']) == native['nro_sha256']
    assert sha(native['elf']) == native['elf_sha256']
    assert sha(ROOT / 'src/native_dxvk/probe_horizon_main.cpp') == native['source_sha256']
    assert sha(ROOT / 'tools/build_native_dxvk_horizon.py') == native['builder_sha256']
    assert sha(EVIDENCE / 'build-horizon.json') == native['dxvk_build_receipt_sha256']
    for group in ('inputs', 'header_inputs'):
        for name, expected in native[group].items():
            assert sha(name) == expected, name

    entries = {PREFIX + 'sd-dxvk-native-probe.nro': Path(native['nro']).read_bytes(),
               'README-TEST.txt': INSTRUCTIONS.encode()}
    project_files = [*sorted((ROOT / 'src/native_dxvk').glob('*')),
                     ROOT / 'tests/native_dxvk_abi.c', ROOT / 'THIRD_PARTY.md',
                     ROOT / 'docs/native-dxvk-probe-v1.md',
                     *[ROOT / 'tools' / name for name in (
                         'build_native_dxvk_probe.py', 'build_native_dxvk_horizon.py',
                         'package_native_dxvk_horizon.py', 'export_native_dxvk_probe.py',
                         'test_native_dxvk_probe.py', 'compile_native_probe_shaders.py',
                         'build_mesa_backport.py', 'build_mesa_shader_v14.py',
                         'build_mesa_cache_v141.py', 'port_common.py')],
                     ROOT / 'vendor/dxvk/native-probe-v1.patch',
                     ROOT / 'vendor/dxvk/native-probe-v1-inputs.json']
    for path in project_files:
        entries['source/project/' + path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for name in ('build-horizon.json', 'build-host.json', 'host-test.json', 'horizon-executable.json'):
        entries['source/evidence/' + name] = (EVIDENCE / name).read_bytes()
    entries['source/evidence/host-log.txt'] = (ROOT / 'reports/native-dxvk-probe-v1-host-log.txt').read_bytes()

    # Full pinned renderer tree, including its subprojects and adaptations.
    inputs = json.loads((ROOT / 'vendor/dxvk/native-probe-v1-inputs.json').read_text())
    horizon = json.loads((EVIDENCE / 'build-horizon.json').read_text())
    host = json.loads((EVIDENCE / 'build-host.json').read_text())
    test = json.loads((EVIDENCE / 'host-test.json').read_text())
    assert test['status'] == 'PASS' and test['draw_pixels_verified'] == 1280 * 720
    assert sha(EVIDENCE / 'build-host.json') == test['build_receipt_sha256']
    assert horizon['adapted_files'] == host['adapted_files']
    for name, expected in inputs['source_files'].items():
        path = args.work / 'source' / name
        assert sha(path) == horizon['adapted_files'].get(name, expected), name
        entries['source/dxvk/' + name] = path.read_bytes()

    # Retain versioned Mesa overlays, keeping their original source notices.
    mesa_root = Path('/home/blekjek')
    mesa_files = 0
    for version in ('v13', 'v14', 'v141'):
        work = mesa_root / ('sleepingdogs-mesa-' + version)
        if version == 'v141':
            receipt = json.loads((work / 'compile.json').read_text())
            changed = {Path(row['command'][-1]).relative_to(work / 'source').as_posix(): row['source_sha256']
                       for row in receipt['recipes'].values()}
            evidence_names = ('compile.json', 'dependencies.json')
        else:
            receipt = json.loads((work / 'prepared.json').read_text())
            changed = receipt['changed']
            evidence_names = ('prepared.json', 'build.json')
        for name, expected in changed.items():
            path = work / 'source' / name
            assert sha(path) == expected, (version, name)
            entries['source/mesa-overlays/' + version + '/' + name] = path.read_bytes()
            mesa_files += 1
        for name in evidence_names:
            entries['source/mesa-overlays/' + version + '/' + name] = (work / name).read_bytes()

    for path in sorted((ROOT / 'vendor/dxvk').glob('*LICENSE*')):
        if path.is_file(): entries['notices/' + path.name] = path.read_bytes()
    entries['notices/FEXTendo-probe-MIT'] = (ROOT / 'src/native_dxvk/LICENSE').read_bytes()
    entries['notices/libnx-ISC.txt'] = (ROOT / 'tools/scratch_pages/libnx-LICENSE.md.txt').read_bytes()
    mesa_source = mesa_root / 'sleepingdogs-mesa-v13/source'
    entries['notices/mesa-license.rst'] = (mesa_source / 'docs/license.rst').read_bytes()
    for path in sorted((mesa_source / 'licenses').glob('*')):
        if path.is_file(): entries['notices/mesa/' + path.name] = path.read_bytes()
    sdk = Path('/opt/devkitpro/portlibs/switch')
    for path in sorted((sdk / 'licenses/switch-libzstd').glob('*')):
        if path.is_file(): entries['notices/zstd/' + path.name] = path.read_bytes()
    entries['notices/zlib-LICENSE'] = (sdk / 'licenses/switch-zlib/LICENSE').read_bytes()
    entries['notices/expat-header-notice.h'] = (sdk / 'include/expat_external.h').read_bytes()
    entries['notices/blake3-README'] = (mesa_source / 'src/util/blake3/README').read_bytes()
    entries['notices/GNU-GPL-3'] = Path('/usr/share/common-licenses/GPL-3').read_bytes()
    gcc_notices = Path('/usr/share/doc/gcc-15-base/copyright').read_text()
    runtime_exception = 'GCC RUNTIME LIBRARY EXCEPTION\n' + gcc_notices.split('GCC RUNTIME LIBRARY EXCEPTION\n', 1)[1].split('\n\nlibquadmath/', 1)[0]
    entries['notices/GCC-RUNTIME-LIBRARY-EXCEPTION-3.1'] = runtime_exception.encode()
    gcc_header = next(Path(name) for name in native['header_inputs'] if name.endswith('/bits/c++config.h'))
    entries['notices/libstdc++-configuration-notice.h'] = gcc_header.read_bytes()

    assert all(not name.lower().endswith(('.exe', '.nsp', '.keys', '.kip', '.big', '.bix', '.dll')) for name in entries)
    destination = ROOT / 'dist'
    destination.mkdir(exist_ok=True)
    package = archive(destination / (NAME + '.zip'), entries)
    extracted = destination / NAME / PREFIX
    extracted.mkdir(parents=True, exist_ok=True)
    (extracted / 'sd-dxvk-native-probe.nro').write_bytes(entries[PREFIX + 'sd-dxvk-native-probe.nro'])
    (destination / NAME / 'README-TEST.txt').write_bytes(entries['README-TEST.txt'])
    (ROOT / 'reports/native-dxvk-horizon-v1.json').write_bytes(encode(native))
    report = dict(status='PASS', build=native['build'], package=package,
                  nro_sha256=native['nro_sha256'], nro_bytes=native['nro_bytes'],
                  native_receipt_sha256=sha(EVIDENCE / 'horizon-executable.json'),
                  dxvk_source_files=len(inputs['source_files']), mesa_overlay_files=mesa_files,
                  elf_audit=native['elf_audit'], nro_audit=native['nro_audit'],
                  builder_sha256=sha(__file__), guest_execution=False, game_integration=False,
                  hardware_tested=False, fps_gain_measured=False)
    (ROOT / 'reports/native-dxvk-horizon-v1-package.json').write_bytes(encode(report))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
