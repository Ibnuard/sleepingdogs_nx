"""Prepare an immutable ready-copy update, controlled A/B and exact rollback."""
from pathlib import Path
import hashlib,json,os

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/launcher-v2'
COMPACT=ROOT/'local/native-dxvk-compact-v1'
PREFIX='switch/sleepingdogs-fex/'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encode(x):return (json.dumps(x,indent=2)+'\n').encode()
def host(p):
    s=str(p)
    if os.name=='nt':
        if s.startswith('/mnt/'):return Path(s[5]+':/'+s[7:])
        if s.startswith('/'):return Path('//wsl.localhost/Ubuntu'+s)
    return Path(s)

INSTRUCTIONS='''SLEEPING DOGS - LAUNCHER v2: CACHED CHECK / NATIVE LSFG / LIGHT 720p

Tutup aplikasi sepenuhnya dari HOME. Salin HANYA folder switch/ utama di
sini ke root SD, pilih Replace. Tidak perlu start-game untuk pemasangan biasa.
Ini update untuk instalasi Sleeping Dogs FEXTendo yang sudah berjalan.

LIGHT 720p wajib setiap launch; pilihan Light/Original dihapus. Nilai lama
launcher/game-quality.txt diabaikan. Game asli, save dan DisplaySettings.xml
tidak dibundel. Backup XML sebelum Light tetap dipertahankan.

System Check: verifikasi SHA256 lengkap sekali setelah update. Pembukaan
berikutnya memakai hasil tersimpan selama ukuran/waktu modifikasi file sama.
Update/perubahan file atau Settings > System Check memicu verifikasi penuh.
Validasi HOME/patch low-memory aktif dan mapping tetap berjalan singkat
setiap proses. Mengganti firmware/boot tidak bisa dilewati dengan cache.

LSFG: Settings > Frame Generation > ON. Pilihan diterapkan saat Play.
Sambungan native DXVK sekarang ikut menggunakan backend LSFG. Paket shader
pribadi ikut disertakan; jangan distribusikan pack ini sebagai rilis publik.
LSFG OFF tetap render biasa. Keyboard sementara menghentikan interpolasi.
Log yang membuktikan frame generation:
  [SD-LSFG-V15] 2x generating; first interpolated present submitted
  window_ms=... real=... generated=...
Requested ON atau initialized saja belum membuktikan frame hasil interpolasi.
DXVK HUD dan [SD-NDX-FPS] tetap menghitung FPS game asli.

Build ini memperbaiki verifier, Light wajib, dan sambungan LSFG. Optimasi
Compact COM/FEX sebelumnya dipertahankan; log terbaru belum membuktikan
kenaikan FPS asli. LSFG menambah frame tampilan dan biaya GPU, bukan kecepatan
simulasi. Tidak ada klaim 30 FPS asli atau kenaikan performa Switch.

Opsional, jangan copy semua subfolder:
- start-com-test: COM self-test; sesudahnya start-game kembali ke GUI.
- performance-off/on: bandingkan proxy Ref v1/Compact pada NRO baru yang sama.
- rollback-launcher-v1: kembali ke launcher/compact sebelumnya.
- rollback-ref-v1: kembali ke NRO H4v9 dan proxy Ref v1.

Kirim fex-runtime.log, system-check.log dan HKShip.exe_d3d11.log dari sesi
baru. Untuk uji FPS asli pakai LSFG OFF, 720p, CPU 1728/GPU 768/RAM 1600,
rute dan kamera sama. Uji ON terpisah; simpan log masing-masing sesi.

Keyboard tetap L+R+Left Stick. Debug hanya tampil jika toggle Settings ON.
Source, lisensi, laporan dan checksum tidak perlu disalin ke SD.
'''

