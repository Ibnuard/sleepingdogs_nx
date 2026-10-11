# Legacy project notes

> Archived README, preserved on 2026-10-11. These notes describe successive
> test builds, including the superseded 32-bit installation. They are not
> the current setup guide or an instruction to install every patch. Start
> with [Installation](INSTALL.md), [Current status](STATUS.md), or the
> [development history](HISTORY.md). Local `dist/` paths below are artifact
> names from the original workspace, not GitHub downloads.

---

# Sleeping Dogs — FEXTendo / Wine-NX + FEX

Port eksperimental **Sleeping Dogs PC original (HKShip.exe, x86)** untuk Nintendo
Switch. Folder dan prefix terpisah: `switch/sleepingdogs-fex/`.

Untuk boot **FEXTendo Memory v1 TEST**, install forwarder descriptor v1 dari
**`dist/sleepingdogs-fex-fextendo-memory-v1/forwarder/`**. Title ID dan target
tetap sama; gunakan NRO v7, v8, atau v9 di bawah. Tidak perlu reboot lagi jika boot generik
itu masih aktif. [Petunjuk forwarder generik](forwarder-memory-v1.md).

**Pengguna sudah mengonfirmasi gameplay pada v6 di OLED handheld
(CPU 1728 / GPU 768 / RAM 1600 MHz). Bug jumlah worker nol telah terlewati;
performa masih rendah. v7 menambahkan HUD dan pilihan Performance, serta
mengurangi pengamatan rinci pada Launch biasa. Log v7 Performance terbaru
mengonfirmasi sekitar 17 FPS pada bagian lambat di 720p, tanpa GPU OOM dan
dengan VSync mati. Target 30 FPS stabil belum tercapai.**

Dasar: FEXTendo/PES13 approved input-fix + perbaikan DX11, audio, APC,
thread/heap, GPU dan page-store dari F1. FEX ARM64 menerjemahkan kode x86;
Wine-NX menyediakan API Windows; DXVK menerjemahkan D3D11 ke Vulkan/Mesa.
Tidak memakai port Android atau Box64. EXE dan DLL milik game tidak dipatch.

Integrasi FEX untuk Switch adalah port **FEXTendo / AndroSwitch Project /
Ibnuard** yang berasal dari `pes13-fex`, memakai engine upstream FEX-Emu.
Ini bukan integrasi FEX yang diimpor dari Autorun. Dasar Wine-NX dan patch
runtime yang diadaptasi dari Autorun dicatat terpisah dari port FEX tersebut.

Paket uji optimasi shader: **`dist/sleepingdogs-fex-low-window-shader-optimizations.zip`**.
v9 mengadaptasi penjadwalan worker/pipeline shader dan cache alokasi NAK ke
runtime FEXTendo. Keduanya memiliki sakelar untuk perbandingan, dan counter
v8 tetap tersedia. Perbaikan FPS pada perangkat belum diukur.
[Pemasangan, pilihan uji dan rollback v9](low-window-shader-optimizations.md).

Paket diagnosis terbaru: **`dist/sleepingdogs-fex-low-window-perf-counters.zip`**.
v8 menambahkan counter CPU/wait/compiler/I/O tiap sekitar 10 detik pada
Launch biasa untuk membandingkan 720p dan 540p. Ini belum merupakan optimasi
FPS. [Pemasangan dan cara uji v8](low-window-perf-counters.md).

Paket HUD/Performance dan rollback v8:
**`dist/sleepingdogs-fex-low-window-performance-hud.zip`**.
Pilih **Settings → DXVK HUD → None / FPS / Full**. HUD tetap aktif melalui
**Launch** biasa. **Settings → Graphics → Performance** adalah profil
opsional untuk dibandingkan dengan Stable; pilihan pengguna tidak ditimpa.
Ringkasan FPS ringan tersedia dalam log normal. Semua pilihan Graphics Level
`undefined` di menu game masih perlu diagnosis dari `Data/DisplaySettings.xml`
dan tampilan Advanced Options.
[Pemasangan, hasil analisis, dan batas pengujian v7](low-window-performance-hud.md).

