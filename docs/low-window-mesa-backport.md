# Sleeping Dogs FEXTendo v13 — kesempatan uji 1 dari 2

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

Target tetap **1280×720, 30 FPS gameplay**. Paket ini mengubah driver NVK
dan pilihan memori GPU. Hasil FPS pada Switch belum diukur; keberhasilan
kompilasi dan pengujian host tidak menjamin 30 FPS.

## Memasang dan menguji

1. Tutup game/FEXTendo sepenuhnya dari HOME.
2. Ekstrak seluruh folder `switch` dari
   `sleepingdogs-fex-low-window-mesa-backport.zip` ke root SD, lalu timpa.
3. Pilih **DXVK 3.1.1 → Performance → Launch GUI**, resolusi **1280×720**.
   Pilihan HUD Off/FPS/Full tetap tersedia. Forwarder tidak perlu dipasang ulang.
4. Pertahankan CPU **1728**, GPU **768**, RAM **1600 MHz** selama tes pembanding.
   Paket ini tidak mengatur clock.
5. Jalankan rute yang sama selama 2–3 menit, termasuk area tempat FPS biasanya
   turun. Catat FPS setelah loading dan simpan `fex-runtime.log` sebelum
   menjalankan sesi berikutnya. Catat juga jika muncul objek berkedip,
   kedalaman/shadow salah, atau hang.

Paket adalah update untuk instalasi yang sudah berhasil menjalankan v12;
file game dan save tidak disertakan atau diubah. NRO memakai kode runtime
v11 yang sama, sehingga banner runtime masih menyebut v11. Identitas driver
baru pada informasi adapter adalah **`26.2.2-sdv13-zcull-ubo`**.
DXVK tetap **`3.1.1-sdbatch1`**, dengan batching aktif pada Performance.
Penanda `[SD-NVK-V13] private_gpu_type=0` mengonfirmasi tipe memori baru.
Penanda `ZCULL active mode=persistent` atau `transient` dicatat sekali ketika
driver merekam perintah dengan mode tersebut; ini belum mengukur waktu GPU
atau membuktikan kenaikan FPS.

Untuk membatalkan, tutup aplikasi lalu ekstrak
`sleepingdogs-fex-low-window-mesa-backport-rollback.zip` ke root SD dan timpa.
Ini mengembalikan NRO dan receipt v12. DXVK tetap versi batching yang telah
dipakai pada tes terakhir.

## Mengapa perubahan ini dipilih

Log terbaru SHA-256
`e9589ec56f84dfb89574553168c21f5d69e1ea7f5b74233c4d921f7145927ebc`
memuat capture 30 detik sepenuhnya pada 720p: **17,14 FPS**, dibandingkan
15,47 FPS pada capture sebelumnya. Waktu dinding di pemanggilan submit
Vulkan turun dari 6,421 menjadi 0,794 detik dalam masing-masing capture.
Kedua sesi tidak memakai adegan/kamera yang terkontrol, sehingga angka itu
bukan persentase peningkatan yang dapat diatribusikan pasti ke batching.
Tujuh jendela terakhir pada log baru masih hanya rata-rata **13,91 FPS**.

Audit source menemukan bahwa ZCULL belum aktif pada jalur Switch driver
lama. ZCULL menggunakan informasi kedalaman untuk mengurangi pekerjaan
render yang tertutup objek lain. Ada perbaikan upstream untuk mengaktifkannya,
tetapi pemetaan memori WoW64 proyek ini mengimpor seluruh alokasi Vulkan
yang bertipe host-visible. Pengaman ZCULL memang menolak memori impor.
Memasang patch upstream saja tidak menyelesaikan hambatan tersebut.

