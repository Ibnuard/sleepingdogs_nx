# Sleeping Dogs FEXTendo v11 — pengukuran frame 720p

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

Update diagnostik ini memakai perilaku gameplay v10. Tujuannya memisahkan
waktu tunggu thread utama, request Wine, dan Vulkan setelah log v10 masih
mencatat sekitar 18,81 FPS pada segmen gameplay yang lambat. Ini belum
merupakan peningkatan FPS yang terbukti atau jaminan 30 FPS.

## Memasang dan menguji

Ekstrak isi ZIP ke root SD dan timpa file update. Jalankan melalui
forwarder/title yang sebelumnya berhasil, pilih Performance, Launch GUI,
720p, dan HUD FPS. Menu HUD Off/FPS/Full tetap tersedia.

Gunakan satu set clock yang sama sepanjang sesi agar perubahan clock
tidak tercampur dengan perubahan adegan. Untuk membandingkan dengan
pengujian awal, gunakan setelan pengguna sebelumnya: CPU 1728 / GPU 768 /
RAM 1600 MHz pada OLED handheld. Paket tidak mengatur clock perangkat.

Masuk gameplay, mainkan rute yang biasa turun ke 15–20 FPS sekitar dua
menit. Simpan `switch/sleepingdogs-fex/fex-runtime.log` sebelum peluncuran
berikutnya. File log menyebut `[SD-DIAG] phase=start` saat perekaman dimulai
dan `phase=complete` setelah 30 detik. Pemicu memakai dua jendela pengamatan
berturut-turut dengan 3–25 FPS; itu heuristik beban, bukan deteksi adegan.
Jika gameplay lebih singkat atau FPS di luar rentang, perekaman mungkin
belum dimulai. Log normal tetap tersedia.

## Apa yang diukur

`[SD-DIAG-MAP]` menghubungkan handle native dengan thread Wine/server.
`[SD-DIAG-WAIT]` memisahkan select/event/request Wine lain dan
acquire/submit/fence/semaphore Vulkan per thread. Data berisi jumlah,
total/rata-rata/puncak waktu, timeout/error, serta jalur direct/pipe.
`[SD-DIAG-FRAME]` mencatat interval antar-Present dan CPU ticks thread
presentasi, termasuk jumlah interval di atas 33,33 / 50 / 100 ms.

Perekaman pasif ini tidak menjeda thread atau mengambil stack sampel.
Pencatatan memakai timestamp yang telah dikumpulkan sebelumnya; hanya
selama jendela perekaman ada satu query CPU tick tambahan per Present.
Penyimpanan tetap dibatasi 128 lifetime thread dan log ditulis dari monitor
setiap sekitar 10 detik. Tidak ada alokasi, mutex, atau file I/O tambahan
di callback pencatat pada jalur rendering/request.

Counter bersifat kumulatif selama satu capture. Snapshot saat thread masih
menulis bersifat mendekati; panggilan yang melintasi batas waktu capture
tidak dihitung. Waktu antar-thread bisa tumpang tindih. Waktu tunggu Vulkan
bukan waktu eksekusi GPU, dan CPU tick thread presentasi bukan utilisasi
seluruh CPU/GPU. Log tidak mengukur clock aktual atau suhu perangkat.

## Mematikan dan memulihkan

`frame-diagnostics.txt=1` disertakan. Ubah menjadi `0`, lalu luncurkan ulang
untuk mematikan capture. File yang hilang atau nilai selain `1` juga
mematikannya. Dalam satu sesi capture berhenti otomatis setelah 30 detik
dan tidak mengulang. Counter normal v10 tetap mengikuti
`performance-counters.txt`.

Rollback penuh: timpa NRO dari
`sleepingdogs-fex-low-window-direct-sync.zip` (v10). NRO v10 mengabaikan file
diagnostik baru. ZIP v10, log pengujian pengguna, dan simbol v10 dipertahankan.

## Cakupan dan validasi

Resolusi/preset, FEXTendo adapter, guest DLL, DXVK, shader cache, sinkronisasi
v10, CPU affinity, save, dan game EXE tetap memakai input v10. Label Graphics
Level `undefined` tidak diubah oleh diagnostik ini.

Collector dan handler client yang benar-benar dipakai diuji dengan
AddressSanitizer/UndefinedBehaviorSanitizer, termasuk pencatatan konkuren,
batas penyimpanan, validasi CPU ticks, dan penghentian capture. Pemeriksaan
ARM64 memvalidasi callback terhubung serta guard diagnostik, direct sync,
startup, CPU topology, low VA, dan binding shader. Tes ini tidak menggantikan
pengujian gameplay pada Switch.

Port Switch FEXTendo tetap milik AndroSwitch Project / Ibnuard dari
pes13-fex proyek ini, memakai engine FEX-Emu. Adaptasi sinkronisasi Wine pada
v10 dipertahankan. Source diagnostik berlisensi LGPL-2.1-or-later; source
yang berubah, receipt, dan laporan pengujian disertakan pada
`source/low-window-frame-diagnostics/`.
