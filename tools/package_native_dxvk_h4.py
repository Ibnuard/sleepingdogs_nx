"""Create the H4 COM/game update directory, with preserved x86 choices and v18 rollback."""
from pathlib import Path
import fcntl
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tarfile
import zipfile
from urllib.parse import quote
from build_native_dxvk_h4 import BUILD,APP_VERSION,LOCAL

ROOT=Path(__file__).resolve().parents[1]
PREFIX='switch/sleepingdogs-fex/'
NAME='sd-dxvk-native-h4-v9-update'
LAUNCHER_INPUTS=ROOT/'vendor/wine/native-dxvk-h4-launcher-inputs.json'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(data):return hashlib.sha256(data).hexdigest()
def encode(data):return (json.dumps(data,indent=2)+'\n').encode()

INSTRUCTIONS='''FEXTendo / Sleeping Dogs Native DXVK H4 v9 - bridge + Map + batching

FOLDER SIAP SALIN, TANPA ZIP. Untuk instalasi lengkap yang sudah berjalan.
Resolusi tetap 1280x720. Tidak ada game atau save disertakan.

Acuan v8.1 Light: laporan 20-22 FPS, keramaian 16, peak terbatas 30.
Lima jendela Present akhir: 20,67 FPS. Belum ada pengukuran FPS v9 di Switch.

Perubahan v9:
- Paket bridge memakai satu probe baca/tulis Wine; pemeriksaan batas alamat,
  ukuran, izin halaman dan penanganan fault dipertahankan pada setiap call.
- WRITE_DISCARD tidak mengosongkan ulang shadow yang dapat dipakai kembali.
  Mode yang mempertahankan isi tetap copy-in; Unmap tetap full copy-out.
  Ini mengurangi kerja memori, belum merupakan zero-copy.
- Native Performance mengaktifkan batching otomatis yang sudah ada: maksimal
  24 chunk, hanya saat >=2 submission belum selesai, tetap memakai cost cap.
  Flush wajib untuk Present/readback/sinkronisasi tetap dipertahankan.
- COM self-test menambah delapan guard memori dan 183 byte partial-DISCARD
  readback. COM sekarang juga meminta batching ON.

1. Tutup aplikasi sepenuhnya dari HOME. Salin switch/ di folder utama ini
   ke root SD dan timpa file terkait. Gunakan forwarder full-memory yang
   sudah berhasil. source/ dan notices/ tidak perlu disalin ke SD.
2. Jalankan COM self-test. Hasil yang diperlukan: build native-dxvk-h4-v9,
   PASS, exit 00000000, memory_guard_checks=8,
   discard_partial_bytes_verified=183, sampler_roundtrip_slots_verified=72,
   dsv_guard_checks=16. Jika gagal, simpan log lalu gunakan rollback-v8.1.
3. Simpan log COM sebelum menjalankan game:
   switch/sleepingdogs-fex/drive_c/native-dxvk-h4-result.json
   switch/sleepingdogs-fex/drive_c/native-dxvk-h4-guest.log
   switch/sleepingdogs-fex/native-dxvk-h4/runtime.log
   switch/sleepingdogs-fex/native-dxvk-h4/HKShip.exe_d3d11.log
4. Setelah PASS, salin start-game-light/switch/ ke root SD. Jalankan GUI,
   DXVK Native ARM64, Performance, FPS HUD, Light 720p. LSFG OFF pada native.
   start-game/switch/ tersedia bila ingin memakai nilai detail game saat ini.
5. Uji lokasi/kamera dan rute ramai yang sama, cache sudah hangat. Catat
   FPS biasa/minimum, pause/resume dan keluar normal. Pakai clock yang sama;
   referensi sebelumnya CPU 1728 / GPU 768 / RAM 1600 MHz.
6. Untuk mengisolasi batching: tutup HOME, salin batch-off/switch/ ke root SD,
   lalu pilih Performance lagi. Ini mengubah tepat satu opsi pada profil
   native Performance. batch-on/switch/ mengaktifkannya kembali. Profil
   native lainnya tetap batching OFF; renderer x86 tidak diubah.

Log game yang dikirim, relatif switch/sleepingdogs-fex/:
  fex-runtime.log
  native-dxvk-h4/HKShip.exe_d3d11.log
  crash.log jika terjadi crash baru

Marker: BUILD native-dxvk-h4-v9; memory_probe=single-readwrite;
discard_zero_fill=off. [SD-NDX-MAP] mencatat zero_fill_skipped_bytes.
[SD-DXVK-BATCH] v2 enabled=1 untuk Performance ON, enabled=0 untuk OFF.
Counter ini menunjukkan kerja yang dihindari, bukan waktu GPU atau gain FPS.
Present windows dapat mencakup menu/loading; log async dapat kehilangan tail.

PEMULIHAN: Tutup HOME lalu salin rollback-v8.1/switch/ ke root SD untuk
mengembalikan NRO, DLL native dan seluruh profil launcher v8.1, lalu masuk
game dengan native + Light 720p. Data/save tetap. rollback-v18/switch/
tersedia untuk jalur x86 lama dan mematikan penerapan Light. Gunakan Settings
> Game detail > Restore original jika ingin mengembalikan XML kualitas awal.

start-com-test/switch/ mengulang COM. Folder v8.1 asli tetap terpisah.
SHA256SUMS.txt memuat checksum. Detail dan batas pengujian:
source/project/docs/native-dxvk-h4-v9-memory-batching.md
Ini build eksperimen. Hasil lokal tidak menjamin 30 FPS atau kesiapan produksi.
'''


