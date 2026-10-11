# v9 — optimasi shader untuk FEXTendo

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

Paket uji: `dist/sleepingdogs-fex-low-window-shader-optimizations.zip`.
Ini menerapkan dua optimasi shader pada runtime Sleeping Dogs kita. Kenaikan
FPS dan kestabilan gameplay di Switch belum diukur; target 30 FPS belum
terbukti. Baseline perangkat terakhir tetap sekitar 17 FPS di 720p.

FEX di sini adalah port Switch FEXTendo milik AndroSwitch Project / Ibnuard,
berasal dari `pes13-fex`, menggunakan engine upstream FEX-Emu. Integrasi ini
bukan diambil dari integrasi FEX Autorun. Yang diadaptasi untuk v9 adalah
perbaikan shader pada lapisan Wine/Mesa/native runtime. Adapter FEX, DLL FEX,
DXVK, kebijakan sinkronisasi, dan profil Fastest tetap seperti v8.

## Memasang

1. Tutup game dari HOME. Timpa folder `switch/` dari ZIP ke root SD pada
   instalasi Sleeping Dogs yang sudah berhasil masuk gameplay.
2. Buka launcher dari forwarder yang sama. Tidak perlu NSP baru atau reboot
   selama boot FEXTendo Memory yang sebelumnya berhasil masih aktif.
3. Pilih **Graphics → Performance**, **DXVK HUD → FPS**, lalu **Launch** biasa.
   Pertahankan clock dan pengaturan game yang sama dengan pengukuran sebelumnya.
4. Pastikan log menyebut `low-window-v9-shader-optimizations` dan
   `[SD-SHADER] v1 affinity=1 cache=1`.

Paket hanya memperbarui NRO, metadata launcher, dan sakelar fitur. Game, save,
DLL renderer, setelan pilihan launcher, kernel dan forwarder tidak dibundel.
Menu HUD None/FPS/Full tetap tersedia. Label Graphics Level `undefined`
belum diperbaiki oleh perubahan ini.

## Dua optimasi yang dapat dipisahkan

File ada di `switch/sleepingdogs-fex/`; isinya satu angka `0` atau `1`.
Perubahan berlaku setelah aplikasi ditutup dan diluncurkan lagi.

| `shader-affinity.txt` | `shader-cache.txt` | Mode |
|---|---|---|
| 1 | 1 | Bawaan paket v9: kedua optimasi aktif |
| 1 | 0 | Penjadwalan shader saja |
| 0 | 1 | Cache alokasi shader saja |
| 0 | 0 | Kontrol: kedua optimasi mati |

**Affinity shader:** worker DXVK yang dikenal dan thread saat membuat
pipeline Vulkan boleh berpindah pada core aplikasi 0–2. Priority tidak
diubah. Affinity yang diminta game dan helper core 3 tetap dihormati.
Thread biasa kembali ke affinity sebelumnya setelah kompilasi. Jika kernel
menolak pemulihan, metadata dipertahankan agar balancer tidak menimpanya;
pemulihan dicoba lagi pada siklus balancer atau kesempatan berikutnya.

**Cache alokasi:** alokasi CPU Mesa/Rust dapat dipakai ulang hanya selama
panggilan compiler shader NAK. Ini bukan cache hasil shader dan bukan frame
generation. Batas blok 64 KiB, cache 1 MiB per worker, maksimal delapan worker
yang memakai cache. Sisa blok langsung dilepas saat kompilasi selesai atau
saat allocator gagal dan membutuhkan ruang. Alokasi page-store, GPU, kode
JIT dan pemanggil malloc lain tidak masuk cache. Jalur pemulihan memori
FEXTendo dipertahankan.

Perubahan ini paling langsung menyasar biaya kompilasi dan stutter. FPS
sesudah semua shader selesai dikompilasi bisa saja tetap sama.

## Perbandingan perangkat

Mulai dari 720p dengan detail rata kiri, OLED handheld, clock CPU 1728 /
GPU 768 / RAM 1600 MHz seperti pengujian sebelumnya. Mainkan rute yang sama
sekali untuk pemanasan, kemudian catat sekitar 60 detik gameplay. Salin
`switch/sleepingdogs-fex/fex-runtime.log` menjadi `v9-on-720p.log` sebelum
peluncuran berikutnya.

Untuk kontrol, set kedua sakelar ke `0`, tutup dan jalankan lagi, lalu ulangi
rute/pemanasan/pengukuran yang sama. Simpan sebagai `v9-off-720p.log`.
Gunakan HUD yang sama dan pertahankan cache disk. Bila ingin memisahkan
pengaruh kedua fitur, gunakan dua mode lainnya dalam tabel. Perbandingan
960×540 tetap berguna jika FPS 720p masih rendah.

Counter v8 tetap tersedia melalui `performance-counters.txt=1`:

- `[SD-FRAME]` untuk ringkasan FPS.
- `[SD-PERF]`, `[THREADS]`, laporan driver/compiler/I/O untuk diagnosis.
- `[SD-SHADER-CACHE]` untuk jumlah scope kompilasi selesai, cache hit/miss,
  blok yang disimpan, serta puncak byte cache per worker. Angka kumulatif ini
  baru bertambah saat scope kompilasi selesai, bukan pengukuran beban GPU.
- Baris penamaan worker `[FEX3-DXVKCORE]` kini menyertakan `shader_mode`:
  0 biasa, 1 worker migratable, 2 scope pipeline, 3 menunggu pemulihan.

Lewati baseline startup dan baris `[SERVER]` pertama seperti pada v8.
Untuk mengukur biaya logging, `performance-counters.txt=0` mematikan laporan
interval tambahan; gunakan nilai yang sama di kedua sisi perbandingan.

Rollback penuh: timpa NRO/folder `switch/` dari
`dist/sleepingdogs-fex-low-window-perf-counters.zip` (v8). File sakelar shader
tidak dibaca oleh NRO v8, sehingga tidak perlu dihapus.

## Provenance dan validasi

Adaptasi menggunakan commit Autorun/Wine-NX:

- [5a75cfb647a0](https://github.com/autorunhq/autorun/commit/5a75cfb647a010704a2811f535323fc4b39c9109): migrasi worker shader.
- [e823a778f5cc](https://github.com/autorunhq/autorun/commit/e823a778f5ccf40ae8392209b9ff769b42780c14): scope kompilasi pipeline Vulkan.
- [e7168c3f438a](https://github.com/autorunhq/autorun/commit/e7168c3f438ace433c4e77da2cb4533762a77399): cache alokasi sementara.

Source adaptasi diberi atribusi LGPL-2.1-or-later; helper allocator FEXTendo
mempertahankan lisensi MIT. Engine FEX-Emu dan port Switch FEXTendo tetap
memiliki provenance masing-masing.

Build memverifikasi seluruh manifest v8 dan menyimpan source sebelum patch.
Tes host ASan/UBSan mencakup scope/nesting, rename worker, explicit affinity,
helper core 3, kegagalan dan retry pemulihan, batas cache, alignment, zeroing,
realloc gagal, lifetime objek, memory pressure, page fallback, dan konkurensi.
ABI NAK serta jalur Rust malloc/free diperiksa pada library yang dipin.
Pemeriksaan ELF memverifikasi hook Vulkan dan allocator serta mengeksekusi
wrapper ARM64. Replay topologi CPU HKShip, guard startup, dan low-window
tetap dijalankan. Semua laporan disertakan dalam ZIP; ini belum menggantikan
pengujian gameplay pada perangkat.
