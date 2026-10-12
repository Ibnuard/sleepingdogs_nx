"""Build a source-bound, immutable ready-copy local-reference update; no ZIP."""
from pathlib import Path
import hashlib,json,re
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/native-dxvk-ref-v1'
PREFIX='switch/sleepingdogs-fex/'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(data):return hashlib.sha256(data).hexdigest()
def encode(value):return (json.dumps(value,indent=2)+'\n').encode()

INSTRUCTIONS='''FEXTendo Native DXVK Ref v1 — kurangi panggilan referensi FEX/Wine

FOLDER SIAP SALIN, TANPA ZIP. Memerlukan instalasi native H4 v9 yang sudah
berjalan. Pertahankan FEX context v1 dari tes terakhir dan resolusi 1280x720.
Ini mengganti proxy sdndx4.dll dan klien tes COM; tidak menyertakan NRO.
Versi NRO tetap h4.9. FPS crowded 20+ / stabil 30 belum dibuktikan di Switch.

1. Tutup aplikasi sepenuhnya dari HOME. Salin switch/ utama ke root SD dan
   timpa file terkait. Kedua salinan sdndx4.dll perlu diganti: launcher dapat
   menyalin ulang DLL renderer ke folder game.
2. Jalankan COM self-test dahulu. native-dxvk-h4-result.json harus PASS,
   reference_optimization=native-dxvk-ref-v1, reference_pairs=2048,
   reference_crossings_saved=4096, live_interfaces=0, live_maps=0,
   bridge_failures=0. Tes juga mempertahankan pemeriksaan gambar dan Map.
3. Simpan log COM sebelum game. Setelah PASS, salin start-game-light/switch/
   ke root SD. Pilih DXVK Native ARM64, Performance, Light 720p, HUD FPS.
4. Bandingkan lokasi/kamera ramai yang sama setelah cache hangat. Referensi
   clock CPU 1728 / GPU 768 / RAM 1600 MHz. Catat FPS biasa dan saat ramai;
   cek pause/resume dan keluar normal. Jangan menggabungkan overlay A/B.
5. Kirim log sesi GAME berikut:
   switch/sleepingdogs-fex/fex-runtime.log
   switch/sleepingdogs-fex/native-dxvk-h4/HKShip.exe_d3d11.log
   switch/sleepingdogs-fex/drive_c/native-dxvk-ref-v1.log  (BARU, penting)
   serta native-dxvk-h4/runtime.log bila diperbarui pada sesi tersebut.

Log baru ditulis pada Present pertama, setiap 600 Present, serta saat tes
mengambil statistik. local_addrefs + local_releases adalah jumlah panggilan
yang tidak menyeberang ke native; angka ini bukan FPS atau waktu CPU.
Counter kumulatif 32-bit dapat berputar pada sesi yang sangat panjang.

Jika ada crash/gambar rusak atau untuk perbandingan, tutup HOME dan salin
ref-baseline/switch/ ke root SD. Ini mengembalikan DLL + klien tes v9 asli,
mematikan COM otomatis, dan mempertahankan FEX serta konfigurasi grafis.
ref-local/switch/ mengaktifkan kandidat kembali tanpa menjalankan COM otomatis.
Log ref-v1 lama bisa tetap ada setelah rollback; periksa sesi/tanggalnya.

Jangan salin source/, reports/, ref-baseline/, ref-local/ bersamaan ke SD.
Source dan bukti tes tersedia untuk ditinjau. Tidak ada data game/save di sini.
'''