def native_fifo_config(data,batching=False):
    """Keep FIFO and make the existing native-only batching policy explicit."""
    config=data.decode()
    config,count=re.subn(r'(?m)^(dxgi\.syncInterval\s*=\s*)[^\r\n]+$',r'\g<1>1',config)
    if count!=1:raise ValueError('Expected one active dxgi.syncInterval in native profile')
    if 'd3d11.sdSubmissionBatching' in config:raise ValueError('Batching already present in canonical input')
    return (config+'d3d11.sdSubmissionBatching = '+('True' if batching else 'False')+'\n').encode()

def launcher_payload():
    """Only binary sets/config templates; no user preferences or game data."""
    from port_common import profile_config
    from sleepingdogs_performance_hud import performance_config
    inputs=json.loads(LAUNCHER_INPUTS.read_text())
    for name,expected in inputs['files'].items():assert sha(ROOT/name)==expected,('launcher input changed',name)
    entries={};legacy=json.loads((ROOT/'reports/native-v15-package.json').read_text())
    for name in ('d3d9.dll','d3d11.dll','dxgi.dll'):
        data=(ROOT/'local/dxvk-native-v15'/name).read_bytes();target=PREFIX+'launcher/renderers/dxvk-3.1.1/'+name
        assert digest(data)==legacy['runtime_files'][target];entries[target]=data
    with tarfile.open(ROOT/inputs['async_archive'],'r:gz') as archive:
        for name in ('d3d9.dll','d3d11.dll','dxgi.dll'):
            entries[PREFIX+'launcher/renderers/dxvk-2.7.1-async/'+name]=archive.extractfile('dxvk-gplasync-v2.7.1-1/x32/'+name).read()
    for renderer in ('dxvk-3.1.1','dxvk-2.7.1-async'):
        async_mode=renderer.endswith('async')
        entries[PREFIX+'launcher/renderers/'+renderer+'/dxvk.conf']=profile_config('balanced',async_mode).encode()
        for profile in ('balanced','low-latency','stable','quality','performance'):
            config=performance_config(async_mode) if profile=='performance' else profile_config(profile,async_mode)
            entries[PREFIX+'launcher/presets/'+profile+'/'+renderer+'/dxvk.conf']=config.encode()
    old=PREFIX+'launcher/renderers/dxvk-3.1.1/'
    native=PREFIX+'launcher/renderers/dxvk-native-h4/'
    entries[native+'d3d9.dll']=entries[old+'d3d9.dll']
    entries[native+'dxvk.conf']=entries[old+'dxvk.conf']
    for name in ('d3d11.dll','dxgi.dll','sdndx4.dll'):entries[native+name]=(LOCAL/name).read_bytes()
    for name in list(entries):
        if '/launcher/presets/' in name and '/dxvk-3.1.1/' in name:
            entries[name.replace('/dxvk-3.1.1/','/dxvk-native-h4/')]=entries[name]
    for name in entries:
        if '/dxvk-native-h4/' in name and name.endswith('/dxvk.conf'):
            entries[name]=native_fifo_config(entries[name],'/presets/performance/' in name)
    return entries

