"""Stage a verified H3 ready-to-install folder. Never create an output ZIP.

Reuses the pinned H1 source/notices archive as a read-only input. Does not
overwrite unrecognized or modified files in an existing staged directory.
"""
from pathlib import Path
import fcntl
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-h3-v1'
NAME='sd-dxvk-native-h3-v1-update'
PREFIX='switch/sleepingdogs-fex/'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(data):return hashlib.sha256(data).hexdigest()
def encode(value):return (json.dumps(value,indent=2)+'\n').encode()

INSTRUCTIONS='''FEXTendo Native DXVK H3 v1 / guest-driven native Present

FOLDER SIAP SALIN. Tidak perlu extract ZIP.
Ini tes diagnostik 1280x720, belum renderer/gameplay Sleeping Dogs.
Gunakan instalasi Sleeping Dogs/FEXTendo v18 yang sudah lulus H2.

1. Tutup FEXTendo sepenuhnya dari HOME. BACKUP NRO game di SD:
   switch/sleepingdogs-fex/sleepingdogs-fex.nro
2. Salin HANYA folder switch/ dari folder ini ke root SD dan timpa NRO.
   Tambahan: drive_c/sdndx3.dll dan drive_c/sd-native-dxvk-h3-guest.exe.
   Jangan salin source/, notices/, atau rollback-v18/ bersama update.
3. Buka lewat forwarder Sleeping Dogs low-window/full-memory yang lulus H2.
   Jangan buka lewat Album/applet mode. Clock referensi tetap
   CPU 1728 / GPU 768 / RAM 1600 MHz; program tidak mengubah clock.
4. Console mengidentifikasi Native DXVK H3. Game tidak dibuka.
   Layar bisa hitam selama inisialisasi, lalu BIRU polos kira-kira 5 detik:
   guest x86 menjalankan 300 native FIFO Present lewat Wine/FEX.
   Tunggu console kembali dengan "H3 guest exited: 00000000".
   Tutup dari HOME. Jika hang, simpan log sebelum mencoba lagi.
5. Ambil empat file dan catat apakah layar biru sempat muncul:
   switch/sleepingdogs-fex/drive_c/native-dxvk-h3-result.json
   switch/sleepingdogs-fex/drive_c/native-dxvk-h3-guest.log
   switch/sleepingdogs-fex/native-dxvk-h3/runtime.log
   switch/sleepingdogs-fex/native-dxvk-h3/sd-dxvk-native-probe_d3d11.log
6. Setelah tes, pulihkan NRO game dari BACKUP. NRO v18 asli disediakan
   sebagai fallback di rollback-v18/switch/sleepingdogs-fex/sleepingdogs-fex.nro.

H2 hardware PASS sudah dicatat. H3 BUILD/host PASS belum berarti Switch PASS.
H3 mengecek 1 KiB buffer, seluruh piksel offscreen dan backbuffer 720p,
present count, stale tokens, serta biaya validasi/dispatch native.
Draw/Present memakai token native tanpa scan 8 MiB setiap panggilan;
Map/Unmap dan shader tetap diperiksa dengan helper memori Wine.
Arena tetap milik satu thread diagnostik; ini belum ABI COM produksi.
Loop timing mencakup FIFO waits dan progress I/O. Ini BUKAN FPS game.
LSFG tidak dipakai. Tidak ada klaim target 30 FPS game sudah tercapai.
Tes menimpa hasil/log H3 tiap run; simpan hasil gagal sebelum retry.

Record: source/project/docs/native-dxvk-h3-v1.md
Sources: https://github.com/Ibnuard/sleepingdogs_nx/tree/experiment/native-dxvk-probe-v1
Prepared Wine/FEX/Mesa/SDK lokal masih diperlukan untuk rebuild.
Folder ini update diagnostik lokal, bukan paket fresh install/rilis lengkap.
'''