Build ini menambahkan tipe **DEVICE_LOCAL saja** pada perangkat Switch SoC,
di heap RAM yang sama. DXVK dapat memilihnya untuk gambar GPU yang tidak
memerlukan akses CPU. Tipe host-visible cached dan coherent tetap tersedia
untuk staging, dynamic buffer, serta resource yang perlu dipetakan oleh game.
Jalur impor memori dan pengaman ZCULL untuk memori eksternal tetap dipertahankan.
Ini tidak menambah kapasitas RAM atau membuat VRAM fisik baru.

## Source yang diterapkan

Dasar tetap Mesa **26.2.2 / `b297e230ef88c6c88df2561becf864f979f494a6`**.
Empat perubahan berikut diambil dari upstream; ini bukan upgrade penuh 26.2.4:

- [ZCULL persistent dan transient dengan pengaman Horizon](https://github.com/danfromtico/mesa-switch/commit/ed2b4dd00d06a60b233a6fb3b1397689eb4e80a3).
- [Menghindari pembaruan dynamic UBO yang berulang](https://github.com/danfromtico/mesa-switch/commit/1b03eff0ad5c882b392abbf2b9ac7142295d32bc).
- [Perbaikan penghitungan kapasitas antrean GPFIFO](https://github.com/danfromtico/mesa-switch/commit/f68a41350dbc0b380dcb1462898d8bed48dfdb5e).
- [Perbaikan binding memori depth/stencil](https://github.com/danfromtico/mesa-switch/commit/a72f9551e79e7881ba67940f41df2b115d360600).

Tambahan tipe memori GPU dan penanda diagnostik terbatas adalah integrasi
proyek ini. Compiler shader NAK/NIR, Wine, FEX, DXVK, resolusi, dan preset
grafis tetap berasal dari build yang sudah diuji. Driver memperoleh build ID
baru agar cache driver tidak tertukar. Kompilasi shader pertama setelah
pergantian driver masih bisa menimbulkan jeda.

Analisis alternatif DXVK ada pada `docs/v13-dxvk-research.md` di source paket.
Opsi baru untuk mengabaikan flush eksplisit tidak menghilangkan flush Present
wajib yang dominan pada counter tersebut. Perubahan allocator/thread FEX
juga belum didukung log sebagai solusi utama untuk beban gameplay ini.

## Validasi dan batasnya

Source upstream dan patch dipin dengan hash. Seluruh object NVK yang memakai
struktur internal terkait dikompilasi ulang di direktori terpisah. Linker
memakai object Horizon baru secara eksplisit agar salinan lama dalam library
OpenGL tidak mengambil alih. Library SDK bersama tidak diubah.

Sebelum relink, build lama direproduksi byte demi byte dengan hash ELF v11.
Paket menyertakan laporan pemeriksaan source, archive, linker, binary ARM64,
serta integritas ZIP. Pengujian ini tidak menjalankan GPU Switch. Kecepatan,
stabilitas gameplay, dan penggunaan ZCULL pada adegan nyata harus dibuktikan
oleh log dan tes perangkat.

`Graphics Level = undefined` belum didiagnosis dari file konfigurasi game;
paket ini tidak mengklaim memperbaiki label tersebut atau memaksakan preset
grafis game. Gunakan pengaturan Advanced yang sama saat membandingkan.

Port Switch FEXTendo tetap berasal dari **AndroSwitch Project / Ibnuard**,
berbasis pes13-fex milik proyek ini dan engine FEX-Emu. Kredit patch driver
milik kontributor Mesa/NVK/mesa-switch. Source, lisensi, receipt, serta laporan
tersedia di `source/low-window-mesa-backport/`.

Script reproduksi memakai workspace proyek yang sudah disiapkan: object
runtime v11, checkout dasar Mesa, generated header SDK, compiler devkitA64,
dan fixture pengujian terdahulu. Source paket mendokumentasikan perubahan
dan input tersebut; paket ini bukan SDK mandiri untuk build dari direktori kosong.

Kesempatan kedua disimpan sampai hasil v13 tersedia agar perubahan berikutnya
ditentukan oleh pengukuran, bukan dua build spekulatif sekaligus.
