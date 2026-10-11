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
from build_native_dxvk_h4 import BUILD,APP_VERSION,LOCAL

ROOT=Path(__file__).resolve().parents[1]
PREFIX='switch/sleepingdogs-fex/'
NAME='sd-dxvk-native-h4-v3-update'
LAUNCHER_INPUTS=ROOT/'vendor/wine/native-dxvk-h4-launcher-inputs.json'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(data):return hashlib.sha256(data).hexdigest()
def encode(data):return (json.dumps(data,indent=2)+'\n').encode()

INSTRUCTIONS='''FEXTendo / Sleeping Dogs Native DXVK H4 v3 - sponsor freeze diagnostic

H4 v2 sudah menghasilkan COM PASS di Switch (1.845.687 checks / 300 Present),
tetapi game berhenti di halaman sponsor setelah satu frame native.
V3 menguji FIFO (dxgi.syncInterval=1) pada semua profil renderer Native ARM64
dan menambah BEGIN/END untuk panggilan awal Map/Unmap/BindMap/Present/GetData
serta Context setelah frame pertama. Trace berhenti pada tiga Present atau
128 panggilan; durasinya termasuk logging dan bukan waktu GPU.
Penyebab freeze BELUM terkonfirmasi; v3 belum diuji di Switch.
Folder v1/v2 tetap terpisah. Resolusi tetap 720p, clock tidak diubah.

FOLDER SIAP SALIN, TANPA ZIP. Update untuk instalasi v18 lengkap yang sudah
berfungsi; game, save, Wine modules, aset launcher dan forwarder tetap dari SD.
H1-H3 dan tes COM H4 v2 sudah lolos di Switch. V3 baru lolos build/tes host;
BELUM ada bukti gameplay atau kenaikan FPS di Switch pada versi ini.

A. TES COM X86 DI SWITCH
1. Tutup aplikasi sepenuhnya dari HOME. Backup NRO game di SD.
2. Salin HANYA folder switch/ dari folder ini ke root SD, timpa file terkait.
   Gunakan forwarder low-window/full-memory yang berhasil pada H3, bukan Album.
3. Jalankan. Mode awal otomatis COM self-test, bukan HKShip.exe.
   Layar biru 720p dan 300 Present; tunggu console menampilkan exit 00000000.
   Tes ini juga mencoba thread guest, buffer, texture BC1, COM identity dan
   private interface. Jika gagal/hang, simpan log dulu, jangan lanjut ke game.
4. Tutup dari HOME. Ambil empat file:
   switch/sleepingdogs-fex/drive_c/native-dxvk-h4-result.json
   switch/sleepingdogs-fex/drive_c/native-dxvk-h4-guest.log
   switch/sleepingdogs-fex/native-dxvk-h4/runtime.log
   switch/sleepingdogs-fex/native-dxvk-h4/HKShip.exe_d3d11.log
   File DXVK ini ditimpa saat game dijalankan. Simpan keempat file COM dulu.

B. VALIDASI GAME NATIVE SETELAH HASIL COM PASS
5. Salin folder start-game/switch/ ke root SD, timpa dua file pilihan saja.
   Jalankan NRO yang sama. Settings > Renderer kini punya DXVK Native ARM64.
   Pilih mode native, Launch GUI, HUD FPS, 1280x720. LSFG otomatis OFF di mode
   native meskipun preferensi lamanya ON. Clock referensi sama seperti v17:
   CPU 1728 / GPU 768 / RAM 1600 MHz. Build tidak mengubah clock.
6. Uji menu, load save, jalan di rute/arah kamera yang sama termasuk area ramai,
   pindah area, pause/resume, lalu keluar. Beri waktu shader/cache menghangat.
   Simpan fex-runtime.log, native-dxvk-h4/HKShip.exe_d3d11.log dan, bila ada,
   crash.log. UNKNOWN_IID/UNSUPPORTED/FAULT dicatat di runtime log.
   Catat FPS GAME dari HUD;
   FPS menu, loop COM biru, dan frame generation bukan hasil gameplay.
7. Log game harus mencatat BUILD native-dxvk-h4-v3 mode=SleepingDogs,
   [SD-NDX-WINDOW] handoff complete launcher_owned=0 console_active=0,
   dimensions rc=00000000, lalu
   D3D11CreateDevice native=ARM64 dan FIRST_PRESENT real COM path.
   Log DXVK harus mencatat syncInterval=1 dan VK_PRESENT_MODE_FIFO_KHR.
   [SD-NDX-CALL] BEGIN/END menunjukkan panggilan awal beserta thread/argumen.
   BEGIN tanpa END hanya berarti panggilan belum selesai pada log; bukan
   bukti deadlock. Catat layar terakhir dan apakah HOME masih merespons.
   [SD-NDX-FPS] mencatat 600 interval native Present, LSFG=OFF. Menu/loading
   bisa ikut terhitung; belum merupakan benchmark gameplay terkontrol.

FALLBACK
- Untuk A/B pada H4 yang sama, pilih DXVK 3.1.1 atau DXVK 2.7.1 async di
  launcher, lalu restart dari HOME. Ketiganya memakai pemasangan atomik DLL.
- Pulih penuh: salin rollback-v18/switch/ ke root SD setelah menutup dari HOME.
  Itu mengembalikan NRO v18, pilihan renderer 0, mode COM OFF, serta pasangan
  D3D11/DXGI x86 yang sesuai. File tambahan native boleh tetap ada.
- Mengulang COM: salin start-com-test/switch/, restart penuh; hasil/log COM
  ditimpa tiap sesi. Simpan hasil sebelumnya dahulu.

DXVK C++ berjalan ARM64 di NRO; DLL PE32 hanya proxy untuk Wine/FEX.
Map tetap memakai shadow pointer 32-bit dengan lifetime sampai Unmap.
External shared handles, GDI surfaces dan D3D11/DXGI versi lanjutan belum
diimplementasikan. Kegagalan metode direkam; tidak diam-diam memakai builtin.
Native worker dicatat di log, di luar registry thread guest FEX.
Target stable 30 FPS BELUM terbukti. Ini kandidat uji integrasi, bukan rilis.

Checksum seluruh isi: SHA256SUMS.txt. Jangan salin source/ dan notices/ ke SD.
Detail: source/project/docs/native-dxvk-h4-v3-sponsor.md.
Prepared Wine/FEX/Mesa/SDK lokal tetap diperlukan untuk rebuild.
'''