def main():
    LOCAL.mkdir(parents=True,exist_ok=True);lock=(LOCAL/'packaging.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    receipts={name:json.loads((LOCAL/(name+'.json')).read_text()) for name in ('build','host-test','abi-check','launcher-check','game-imports','window-check','logging-check','guest-output-check','dispatch-benchmark','guest-lookup','array-check','guest-maps','game-quality','game-quality-ui','guest-transport','memory-probes','native-batch')}
    build=receipts['build'];assert build['status']=='BUILT' and build['baseline_reproduced']
    assert all(receipts[n]['status']=='PASS' for n in receipts if n!='build')
    guest=receipts['guest-output-check']
    assert guest['pe32_proxy_executed_on_windows'] and guest['modeled_native_endpoint']
    assert guest['cases']['current']['exit_code']==0 and not guest['cases']['current']['expected_regression_failure']
    for case in ('v4-scalar','v4-publication'):
        assert guest['cases'][case]['exit_code']==1 and guest['cases'][case]['expected_regression_failure']
    for receipt in (build,receipts['host-test'],guest,receipts['dispatch-benchmark'],receipts['guest-lookup'],receipts['array-check'],receipts['guest-maps'],receipts['game-quality'],receipts['game-quality-ui'],receipts['guest-transport'],receipts['memory-probes'],receipts['native-batch']):
        for name,expected in receipt['source_files'].items():assert sha(ROOT/name)==expected,('source changed',name)
    assert sha(ROOT/'tools/build_native_dxvk_h4.py')==build['builder_sha256']
    for name,tool in [('host-test','test_native_dxvk_h4_host.py'),('abi-check','check_native_dxvk_h4_abi.py'),('launcher-check','check_native_dxvk_h4_launcher.py'),('game-imports','check_native_dxvk_h4_imports.py'),('window-check','test_native_dxvk_h4_window.py'),('logging-check','test_native_dxvk_h4_logging.py'),('guest-output-check','test_native_dxvk_h4_guest_outputs.py'),('dispatch-benchmark','benchmark_native_dxvk_h4_dispatch.py'),('guest-lookup','test_native_dxvk_h4_guest_lookup.py'),('array-check','test_native_dxvk_h4_arrays.py'),('guest-maps','test_native_dxvk_h4_guest_maps.py'),('game-quality','test_native_dxvk_h4_game_quality.py'),('game-quality-ui','test_native_dxvk_h4_game_quality_ui.py'),('guest-transport','test_native_dxvk_h4_guest_transport.py'),('memory-probes','test_native_dxvk_h4_memory.py'),('native-batch','test_native_dxvk_h4_batch.py')]:
        assert sha(ROOT/'tools'/tool)==receipts[name]['runner_sha256']
    for name,expected in build['inputs'].items():assert sha(name)==expected
    for name,expected in build['header_inputs'].items():assert sha(name)==expected
    assert sha(ROOT/'vendor/wine/native-dxvk-h3-inputs.json')==build['input_manifest_sha256']
    assert sha(LOCAL/'sleepingdogs-fex.nro')==build['nro_sha256']
    nro=(LOCAL/'sleepingdogs-fex.nro').read_bytes();assert nro[0x10:0x14]==b'NRO0'
    for marker in (('sleepingdogs-'+BUILD).encode(),b'dxvk-native-h4',b'DXVK Native ARM64',b'[SD-NDX-WINDOW] handoff complete',
                   b'sd-native-dxvk-h4-test.exe',b'sdndx4.dll',b'd3d11,dxgi,sdndx4=n;d3d9=n,b',b'[SD-NDX-COM] FIRST_PRESENT',b'[SD-NDX-WORKER]',
                   b'[SD-NDX-CALL] BEGIN',b'[SD-NDX-CALL] END',b'[SD-NDX-PROGRESS]',b'[SD-NDX-ACTIVE]',b'[SD-NDX-LOG] async queue=512',b'[SD-NDX-PERF] progress_stride=256',b'[SD-NDX-PERF] proxy_lookup=hash native_pointer_array_inline=128',b'[SD-NDX-PERF] map_shadow_cache=16MiB/4 exact-size idle entries; discard zeroing=off',b'Light 720p',b'Restore original',b'[SD-NDX-PERF] guest_endpoint=acquire-release',b'[SD-NDX-PERF] memory_probe=single-readwrite discard_zero_fill=off',b'[SD-NDX-MAP] discard_maps='):
        assert marker in nro,('missing binary marker',marker)
    asset=struct.unpack_from('<I',nro,0x18)[0];assert nro[asset:asset+4]==b'ASET'
    nacp_offset,nacp_size=struct.unpack_from('<QQ',nro,asset+0x18);nacp=nro[asset+nacp_offset:asset+nacp_offset+nacp_size]
    assert len(nacp)==0x4000 and nacp.startswith(b'FEXTendo Native DXVK H4\0') and APP_VERSION.encode()+b'\0' in nacp
    assert not any(build[k] for k in ('hardware_tested','com_guest_execution_tested','game_integration_tested','game_fps_measured'))
    entries=launcher_payload()
    assert receipts['launcher-check']['source_sha256']==build['patches']['runtime']['source_sha256']
    assert receipts['window-check']['runtime_source_sha256']==build['patches']['runtime']['source_sha256']
    assert receipts['logging-check']['runtime_source_sha256']==build['patches']['runtime']['source_sha256']
    assert receipts['game-quality-ui']['runtime_sha256']==build['patches']['runtime']['source_sha256']
    assert receipts['game-quality-ui']['settings_sha256']==build['patches']['settings']['source_sha256']
    for check in ('window-check','logging-check'):
        for name,expected in receipts[check]['source_files'].items():assert sha(ROOT/name)==expected,name
    assert receipts['launcher-check']['payload_sha256']=={name:digest(data) for name,data in entries.items()}
    assert receipts['abi-check']['inventory_sha256']==sha(ROOT/'src/native_dxvk_com/com_inventory.json')
    inventory=json.loads((ROOT/'src/native_dxvk_com/com_inventory.json').read_text())
    assert inventory['generator_sha256']==sha(ROOT/'tools/generate_native_dxvk_com.py')
    for name,expected in inventory['header_inputs'].items():assert sha(name)==expected
    pin=json.loads((ROOT/'vendor/wine/native-dxvk-h3-inputs.json').read_text())
    assert sha(pin['winternl_header'])==pin['winternl_sha256']
    assert sha(pin['wow64_virtual_source'])==pin['wow64_virtual_sha256']
    for item in receipts['game-imports']['graphics_imports']:assert sha(LOCAL/item['dll'].lower())==item['proxy_sha256']
    for name,audit in build['pe_audits'].items():assert sha(LOCAL/name)==audit['sha256']
    entries.update({PREFIX+'sleepingdogs-fex.nro':nro,
                    PREFIX+'drive_c/sd-native-dxvk-h4-test.exe':(LOCAL/'sd-native-dxvk-h4-test.exe').read_bytes(),
                    PREFIX+'run-native-com-test.txt':b'1\n',
                    PREFIX+'native-dxvk-h4/com-test.conf':b'dxgi.syncInterval = 1\ndxvk.numCompilerThreads = 2\ndxvk.hud = fps\nd3d11.sdSubmissionBatching = True\n',
                    'README-INSTALL.txt':INSTRUCTIONS.encode()})
    for mode,value in [('start-com-test',b'1\n'),('start-game',b'0\n'),('start-game-light',b'0\n')]:
        entries[mode+'/'+PREFIX+'run-native-com-test.txt']=value
        entries[mode+'/'+PREFIX+'launcher/renderer-choice.txt']=b'2\n'
        if mode!='start-com-test':entries[mode+'/'+PREFIX+'launcher/game-quality.txt']=b'1\n' if mode=='start-game-light' else b'0\n'
    # Both A/B overlays change exactly the native Performance batching option.
    performance=PREFIX+'launcher/presets/performance/dxvk-native-h4/dxvk.conf'
    for variant,value in [('batch-on',b'True'),('batch-off',b'False')]:
        data,count=re.subn(rb'(?m)^(d3d11\.sdSubmissionBatching = )True$',lambda m:m[1]+value,entries[performance])
        assert count==1
        entries[variant+'/'+performance]=data
    # Preserve a self-contained native rollback at the same Light resolution.
    prior=ROOT/'dist/sd-dxvk-native-h4-v8.1-update'
    prior_receipt=json.loads((ROOT/'reports/native-dxvk-h4-v8.1-folder.json').read_text())
    assert sha(prior/'SHA256SUMS.txt')==prior_receipt['checksums_sha256']
    for line in (prior/'SHA256SUMS.txt').read_text().splitlines():
        expected,name=line.split('  ',1)
        if not name.startswith(PREFIX):continue
        file=prior/name;assert sha(file)==expected
        entries['rollback-v8.1/'+name]=file.read_bytes()
    assert digest(entries['rollback-v8.1/'+PREFIX+'sleepingdogs-fex.nro'])==prior_receipt['nro_sha256']
    for name,value in [('run-native-com-test.txt',b'0\n'),('launcher/renderer-choice.txt',b'2\n'),('launcher/game-quality.txt',b'1\n')]:
        entries['rollback-v8.1/'+PREFIX+name]=value
    rollback=ROOT/'local/apc-v18/sleepingdogs-fex.nro';assert sha(rollback)==build['baseline_nro_sha256']
    entries['rollback-v18/'+PREFIX+'sleepingdogs-fex.nro']=rollback.read_bytes()
    entries['rollback-v18/'+PREFIX+'run-native-com-test.txt']=b'0\n'
    entries['rollback-v18/'+PREFIX+'launcher/renderer-choice.txt']=b'0\n'
    entries['rollback-v18/'+PREFIX+'launcher/game-quality.txt']=b'0\n'
    for name in ('d3d11.dll','dxgi.dll'):
        entries['rollback-v18/'+PREFIX+'drive_c/SleepingDogs/'+name]=entries[PREFIX+'launcher/renderers/dxvk-3.1.1/'+name]
    inherited=ROOT/'dist/sd-dxvk-native-probe-horizon-v1.zip';h1=json.loads((ROOT/'reports/native-dxvk-horizon-v1-package.json').read_text())
    assert sha(inherited)==h1['package']['sha256']
    with zipfile.ZipFile(inherited) as archive:
        for name in archive.namelist():
            if name.startswith(('source/','notices/')):entries[name]=archive.read(name)
    entries['notices/Wine-LGPL-2.1']=(ROOT/'LICENSE').read_bytes()
    entries['notices/DXVK-LICENSE']=(ROOT/'vendor/dxvk/DXVK-LICENSE').read_bytes()
    paths=['tools/build_native_dxvk_h4.py','tools/generate_native_dxvk_com.py','tools/check_native_dxvk_h4_abi.py','tools/check_native_dxvk_h4_launcher.py',
           'tools/check_native_dxvk_h4_imports.py','tools/test_native_dxvk_h4_host.py','tools/test_native_dxvk_h4_window.py','tools/package_native_dxvk_h4.py','tools/analyze_native_dxvk_h4.py',
           'tools/build_native_dxvk_h3.py','tools/build_native_dxvk_h2.py','docs/native-dxvk-h4-v1.md','docs/native-dxvk-h3-v1.md',
           'docs/STATUS.md','docs/native-dxvk-h4-v2-window.md','docs/native-dxvk-h4-v3-sponsor.md','docs/native-dxvk-h4-v4-logging.md','docs/native-dxvk-h4-v5-com-outputs.md',
           'README.md','docs/README.md','docs/BUILD.md','docs/CONFIGURATION.md','docs/HISTORY.md',
           'tools/test_native_dxvk_h4_logging.py','tests/native_dxvk_logging_host.cpp','reports/native-dxvk-h4-v3-sponsor-analysis.json',
           'tools/test_native_dxvk_h4_guest_outputs.py','tests/native_dxvk_guest_outputs.c','reports/native-dxvk-h4-v4-press-start-analysis.json',
           'tools/benchmark_native_dxvk_h4_dispatch.py','docs/native-dxvk-h4-v6-dispatch.md','reports/native-dxvk-h4-v5-gameplay-observation.json',
           'tools/test_native_dxvk_h4_guest_lookup.py','tests/native_dxvk_guest_lookup.c',
           'tools/test_native_dxvk_h4_arrays.py','tests/native_dxvk_array_host.cpp',
           'docs/native-dxvk-h4-v7-objects.md','reports/native-dxvk-h4-v6-gameplay-observation.json',
           'docs/native-dxvk-h4-v8.1-transport.md','reports/native-dxvk-h4-v8-gameplay-observation.json','reports/original-game-global-setting-audit.json','reports/native-dxvk-h4-v9-endpoint-audit.json',
           'tools/test_native_dxvk_h4_guest_transport.py','tools/check_native_dxvk_h4_endpoint.py','tests/native_dxvk_guest_transport.c','tests/native_dxvk_game_quality_capture.c',
           'docs/native-dxvk-h4-v8-game-detail.md','reports/native-dxvk-h4-v7-gameplay-observation.json','reports/original-game-display-settings-audit.json',
           'tools/test_native_dxvk_h4_guest_maps.py','tests/native_dxvk_guest_maps.c',
           'tools/test_native_dxvk_h4_game_quality.py','tests/native_dxvk_game_quality_host.c','tools/test_native_dxvk_h4_game_quality_ui.py',
           'reports/native-dxvk-h4-v2-sponsor-observation.json','THIRD_PARTY.md','tests/native_dxvk_com_host.cpp','tests/native_dxvk_window_host.cpp','tests/check_native_dxvk_h4_capture.py',
           'vendor/wine/native-dxvk-h3-inputs.json','vendor/wine/native-dxvk-h4-launcher-inputs.json',
           'tools/port_common.py','tools/sleepingdogs_performance_hud.py','reports/native-v15-package.json']
    paths += ['tools/test_native_dxvk_h4_memory.py','tests/native_dxvk_memory_probes.cpp',
              'tools/test_native_dxvk_h4_batch.py','tests/dxvk_batch.cpp',
              'docs/native-dxvk-h4-v9-memory-batching.md',
              'reports/native-dxvk-h4-v8.1-endpoint-audit.json',
              'reports/native-dxvk-h4-v8.1-guest-transport.json',
              'reports/native-dxvk-h4-v8.1-light-observation.json']
    paths += [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'src/native_dxvk_com').iterdir() if p.is_file()]
    for name in paths:entries['source/project/'+name]=(ROOT/name).read_bytes()
    for name,receipt in receipts.items():
        entries['source/evidence/h4-'+name+'.json']=encode(receipt)
        entries['source/project/reports/'+BUILD+'-'+name+'.json']=encode(receipt)
    # Historical notes retain version-specific receipts instead of linking to
    # the current candidate's different measurements inside the source folder.
    for name,data in list(entries.items()):
        if not name.startswith('source/project/docs/') or not name.endswith('.md'):continue
        for relative in re.findall(r'\]\(\.\./(reports/native-dxvk-h4-[^)#\s]+\.json)',data.decode()):
            key='source/project/'+relative
            if key in entries:continue
            file=(ROOT/relative).resolve();assert file.is_relative_to((ROOT/'reports').resolve()) and file.is_file()
            entries[key]=file.read_bytes()
    # Preserve the real H3 capture as a prerequisite, separately from H4 flags.
    h3=ROOT/'reports/native-dxvk-h3-36d3933d1d46.json';capture=json.loads(h3.read_text())
    assert capture['hardware_tested'] and capture['real_pe32_native_present_api_passed']
    entries['source/project/'+str(h3.relative_to(ROOT))]=h3.read_bytes()
    for detail in capture['evidence'].values():
        path=ROOT/detail['path'];assert sha(path)==detail['sha256'];entries['source/project/'+detail['path']]=path.read_bytes()
    startup_path=ROOT/'reports/native-dxvk-h4-startup-95efa6101d4f.json'
    startup=json.loads(startup_path.read_text())
    assert startup['status']=='STARTUP_FAILED_BEFORE_NATIVE_DEVICE' and not startup['fix_hardware_tested']
    entries['source/project/'+startup_path.relative_to(ROOT).as_posix()]=startup_path.read_bytes()
    for detail in startup['evidence'].values():
        path=ROOT/detail['path'];assert sha(path)==detail['sha256'];entries['source/project/'+detail['path']]=path.read_bytes()
    # Preserve v3 game bytes and separate COM evidence without certifying gameplay.
    analysis=json.loads((ROOT/'reports/native-dxvk-h4-v3-sponsor-analysis.json').read_text())
    capture_path=ROOT/analysis['game_capture_report'];assert sha(capture_path)==analysis['game_capture_report_sha256']
    entries['source/project/'+capture_path.relative_to(ROOT).as_posix()]=capture_path.read_bytes()
    capture=json.loads(capture_path.read_text())
    for collection in (capture['evidence'],analysis['additional_evidence'],analysis['prior_com_evidence']):
        for detail in collection.values():
            if not isinstance(detail,dict) or 'path' not in detail:continue
            path=ROOT/detail['path'];assert sha(path)==detail['sha256']
            entries['source/project/'+detail['path']]=path.read_bytes()
    for dirname in ('native-dxvk-h4-game-a227d3dee3f4','native-dxvk-h4-v3-com-9678e556e955'):
        name='reports/'+dirname+'/.gitattributes';entries['source/project/'+name]=(ROOT/name).read_bytes()
    name='reports/native-dxvk-h4-game-a227d3dee3f4/extra-evidence.json';entries['source/project/'+name]=(ROOT/name).read_bytes()
    analysis=json.loads((ROOT/'reports/native-dxvk-h4-v4-press-start-analysis.json').read_text())
    capture_path=ROOT/analysis['game_capture_report'];assert sha(capture_path)==analysis['game_capture_report_sha256']
    entries['source/project/'+capture_path.relative_to(ROOT).as_posix()]=capture_path.read_bytes()
    for detail in json.loads(capture_path.read_text())['evidence'].values():
        path=ROOT/detail['path'];assert sha(path)==detail['sha256'];entries['source/project/'+detail['path']]=path.read_bytes()
    name='reports/native-dxvk-h4-game-deb1442c33dc/.gitattributes';entries['source/project/'+name]=(ROOT/name).read_bytes()
    # Preserve the v5 game capture and distinguish the supplied older COM file.
    observation=json.loads((ROOT/'reports/native-dxvk-h4-v5-gameplay-observation.json').read_text())
    capture_path=ROOT/observation['game_capture_report'];assert sha(capture_path)==observation['game_capture_report_sha256']
    entries['source/project/'+capture_path.relative_to(ROOT).as_posix()]=capture_path.read_bytes()
    for collection in (json.loads(capture_path.read_text())['evidence'],observation['additional_evidence']):
        for detail in collection.values():
            path=ROOT/detail['path'];assert sha(path)==detail['sha256'];entries['source/project/'+detail['path']]=path.read_bytes()
    name='reports/native-dxvk-h4-game-cc4aa81f2903/.gitattributes';entries['source/project/'+name]=(ROOT/name).read_bytes()
    observation=json.loads((ROOT/'reports/native-dxvk-h4-v6-gameplay-observation.json').read_text())
    capture_path=ROOT/observation['game_capture_report'];assert sha(capture_path)==observation['game_capture_report_sha256']
    entries['source/project/'+capture_path.relative_to(ROOT).as_posix()]=capture_path.read_bytes()
    for collection in (json.loads(capture_path.read_text())['evidence'],observation['additional_evidence']):
        for detail in collection.values():
            path=ROOT/detail['path'];assert sha(path)==detail['sha256'];entries['source/project/'+detail['path']]=path.read_bytes()
    name='reports/native-dxvk-h4-game-e7db87b6b83a/.gitattributes';entries['source/project/'+name]=(ROOT/name).read_bytes()
    observation=json.loads((ROOT/'reports/native-dxvk-h4-v7-gameplay-observation.json').read_text())
    capture_path=ROOT/observation['game_capture_report'];assert sha(capture_path)==observation['game_capture_report_sha256']
    entries['source/project/'+capture_path.relative_to(ROOT).as_posix()]=capture_path.read_bytes()
    for collection in (json.loads(capture_path.read_text())['evidence'],observation['additional_evidence']):
        for detail in collection.values():
            path=ROOT/detail['path'];assert sha(path)==detail['sha256'];entries['source/project/'+detail['path']]=path.read_bytes()
    name='reports/native-dxvk-h4-game-75cd47bd67fe/.gitattributes';entries['source/project/'+name]=(ROOT/name).read_bytes()
    observation=json.loads((ROOT/'reports/native-dxvk-h4-v8-gameplay-observation.json').read_text())
    capture_path=ROOT/observation['game_capture_report'];assert sha(capture_path)==observation['game_capture_report_sha256']
    entries['source/project/'+capture_path.relative_to(ROOT).as_posix()]=capture_path.read_bytes()
    for collection in (json.loads(capture_path.read_text())['evidence'],observation['additional_evidence']):
        for detail in collection.values():
            path=ROOT/detail['path'];assert sha(path)==detail['sha256'];entries['source/project/'+detail['path']]=path.read_bytes()
    name='reports/native-dxvk-h4-game-7d1ee877d066/.gitattributes';entries['source/project/'+name]=(ROOT/name).read_bytes()
    observation=json.loads((ROOT/'reports/native-dxvk-h4-v8.1-light-observation.json').read_text())
    capture_path=ROOT/observation['game_capture_report'];assert sha(capture_path)==observation['game_capture_report_sha256']
    entries['source/project/'+capture_path.relative_to(ROOT).as_posix()]=capture_path.read_bytes()
    for detail in observation['evidence'].values():
        file=ROOT/detail['path'];assert sha(file)==detail['sha256'];entries['source/project/'+detail['path']]=file.read_bytes()
    name='reports/native-dxvk-h4-game-57d78c4032a1/.gitattributes';entries['source/project/'+name]=(ROOT/name).read_bytes()
    memory=receipts['memory-probes'];assert memory['current_read_probes']==0 and memory['current_write_probes']==memory['iterations']
    assert sha(memory['pinned_wine_source']['path'])==memory['pinned_wine_source']['sha256']
    batching=receipts['native-batch'];assert batching['max_deferred_hint_chunks']==24 and batching['min_pending_submissions']==2
    assert batching['native_dxvk_sha256']==build['native_dxvk_baseline_sha256']
    for name,expected in batching['compiled_tracker_inputs'].items():assert sha(name)==expected
    transport=receipts['guest-transport']
    assert transport['hot_lock_pairs_per_10000_calls']=={'v8':10000,'current':0}
    assert transport['pe32_proxy_executed_on_windows'] and not transport['game_fps_measured']
    endpoint=json.loads((ROOT/'reports/native-dxvk-h4-v9-endpoint-audit.json').read_text())
    assert endpoint['guest_sha256']==sha(ROOT/'src/native_dxvk_com/com_guest.c') and endpoint['proxy_sha256']==sha(LOCAL/'sdndx4.dll')
    assert endpoint['checker_sha256']==sha(ROOT/'tools/check_native_dxvk_h4_endpoint.py')
    work=Path(build['work']);pin=json.loads((ROOT/'vendor/wine/native-dxvk-h3-inputs.json').read_text())
    originals={'runtime':Path(pin['runtime_source']),'virtual':Path(pin['virtual_source']),
               'settings':Path(pin['runtime_source']).parent/'f1_settings.h',
               'dxvk-env':Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1/source/src/util/util_env.cpp')}
    relative={'runtime':'wine-nx-probe/source/runtime.c','virtual':'dlls/ntdll/unix/virtual.c',
              'settings':'wine-nx-probe/source/f1_settings.h','dxvk-env':'src/util/util_env.cpp'}
    for kind,detail in build['patches'].items():
        patch=work/(kind+'.patch');assert sha(patch)==detail['patch_sha256']
        scratch=work/'patch-check'/kind;target=scratch/relative[kind];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(originals[kind],target)
        subprocess.run(['git','-C',str(scratch),'apply','--check',str(patch)],check=True)
        subprocess.run(['git','-C',str(scratch),'apply',str(patch)],check=True)
        assert sha(target)==detail['source_sha256']
        entries['source/h4-overlays/'+patch.name]=patch.read_bytes()
        (ROOT/'vendor/wine'/('native-dxvk-h4-'+kind+'.patch')).write_bytes(patch.read_bytes())
    # This distribution carries the H4 source subset, not the whole repository.
    # Keep its documentation navigable without copying unrelated experiments.
    documentation_git=['git','-c','safe.directory='+str(ROOT)]
    documentation_revision=subprocess.check_output(documentation_git+['rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    external_documentation_links=0
    for name,data in list(entries.items()):
        if not name.startswith('source/project/') or not name.endswith('.md'):continue
        original=ROOT/name.removeprefix('source/project/')
        def repository_link(match):
            nonlocal external_documentation_links
            link=match.group(1)
            if ':' in link or link.startswith('#'):return match.group(0)
            relative,separator,anchor=link.partition('#')
            target=(original.parent/relative).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file():return match.group(0)
            relative=target.relative_to(ROOT.resolve()).as_posix()
            if 'source/project/'+relative in entries:return match.group(0)
            subprocess.run(documentation_git+['cat-file','-e',documentation_revision+':'+relative],cwd=ROOT,check=True)
            external_documentation_links+=1
            return '](https://github.com/Ibnuard/sleepingdogs_nx/blob/'+documentation_revision+'/'+quote(relative,safe='/')+separator+anchor+')'
        entries[name]=re.sub(r'\]\(([^)]+)\)',repository_link,data.decode()).encode()
    entries['SHA256SUMS.txt']=''.join(digest(data)+'  '+name+'\n' for name,data in sorted(entries.items())).encode()
    dist=ROOT/'dist';path=dist/NAME;assert path.resolve().parent==dist.resolve()
    if path.exists():
        prior=path/'SHA256SUMS.txt'
        if not prior.is_file():raise RuntimeError('Existing folder has no verified manifest; choose a fresh version.')
        allowed={'SHA256SUMS.txt'}
        for line in prior.read_text().splitlines():
            expected,name=line.split('  ',1);allowed.add(name);assert sha(path/name)==expected,('preserving changed staged file',name)
        existing={p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}
        if existing-allowed or existing-set(entries):raise RuntimeError('Preserving extra staged files/logs; choose a fresh version.')
    for name,data in entries.items():
        assert not name.startswith('/') and '..' not in Path(name).parts
        target=path/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for line in (path/'SHA256SUMS.txt').read_text().splitlines():
        expected,name=line.split('  ',1);assert sha(path/name)==expected,name
    report=dict(status='PASS',build=build['build'],distribution_format='directory',zip_created=False,path=str(path),files=len(entries),
                total_bytes=sum(map(len,entries.values())),checksums_sha256=sha(path/'SHA256SUMS.txt'),all_file_hashes_verified=True,wine_overlay_patches_reproduced=True,
                unbundled_documentation_links=external_documentation_links,documentation_revision=documentation_revision,
                nro_sha256=build['nro_sha256'],rollback_nro_sha256=sha(rollback),renderer_choices=['dxvk-3.1.1','dxvk-2.7.1-async','dxvk-native-h4'],
                software_game_route_implemented=True,hardware_tested=False,com_guest_execution_tested=False,game_integration_tested=False,game_fps_measured=False,
                receipts={name:sha(LOCAL/(name+'.json')) for name in receipts},packager_sha256=sha(__file__),instructions_sha256=digest(INSTRUCTIONS.encode()),
                launcher_inputs_sha256=sha(LAUNCHER_INPUTS),canonical_profiles_regenerated=True,native_sync_interval=1,native_fifo_diagnostic=True,
                native_log_queue_slots=512,native_log_batch_lines=32,native_progress_interval_seconds=5,native_bulk_observer_disabled=True,
                guest_endpoint_publication='acquire-release',guest_hot_discovery_lock=False,global_setting_minus_one_supported=True,
                guest_map_cache_bytes=16*1024*1024,guest_map_cache_entries=4,native_discard_zeroing=False,native_write_probe='single-readwrite',native_performance_batching=True,native_batching_chunk_bound=24,game_quality_menu=True,light_resolution=[1280,720],
                game_quality_requires_existing_xml=True,game_quality_original_backup=True,guest_proxy_lookup='hash',native_pointer_array_inline=128,native_progress_sample_stride=256,native_stats_clock_stride=1024,native_critical_and_fault_snapshots_preserved=True,
                sd_payload=sorted(name for name in entries if name.startswith(PREFIX)),game_data_included=False)
    for name,receipt in receipts.items():(ROOT/'reports'/(BUILD+'-'+name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
    (ROOT/'reports'/(BUILD+'-folder.json')).write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