Baseline/rollback v7: **`dist/sleepingdogs-fex-low-window-cpu-topology-fix.zip`**.
NRO v6 melaporkan core CPU melalui API topologi legacy dan Ex. Dalam replay
kode HKShip asli, jumlah worker berubah dari 0 menjadi 4 dan tabel indeks
semaphore terisi benar. Profil tetap **Fastest**; cukup timpa folder `switch/`,
tanpa memasang ulang NSP atau reboot pada boot FEXTendo Memory yang aktif.
[Petunjuk pemasangan dan verifikasi](low-window-cpu-topology-fix.md).

Rollback v6: **`dist/sleepingdogs-fex-low-window-sync-startup-fix.zip`**.
NRO v5 memperbaiki observer v4 yang membaca CPU TLS kosong saat startup.
Log perangkat terbaru mengonfirmasi v5 bisa mencapai loading lagi.
[Catatan guard startup](low-window-sync-startup-fix.md).

Cadangan: **`dist/sleepingdogs-fex-low-window-v3-recovery.zip`**, NRO v3 yang
hash-nya sama persis dengan rilis yang sebelumnya mencapai menu, plus Fastest.
Paket diagnosis v4 `sleepingdogs-fex-low-window-sync-watch.zip` disimpan sebagai
baseline reproduksi bug; gunakan v6 untuk pengujian berikutnya.
[Catatan diagnosis semaphore dan perbandingan Fast](low-window-sync-watch.md).

Tes konfigurasi sebelumnya: **`dist/sleepingdogs-fex-low-window-tso-test.zip`**.
Hasil perangkat: TSO aktif tidak menghilangkan freeze. Jika hanya ingin kembali
ke Fastest tanpa NRO diagnosis baru, gunakan **`dist/sleepingdogs-fex-restore-fastest.zip`**.
[Catatan tes TSO](low-window-tso-test.md).

NRO diagnosis: **`dist/sleepingdogs-fex-low-window-loading-watch.zip`**.
Mempertahankan pengamatan Debug setelah frame pertama, dengan progres render
tiap 15 detik dan snapshot thread sekitar tiap 30 detik selama 10 menit.
Log terakhir masih mempunyai sekitar 1009 MiB heap tersedia; Present berhenti
pada frame 3441 dan thread 4/72 berulang menerima `STATUS_INVALID_HANDLE` untuk
`0x6d4ffff0`. Paket ini belum diklaim memperbaiki freeze.
[Petunjuk uji loading](low-window-loading-watch.md).

Perbaikan admission: **`dist/sleepingdogs-fex-low-window-launch-order-fix.zip`**.
Memperbarui NRO agar menyiapkan memori sebelum memeriksa kesiapan Launch Debug /
GUI. Log perangkat telah mengonfirmasi heap sekitar 3,12 GiB; launcher lama
menolak Play karena init-nya baru dijadwalkan setelah validasi itu lolos.
Tes launcher, binary ARM64 dan arena lulus; probe/arena NRO v2 kini juga
dikonfirmasi di Switch dan sudah mencapai menu/loading.
Ikuti [petunjuk Launch Debug](low-window-launch-order-fix.md).

NSP yang diperlukan: **`dist/sleepingdogs-fex-low-window-startup-fix.zip`**.
NSP ini sudah dikonfirmasi membuka launcher dari HOME. Jika sudah terpasang,
update Launch Debug cukup menimpa folder `switch/`, tanpa memasang NSP lagi.
Lihat [petunjuk startup](low-window-startup-fix.md) untuk instalasi awalnya.

Basis low-window: **`dist/sleepingdogs-fex-low-window-fix.zip`**, untuk HOS 22.5.0 /
AMS 1.11.2 / HOC 2.5.1, dengan kernel/loader whitelist Sleeping Dogs dan arena
guest rendah dari backing heap tinggi. **NSP di paket basis wajib diganti
dengan StartupFix di atas.** Profil FEX tetap Fastest. [Petunjuk low-window](low-window-fix.md)
mencakup entry Hekate **More configs** dan rollback ke build 32-bit.

