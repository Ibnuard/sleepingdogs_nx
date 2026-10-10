# Sleeping Dogs v17: perbandingan present FIFO dan IMMEDIATE

Paket ini menguji satu pengaturan pada runtime v17 yang sudah berjalan di Switch:
`dxgi.syncInterval = 1` menjadi `0`. Paket tidak mengganti NRO atau DXVK DLL dan
tidak menambahkan frame hasil LSFG. Target tes tetap FPS asli pada 1280×720.

Log `2a6219ff780b5d7e222898e914c3dd94d0a9ae7f652ff54a771f64d8734de024`
memastikan scheduler v17 aktif, profil Stable, DXVK 3.1.1, LSFG OFF dan present
FIFO. Capture berisi 612 interval selama 29,95454 detik: sekitar 20,43 FPS.
Pengguna mengonfirmasi CPU 1728 / GPU 768 / RAM 1600 MHz.

Kandidat ini menguji apakah menonaktifkan permintaan VSync membantu setelah
scheduler v17 meningkatkan pasokan pekerjaan render. Pengaruh FPS belum diuji
di Switch; 30 FPS belum terbukti.

## Isi paket

Kedua ZIP hanya menimpa satu file runtime:

`switch/sleepingdogs-fex/launcher/presets/stable/dxvk-3.1.1/dxvk.conf`

- `sleepingdogs-fex-v17-present-immediate-test.zip`: `dxgi.syncInterval = 0`.
- `sleepingdogs-fex-v17-present-fifo-restore.zip`: preset Stable standar dengan
  `dxgi.syncInterval = 1`.

Restore memulihkan byte preset standar. Jika file tersebut pernah diubah
sendiri, cadangkan dahulu agar pengaturan khusus itu dapat dipulihkan.

Parameter lain identik: `dxgi.maxFrameLatency = 2`, satu compiler thread,
anisotropy 0, kedua opsi descriptor False, dan nilai pelaporan memori tetap.
Pilihan HUD diterapkan launcher seperti sebelumnya. Profil Performance tidak
digunakan karena juga mengubah maxFrameLatency menjadi 3.

## Cara membandingkan

1. Tutup FEXTendo sepenuhnya melalui HOME.
2. Ekstrak ZIP tes, lalu salin folder `switch` ke root SD dan timpa preset di atas.
3. Di launcher pilih **DXVK 3.1.1**, **Stable**, **Launch GUI**, dan **LSFG OFF**.
4. Pertahankan 1280×720, CPU 1728 / GPU 768 / RAM 1600 MHz, pengaturan game dan
   HUD yang sama. Lewati area tes sekali untuk pemanasan, lalu bandingkan posisi,
   arah kamera dan rute yang sama.
5. Simpan `fex-runtime.log` sebelum membuka sesi berikutnya. Log tes harus berisi
   `[SD-SCHED-V17] mode=auto`, `dxgi.syncInterval = 0`,
   `dxgi.maxFrameLatency = 2`, `dxvk.numCompilerThreads = 1` dan
   `Present mode: VK_PRESENT_MODE_IMMEDIATE_KHR`.
6. Untuk kembali ke FIFO, lakukan langkah yang sama memakai ZIP restore.
   Log harus menunjukkan `dxgi.syncInterval = 1` dan
   `Present mode: VK_PRESENT_MODE_FIFO_KHR`.

Launcher membaca preset saat Play. Jangan mengedit konfigurasi aktif dalam
`drive_c/SleepingDogs` untuk tes ini. Jika marker berbeda, sesi tersebut belum
menguji konfigurasi yang dimaksud.

## Dasar teknis dan batas kesimpulan

Driver Switch yang digunakan mengiklankan FIFO dan IMMEDIATE. IMMEDIATE dipetakan
ke `nwindowSetSwapInterval(0)`; SDK mengizinkan interval 0 dengan minimal tiga
buffer, sesuai swapchain tiga image yang tercatat di log. MAILBOX tidak diiklankan.
IMMEDIATE tidak menunggu vertical blank dan dapat menimbulkan tearing, sesuai
[definisi Vulkan](https://docs.vulkan.org/refpages/latest/refpages/source/VkPresentModeKHR.html).

Wait fence sekitar 16,42 ms dalam capture berasal dari DXVK yang memastikan
semaphore present aman digunakan kembali. Angka itu mencakup tunggu penyelesaian
GPU dan penjadwalan; itu bukan pengukuran VBlank murni dan tidak seluruhnya dapat
dianggap waktu yang dapat dihapus. Semua fence tetap dipakai dalam eksperimen ini.

Sumber yang diperiksa: DXVK `src/dxvk/dxvk_presenter.cpp` (pemilihan present mode
dan `waitForSwapchainFence`), Mesa `src/vulkan/wsi/wsi_common_switch.c` (mode
yang tersedia dan interval native), `src/vulkan/wsi/wsi_common.c` (signal present
fence), serta libnx `include/switch/display/native_window.h`.

## Validasi paket

Preset standar diambil dari staging yang tercatat dalam
`reports/buffer-reuse-package-check.json`; hash file cocok dengan receipt paket
`reports/fex-debug-package.json` dan hasil recipe yang disertakan dalam paket v17.
Semua nilai preset cocok persis dengan blok Effective configuration pada log
terbaru, setelah memperhitungkan `dxvk.hud = full` yang ditambahkan launcher.

Packager memastikan hanya satu nilai berubah, restore identik dengan baseline,
runtime ZIP hanya berisi path preset tersebut, CRC dan seluruh SHA256SUMS valid,
serta NRO v17 tetap berhash
`366e9d7c175b48654c0faf9200dc04da98b4a6e1ba85da0771c8b7318b917fbb`.
Hasil pemeriksaan ada di `reports/present-ab-v17-package.json`.