def main():
    LOCAL.mkdir(parents=True,exist_ok=True)
    lock=(LOCAL/'packaging.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    build=json.loads((LOCAL/'build.json').read_text())
    host=json.loads((LOCAL/'host-test.json').read_text())
    assert build['status']=='BUILT' and build['baseline_reproduced'] and host['status']=='PASS'
    assert not build['hardware_tested'] and not build['game_integration'] and not host['wow64_gate_tested']
    assert sha(ROOT/'tools/build_native_dxvk_h3.py')==build['builder_sha256']
    assert sha(ROOT/'tools/test_native_dxvk_h3_host.py')==host['runner_sha256']
    for receipt in (build,host):
        for name,expected in receipt['source_files'].items():assert sha(ROOT/name)==expected,name
    assert sha(ROOT/'vendor/wine/native-dxvk-h3-inputs.json')==build['input_manifest_sha256']
    for name,expected in build['inputs'].items():assert sha(name)==expected,('link input changed',name)
    for name,expected in build['header_inputs'].items():assert sha(name)==expected,('compiled header changed',name)
    nro=LOCAL/'sleepingdogs-fex.nro';assert sha(nro)==build['nro_sha256']
    rollback=ROOT/'local/apc-v18/sleepingdogs-fex.nro';assert sha(rollback)==build['baseline_nro_sha256']
    entries={PREFIX+'sleepingdogs-fex.nro':nro.read_bytes(),
             'rollback-v18/'+PREFIX+'sleepingdogs-fex.nro':rollback.read_bytes(),
             'README-TEST.txt':INSTRUCTIONS.encode(),
             'source/evidence/h3-build.json':encode(build),
             'source/evidence/h3-host.json':encode(host),
             'source/project/reports/native-dxvk-h3-v1-build.json':encode(build),
             'source/project/reports/native-dxvk-h3-v1-host.json':encode(host)}
    for name,audit in build['pe_audits'].items():
        path=LOCAL/name;assert sha(path)==audit['sha256'];entries[PREFIX+'drive_c/'+name]=path.read_bytes()
    # Read the historical input archive; do not produce another archive.
    inherited=ROOT/'dist/sd-dxvk-native-probe-horizon-v1.zip'
    original=json.loads((ROOT/'reports/native-dxvk-horizon-v1-package.json').read_text())
    assert sha(inherited)==original['package']['sha256']
    with zipfile.ZipFile(inherited,'r') as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            if name.startswith(('source/','notices/')):
                assert not name.startswith('/') and '..' not in Path(name).parts
                entries[name]=archive.read(name)
    entries['notices/Wine-LGPL-2.1']=(ROOT/'LICENSE').read_bytes()
    entries['source/project/THIRD_PARTY.md']=(ROOT/'THIRD_PARTY.md').read_bytes()
    files=['docs/native-dxvk-h3-v1.md','docs/native-dxvk-h2-v1.md','docs/native-dxvk-probe-v1.md',
           'vendor/wine/native-dxvk-h3-inputs.json','tools/build_native_dxvk_h3.py',
           'tools/test_native_dxvk_h3_host.py','tools/package_native_dxvk_h3.py',
           'tools/analyze_native_dxvk_h3.py','tools/analyze_native_dxvk_h2.py','tests/native_dxvk_present_abi.c',
           'tests/native_dxvk_present_host.cpp','src/native_dxvk_bridge/bridge_protocol.h']
    files += [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'src/native_dxvk_present').iterdir() if p.is_file()]
    for name in files:entries['source/project/'+name]=(ROOT/name).read_bytes()
    pin=json.loads((ROOT/'vendor/wine/native-dxvk-h3-inputs.json').read_text())
    hardware=ROOT/pin['h2_hardware_report'];assert sha(hardware)==pin['h2_hardware_report_sha256']
    entries['source/evidence/h2-switch-result.json']=hardware.read_bytes()
    entries['source/project/'+pin['h2_hardware_report']]=hardware.read_bytes()
    capture=json.loads(hardware.read_text())
    assert capture['hardware_tested'] and capture['real_pe32_guest_bridge_passed']
    for detail in capture['evidence'].values():
        path=ROOT/detail['path'];assert sha(path)==detail['sha256']
        entries['source/evidence/h2-capture/'+path.name]=path.read_bytes()
        entries['source/project/'+detail['path']]=path.read_bytes()
    work=Path(build['work'])
    for kind,detail in build['patches'].items():
        patch=work/(kind+'.patch');assert sha(patch)==detail['patch_sha256']
        relative='dlls/ntdll/unix/virtual.c' if kind=='virtual' else 'wine-nx-probe/source/runtime.c'
        scratch=work/'patch-check';target=scratch/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(pin[kind+'_source'],target)
        subprocess.run(['git','-C',str(scratch),'apply','--check',str(patch)],check=True)
        subprocess.run(['git','-C',str(scratch),'apply',str(patch)],check=True)
        assert sha(target)==detail['source_sha256'],('overlay patch reproduction',kind)
        entries['source/wine-overlays/'+patch.name]=patch.read_bytes()
        (ROOT/'vendor/wine'/('native-dxvk-h3-'+kind+'.patch')).write_bytes(patch.read_bytes())
    sums=''.join(digest(data)+'  '+name+'\n' for name,data in sorted(entries.items()))
    entries['SHA256SUMS.txt']=sums.encode()
    dist=ROOT/'dist';dist.mkdir(exist_ok=True);path=dist/NAME
    assert path.resolve().parent==dist.resolve()
    if path.exists():
        prior=path/'SHA256SUMS.txt'
        if not prior.is_file():raise RuntimeError('Existing folder has no verified manifest; preserve it and choose another output version.')
        allowed={'SHA256SUMS.txt'}
        for line in prior.read_text().splitlines():
            expected,name=line.split('  ',1)
            assert not name.startswith('/') and '..' not in Path(name).parts
            allowed.add(name)
            if sha(path/name)!=expected:raise RuntimeError('Preserving modified staged file: '+name)
        existing={str(p.relative_to(path)).replace('\\','/') for p in path.rglob('*') if p.is_file()}
        if existing-allowed:raise RuntimeError('Preserving unexpected staged files: '+repr(sorted(existing-allowed)))
        if existing-set(entries):raise RuntimeError('Refusing to remove previously staged files.')
    path.mkdir(exist_ok=True)
    for name,data in entries.items():
        assert not name.startswith('/') and '..' not in Path(name).parts
        destination=path/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
    for line in (path/'SHA256SUMS.txt').read_text().splitlines():
        expected,name=line.split('  ',1);assert sha(path/name)==expected,name
    payload=sorted(str(p.relative_to(path)).replace('\\','/') for p in (path/'switch').rglob('*') if p.is_file())
    assert payload==sorted(PREFIX+n for n in ['sleepingdogs-fex.nro','drive_c/sdndx3.dll','drive_c/sd-native-dxvk-h3-guest.exe'])
    report=dict(status='PASS',build='native-dxvk-h3-v1',distribution_format='directory',zip_created=False,
                path=str(path),files=len(entries),total_bytes=sum(len(data) for data in entries.values()),
                checksums_sha256=sha(path/'SHA256SUMS.txt'),all_file_hashes_verified=True,
                wine_overlay_patches_reproduced=True,nro_sha256=sha(nro),rollback_nro_sha256=sha(rollback),
                sd_payload=payload,guest_pe32_files=build['pe_audits'],h2_hardware_report_sha256=sha(hardware),
                hardware_tested=False,guest_execution_tested=False,game_integration=False,game_fps_measured=False,
                packager_sha256=sha(__file__),build_receipt_sha256=sha(LOCAL/'build.json'),
                host_receipt_sha256=sha(LOCAL/'host-test.json'),instructions_sha256=digest(INSTRUCTIONS.encode()))
    for name,data in [('native-dxvk-h3-v1-build.json',build),('native-dxvk-h3-v1-host.json',host),('native-dxvk-h3-v1-folder.json',report)]:
        (ROOT/'reports'/name).write_text(json.dumps(data,indent=2)+'\n',newline='\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