## Baseline 32-bit dan instalasi awal

Patch baseline 32-bit: **`dist/sleepingdogs-fex-buffer-reuse-fix.zip`**. Log SS/09
memastikan dua compiler aktif, tetapi buffer GPU 5 MiB masih gagal setelah
ribuan alokasi dan pelepasan. DXVK sekarang dapat memakai ulang buffer besar
yang seluruh referensinya telah selesai, dengan ukuran dan tipe memori yang
sama. Simpanan dibatasi 16 MiB dan dilepas ketika allocator terdesak.
NRO/FEX tetap versi dua compiler dan profil Fastest tetap aktif. Kecukupan
memori untuk seluruh adegan 3D masih perlu diuji pada Switch.

Tutup aplikasi dari HOME, lalu timpa **seluruh** folder `switch/` dari ZIP
ini ke root SD **paling akhir**. Jika NSP dari patch GPU-budget sebelumnya
sudah aktif, **tidak perlu install ulang NSP**. Untuk instalasi dari basis
lama, install NSP di `forwarder/` ZIP ini sekali. Buka Sleeping Dogs dari HOME,
pilih **DXVK 3.1.1**, lalu **Launch Debug** dan coba New Game.
Cari `[SD-DXVK-RECYCLE] v1` dan kemudian `event=reuse` saat cache digunakan.
**Seluruh set DLL renderer** pada game dan launcher harus diperbarui bersama.
Jika `[SD-GPU-BUDGET]` menunjukkan `paired_loader=0`,
forwarder lama masih aktif atau heap terlalu kecil; pool kembali ke 128 MiB.

Pengujian host/binari dan paket dijalankan; gameplay pada Switch masih perlu
diuji. Jika gagal, kirim `fex-runtime.log` dan `crash.log` terbaru.
Rincian anggaran RAM dan pengujian: `docs/buffer-reuse-fix.md`. Semua perbaikan
sebelumnya disertakan. Rollback renderer tersedia dalam
`dist/sleepingdogs-fex-buffer-reuse-rollback.zip`; NRO/FEX dan NSP tetap sama.

1. Ekstrak `dist/sleepingdogs-fex-0.1.0-sd.zip` ke root SD.
2. Salin **isi** instalasi `Sleeping Dogs/` ke
   `switch/sleepingdogs-fex/drive_c/SleepingDogs/`. Pertahankan DLL DXVK dan
   `dxvk.conf` dari paket. Salin semua BIG/BIX, `Data/`, `HKShip.exe`, DLL dan
   file pendamping game. Arsip launcher tidak menyertakan data game.
3. Install **`FEXTendo-SleepingDogs-32bit.nsp`** yang disertakan, lalu buka
   **Sleeping Dogs - FEXTendo** dari HOME. Forwarder memakai **32-bit no-alias,
   4 core**, target
   `sdmc:/switch/sleepingdogs-fex/sleepingdogs-fex.nro`.
   Jangan gunakan forwarder 39-bit F1 atau Album/applet mode.
4. Pilih **Launch Debug** untuk percobaan awal. Setelah berhasil, gunakan
   **Launch GUI**. XInput gamepad aktif secara default, tanpa emulasi tombol
   keyboard PES. Resolusi yang tersedia: 1280×720 dan 960×540.
5. Jika mencapai menu game, pilih detail rendah dan coba 960×540 terlebih dahulu.
   Pilihan DXVK di launcher mengatur antrean/filtering, bukan kualitas dunia game.
   `UserOptions.dat` adalah format biner milik game dan tidak ditulis ulang.

Folder lokal `dist/sleepingdogs-fex-ready/` sudah menyertakan salinan game dari
workspace. Salin folder `switch/` di dalamnya ke root SD, lalu install NSP di
folder yang sama. ZIP `-sd.zip` hanya berisi launcher/runtime dan forwarder.

