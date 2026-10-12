"""Package a FEX-only A/B delta for an existing native H4 v9 installation."""
from pathlib import Path
import json,re
from urllib.parse import quote
from build_fex_context import ROOT,LOCAL,WORK,BASE,PIN,BUILD,MARKER,sha,write_json

PREFIX='switch/sleepingdogs-fex/'
INSTRUCTIONS='''FEXTendo Sleeping Dogs - FEX context v1

FOLDER SIAP SALIN, TANPA ZIP. Update khusus instalasi Native H4 v9 yang sudah
berjalan. Tetap Light 1280x720. Belum ada hasil FPS kandidat ini di Switch.

Update ini mempercepat konversi konteks x87 FEX untuk nilai yang persis bisa
direpresentasikan. Presisi/profil FEX tetap; nilai lain memakai konversi lama.
Wine, NRO, DXVK, shader cache, batching dan XML tidak diganti oleh update utama.
9,7 juta pemeriksaan lokal lulus; ini bukan bukti kenaikan FPS game.

1. Tutup aplikasi sepenuhnya dari HOME. Salin switch/ utama ke root SD, timpa
   file terkait. Jalankan COM test. Harus PASS, exit 00000000, dan runtime.log
   COM harus memuat [SD-FEX-CONTEXT] v1 exact x87 import.
   Label NRO/hasil tetap native-dxvk-h4-v9 karena NRO tidak diganti.
2. Simpan log COM sebelum tes game, dari switch/sleepingdogs-fex/:
   drive_c/native-dxvk-h4-result.json
   drive_c/native-dxvk-h4-guest.log
   native-dxvk-h4/runtime.log
3. Jika PASS, tutup HOME, salin start-game-light/switch/ ke root SD. Pilih
   Native ARM64, Performance, Light 720p, HUD yang sama. LSFG OFF pada native.
   Gunakan clock sama: acuan CPU 1728 / GPU 768 / RAM 1600 MHz.
4. Tes posisi/kamera yang sama setelah cache hangat 30-60 detik, kemudian
   rute keramaian yang sama. Simpan log sebelum launch berikutnya.
5. Untuk A/B atau rollback: tutup HOME dan salin fex-baseline/switch/.
   Ini mengembalikan DLL FEX lama persis. Untuk kandidat lagi gunakan
   fex-fast/switch/ setelah tutup HOME. Tes ulang kondisi yang sama.

JANGAN SALIN SEMUA FOLDER SEKALIGUS. Main switch/ sudah memasang kandidat;
fex-fast tidak perlu disalin lagi kecuali setelah menggunakan fex-baseline.
Tidak perlu batch-on/batch-off; pertahankan kondisi batching yang sama.
Jika COM gagal atau gameplay bermasalah, pulihkan fex-baseline.

Kirim log game tiap kondisi dari switch/sleepingdogs-fex/:
  fex-runtime.log
  native-dxvk-h4/HKShip.exe_d3d11.log
  crash.log jika ada crash baru
Marker FEX kandidat: [SD-FEX-CONTEXT] v1 exact x87 import.
Baseline tidak memiliki marker itu. Catat FPS biasa/ramai, pause/resume,
dan keluar normal. runtime.log COM lama tidak membuktikan tes terbaru.

Tidak ada game/save/DisplaySettings.xml/UserOptions.dat di paket.
source/ dan reports/ tidak perlu disalin ke SD. Detail: source/fex-context-v1.md.
30 FPS stabil belum dibuktikan. Angka instruksi lokal bukan estimasi FPS.
'''

