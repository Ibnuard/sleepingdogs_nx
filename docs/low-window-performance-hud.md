# Sleeping Dogs v7 — DXVK HUD dan pilihan Performance

Update untuk instalasi v6 low-window yang sudah mencapai gameplay.
Paket: `sleepingdogs-fex-low-window-performance-hud.zip`.

## Pasang dan gunakan

1. Tutup game sepenuhnya dari HOME.
2. Timpa folder `switch/` dari ZIP ke root SD.
3. Buka **Settings → DXVK HUD**, pilih **None**, **FPS**, atau **Full**, lalu A.
4. Untuk tes performa, pilih **Launch** biasa. HUD tetap bekerja tanpa Launch Debug.
5. Bandingkan **Settings → Graphics → Stable** dengan **Performance** di adegan yang sama.

Tidak perlu mengganti forwarder, memasang NSP ulang, atau reboot bila boot
FEXTendo Memory yang sebelumnya dipakai masih aktif. File pilihan HUD/profil
disimpan oleh launcher. Paket tidak menetapkan ulang pilihan renderer, FEX,
HUD, atau profil yang sudah tersimpan.

**Performance** meminta interval VSync 0, antrean sampai 3 frame, dan filtering
ringan. Nilai anggaran memori, descriptor, serta satu compiler worker tetap
sama seperti Stable. Ini eksperimen yang bisa dipilih kembali ke Stable;
belum ada pengukuran peningkatan FPS di Switch. Jalur present native masih
dapat memakai FIFO, jadi interval DXGI 0 bukan bukti bahwa semua penantian
VSync di driver hilang. Antrean lebih panjang juga dapat menambah input lag.

HUD mengikuti opsi resmi DXVK: `fps` untuk angka FPS dan `full` untuk semua
elemen yang didukung, termasuk grafik frame time serta perkiraan GPU load.
Gunakan FPS untuk perbandingan rutin, dan Full untuk melihat detail hambatan.
Referensi: https://github.com/doitsujin/dxvk/blob/master/README.md#hud

## Perubahan normal launch

v6 mengaktifkan pengamatan syscall dan snapshot thread pada kedua tombol
Launch. v7 membatasi pengamatan rinci tersebut ke **Launch Debug**. Jalur
normal tetap menyimpan informasi startup, error/crash, dan ringkasan
`[SD-FRAME]` setiap sekitar 10 detik. Ringkasan hanya membaca penghitung yang
sudah ada; tidak menghentikan thread game. `present_avg_us`, `lock_avg_us`,
dan `driver_avg_us` mencakup waktu menunggu, bukan waktu GPU murni.

Perbaikan topologi CPU v6 dan guard startup tetap ada. FEX, DLL DXVK, game,
kernel, forwarder, save, `UserOptions.dat`, dan `Data/DisplaySettings.xml`
tidak dimodifikasi oleh update ini.

## Temuan dari log v6

Pengguna mengonfirmasi gameplay pada OLED handheld, CPU 1728 MHz, GPU 768 MHz,
RAM 1600 MHz. Log memakai Launch Debug, Fastest, DXVK 3.1.1, dan mode 720p.
Frame terus bertambah sampai 7354; bug antrean lama tidak berulang.

Interval 15 detik setelah detik 95 berkisar 8,6–19,4 present/detik. Rekaman
berisi adegan/menu yang tidak ditandai, sehingga ini bukan benchmark gameplay
terkontrol. Native heap tersedia paling sedikit sekitar 869,5 MiB dan tidak
ada OOM GPU tercatat. Pada sekitar 105 detik terakhir, akumulasi dispatch JIT
hanya bertambah sekitar 0,86 detik; itu tidak mendukung JIT sebagai satu-satunya
penyebab FPS rendah yang terus-menerus.

Driver submit dan semaphore wait memakan waktu yang berarti. Penghitung itu
meliputi penjadwalan dan penantian lintas thread; belum cukup untuk membedakan
GPU yang sibuk, serialisasi driver, dan keterbatasan CPU. Log memuat 6944 baris
Wine, 1732 snapshot PC, 1732 stack, serta 1224 ringkasan syscall. Dampak beban
diagnostik harus dibandingkan pada adegan yang sama.

Target **30 FPS stabil belum terverifikasi**. Setelah membandingkan normal
Launch/Stable/Performance pada clock yang sama, tes resolusi 960×540 dan opsi
grafis dalam game yang paling ringan. 540p memuat 43,75% lebih sedikit piksel
daripada 720p, tetapi FPS tidak harus naik dengan rasio yang sama.

## Graphics Level `undefined`

Pengguna mengonfirmasi semua pilihan kiri/kanan tetap `undefined`. Penyebab
label preset ini belum ditemukan dan tidak diperbaiki oleh update HUD.
Log v6 membuktikan pembacaan `Data/DisplaySettings.xml` berhasil (888 byte),
tetapi tidak merekam nilai kualitas di dalamnya. Karena itu, `undefined`
tidak digunakan sebagai bukti bahwa kualitas Low atau High sedang aktif.

Untuk melanjutkan diagnosis, diperlukan file dari instalasi SD yang dipakai:
`switch/sleepingdogs-fex/drive_c/SleepingDogs/Data/DisplaySettings.xml`, serta
tampilan **Advanced Options**. Jangan menggantinya dengan file dari PC atau
menghapusnya sebelum salinan konfigurasi yang bermasalah disimpan.

## Validasi

- C launcher dengan ASan/UBSan: kedua renderer × lima profil × tiga HUD;
  penyimpanan, format rusak, pemulihan rename, navigasi, batas render.
- Ringkasan frame: interval, penghitungan FPS/durasi, dan kondisi nol frame.
- ELF ARM64 v7: topologi CPU, kode antrean HKShip asli, guard startup, low-window.
- Isi ZIP, NRO, ELF, sumber, profil, dan laporan diikat dengan SHA-256.

Tes host/Unicorn memodelkan layanan platform; bukan pengujian gameplay Switch.
Rollback: pilih Stable sebelum kembali memakai paket v6 CPU Topology Fix.