Patch sebelumnya: **`dist/sleepingdogs-fex-named-pipe-fix.zip`** menambahkan
named pipe lokal untuk DLL pendamping game setelah log lama menunjukkan
`SteamAPI_Init()` gagal dan `exit(1)`. Hasil uji perangkat berikutnya mencapai
frame pertama. Perbaikan ini sudah termasuk dalam patch terbaru di atas.

Host ASan/UBSan: 13 kelompok tes, 500 siklus koneksi dan 200 pertukaran pesan
antarthread; replay empat skenario pada fungsi pipe DLL asli juga lulus. Build
NRO lulus.
Rincian dan batas dukungan: `docs/named-pipe-fix.md`. Paket runtime/ready tetap
menjadi basis; pasang patch terbaru paling akhir. Rollback NRO tersedia di
`dist/sleepingdogs-fex-named-pipe-rollback.zip`.

Riwayat perbaikan sebelumnya:

Log Switch 7 Oktober sudah membuktikan alokasi arena 1.000 MiB berhasil.
Log diagnostik berikutnya memperlihatkan DR0–DR3 aktif (`DR7=0x155`), tetapi
FEX belum memicu breakpoint eksekusi. Startup game lalu mengosongkan stack
beserta handler SEH, kembali ke `fffffffe`, kemudian berulang ke handler `0`.
Urutan ini berhasil direproduksi pada kode x86 asli di pengujian host.

Patch breakpoint sebelumnya **`dist/sleepingdogs-fex-debug-register-fix.zip`** dipasang setelah
paket runtime/ready di atas: tutup aplikasi dari HOME, timpa folder `switch/`
di root SD, lalu pilih **Launch Debug**. Patch menambahkan dukungan breakpoint
eksekusi per thread di FEX dan mempertahankan Fastest, arena 1.000 MiB, WoW64,
renderer, serta NRO diagnostik. **Tidak perlu install ulang NSP.** Cari
`[SD-DB] execution-breakpoints v1` dan `[SD-DB] hit` di log untuk memastikan
DLL baru terpakai. Jika masih gagal, ambil `fex-runtime.log` dan `crash.log`
terbaru. Boot di Switch masih memerlukan pengujian perangkat.

Paket runtime biasa dan folder ready tetap menjadi basis; timpa patch terbaru
setelah menyalinnya. Build launcher berikutnya otomatis memakai DLL FEX baru.
Paket `dist/sleepingdogs-fex-debug-register-rollback.zip` mengembalikan DLL FEX
sebelumnya jika diperlukan. Rincian bukti dan pengujian ada di
`docs/debug-register-fix.md`. Paket diagnostik lama
`dist/sleepingdogs-fex-first-fault-trace.zip` tetap tersedia untuk pembanding.

Untuk log yang berakhir dengan **`out of address space: 1024000 KB`**, gunakan
**`dist/sleepingdogs-fex-startup-memory-fix.zip`**. Tutup aplikasi dari HOME,
ekstrak folder `switch/` ke root SD dan timpa, lalu buka **Launch Debug**.
Paket kumulatif ini mengganti NRO serta menyertakan perbaikan WoW64 dan renderer.
FEX tetap **Fastest** dan forwarder 32-bit yang sama tetap digunakan; tidak
perlu install ulang NSP. Folder ready dan ZIP runtime juga telah diperbarui.

Game meminta satu blok tetap **1.000 MiB** sebelum membuat perangkat grafis.
Runtime lama mencoba menyediakan alamat kedua untuk backing heap, sedangkan
ruang alamat kosong terbesar pada log terbaru hanya 185 MiB. Runtime baru
mencadangkan blok miliknya dari heap lebih awal dan memberikannya langsung
sebagai satu view data Wine. Cadangan awal GPU menjadi 256 MiB; ini bukan
batas keras alokasi GPU. Jatah RAM proses tidak bertambah. Penanda yang perlu
terlihat: `[SD-DIRECT] init ... reserved=1048576000` dan
`[SD-DIRECT] allocated 1000 MiB RW`.

