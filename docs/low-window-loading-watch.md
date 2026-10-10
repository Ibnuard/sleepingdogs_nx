# Sleeping Dogs: diagnosis loading menuju 3D

Paket: `sleepingdogs-fex-low-window-loading-watch.zip`.
Ini update NRO untuk merekam titik macet setelah menu. Penyebab freeze belum
terbukti; paket ini belum diklaim memperbaiki freeze.

## Pemasangan dan percobaan

1. Tutup Sleeping Dogs sepenuhnya dari HOME.
2. Ekstrak ZIP, lalu timpa folder `switch/` ke root SD.
3. Buka ikon Sleeping Dogs yang sama dan pilih **Launch Debug**. Segera coba
   **New Game** hingga loading menuju 3D.
4. Jika gambar diam, tunggu sekitar **5 menit sejak macet**, lalu tutup aplikasi
   dari HOME dan kirim `switch/sleepingdogs-fex/fex-runtime.log` yang baru.
   Jika benar-benar crash, sertakan `crash.log` sesi tersebut juga.

Gunakan instalasi low-window yang sudah berhasil membuka menu, dengan NSP
**39bit-LowWindow-StartupFix** dan kernel low-window aktif. Tidak perlu memasang
NSP lagi atau reboot tambahan untuk update NRO ini. FEX tetap **Fastest**.
Pengaturan grafis, renderer, save, file game, kernel dan Hekate tidak ditimpa.
Folder `source/` disediakan untuk pemeriksaan di PC, tidak perlu disalin ke SD.

Pencatatan detail berlaku selama **10 menit sejak Launch Debug**. Masuk New Game
dalam rentang itu. Sesudahnya pemantauan resource dan error tetap aktif, tetapi
pengamatan syscall dan snapshot thread berhenti. Launch GUI tidak menyalakan
pengamatan ini. Mode Debug memiliki overhead pengamatan; jangan jadikan sesi
ini pengukuran FPS.

## Bukti dari log sebelumnya

Input: `SS/SS/fex-runtime.log`, SHA256
`6d45ef9e46ed4e91552e04bb96fa1e3eb735ba5b4cb67222d14f009c89b77d2f`.
Pengguna melihat gambar diam dan menunggu kurang dari tiga menit.

- Build v2 sudah menjalankan probe RX/RW low-window dan arena alias 1000 MiB.
  Penolakan Launch Debug pada versi sebelumnya sudah terlewati di perangkat.
- Sampel resource terakhir: `heap_available=1058279648` (sekitar 1009 MiB),
  `free_threads=195`, `VKMEM oom=0`. Tidak ada kegagalan alokasi Vulkan tercatat.
  Angka ini tidak menjamin setiap ukuran alokasi berhasil, tetapi log tidak
  menunjukkan OOM yang menjelaskan freeze kali ini.
- `compile_code` berhenti bertambah pada 48267 panggilan dari uptime 101519 ms
  sampai akhir log 132679 ms. `dispatch_compile` masih bertambah dari 107648
  menjadi 122271. Aktivitas runtime saja tidak membuktikan game masih maju.
- Log lama menonaktifkan pengamatan syscall/file ketika launcher menyerahkan
  layar pertama kali. Snapshot thread terakhir sekitar detik ke-30, sehingga
  tidak ada stack thread pada saat loading 3D macet. Catatan Present juga jarang;
  tidak cukup untuk menetapkan kapan Present terakhir benar-benar selesai.

`UsedMemorySize` pada `[SD-MEMBUDGET]` mencakup heap yang sudah dicadangkan oleh
proses. Jangan mengartikannya sebagai jumlah alokasi aktif newlib, atau
menganggap selisih quota sebagai seluruh sisa heap. Pelaporan memori Windows
belum diubah dalam paket diagnosis ini.

## Perubahan dan pembacaan log

`[BUILD] sleepingdogs-fextendo-0.1.0-low-window-v3-load-watch` memastikan NRO baru.
Pengamatan Debug kini bertahan setelah handoff layar dan kedaluwarsa di monitor,
bukan di frame pertama. Resource/call/file dicatat tiap 5 detik sebelum Present
dan tiap 15 detik sesudahnya selama jendela diagnosis. Snapshot thread sekitar
tiap 30 detik, maksimal 20 capture; setiap capture berisi dua sampel berjarak
2 ms. Try-lock dipakai agar registry/profiler yang sibuk dilewati. Tidak ada
pencatatan file ketika thread target sedang dihentikan sementara.

- `[SD-LOAD]`: jumlah Present yang selesai, pertambahan sejak laporan sebelumnya,
  dan umur Present terakhir. Ini belum mengukur pekerjaan GPU yang selesai.
- `[FEX3-PIPE]`: jumlah/waktu panggilan driver acquire/submit/fence/semaphore yang
  sudah kembali, timeout/error, serta kemajuan shared clock.
- `[SD-CALL]` / `[SD-FILE]`: batas syscall dan akses file terakhir tiap thread;
  `entered` berarti belum ada return teramati, bukan bukti tunggal deadlock.
- `[SD-PC]` / `[SD-STACK]`: PC native, waktu CPU, stack dan saved guest context.
  Saved EIP serta label blok JIT bukan PC x86 langsung pada saat sampling.

Kombinasi itu akan membedakan tidak adanya Present baru, pekerjaan loading yang
masih bergerak, wait Windows/file, dan lokasi tunggu driver. Hasil Switch tetap
diperlukan untuk menetapkan penyebabnya.

## Verifikasi

Delapan skenario host/UBSan memakai fungsi monitor, handoff dan sampler dari
sumber yang dibangun: freeze setelah Present, expiry, kegagalan pause/read/resume,
mutex sibuk, izin SVC tidak tersedia, dan GUI tanpa sampling. Seluruh target yang
berhasil dipause dilanjutkan sebelum logging; kegagalan resume dicoba ulang.
Delapan tes launcher, 15 kasus preflight/allocator native ARM64, dan 12 kasus
admission ARM64 juga lulus dengan ELF v3. SVC dimodelkan di PC; ini bukan uji
eksekusi game pada Switch.

Paket diverifikasi hanya mengganti NRO dan receipt JSON. Source native yang
berbeda dari v2 hanya `runtime.c`, `thread_profile.c` dan dua include diagnosis.
FEX adapter dan perbaikan memory/forwarder yang sudah berjalan dipertahankan.
Jika ingin kembali ke v2, timpa `switch/` dari
`sleepingdogs-fex-low-window-launch-order-fix.zip` lalu buka aplikasi ulang.