def native_fifo_config(data):
    """Change just the native present interval; retain the canonical tuning."""
    config=data.decode()
    config,count=re.subn(r'(?m)^(dxgi\.syncInterval\s*=\s*)[^\r\n]+$',r'\g<1>1',config)
    if count!=1:raise ValueError('Expected one active dxgi.syncInterval in native profile')
    return config.encode()

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
            entries[name]=native_fifo_config(entries[name])
    return entries

def main():
    LOCAL.mkdir(parents=True,exist_ok=True);lock=(LOCAL/'packaging.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    receipts={name:json.loads((LOCAL/(name+'.json')).read_text()) for name in ('build','host-test','abi-check','launcher-check','game-imports','window-check')}
    build=receipts['build'];assert build['status']=='BUILT' and build['baseline_reproduced']
    assert all(receipts[n]['status']=='PASS' for n in ('host-test','abi-check','launcher-check','game-imports','window-check'))
    for receipt in (build,receipts['host-test']):
        for name,expected in receipt['source_files'].items():assert sha(ROOT/name)==expected,('source changed',name)
    assert sha(ROOT/'tools/build_native_dxvk_h4.py')==build['builder_sha256']
    for name,tool in [('host-test','test_native_dxvk_h4_host.py'),('abi-check','check_native_dxvk_h4_abi.py'),('launcher-check','check_native_dxvk_h4_launcher.py'),('game-imports','check_native_dxvk_h4_imports.py'),('window-check','test_native_dxvk_h4_window.py')]:
        assert sha(ROOT/'tools'/tool)==receipts[name]['runner_sha256']
    for name,expected in build['inputs'].items():assert sha(name)==expected
    for name,expected in build['header_inputs'].items():assert sha(name)==expected
    assert sha(ROOT/'vendor/wine/native-dxvk-h3-inputs.json')==build['input_manifest_sha256']
    assert sha(LOCAL/'sleepingdogs-fex.nro')==build['nro_sha256']
    nro=(LOCAL/'sleepingdogs-fex.nro').read_bytes();assert nro[0x10:0x14]==b'NRO0'
    for marker in (('sleepingdogs-'+BUILD).encode(),b'dxvk-native-h4',b'DXVK Native ARM64',b'[SD-NDX-WINDOW] handoff complete',
                   b'sd-native-dxvk-h4-test.exe',b'sdndx4.dll',b'd3d11,dxgi,sdndx4=n;d3d9=n,b',b'[SD-NDX-COM] FIRST_PRESENT',b'[SD-NDX-WORKER]',
                   b'[SD-NDX-CALL] BEGIN',b'[SD-NDX-CALL] END'):
        assert marker in nro,('missing binary marker',marker)
    asset=struct.unpack_from('<I',nro,0x18)[0];assert nro[asset:asset+4]==b'ASET'
    nacp_offset,nacp_size=struct.unpack_from('<QQ',nro,asset+0x18);nacp=nro[asset+nacp_offset:asset+nacp_offset+nacp_size]
    assert len(nacp)==0x4000 and nacp.startswith(b'FEXTendo Native DXVK H4\0') and APP_VERSION.encode()+b'\0' in nacp
    assert not any(build[k] for k in ('hardware_tested','com_guest_execution_tested','game_integration_tested','game_fps_measured'))
    entries=launcher_payload()
    assert receipts['launcher-check']['source_sha256']==build['patches']['runtime']['source_sha256']
    assert receipts['window-check']['runtime_source_sha256']==build['patches']['runtime']['source_sha256']
    for name,expected in receipts['window-check']['source_files'].items():assert sha(ROOT/name)==expected,name
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
                    PREFIX+'native-dxvk-h4/com-test.conf':b'dxgi.syncInterval = 1\ndxvk.numCompilerThreads = 2\ndxvk.hud = fps\n',
                    'README-INSTALL.txt':INSTRUCTIONS.encode()})
    for mode,value in [('start-com-test',b'1\n'),('start-game',b'0\n')]:
        entries[mode+'/'+PREFIX+'run-native-com-test.txt']=value
        entries[mode+'/'+PREFIX+'launcher/renderer-choice.txt']=b'2\n'
    rollback=ROOT/'local/apc-v18/sleepingdogs-fex.nro';assert sha(rollback)==build['baseline_nro_sha256']
    entries['rollback-v18/'+PREFIX+'sleepingdogs-fex.nro']=rollback.read_bytes()
    entries['rollback-v18/'+PREFIX+'run-native-com-test.txt']=b'0\n'
    entries['rollback-v18/'+PREFIX+'launcher/renderer-choice.txt']=b'0\n'
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
           'docs/STATUS.md','docs/native-dxvk-h4-v2-window.md','docs/native-dxvk-h4-v3-sponsor.md',
           'reports/native-dxvk-h4-v2-sponsor-observation.json','THIRD_PARTY.md','tests/native_dxvk_com_host.cpp','tests/native_dxvk_window_host.cpp','tests/check_native_dxvk_h4_capture.py',
           'vendor/wine/native-dxvk-h3-inputs.json','vendor/wine/native-dxvk-h4-launcher-inputs.json',
           'tools/port_common.py','tools/sleepingdogs_performance_hud.py','reports/native-v15-package.json']
    paths += [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'src/native_dxvk_com').iterdir() if p.is_file()]
    for name in paths:entries['source/project/'+name]=(ROOT/name).read_bytes()
    for name,receipt in receipts.items():
        entries['source/evidence/h4-'+name+'.json']=encode(receipt)
        entries['source/project/reports/'+BUILD+'-'+name+'.json']=encode(receipt)
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
                nro_sha256=build['nro_sha256'],rollback_nro_sha256=sha(rollback),renderer_choices=['dxvk-3.1.1','dxvk-2.7.1-async','dxvk-native-h4'],
                software_game_route_implemented=True,hardware_tested=False,com_guest_execution_tested=False,game_integration_tested=False,game_fps_measured=False,
                receipts={name:sha(LOCAL/(name+'.json')) for name in receipts},packager_sha256=sha(__file__),instructions_sha256=digest(INSTRUCTIONS.encode()),
                launcher_inputs_sha256=sha(LAUNCHER_INPUTS),canonical_profiles_regenerated=True,native_sync_interval=1,native_fifo_diagnostic=True,
                sd_payload=sorted(name for name in entries if name.startswith(PREFIX)),game_data_included=False)
    for name,receipt in receipts.items():(ROOT/'reports'/(BUILD+'-'+name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
    (ROOT/'reports'/(BUILD+'-folder.json')).write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