Pengujian host dengan arena berukuran penuh 1.000 MiB dan ASan/UBSan lolos
15 skenario alokasi, proteksi, decommit/recommit, rollback gagal proteksi,
release dan reuse. Boot serta pemakaian RAM/GPU selanjutnya tetap perlu
diuji di Switch. Arena khusus ini mendukung release penuh dan decommit per
halaman; partial release serta perubahan menjadi executable/WRITECOPY ditolak.
EXE game tetap asli. Jika gagal lagi, kirim `fex-runtime.log` terbaru.

Untuk hang startup lama dengan `NtSuspendThread` dan laporan `NHEAP` berulang,
gunakan **`dist/sleepingdogs-fex-startup-context-fix.zip`**. Tutup aplikasi dari
HOME, ekstrak folder `switch/` ke root SD dan timpa, lalu buka **Launch Debug**.
Patch memperbaiki `wow64.dll`: query `GetThreadContext` pada thread sendiri
langsung membaca konteks guest di batas syscall, sehingga tidak menangguhkan
pemanggil sebelum ia sempat resume. Handle biasa yang menunjuk thread sendiri
juga dikenali; kegagalan suspend thread lain tidak diikuti resume yang salah.
Patch menyertakan perbaikan renderer di bawah. Pilihan FEX Fastest dan profil
tersimpan tetap berlaku. NRO/NSP tidak perlu diganti. Folder ready dan ZIP
runtime sudah diperbarui. Perbaikan telah diuji pada host dan instruksi ARM64
DLL final; hasil boot berikutnya masih perlu diuji pada Switch.

Jika paket awal menampilkan **Invalid renderer config: dxvk.conf**, ekstrak
`dist/sleepingdogs-fex-renderer-config-fix.zip` ke root SD dan timpa 11 file
konfigurasi di `switch/sleepingdogs-fex/launcher/`, lalu buka launcher kembali.
Patch ini menambahkan `d3d9.presentInterval = 1` yang diwajibkan validator
renderer bersama pengaturan DX11 `dxgi.syncInterval = 1`. Pilihan profil,
renderer dan FEX Fastest tetap tersimpan; NRO/NSP tidak perlu diganti.
Folder ready dan ZIP runtime saat ini sudah memuat perbaikan tersebut.

Kirim `switch/sleepingdogs-fex/fex-runtime.log`, `crash.log` bila ada, serta
`drive_c/SleepingDogs/HKShip_d3d11.log` dan `HKShip_dxgi.log` setelah pengujian.
Boot bisa memerlukan kompilasi shader. Versi ini tidak menjanjikan FPS tertentu.

EXE yang diaudit tidak memiliki relocations dan tidak Large Address Aware.
Alamat tetap `0x00400000` harus tersedia; runtime menolak profil 39-bit.
Default: FEX **Fastest**, DXVK 3.1.1 dengan alokasi kecil dari F1, profil Stable,
VRAM terlapor 256 MiB, satu thread compiler shader DXVK. Alternatif DXVK 2.7.1 async
tersedia di Settings. Ini konfigurasi awal untuk pengujian, bukan hasil tuning
yang sudah terukur pada Sleeping Dogs.

## Build lokal

Dependensi workspace: `../pes13-nx/local/production-input-fix/approved/`,
`../pes13-nx/local/production-input-fix/wine-source.tar.gz`, toolchain devkitPro
dan Wine/Mesa di `/home/blekjek/pes13-build` pada WSL Ubuntu.
Helper F1 disalin ke proyek ini; build tidak menulis ke proyek F1/PES13.

```powershell
python tools/build_assets.py
wsl -d Ubuntu --exec python3 /mnt/d/Dev/Switch/SwitchHub/sleepingdogs-fex/tools/build_launcher.py --jobs 4
```

Gunakan `--work /home/blekjek/sleepingdogs-fex-build-v2` untuk input sumber baru.
Receipt mengikat hash sumber dan layout PE sehingga build lama tidak tercampur.
`--prepare-only` menyiapkan sumber, `--build-only` menghasilkan ELF/NRO saja.

