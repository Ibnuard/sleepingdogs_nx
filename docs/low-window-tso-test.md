# Sleeping Dogs: tes pengurutan memori saat loading 3D

Paket `sleepingdogs-fex-low-window-tso-test.zip` adalah **tes konfigurasi sementara**,
bukan perbaikan freeze yang sudah dikonfirmasi. Gunakan di atas instalasi
**low-window-loading-watch v3** yang menghasilkan log terakhir.

## Pemasangan

1. Tutup Sleeping Dogs sepenuhnya dari HOME.
2. Ekstrak ZIP uji, lalu timpa folder `switch/` ke root SD. Satu-satunya file
   runtime di paket ini adalah `switch/sleepingdogs-fex/launcher/fex-mode.txt`.
3. Buka launcher yang sama, pilih **Launch Debug**, lalu **New Game**. Pertahankan
   renderer, resolusi, dan pengaturan game dari percobaan sebelumnya.
4. Jika tetap freeze, diamkan sekitar **60–90 detik sejak macet**, tutup dari
   HOME, lalu simpan/kirim `switch/sleepingdogs-fex/fex-runtime.log` yang baru.
   Kalau masuk adegan 3D, coba bermain sekitar satu menit dan simpan lognya juga.

Tidak perlu memasang NSP lagi atau reboot tambahan selama kernel low-window
yang sebelumnya bekerja masih aktif. Profil baru berlaku saat proses diluncurkan
ulang. NRO v3, DLL FEX, DXVK, data game, save, Hekate, dan kernel tetap versi yang
sama; paket ini tidak membawa file-file tersebut.

## Profil yang diuji

File uji berisi `fast`, **bukan `fastest`**. Fast mempertahankan x87 64-bit,
multiblock, SMC mtrack, dan pengaturan compiler sebelumnya, sambil mengaktifkan
scalar/vector/memcpy TSO. Ini menguji kemungkinan pengurutan akses memori
antarthread pada CPU ARM. Performa dapat berkurang. Profil Fastest sebelumnya
belum ditetapkan sebagai penyebab.

Pastikan log baru memuat:

```text
[SD-FEX-MODE] source=launcher/fex-mode.txt: fast profile=1 guest_tests=0
[FEX3-PRESET] fast x87=64 scalar_tso=1 vector_tso=1 memcpy_tso=1 multiblock=1 smc=mtrack
```

Paket ini tidak menambahkan build baru; marker NRO tetap
`sleepingdogs-fextendo-0.1.0-low-window-v3-load-watch`.

Untuk kembali ke pilihan Fastest sebelumnya, tutup aplikasi lalu timpa folder
`switch/` dari **`sleepingdogs-fex-restore-fastest.zip`**. Alternatifnya, isi
`launcher/fex-mode.txt` dengan `fastest` dan newline, lalu buka ulang aplikasi.
Jangan pasang ZIP pemulihan bersamaan dengan ZIP tes.

## Bukti dari sesi v3

Log SHA256 `bc83d378715f4e3284feeff39ffea08fda92f74b661605d7e5b8a63a0791b7f3`:

- Present mencapai **3441** pada sampel detik 115 dan tidak bertambah sampai
  detik 280; umur Present terakhir mencapai **165594 ms**.
- Thread **4** dan **72** mengulang `NtWaitForSingleObject(0x6d4ffff0, false,
  infinite)`. Sampel return menunjukkan **STATUS_INVALID_HANDLE / 0xc0000008**.
  Jumlah syscall masing-masing bertambah lebih dari 11 juta selama rentang itu.
- Kedua stack melewati `0xbb6f3b -> 0xbb7c6a -> 0xbb7e31`. Pemeriksaan statis
  EXE asli menunjukkan wrapper semaphore membaca HANDLE dari objek dan memanggil
  `WaitForSingleObject`; wrapper langsung kembali tanpa memeriksa hasilnya.
  Ini konsisten dengan loop retry game yang terlihat di log.
- Heap native terakhir masih sekitar **1009 MiB** tersedia dan `VKMEM oom=0`.
  Tidak ada OOM Vulkan yang menjelaskan sesi ini. Sisa heap native tidak menjamin
  semua suballocator di dalam game masih memiliki ruang.
- Counter driver acquire/submit/fence/semaphore tidak bertambah setelah detik
  130, sementara shared clock dan syscall terus berjalan.

Nilai handle itu berada dalam rentang arena guest, tetapi log belum merekam
penulis nilai tersebut. Belum dapat dipastikan apakah asalnya stale/freed
storage, pengurutan memori, atau korupsi lain. Mengabaikan error atau membuat
semaphore pengganti untuk handle itu akan menyembunyikan masalah sinkronisasi.

## Verifikasi paket dan hasil yang diperlukan

SHA NRO/DLL dan sumber pemilih profil dicocokkan dengan receipt build yang sudah
dikirim. Paket diperiksa agar hanya satu file di bawah `switch/` yang berubah;
isinya tepat `fast\n`. CRC dan SHA256 setiap anggota arsip diperiksa. Tidak ada
rebuild runtime atau klaim gameplay berhasil di Switch dari pemeriksaan ini.

Jika Fast mencapai 3D, hasil itu mendukung dugaan masalah yang peka terhadap
ordering/timing, tetapi satu percobaan belum membuktikan penyebab. Jika handle
invalid tetap berulang, langkah berikutnya adalah merekam pembuatan/penutupan
semaphore serta objek queue di sekitar invalid wait pertama. Log v3 masih
tersedia selama sepuluh menit sejak Launch Debug untuk membandingkan kedua mode.
