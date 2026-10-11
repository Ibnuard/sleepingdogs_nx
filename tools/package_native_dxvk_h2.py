"""Package the H2 diagnostic update, exact sources/evidence and v18 rollback.

For the existing local Wine/FEX installation; no game data is supplied.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-h2-v1'
NAME='sd-dxvk-native-h2-v1-update'
PREFIX='switch/sleepingdogs-fex/'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(data):return hashlib.sha256(data).hexdigest()
def encode(value):return (json.dumps(value,indent=2)+'\n').encode()

INSTRUCTIONS='''FEXTendo Native DXVK H2 v1 / PE32 Wine-FEX bridge test

Ini tes diagnostik OFFSCREEN 1280x720, belum renderer Sleeping Dogs.
Gunakan instalasi Sleeping Dogs/FEXTendo v18 yang sudah bisa gameplay.

1. Tutup FEXTendo sepenuhnya dari HOME. BACKUP NRO milikmu di SD:
   switch/sleepingdogs-fex/sleepingdogs-fex.nro
2. Salin HANYA folder switch/ dari ZIP ke root SD dan timpa NRO.
   Tambahan: drive_c/sdndx.dll dan drive_c/sd-native-dxvk-guest.exe.
3. Buka lewat forwarder Sleeping Dogs low-window/full-memory yang sudah
   bekerja untuk gameplay. Tes H2 memerlukan jalur low-address Wine/FEX itu.
   Jangan buka dari Album/applet mode.
4. Layar console menampilkan Native DXVK H2. Game tidak dibuka.
   Tes memakai guest x86 asli untuk native-device, buffer Map/Unmap,
   shader draw dan readback 921600 pixel. Tidak ada present atau tes FPS.
   Tunggu pesan guest exit; lalu tutup dari HOME. Jika hang, simpan log.
5. Ambil empat file ini:
   switch/sleepingdogs-fex/drive_c/native-dxvk-h2-result.json
   switch/sleepingdogs-fex/drive_c/native-dxvk-h2-guest.log
   switch/sleepingdogs-fex/native-dxvk-h2/runtime.log
   switch/sleepingdogs-fex/native-dxvk-h2/sd-dxvk-native-probe_d3d11.log
6. Setelah tes, pulihkan NRO game dari BACKUP. Fallback NRO v18 yang asli
   disediakan di rollback-v18/switch/sleepingdogs-fex/sleepingdogs-fex.nro.
   Jangan salin folder rollback-v18 bersamaan dengan update.

Kondisi referensi: OLED handheld, CPU 1728 / GPU 768 / RAM 1600 MHz.
Program tidak mengubah clock. Tes menimpa hasil/log H2 setiap sesi.
RUNNING berarti belum selesai; PASS harus berasal dari result JSON di SD.
BUILT/PASS dalam source/evidence adalah hasil build/host, bukan hasil Switch.
Tidak ada game FPS gain yang sudah terukur dari H2.

Folder source/ dan notices/ untuk developer; hanya switch/ untuk tes.
NRO diagnostic memakai baseline v18 (Wine/FEX dan komponen native yang sama,
termasuk backend LSFG tertaut) plus subset ARM64 DXVK H1. LSFG tidak diuji.
Ini update lokal eksperimental, bukan paket fresh install atau rilis lengkap.
Rebuild masih memerlukan prepared Wine/FEX/Mesa/SDK lokal yang terdokumentasi.
Record: source/project/docs/native-dxvk-h2-v1.md
Sources: https://github.com/Ibnuard/sleepingdogs_nx/tree/experiment/native-dxvk-probe-v1
'''

def main():
    build=json.loads((LOCAL/'build.json').read_text());host=json.loads((LOCAL/'host-test.json').read_text())
    assert build['status']=='BUILT' and build['baseline_reproduced'] and host['status']=='PASS'
    assert not build['hardware_tested'] and not build['game_integration'] and not host['wow64_gate_tested']
    assert sha(ROOT/'tools/build_native_dxvk_h2.py')==build['builder_sha256']
    assert sha(ROOT/'tools/test_native_dxvk_h2_host.py')==host['runner_sha256']
    for receipt in (build,host):
        for name,expected in receipt['source_files'].items():assert sha(ROOT/name)==expected,name
    assert sha(ROOT/'vendor/wine/native-dxvk-h2-inputs.json')==build['input_manifest_sha256']
    for name,expected in build['inputs'].items():assert sha(name)==expected, ('link input changed',name)
    for name,expected in build['header_inputs'].items():assert sha(name)==expected, ('compiled header changed',name)
    nro=LOCAL/'sleepingdogs-fex.nro';assert sha(nro)==build['nro_sha256']
    rollback=ROOT/'local/apc-v18/sleepingdogs-fex.nro';assert sha(rollback)==build['baseline_nro_sha256']
    entries={PREFIX+'sleepingdogs-fex.nro':nro.read_bytes(),
             'rollback-v18/'+PREFIX+'sleepingdogs-fex.nro':rollback.read_bytes(),
             'README-TEST.txt':INSTRUCTIONS.encode(),
             'source/evidence/h2-build.json':encode(build),'source/evidence/h2-host-test.json':encode(host)}
    for name in ('sdndx.dll','sd-native-dxvk-guest.exe'):
        p=LOCAL/name;assert sha(p)==build['pe_audits'][name]['sha256'];entries[PREFIX+'drive_c/'+name]=p.read_bytes()
    # Reuse the verified H1 full native-DXVK sources, Mesa overlays and notices.
    h1=ROOT/'dist/sd-dxvk-native-probe-horizon-v1.zip'
    assert sha(h1)=='ddb7161482c960282bfe715c928b3724f894ef15714a8a770e1255310383b945'
    with zipfile.ZipFile(h1) as z:
        assert z.testzip() is None
        sums=dict(line.split('  ',1)[::-1] for line in z.read('SHA256SUMS.txt').decode().splitlines())
        for name in z.namelist():
            if name.startswith(('source/dxvk/','source/mesa-overlays/','notices/')):
                data=z.read(name);assert digest(data)==sums[name];entries[name]=data
    entries['notices/Wine-LGPL-2.1']= (ROOT/'LICENSE').read_bytes()
    entries['source/project/THIRD_PARTY.md']=(ROOT/'THIRD_PARTY.md').read_bytes()
    files=['docs/native-dxvk-h2-v1.md','docs/native-dxvk-probe-v1.md','vendor/wine/native-dxvk-h2-inputs.json',
           'tools/build_native_dxvk_h2.py','tools/test_native_dxvk_h2_host.py','tools/package_native_dxvk_h2.py',
           'tools/analyze_native_dxvk_h2.py','tools/build_native_dxvk_probe.py',
           'tests/native_dxvk_bridge_abi.c','tests/native_dxvk_bridge_host.cpp']
    files += [str(p.relative_to(ROOT)).replace('\\','/') for folder in ('src/native_dxvk','src/native_dxvk_bridge') for p in (ROOT/folder).iterdir() if p.is_file()]
    for name in files:entries['source/project/'+name]=(ROOT/name).read_bytes()
    work=Path(build['work'])
    for kind,detail in build['patches'].items():
        patch=work/(kind+'.patch');assert sha(patch)==detail['patch_sha256']
        pin=json.loads((ROOT/'vendor/wine/native-dxvk-h2-inputs.json').read_text())
        relative='dlls/ntdll/unix/virtual.c' if kind=='virtual' else 'wine-nx-probe/source/runtime.c'
        scratch=work/'patch-check';target=scratch/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(pin[kind+'_source'],target)
        subprocess.run(['git','-C',str(scratch),'apply','--check',str(patch)],check=True)
        subprocess.run(['git','-C',str(scratch),'apply',str(patch)],check=True)
        assert sha(target)==detail['source_sha256'], ('overlay patch reproduction',kind)
        data=patch.read_bytes();entries['source/wine-overlays/'+patch.name]=data
        destination=ROOT/'vendor/wine'/('native-dxvk-h2-'+kind+'.patch')
        destination.write_bytes(data)
    entries['source/evidence/h1-switch-result.json']=(ROOT/'reports/native-dxvk-h1-73faa8ebc4ef.json').read_bytes()
    sums=''.join(digest(data)+'  '+name+'\n' for name,data in sorted(entries.items()))
    entries['SHA256SUMS.txt']=sums.encode()
    dist=ROOT/'dist';dist.mkdir(exist_ok=True);path=dist/(NAME+'.zip')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in sorted(entries.items()):
            assert not name.startswith('/') and '..' not in Path(name).parts
            info=zipfile.ZipInfo(name,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,data)
    with zipfile.ZipFile(path) as z:
        assert len(z.namelist())==len(set(z.namelist())) and z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            expected,name=line.split('  ',1);assert digest(z.read(name))==expected,name
        assert sorted(n for n in z.namelist() if n.startswith('switch/'))==sorted(PREFIX+n for n in ['sleepingdogs-fex.nro','drive_c/sdndx.dll','drive_c/sd-native-dxvk-guest.exe'])
    staged=dist/NAME;staged.mkdir(exist_ok=True)
    for name,data in entries.items():
        if name.startswith(('switch/','rollback-v18/')) or name in ('README-TEST.txt','SHA256SUMS.txt'):
            p=staged/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    report=dict(status='PASS',build='native-dxvk-h2-v1',path=str(path),sha256=sha(path),bytes=path.stat().st_size,
                files=len(entries),all_member_hashes_verified=True,wine_overlay_patches_reproduced=True,nro_sha256=sha(nro),rollback_nro_sha256=sha(rollback),
                guest_pe32_files=build['pe_audits'],hardware_tested=False,guest_execution_tested=False,game_integration=False,game_fps_measured=False,
                builder_sha256=build['builder_sha256'],packager_sha256=sha(__file__),instructions_sha256=digest(INSTRUCTIONS.encode()),
                build_receipt_sha256=sha(LOCAL/'build.json'),host_receipt_sha256=sha(LOCAL/'host-test.json'))
    reports=ROOT/'reports'
    for name,data in [('native-dxvk-h2-v1-build.json',build),('native-dxvk-h2-v1-host.json',host),('native-dxvk-h2-v1-package.json',report)]:
        (reports/name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
