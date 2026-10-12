"""Ready-copy state-filter/FIFO fix update; retain exact v2 rollback."""
from pathlib import Path
from launcher_v1_overlay import ROOT,replace

INSTRUCTIONS='''SLEEPING DOGS - LAUNCHER v3 / NATIVE STATE v1 / FIFO LSFG FIX

Tutup aplikasi sepenuhnya dari HOME. Salin HANYA folder switch/ utama ke
root kartu SD, pilih Replace. Tidak perlu start-game untuk pemasangan biasa.
Ini update untuk instalasi FEXTendo Sleeping Dogs yang sudah berjalan.

FPS ASLI: filter baru melewati 25 jenis binding render yang persis berulang
sebelum masuk Wine/FEX/native DXVK. Draw, Map/Unmap, copy buffer dan binding
resource berisiko tetap diteruskan. Resolusi tetap Light 1280x720.
Log [SD-NDX-STATE] menunjukkan attempts/skipped dan jenis binding yang dilewati.
Ini kandidat optimasi; kenaikan FPS atau 30 FPS belum diuji pada Switch.

LSFG: log sebelumnya ON tetapi 5034 kali ditolak karena metadata present.
Build ini menerima override FIFO yang cocok. Uji Vulkan host dengan metadata
mode dan present fence menghasilkan frame interpolasi, 0 error validasi.
Bukti saat bermain: "first interpolated present submitted" lalu
"window_ms=... real=... generated=...". ON/initialized saja belum membuktikan
interpolasi. DXVK HUD tetap menghitung FPS game, bukan frame hasil LSFG.

TES: pengaturan LSFG lama dipertahankan. Untuk FPS asli, buka Settings >
Frame Generation dan pilih OFF, lalu Play. Gunakan rute/kamera yang sama,
720p dan CPU 1728 / GPU 768 / RAM 1600. Uji LSFG ON terpisah; mulai motion
12.5% agar biaya tambahan lebih kecil. Ini tidak menurunkan resolusi game.
Kirim fex-runtime.log dan HKShip.exe_d3d11.log dari setiap sesi terpisah.

Pilihan opsional (jangan copy semua sekaligus):
- performance-off/switch: proxy Compact v1, tanpa filter binding, NRO v3 sama.
- performance-on/switch: kembalikan filter Native State v1.
- rollback-launcher-v2/switch: NRO dan proxy persis seperti build sebelumnya.
- start-com-test/switch: tes COM; start-game/switch mengembalikan launch GUI.

Verifier penuh sekali setelah update, lalu memakai cache. System Check manual
memaksa cek penuh; patch low-memory aktif tetap wajib setiap boot. Debug hanya
muncul setelah toggle Settings ON. Keyboard L+R+Left Stick tetap tersedia.
Game, save dan DisplaySettings.xml tidak disertakan; backup XML tetap ada.

Paket LSFG ini berasal dari input pribadi pengguna; jangan distribusikan
shader pack sebagai rilis publik. Source, lisensi, laporan dan checksum
tidak perlu disalin ke SD. Tidak ada ZIP baru.
'''

def main():
    text=(ROOT/'tools/package_launcher_v2.py').read_text()
    text=text.replace('launcher-v2','launcher-v3').replace('native-dxvk-compact-v1','native-dxvk-state-v1')
    text=text.replace("guest['candidate_sha256']","guest['proxy_sha256']").replace("lsfg['generated_sessions']==3","lsfg['generated_sessions']==4")
    text=replace(text,"old_proxy=ROOT/'local/native-dxvk-ref-v1/candidate/sdndx4.dll'","old_proxy=ROOT/'local/native-dxvk-compact-v1/sdndx4.dll'")
    start=text.index("    put('rollback-ref-v1/");end=text.index("    previous=ROOT/",start)
    text=text[:start]+text[end:]
    text=text.replace("dist/sd-launcher-compact-v1-update","dist/sd-launcher-v2-update").replace('rollback-launcher-v1','rollback-launcher-v2')
    text=text.replace("'launcher-v1-game-7cadea575589.json'","'launcher-v2-game-2d5516526c0a.json'")
    text=text.replace("ROOT/'reports/launcher-v1-game-7cadea575589.json'","ROOT/'reports/launcher-v2-game-2d5516526c0a.json'")
    text=text.replace("(COMPACT,'compact',","(COMPACT,'state',")
    text=replace(text,"    for p in (ROOT/'tests').glob('launcher*'):put('source/tests/'+p.name,p)",
        "    for p in (ROOT/'tests').glob('launcher*'):put('source/tests/'+p.name,p)\n"
        "    for name in ('native_dxvk_guest_state.c','lsfg_present_policy.cpp','lsfg_present.cpp','lsfg_headless.cpp'):put('source/tests/'+name,ROOT/'tests'/name)\n"
        "    for name in ('native_dxvk_state.py','build_native_dxvk_state.py','test_native_dxvk_state.py','test_native_dxvk_state_host.py','test_lsfg_native_v3.py','test_lsfg_native_v2.py','launcher_v2_overlay.py'):put('source/tools/'+name,ROOT/'tools'/name)")
    ns={'__name__':'v3_package','__file__':__file__}
    exec(compile(text,__file__,'exec'),ns);ns['INSTRUCTIONS']=INSTRUCTIONS;ns['main']()
if __name__=='__main__':main()
