# Sleeping Dogs FEXTendo v18: notifikasi APC ke thread tujuan

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

v18 mempertahankan scheduler v17 dan membatasi notifikasi APC biasa pada antrean
wait langsung ke thread penerimanya. Ini kandidat optimasi CPU; peningkatan FPS
hardware belum diukur dan target 30 FPS belum terbukti.

Log tes IMMEDIATE terbaru berhash
`31ac6f92b1bd4bdcb043adf6163ae32f9497e811ff68a44bfa7517189ed47e45`.
Pengguna melaporkan sekitar 20–23 FPS tanpa kenaikan tambahan. Capture 30 detik
mencatat sekitar 19,93 FPS. Mode IMMEDIATE terkonfirmasi aktif, sehingga tidak
ada dasar untuk mengklaim VSync sebagai penyebab pembatas yang tersisa.

## Perubahan

Sebelumnya, setiap APC pengguna yang berhasil dimasukkan ke antrean sebuah thread
mengirim notifikasi ke seluruh waiter yang belum dinotifikasi pada antrean
langsung. Padahal enqueue tersebut hanya mengubah antrean APC milik thread
penerima. Thread lain cukup dibangunkan jika
objek yang mereka tunggu kemudian berubah, misalnya ketika callback APC memberi
signal pada event.

Dengan `sync-mode = 2`, v18 membangunkan waiter langsung milik thread penerima.
Broadcast shared dan router legacy tetap dipanggil. Notifier tidak menjalankan
callback, mengambil signal objek, mengubah hasil wait, atau mengganti deadline.
Request tidak valid, jenis APC yang tidak didukung dan target terminated tetap
mengikuti penanganan sebelumnya.

Daftar waiter diperiksa dengan mutex objek yang sama seperti sebelumnya.
Connection dan referensi thread waiter tetap hidup sampai waiter dilepas dari
antrean. Mode 0/1 atau flag OFF menggunakan notifier broad v17.

FEX, DXVK, Mesa, LSFG, affinity v17 dan clock tidak diubah. Paket tidak menimpa
preset konfigurasi, termasuk IMMEDIATE yang sedang dipakai pengguna.

## Instalasi dan perbandingan

1. Tutup FEXTendo sepenuhnya melalui HOME.
2. Ekstrak `sleepingdogs-fex-v18-apc-update.zip`, lalu salin folder `switch` ke
   root SD dan timpa file yang disertakan.
3. Pertahankan **DXVK 3.1.1**, **Stable**, **Launch GUI**, **LSFG OFF**,
   **1280×720**, CPU **1728**, GPU **768**, dan RAM **1600 MHz**.
4. Pertahankan preset IMMEDIATE dari tes terakhir untuk perbandingan satu
   perubahan. Jangan memasang ZIP restore FIFO bersamaan dengan tes v18.
   Gunakan HUD dan pengaturan game yang sama, lakukan pemanasan area, kemudian
   bandingkan posisi, arah kamera dan rute yang sama.
5. Simpan `fex-runtime.log` sebelum menjalankan sesi lain.

Marker yang harus muncul:

```text
[BUILD] sleepingdogs-fextendo-0.1.0-v18-apc
[SD-APC-V18] enabled=1 active=1
[SD-SCHED-V17] mode=auto
dxgi.syncInterval = 0
Present mode: VK_PRESENT_MODE_IMMEDIATE_KHR
```

Untuk A/B pada NRO yang sama, buat
`switch/sleepingdogs-fex/apc-targeted-wake.txt` berisi `0` diikuti newline.
Tutup dari HOME dan jalankan ulang; marker menjadi `enabled=0 active=0` dan
rute notifikasi kembali seperti v17. Hapus file atau isi `1` lalu restart penuh
untuk mengaktifkan lagi. Biarkan `auto-affinity.txt` sesuai konfigurasi v17 yang
sudah bekerja.

`sleepingdogs-fex-v18-rollback-v17.zip` memulihkan byte NRO v17 yang sudah dikirim
beserta metadata terkait. v17 mengabaikan flag APC baru. Preset IMMEDIATE/FIFO,
preferensi, save dan data game tetap milik instalasi pengguna.

## Membaca hasil

`accepted_notices` menghitung APC yang berhasil diantrekan. `target_candidates`
dan `unrelated_candidates_skipped` menghitung waiter yang diperiksa, sedangkan
`target_signals` menghitung pemanggilan signal untuk target yang belum mendapat
notifikasi. Kandidat yang dilewati bukan otomatis jumlah wake yang dihemat,
bukan milidetik CPU, dan bukan kenaikan FPS.

Proporsi wake broad yang berasal dari APC serta dampak ke FPS baru dapat dinilai
dari log hardware v18. Capture fence sebelumnya mencakup waktu tunggu penyelesaian
GPU dan penjadwalan; v18 tidak menghapus fence GPU atau mengklaim seluruh wait
tersebut dapat dihilangkan.

## Pemeriksaan sebelum paket dibuat

Packager mensyaratkan laporan host, eksekusi ARM64 notifier dan regresi native
berstatus PASS untuk sumber serta ELF kandidat yang sama. Payload NRO harus
cocok dengan ELF. Build mereproduksi ELF v17 persis sebelum mengganti dua unit
native, dan memeriksa ulang hash input serta sumber.

Paket memuat source, patch, resep build, fixture/test, layout ABI dan laporan
pemeriksaan. ZIP diverifikasi dengan CRC dan SHA256SUMS. Seluruh dependensi
runtime sebelumnya dipertahankan byte-identik; hanya NRO dan metadata terkait
berubah. Rollback memulihkan seluruh file v17 yang diganti. Hasil paket tercatat
di `reports/apc-v18-package.json`.
