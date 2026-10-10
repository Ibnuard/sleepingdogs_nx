# Sleeping Dogs FEXTendo v10 — direct synchronization, 720p

Paket ini melanjutkan v9 dan mempertahankan 1280×720. Ekstrak isi ZIP ke
root SD, lalu timpa file update. Jalankan melalui jalur forwarder/title yang
sudah berhasil pada v9, pilih profil Performance dan Launch GUI. HUD DXVK
Off/FPS/Full tetap tersedia. Clock pengujian tetap CPU 1728 / GPU 768 /
RAM 1600 MHz, OLED handheld. Paket tidak mengubah resolusi, clock, save,
HKShip.exe, DLL game, FEX adapter, DXVK, atau kernel.

## Perubahan

Operasi event, mutex, semaphore dan select yang memenuhi syarat sekarang
bisa memakai handler Wine yang ada langsung pada thread pemanggil. Ini
menghindari perjalanan request melalui pipe dan thread server terpisah.
Wait pada event/mutex/semaphore/thread dapat masuk antrean per objek,
sehingga signal membangunkan waiter yang relevan. Timer dan message queue
tetap memakai cadence polling lama. Pemeriksaan berkala 20 ms tetap ada.

Handler startup, user APC dan suspend lokal dipertahankan. Setiap objek
yang masuk antrean memiliki reference tambahan sampai wait selesai. Hasil
wait yang berhasil dikonsumsi disimpan sebelum waiter dibangunkan, supaya
reset event sesudahnya tidak menghilangkan signal tersebut.

Counter server tidak membaca clock setiap request ketika seluruh mode
profiling/counter/debug dimatikan. Saat counter aktif, pencatatan request
tetap tersedia dan aman untuk pemanggilan dari beberapa thread.

## Memilih mode dan pemulihan

Ubah `switch/sleepingdogs-fex/sync-mode.txt`, lalu tutup dan luncurkan ulang:

| Isi | Perilaku |
|---|---|
| `2` | Bawaan update: langsung + antrean/wakeup per objek |
| `1` | Langsung, dengan mekanisme wait lama |
| `0` | Jalur pipe/server seperti v9 |

File hilang atau tidak valid memakai mode 0. Jika mode 2 mengalami hang
atau regresi, mode 1 memisahkan pengaruh antrean dari direct dispatch;
mode 0 menyediakan kontrol di dalam NRO yang sama. Rollback penuh cukup
timpa NRO dari `sleepingdogs-fex-low-window-shader-optimizations.zip` (v9).
NRO v9 mengabaikan `sync-mode.txt`.

Pertahankan `shader-affinity.txt`, `shader-cache.txt`, HUD, cache disk,
detail grafik, resolusi 720p dan clock yang sama saat membandingkan.
Mainkan rute yang sama sekali untuk pemanasan, kemudian ulangi sekitar
60 detik, termasuk perpindahan area yang sebelumnya turun ke 15 FPS.
Simpan `fex-runtime.log` sebelum peluncuran berikutnya.

Dengan `performance-counters.txt=1`, log menampilkan `[SD-SYNC-MODE]`
dan ringkasan kumulatif `[SD-DIRECT-SYNC]`: request langsung/pipe, jumlah
select langsung, queued waits, wakeup terarah/umum, completion dan jumlah
waiter aktif/puncak. Selisih counter antar laporan dipakai untuk analisis.
`[SD-FRAME]` tetap mengukur frame yang dipresentasikan. Waktu tunggu select
mencakup blocking yang memang diperlukan dan bukan estimasi FPS yang hilang.

## Batas hasil

Log GUI sebelumnya menunjukkan sekitar 18,55 FPS pada segmen lambat,
dengan sekitar 8.300 request server per detik. Ini alasan menargetkan biaya
sinkronisasi. Tes host dan executable ARM64 tidak menggantikan tes gameplay
pada Switch; kenaikan FPS dan target 30 FPS belum terukur. Label Graphics
Level `undefined` tidak diperbaiki oleh update sinkronisasi ini.

## Asal kode

Port Switch FEXTendo tetap milik AndroSwitch Project / Ibnuard, berasal dari
pes13-fex proyek ini, memakai engine FEX-Emu. Update ini mengadaptasi bagian
sinkronisasi Wine dari Autorun ke handler FEXTendo yang sudah ada:

- https://github.com/autorunhq/autorun/commit/17a558619724270c98b52b921a731f143bed7086
- https://github.com/autorunhq/autorun/commit/0625c79c9dbb7bc71fa6cf9a244cb6332a377eed

Kode adaptasi mempertahankan lisensi LGPL-2.1-or-later. Manifest v9, source
yang diubah, source pengujian, receipt build dan laporan validasi ada dalam
direktori `source/low-window-direct-sync/` pada ZIP. Source native sebelum
perubahan disimpan dalam workspace build khusus Sleeping Dogs.