Build diagnostik terpisah: `python3 tools/build_fault_trace.py --work
/home/blekjek/sleepingdogs-fault-trace-v1`. Overlay ini hanya menambahkan empat
snapshot exception awal, jejak SEH/WoW terbatas, dan salinan snapshot pertama
di area kosong `crash.log`. Pengujian host:
`python3 tests/check_fault_trace.py --output /home/blekjek/sleepingdogs-fault-check`.
Uji tersebut mencakup pembacaan guard/unmapped, pointer rusak, batas rekaman,
gagal tulis, pelestarian context/errno, dan batas log berulang dengan ASan/UBSan.

```powershell
python tools/verify_package.py --prefix dist/sleepingdogs-fex-ready/switch/sleepingdogs-fex
```

`python tools/stage_game.py` membuat salinan game lokal setelah build, dengan
ukuran file diperiksa dan hash EXE/DLL/config dibandingkan. Output harus baru.
`forwarder/build_forwarder.py` membangun NSP dari sumber Sphaira yang dipin;
memerlukan `--nro` dan `--keys` lokal. Kunci tidak masuk paket atau log build.
`python forwarder/package_sd.py` menggabungkan forwarder, lisensi dan checksum
ke ZIP runtime. Detail target dan capability tersedia di `dist/forwarder/build.json`.

`tests/check_renderer_package.py` menjalankan gerbang peluncuran C dari sumber
build pada file persis dari ZIP, kedua renderer dan seluruh delapan kombinasi
profil. Jalankan di WSL dengan `--source <native-source> --update <runtime.zip>
--output <folder-uji>`. Opsi `--patch <patch.zip>` menguji penimpaan konfigurasi
di paket lama sebelum pemeriksaan yang sama, menggunakan ASan/UBSan.

`tools/wow64_context_fix.py` membangun WoW64 dari arsip Wine dan overlay PE
approved dalam direktori terpisah. Build utama memakai hasil ini otomatis.
`tests/check_wow64_context.py --output <folder-uji>` menguji sembilan skenario
pada C asli dengan ASan/UBSan di WSL; `tests/check_wow64_context_binary.py`
mengeksekusi fungsi ARM64 DLL hasil build dengan batas API NT yang disimulasikan
oleh Unicorn. Keduanya mereproduksi suspend diri dari DLL lama. Receipt menyimpan
hash sumber, compiler, DLL lama/baru, dan pengujian; EXE game tetap asli.

`tools/sleepingdogs_memory.py` memasang arena data langsung pada source native
yang terpisah. `tests/check_direct_arena.py --production-size --output <folder-uji>`
menguji C yang sama dengan backing 1.000 MiB pada Linux. Receipt build baru di
`reports/native-memory-build/` menyimpan hash ELF/NRO, source yang benar-benar
dikompilasi, serta verifikasi rekonstruksi overlay terhadap source build lama.

Audit dependency memeriksa 9.381 impor statis pada DXVK 3.1.1 dan 9.201 pada
DXVK 2.7.1 async, termasuk DLL pendamping instalasi. Delay import opsional
`binkw32.dll -> mss32.dll` dan `mfreadwrite.dll -> mf.dll` tidak tersedia;
jalur yang memerlukannya belum diuji. Pemeriksaan ini membuktikan simbol tersedia,
bukan bahwa seluruh fungsi Wine sudah kompatibel pada hardware.

## Asal kode

FEXTendo dan integrasi FEX/Horizon: AndroSwitch Project / Ibnuard.
Wine-NX/Autorun, FEX-Emu, DXVK, Mesa dan libnx tetap memiliki kredit dan lisensi
aslinya; lihat `LICENSE`, `docs/PES13-THIRD-PARTY.md` dan
`reports/upstream-inputs.json`. Beberapa helper internal tetap bernama `f1_*`
untuk keterlacakan. Path runtime, judul, EXE, registry dan data semuanya khusus
Sleeping Dogs. Migrasi XML F1 dan handler yang bergantung alamat kode F1 dibuang.
Optimisasi eksperimen wake/index dan bootstrap 39-bit F1 tidak diaktifkan.
