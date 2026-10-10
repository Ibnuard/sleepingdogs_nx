# v8 — diagnosis FPS pada Launch biasa

Log v7 terbaru mengonfirmasi Performance aktif, DXVK 3.1.1, Fastest,
HUD FPS, serta VSync mati sampai present mode native `IMMEDIATE`.
Sebelas jendela lambat terakhir mencatat 1.885 frame dalam 110,56 detik:
**17,05 FPS**, dengan rentang 15,68–20,38 FPS per jendela. Tidak ada penanda
adegan dalam log; angka ini bukan benchmark terkontrol atau perbandingan
langsung dengan v6. Pengguna mengonfirmasi setelan detail rata kiri, OLED
handheld, CPU 1728 / GPU 768 / RAM 1600 MHz; 960×540 belum dicoba.

Resolusi yang tercatat masih 1280×720; swapchain akhirnya 1292×732 dan
diskalakan ke layar 1280×720. Ini dicatat sebagai temuan, belum dibuktikan
sebagai penyebab FPS rendah. `Present` rata-rata 1,47 ms dibanding sekitar
58,65 ms per frame. Sebagian besar waktu berada sebelum Present; GPU tetap
bisa menahan pekerjaan di fence/semaphore atau panggilan lain.

Heap tersedia sedikitnya sekitar 909 MiB dan tidak ada GPU OOM. Dalam
90,179 detik bagian akhir, waktu agregat `dispatch_compile` FEX bertambah
1,475 detik; kompilasi ulang kode saja belum menjelaskan FPS rendah yang
terus berlangsung. Counter kompilasi ini tidak mengukur biaya menjalankan
kode terjemahan FEX, dan tidak sama dengan kompilasi shader DXVK/Mesa.

## Memasang dan menguji

Paket: `dist/sleepingdogs-fex-low-window-perf-counters.zip`.

1. Tutup game dari HOME, lalu timpa folder `switch/` dari paket ke root SD.
   Gunakan instalasi v7 yang sudah berhasil masuk gameplay. Tidak perlu
   memasang NSP atau reboot jika boot FEXTendo Memory yang sama masih aktif.
2. Pilih **DXVK 3.1.1**, **Graphics → Performance**, **DXVK HUD → FPS**,
   lalu **Launch** biasa. Jangan memakai Launch Debug untuk tes performa ini.
3. Pada 1280×720, tunggu loading selesai lalu mainkan area yang sama selama
   sekitar satu menit. Simpan salinan `switch/sleepingdogs-fex/fex-runtime.log`
   sebagai `720p.log` sebelum peluncuran berikutnya.
4. Ubah **Resolution** di menu game menjadi **960×540**, terapkan, lalu
   bandingkan area/rute yang sama selama sekitar satu menit, dengan detail,
   clock dan HUD tetap sama. Simpan lognya sebagai `540p.log`.
5. Kirim kedua log dan catatan FPS. Jika game tidak menawarkan atau tidak
   menyimpan 960×540, laporkan itu; log dapat memverifikasi resolusi aktual.

540p memuat 43,75% lebih sedikit piksel dari 720p. Kenaikan FPS yang besar
akan mendukung dugaan beban GPU/resolusi; perubahan kecil mengarahkan
penyelidikan ke CPU/runtime atau biaya render lain yang tidak turun bersama
resolusi. Hubungan tersebut adalah petunjuk untuk diuji, bukan bukti tunggal.

Untuk inspeksi tambahan, **HUD Full** menampilkan statistik worker,
kompilasi dan perkiraan beban GPU. DXVK menyatakan perkiraan `gpuload`
bisa tidak akurat; jangan menyimpulkan bottleneck dari satu angkanya saja.
[Dokumentasi HUD DXVK](https://github.com/doitsujin/dxvk#hud).
Gunakan mode HUD yang sama pada kedua pengukuran utama.

## Apa yang berubah

Ini **paket diagnosis**, belum merupakan optimasi yang terbukti menaikkan
FPS. v8 membaca counter yang sudah ada sekali per sekitar 10 detik pada
thread monitor. Laporan mencakup CPU per thread terdaftar, waktu round trip
server, acquire/submit/fence/semaphore, pembuatan pipeline, cache driver,
sleep/yield, serta I/O SD. Tidak menambah sampling atau penghentian thread
game, atau pekerjaan baru di jalur Present. Pengaturan profiler yang sudah
ada tetap milik pengguna; paket tidak mengaktifkan `profile.txt`.

Paket mengaktifkan `performance-counters.txt` dengan isi `1`. Isi `0` untuk
menonaktifkan laporan tambahan, atau timpa NRO dengan paket v7 untuk rollback:
`dist/sleepingdogs-fex-low-window-performance-hud.zip`.

`[SD-PERF] phase=baseline` berisi baseline awal: laporan helper pada blok itu
bisa mencakup startup. Analisis interval dimulai dari `phase=sample`, dengan
satu pengecualian: abaikan **baris `[SERVER]` pertama**, yang masih mencakup
startup karena laporan thread pertama hanya menyiapkan baseline CPU.
Baris `[SERVER]` selanjutnya memakai delta antar-laporan.
`[THREADS]` hanya mencakup thread yang terdaftar, bukan seluruh penggunaan
CPU perangkat. Waktu panggilan driver/server bisa mencakup blocking dan
penjadwalan serta tumpang tindih antar-thread; nilainya bukan waktu eksekusi
GPU dan tidak boleh langsung dijumlahkan menjadi anggaran satu frame.
`observer_us` mencatat biaya laporan termasuk I/O, kecuali baris terakhir.
Pada Launch Debug, laporan v8 dilewati agar baseline laporan Debug tidak
dibaca oleh dua konsumen.

FEX, DXVK, kebijakan core/priority, clock, konfigurasi Performance, file game,
save, dan pengaturan video tidak diubah oleh paket ini. HUD None/FPS/Full
v7 tetap tersedia. `Graphics Level = undefined` belum diperbaiki; isi
`switch/sleepingdogs-fex/drive_c/SleepingDogs/Data/DisplaySettings.xml` dan
tampilan Advanced Options masih diperlukan untuk memastikan preset aktual.

## Validasi

Input dipertahankan di `local/performance-v7/fex-runtime.log`, SHA256
`584eba0f214fef36e277c27bc3fca0aa4bc13f04c9bde9760d25d7be02e07861`.
Laporan analisis: `reports/gameplay-v7-performance-analysis.json`.

Build memverifikasi manifest seluruh sumber dan adapter terhadap v7 serta
mencadangkan sumber yang berubah. Tes host memakai AddressSanitizer dan
UndefinedBehaviorSanitizer untuk cadence, delta counter, unsigned overflow,
baseline awal, jam mundur, biaya observer, serta skip saat off/Debug.
Tes ARM64/guest untuk topologi CPU, guard startup dan arena low-window
dijalankan terhadap ELF v8. Hash dan isi ZIP diverifikasi sebelum diserahkan.
Performa dan kompatibilitas v8 di perangkat tetap harus diuji; **30 FPS
stabil belum dapat dijanjikan**.