def main():
    build=json.loads((LOCAL/'build.json').read_text());host=json.loads((LOCAL/'host-test.json').read_text());arm=json.loads((LOCAL/'arm64-test.json').read_text())
    assert build['status']=='BUILT' and build['baseline_reproduced']
    assert host['status']==arm['status']=='PASS'
    for report in (build,host):
        for name,expected in report['source_files'].items():assert sha(ROOT/name)==expected,name
    assert arm['source_sha256']==sha(ROOT/'tests/fex_context_arm64.py')
    assert arm['build_receipt_sha256']==sha(LOCAL/'build.json')
    assert host['candidate_source_sha256']==build['patches']['fpu']['source_sha256']
    assert arm['dll_sha256']==build['dll_sha256']==sha(LOCAL/'libwow64fex.dll')
    assert arm['baseline_sha256']==build['baseline_sha256']==sha(LOCAL/'baseline-libwow64fex.dll')
    assert sha(PIN)==build['pin_sha256']
    assert MARKER.encode() in (LOCAL/'libwow64fex.dll').read_bytes()
    assert MARKER.encode() not in (LOCAL/'baseline-libwow64fex.dll').read_bytes()
    for path,digest in build['header_inputs'].items():assert sha(path)==digest,path
    for path,digest in build['inputs'].items():assert sha(path)==digest,path
    previous=ROOT/'dist/sd-dxvk-native-h4-v9-update';manifest=previous/'SHA256SUMS.txt'
    expected_manifest=json.loads((ROOT/'reports/native-dxvk-h4-v9-folder.json').read_text())['checksums_sha256']
    assert sha(manifest)==expected_manifest
    entries={};entry=lambda path,data:entries.__setitem__(path,data)
    fex='drive_c/windows/system32/libwow64fex.dll'
    entry(PREFIX+fex,(LOCAL/'libwow64fex.dll').read_bytes())
    client=PREFIX+'drive_c/sd-native-dxvk-h4-test.exe'
    expected=dict((line.split('  ',1)[1],line.split('  ',1)[0]) for line in manifest.read_text().splitlines())
    assert sha(previous/client)==expected[client]
    entry(client,(previous/client).read_bytes());entry(PREFIX+'run-native-com-test.txt',b'1\n')
    for mode,dll in [('fex-baseline','baseline-libwow64fex.dll'),('fex-fast','libwow64fex.dll')]:
        entry(mode+'/'+PREFIX+fex,(LOCAL/dll).read_bytes());entry(mode+'/'+PREFIX+'run-native-com-test.txt',b'0\n')
    for name,value in [('run-native-com-test.txt','0\n'),('launcher/renderer-choice.txt','2\n'),('launcher/game-quality.txt','1\n')]:
        entry('start-game-light/'+PREFIX+name,value.encode())
    identity=dict(build=BUILD,native_runtime_required='native-dxvk-h4-v9',fex_sha256=build['dll_sha256'],baseline_fex_sha256=build['baseline_sha256'],hardware_tested=False,game_fps_measured=False)
    entry(PREFIX+'launcher/fex-context-experiment.json',(json.dumps(identity,indent=2)+'\n').encode())
    # Mirror identity per alternative so metadata never silently claims fast
    # after a baseline copy; the actual DLL/startup marker remains authoritative.
    for mode in ('fex-baseline','fex-fast'):
        data=dict(identity,selected=mode,installed_fex_sha256=identity['baseline_fex_sha256'] if mode=='fex-baseline' else identity['fex_sha256'])
        entry(mode+'/'+PREFIX+'launcher/fex-context-experiment.json',(json.dumps(data,indent=2)+'\n').encode())
    entry('README-INSTALL.txt',INSTRUCTIONS.encode())
    for name in ('build','host-test','arm64-test'):
        data=(LOCAL/(name+'.json')).read_bytes();entry('reports/'+name+'.json',data)
        (ROOT/'reports'/('fex-context-v1-'+name+'.json')).write_bytes(data)
    for name in ('module','fpu'):entry('source/'+name+'.patch',(LOCAL/(name+'.patch')).read_bytes())
    for name in ('Module.cpp','module_fpu.cpp','horizon_fpu.h','exact_x87.h'):
        entry('source/candidate/'+name,(WORK/'source'/name).read_bytes())
    for path in (BASE/'source/Source/Windows/WOW64/Module.cpp',BASE/'adapter/module_fpu.cpp',BASE/'adapter/horizon_fpu.h'):
        entry('source/baseline/'+path.name,path.read_bytes())
    for name in ('tools/build_fex_context.py','tools/test_fex_context.py','tools/package_fex_context.py','tools/port_common.py',
                 'tests/fex_context_exact.cpp','tests/fex_context_arm64.py','src/fex_context/exact_x87.h','vendor/fex/libwow64fex-sd-scene.json'):
        entry('source/project/'+name,(ROOT/name).read_bytes())
    documentation=(ROOT/'docs/fex-context-v1.md').read_text()
    def documentation_link(match):
        url=match[1]
        if url.startswith(('https://','http://','#')):return match[0]
        target=(ROOT/'docs'/url.split('#',1)[0]).resolve()
        relative=target.relative_to(ROOT).as_posix()
        assert target.is_file(),relative
        return '](https://github.com/Ibnuard/sleepingdogs_nx/blob/experiment/native-dxvk-probe-v1/'+quote(relative,safe='/')+')'
    entry('source/fex-context-v1.md',re.sub(r'\]\(([^)]+)\)',documentation_link,documentation).encode())
    entry('source/FEX-LICENSE',(BASE/'source/LICENSE').read_bytes())
    import hashlib
    digest=lambda data:hashlib.sha256(data).hexdigest()
    entry('SHA256SUMS.txt',''.join(digest(data)+'  '+name+'\n' for name,data in sorted(entries.items())).encode())
    path=ROOT/'dist/sd-fex-context-v1-update'
    if path.exists():
        assert {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}==set(entries),'Preserve existing files; use a fresh version'
        for name,data in entries.items():assert (path/name).read_bytes()==data,('Existing package differs; use a fresh version',name)
    else:
        for name,data in entries.items():
            target=path/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for name,data in entries.items():assert sha(path/name)==digest(data),name
    assert sha(previous/'SHA256SUMS.txt')==expected_manifest
    result=dict(status='PASS',build=BUILD,path=str(path),files=len(entries),bytes=sum(map(len,entries.values())),
        all_file_hashes_verified=True,zip_created=False,scope='FEX-only delta on installed H4 v9; COM client unchanged',
        fex_sha256=build['dll_sha256'],rollback_fex_sha256=build['baseline_sha256'],nro_included=False,
        game_data_included=False,resolution=[1280,720],hardware_tested=False,game_fps_measured=False,
        previous_manifest_sha256=expected_manifest,checksums_sha256=sha(path/'SHA256SUMS.txt'),
        receipts={k:sha(LOCAL/(k+'.json')) for k in ('build','host-test','arm64-test')},packager_sha256=sha(__file__))
    write_json(ROOT/'reports/fex-context-v1-folder.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
