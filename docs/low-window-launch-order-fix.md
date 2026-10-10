# Sleeping Dogs: perbaikan Launch Debug / Launch GUI

Update NRO untuk launcher low-window yang sudah terbuka tetapi menolak Play.
Memerlukan instalasi low-window dan NSP **StartupFix** yang sebelumnya sudah
berhasil membuka launcher dari HOME.

## Pemasangan

1. Tutup aplikasi Sleeping Dogs sepenuhnya dari HOME.
2. Ekstrak `sleepingdogs-fex-low-window-launch-order-fix.zip` dan salin folder
   `switch/` ke root SD. Timpa file NRO dan receipt launcher yang sama.
3. Buka ikon Sleeping Dogs yang sama, pilih **Launch Debug**, lalu coba game.

Tidak perlu menginstal NSP lagi atau reboot tambahan selama kernel low-window
masih aktif. Profil FEX tetap Fastest. Paket hanya berisi NRO, receipt dan
sumber perubahan; pengaturan pengguna, renderer, file game dan save tidak
ditulis ulang. Folder `source/` untuk pemeriksaan di PC.

## Temuan dari log perangkat

`fex-runtime.log` sudah menunjukkan layout low-window
`host=200000+7fffe00000`, quota proses 3444572160 byte (3285 MiB), dan kapasitas
heap 3349303296 byte (sekitar 3,12 GiB). Ini memastikan entry boot dan NSP sudah
membuka proses dengan kapasitas lebih dari batas lama 2 GiB.

Namun launcher mencetak `probe=0 arena=0`, tanpa satu pun baris `[SD-LOWVA]` atau
`[SD-ALIAS]`. Pemeriksaan kesiapan dilakukan di dalam `fx_launcher_start`,
sedangkan inisialisasi hanya dipanggil setelah fungsi itu mengizinkan peluncuran
dan kembali ke `main`. Akibatnya kesiapan selalu nol dan game belum dimuat.
`crash.log` yang disertakan masih identik dengan sesi game lama.

NRO v2 memanggil inisialisasi stack, probe low-window dan arena di main thread
ketika Play diterima, sebelum validasi kesiapan. Pada Launch Debug, log sudah
dibuka sehingga hasil probe langsung tercatat. Jalur guest-test menggunakan
fungsi persiapan yang sama. Gagal probe/arena tetap memblokir peluncuran; pesan
sekarang menyebut pemeriksaan memori, bukan selalu menyuruh memilih boot lain.
Percobaan ulang memakai resource yang sudah disiapkan.

## Verifikasi dan penanda log

Pengujian launcher memakai fungsi C yang benar-benar dibangun: versi lama
mereproduksi penolakan sebelum init, versi baru melewati Launch GUI/Debug.
Kasus kegagalan probe, arena, renderer, retry thread dan batal sebelum Play
ikut diperiksa. ELF ARM64 baru menjalankan probe asli dan fungsi admission
pada 12 kasus; 15 kasus preflight dan 20 kasus arena alias 1000 MiB juga lulus.
Horizon pada pengujian otomatis dimodelkan di PC. Log perangkat berikutnya
telah mengonfirmasi probe RX/RW, arena 1000 MiB, serta akses menu/loading dengan
v2. Sesi itu freeze menuju 3D; lihat [diagnosis loading](low-window-loading-watch.md).

Penanda yang diharapkan pada log berikutnya:

```
[SD-INIT] v2 preparing memory before launch validation
[SD-LOWVA] ...
[SD-ALIAS] v1 requested=1048576000 reserved=1048576000 ...
[SD-INIT] v2 ready probe=1 arena=1048576000
[SD-ADDRESS] low-window-v2 ... probe=1 arena=1048576000
```

Jika probe atau arena gagal di perangkat, kirim `fex-runtime.log` lengkap.
Baris `[SD-LOWVA]` / `[SD-ALIAS]` akan menunjukkan tahap dan result pemetaan
yang benar-benar gagal, sebelum game dimuat.