def main():
    build=json.loads((LOCAL/'build.json').read_text());tests=json.loads((LOCAL/'test.json').read_text())
    binary=json.loads((LOCAL/'binary-test.json').read_text());compact=json.loads((COMPACT/'build.json').read_text())
    guest=json.loads((COMPACT/'guest-test.json').read_text());native=json.loads((COMPACT/'host-test.json').read_text())
    assert all(r['status']=='PASS' for r in (tests,binary,guest,native))
    assert binary['nro_sha256']==build['nro_sha256']==sha(LOCAL/'sleepingdogs-fex.nro')
    assert binary['elf_sha256']==build['elf_sha256']==sha(host(build['elf']))
    assert build['compact_build_receipt_sha256']==sha(COMPACT/'build.json')
    assert guest['candidate_sha256']==compact['proxy_sha256']==sha(COMPACT/'sdndx4.dll')
    assert tests['source_files']==build['source_files']
    for name,digest in build['source_files'].items():assert sha(ROOT/name)==digest,name
    for name,digest in build['builder_sources'].items():assert sha(ROOT/name)==digest,name
    for name,digest in compact['source_files'].items():assert sha(COMPACT/name)==digest,name
    assert native['candidate_sources']==compact['source_files']
    catalog=json.loads((LOCAL/'catalog.json').read_text());assert sha(LOCAL/'catalog.json')==build['runtime_catalog_sha256']
    lsfg=json.loads((LOCAL/'lsfg-test.json').read_text());assert lsfg['status']=='PASS' and lsfg['generated_sessions']==3
    for name,digest in lsfg['source_files'].items():assert sha(host(name))==digest,name
    entries={'README.txt':INSTRUCTIONS.encode()}
    def put(name,path=None,data=None):
        assert not name.startswith('/') and '..' not in Path(name).parts
        value=Path(path).read_bytes() if path else data
        entries[name]=value
    prior=ROOT/'dist/sd-dxvk-native-h4-v9-update'
    assert sha(prior/'SHA256SUMS.txt')=='0c3f794d2f39f37c981a8ee187834486b6fa61e0c683529aa92a503ac627ab02'
    prior_files={line.split('  ',1)[1]:line.split('  ',1)[0] for line in (prior/'SHA256SUMS.txt').read_text().splitlines()}
    # Proven native profiles, shims and notices; not an old NRO or COM mode.
    for p in (prior/PREFIX).rglob('*'):
        if p.is_file() and p.name not in ('sleepingdogs-fex.nro','run-native-com-test.txt'):
            relative=p.relative_to(prior).as_posix()
            if relative not in prior_files:continue
            assert sha(p)==prior_files[relative],relative
            put(relative,p)
    for e in catalog:
        p=host(e['source']);assert sha(p)==e['sha256'] and p.stat().st_size==e['bytes'],e['path']
        put(PREFIX+e['path'],p)
    put(PREFIX+'sleepingdogs-fex.nro',LOCAL/'sleepingdogs-fex.nro')
    put(PREFIX+'drive_c/SleepingDogs/sdndx4.dll',COMPACT/'sdndx4.dll')
    for dll in ('d3d11.dll','dxgi.dll'):
        put(PREFIX+'drive_c/SleepingDogs/'+dll,prior/PREFIX/'launcher/renderers/dxvk-native-h4'/dll)
    put(PREFIX+'drive_c/sd-native-dxvk-h4-test.exe',COMPACT/'sd-native-dxvk-h4-test.exe')
    for name,value in (('run-native-com-test.txt','0\n'),('launcher/renderer-choice.txt','2\n'),('launcher/debug-launch.txt','0\n')):
        put(PREFIX+name,data=value.encode())
    marker=dict(build='launcher-v2',nro_sha256=build['nro_sha256'],proxy_sha256=compact['proxy_sha256'],hardware_tested=False)
    put(PREFIX+'launcher/build-v2.json',data=encode(marker))
    old_proxy=ROOT/'local/native-dxvk-ref-v1/candidate/sdndx4.dll'
    assert sha(old_proxy)==compact['baseline_proxy_sha256']
    for mode,dll in (('performance-off',old_proxy),('performance-on',COMPACT/'sdndx4.dll')):
        for path in ('drive_c/SleepingDogs/sdndx4.dll','launcher/renderers/dxvk-native-h4/sdndx4.dll'):put(mode+'/'+PREFIX+path,dll)
        put(mode+'/'+PREFIX+'run-native-com-test.txt',data=b'0\n')
    for name,value in (('start-com-test',b'1\n'),('start-game',b'0\n')):put(name+'/'+PREFIX+'run-native-com-test.txt',data=value)
    put('rollback-ref-v1/'+PREFIX+'sleepingdogs-fex.nro',prior/PREFIX/'sleepingdogs-fex.nro')
    assert sha(prior/PREFIX/'sleepingdogs-fex.nro')==build['baseline_nro_sha256']
    for path in ('drive_c/SleepingDogs/sdndx4.dll','launcher/renderers/dxvk-native-h4/sdndx4.dll'):put('rollback-ref-v1/'+PREFIX+path,old_proxy)
    put('rollback-ref-v1/'+PREFIX+'drive_c/sd-native-dxvk-h4-test.exe',ROOT/'local/native-dxvk-ref-v1/candidate/sd-native-dxvk-h4-test.exe')
    put('rollback-ref-v1/'+PREFIX+'run-native-com-test.txt',data=b'0\n')
    previous=ROOT/'dist/sd-launcher-compact-v1-update'
    for rel in ('sleepingdogs-fex.nro','launcher/renderers/dxvk-native-h4/sdndx4.dll','drive_c/SleepingDogs/sdndx4.dll'):
        put('rollback-launcher-v1/'+PREFIX+rel,previous/PREFIX/rel)
    put('rollback-launcher-v1/'+PREFIX+'run-native-com-test.txt',data=b'0\n')
    for folder in ('src/launcher','src/native_dxvk_com','src/native_dxvk','tests/pes13'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file():put('source/'+p.relative_to(ROOT).as_posix(),p)
    for p in (ROOT/'tools').iterdir():
        if p.name in ('launcher_v1_overlay.py','launcher_v2_overlay.py','native_dxvk_compact.py','make_launcher_vulkan_fixture.py','test_lsfg_native_v2.py') or ('launcher' in p.name or 'native_dxvk_compact' in p.name) and p.suffix=='.py':
            put('source/tools/'+p.name,p)
    for p in (ROOT/'tests').glob('launcher*'):put('source/tests/'+p.name,p)
    put('source/tests/native_dxvk_compact_wire.c',ROOT/'tests/native_dxvk_compact_wire.c')
    for name in ('LICENSE','THIRD_PARTY.md','vendor/pes13-launcher.json','docs/launcher-v2.md'):put(name,ROOT/name)
    for p in (prior/'source').rglob('*'):
        if p.is_file() and any(t in p.name.upper() for t in ('LICENSE','COPYING','NOTICE')):put('licenses/'+p.relative_to(prior/'source').as_posix(),p)
    for folder,prefix,names in ((LOCAL,'launcher',('build.json','test.json','binary-test.json','catalog.json','lsfg-test.json')),
                              (COMPACT,'compact',('build.json','host-test.json','guest-test.json'))):
        for name in names:put('reports/'+prefix+'-'+name,folder/name)
    put('reports/latest-game.json',ROOT/'reports/launcher-v1-game-7cadea575589.json')
    # Include exact generated native/guest deltas, alongside their generators.
    for name,digest in compact['source_files'].items():put('generated/'+name,COMPACT/name)
    for name,digest in build['generated_sources'].items():
        p=host('/home/blekjek/sleepingdogs-launcher-v2/'+name);assert sha(p)==digest
        put('generated/launcher/'+name,p)
    lsfg_root=host('/home/blekjek/sleepingdogs-lsfg-v15')
    for name in ('lsfg.h','lsfg_config.h','sd_lsfg_pack.hpp'):
        put('generated/launcher/source/'+name,lsfg_root/'native-source/wine-nx-probe/source'/name)
    for p in (lsfg_root/'backend').rglob('*'):
        if p.is_file() and '.git' not in p.parts:put('source/lsfg/'+p.relative_to(lsfg_root/'backend').as_posix(),p)
    digest=lambda b:hashlib.sha256(b).hexdigest()
    put('SHA256SUMS.txt',data=''.join(digest(data)+'  '+name+'\n' for name,data in sorted(entries.items())).encode())
    out=ROOT/'dist/sd-launcher-v2-update'
    if out.exists():
        assert {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}==set(entries),'Preserve existing delivery; choose a fresh version'
        for name,data in entries.items():assert (out/name).read_bytes()==data,name
    else:
        for name,data in entries.items():p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    for name,data in entries.items():assert sha(out/name)==digest(data),name
    # No game executable, archives, settings, saves or generated logs in the update.
    game=[n[len(PREFIX+'drive_c/SleepingDogs/'):] for n in entries if n.startswith(PREFIX+'drive_c/SleepingDogs/')]
    assert set(game)<={'d3d11.dll','dxgi.dll','sdndx4.dll'},game
    assert not any(n.lower().endswith(('.zip','.rar')) for n in entries)
    result=dict(status='PASS',path=str(out),files=len(entries),bytes=sum(len(x) for x in entries.values()),all_hashes_verified=True,
                nro_sha256=build['nro_sha256'],proxy_sha256=compact['proxy_sha256'],manifest_sha256=sha(out/'SHA256SUMS.txt'),
                zip_created=False,game_data_included=False,hardware_tested=False,game_fps_measured=False)
    (ROOT/'reports/launcher-v2-folder.json').write_bytes(encode(result));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