def main():
    build=json.loads((LOCAL/'build.json').read_text());test=json.loads((LOCAL/'test.json').read_text())
    assert build['baseline_reproduced'] and test['status']=='PASS'
    assert test['build_receipt_sha256']==sha(LOCAL/'build.json')
    assert sha(LOCAL/'candidate/sdndx4.dll')==build['proxy_sha256']==test['candidate_sha256']
    assert sha(LOCAL/'baseline/sdndx4.dll')==build['baseline_proxy_sha256']
    assert sha(LOCAL/'candidate/sd-native-dxvk-h4-test.exe')==build['com_client_sha256']
    assert build['builder_sha256']==sha(ROOT/'tools/build_native_dxvk_refs.py')
    assert test['runner_sha256']==sha(ROOT/'tools/test_native_dxvk_refs.py')
    for relative,value in build['source_files']['candidate'].items():
        assert sha(LOCAL/'candidate'/relative)==value
        assert sha(ROOT/relative.replace('source/','src/',1))==value,relative
    for name,case in test['cases'].items():
        fixture='refs' if name.startswith('refs') else name
        assert sha(ROOT/'tests'/('native_dxvk_guest_'+fixture+'.c'))==case['fixture_sha256']
    old=ROOT/'dist/sd-dxvk-native-h4-v9-update'
    manifest='0c3f794d2f39f37c981a8ee187834486b6fa61e0c683529aa92a503ac627ab02'
    assert sha(old/'SHA256SUMS.txt')==manifest
    old_dll=old/PREFIX/'launcher/renderers/dxvk-native-h4/sdndx4.dll'
    old_test=old/PREFIX/'drive_c/sd-native-dxvk-h4-test.exe'
    assert sha(old_dll)==build['baseline_proxy_sha256']
    old_receipt=json.loads((ROOT/'local/native-dxvk-h4-v9/build.json').read_text())
    assert sha(old_test)==old_receipt['pe_audits']['sd-native-dxvk-h4-test.exe']['sha256']
    entries={'README.txt':INSTRUCTIONS.encode()}
    def entry(name,data):assert name not in entries;entries[name]=data
    def overlay(name,candidate,com):
        prefix=(name+'/' if name else '')+PREFIX
        dll=(LOCAL/'candidate/sdndx4.dll').read_bytes() if candidate else old_dll.read_bytes()
        for path in ('drive_c/SleepingDogs/sdndx4.dll','launcher/renderers/dxvk-native-h4/sdndx4.dll'):
            entry(prefix+path,dll)
        client=(LOCAL/'candidate/sd-native-dxvk-h4-test.exe').read_bytes() if candidate else old_test.read_bytes()
        entry(prefix+'drive_c/sd-native-dxvk-h4-test.exe',client)
        entry(prefix+'run-native-com-test.txt',(str(com)+'\n').encode())
        entry(prefix+'launcher/native-dxvk-ref-experiment.json',encode(dict(build='native-dxvk-ref-v1',
            mode='local-references' if candidate else 'original-v9',proxy_sha256=digest(dll),
            required_nro_sha256=build['unchanged_nro_sha256'],fps_gain_measured=False)))
    overlay('',True,1);overlay('ref-local',True,0);overlay('ref-baseline',False,0)
    for path,value in [('run-native-com-test.txt','0\n'),('launcher/renderer-choice.txt','2\n'),('launcher/game-quality.txt','1\n')]:
        assert (old/'start-game-light'/PREFIX/path).read_bytes()==value.encode(),path
        entry('start-game-light/'+PREFIX+path,value.encode())
    for relative in build['source_files']['candidate']:
        entry(relative,(LOCAL/'candidate'/relative).read_bytes())
    for name in ('build_native_dxvk_refs.py','test_native_dxvk_refs.py','package_native_dxvk_refs.py'):
        entry('source/tools/'+name,(ROOT/'tools'/name).read_bytes())
    for name in ('refs','outputs','lookup','maps','transport'):
        entry('source/tests/native_dxvk_guest_'+name+'.c',(ROOT/'tests'/('native_dxvk_guest_'+name+'.c')).read_bytes())
    entry('source/LICENSE',(ROOT/'LICENSE').read_bytes())
    entry('source/THIRD_PARTY.md',(ROOT/'THIRD_PARTY.md').read_bytes())
    # Preserve the notices already shipped with the bridge and generated IDL.
    old_hashes={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (old/'SHA256SUMS.txt').read_text().splitlines()}
    for path in sorted((old/'notices').rglob('*')):
        if path.is_file():
            name=path.relative_to(old).as_posix();assert sha(path)==old_hashes[name],name
            entry(name,path.read_bytes())
    def doc_link(match):
        target=match[1]
        if target.startswith(('https://','http://','#')):return match[0]
        relative=(ROOT/'docs'/target).resolve().relative_to(ROOT).as_posix()
        return '](https://github.com/Ibnuard/sleepingdogs_nx/blob/experiment/native-dxvk-probe-v1/'+quote(relative,safe='/')+')'
    document=re.sub(r'\]\(([^)]+)\)',doc_link,(ROOT/'docs/native-dxvk-ref-v1.md').read_text())
    entry('source/native-dxvk-ref-v1.md',document.encode())
    for name in ('build','test'):entry('reports/'+name+'.json',(LOCAL/(name+'.json')).read_bytes())
    entry('reports/previous-gameplay.json',(ROOT/'reports/fex-context-v1-gameplay-observation.json').read_bytes())
    entry('SHA256SUMS.txt',''.join(digest(data)+'  '+name+'\n' for name,data in sorted(entries.items())).encode())
    folder=ROOT/'dist/sd-native-dxvk-ref-v1-update'
    if folder.exists():
        assert {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}==set(entries),'Use a fresh version; preserve existing delivery'
        for name,data in entries.items():assert (folder/name).read_bytes()==data,('Existing delivery differs',name)
    else:
        for name,data in entries.items():
            path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    for name,data in entries.items():assert sha(folder/name)==digest(data),name
    assert sha(old/'SHA256SUMS.txt')==manifest
    result=dict(status='PASS',build=build['build'],path=str(folder),files=len(entries),bytes=sum(map(len,entries.values())),
        all_file_hashes_verified=True,zip_created=False,nro_included=False,game_data_included=False,
        proxy_sha256=build['proxy_sha256'],rollback_proxy_sha256=build['baseline_proxy_sha256'],
        build_receipt_sha256=sha(LOCAL/'build.json'),test_receipt_sha256=sha(LOCAL/'test.json'),
        checksums_sha256=sha(folder/'SHA256SUMS.txt'),packager_sha256=sha(__file__),
        required_native_nro_sha256=build['unchanged_nro_sha256'],resolution=[1280,720],hardware_tested=False,game_fps_measured=False)
    (ROOT/'reports/native-dxvk-ref-v1-folder.json').write_bytes(encode(result));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
