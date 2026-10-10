# Sleeping Dogs: perbaikan startup forwarder low-window

Patch NSP untuk crash segera setelah ikon Sleeping Dogs ditekan dari HOME.
Pasang setelah paket `sleepingdogs-fex-low-window-fix.zip`. Boot kernel/loader
low-window harus sudah aktif melalui **CFW EMUMMC SD Low Window**.

NSP ini sudah dikonfirmasi membuka launcher di Switch. Untuk penolakan saat
Launch Debug/GUI, pasang juga update NRO
`sleepingdogs-fex-low-window-launch-order-fix.zip`; lihat
[perbaikan urutan inisialisasi](low-window-launch-order-fix.md).

## Pemasangan

1. Tutup aplikasi Sleeping Dogs sepenuhnya.
2. Instal `forwarder/FEXTendo-SleepingDogs-39bit-LowWindow-StartupFix.nsp`
   sebagai pengganti forwarder Sleeping Dogs yang ada. Title ID tetap
   `059a3db219b42000`; gunakan opsi instal ulang/timpa jika installer meminta.
3. Jalankan ikon Sleeping Dogs dari HOME lagi. Tidak perlu reboot tambahan
   selama sesi ini sudah memakai entry **CFW EMUMMC SD Low Window**.
4. Setelah launcher muncul, pilih Launch Debug dan coba game.

Paket ini hanya memperbarui NSP. NRO, kernel, HOC, konfigurasi Hekate, profil
FEX Fastest, renderer, file game dan save tetap memakai instalasi sebelumnya.
Folder `source/` dan receipt JSON merupakan bahan pemeriksaan di PC, bukan
file yang perlu disalin ke SD. Jangan pasang kembali NSP v1 dari ZIP low-window
lama setelah memasang perbaikan ini.

## Penyebab dan perubahan

Forwarder low-window v1 memanggil `virtmemAddReservation` untuk menjaga rentang
alamat guest `0x00200000–0x100000000` tetap kosong. Fungsi libnx ini memerlukan
alokasi 32 byte. Forwarder Sphaira yang menjadi basis sengaja mengganti
`__libnx_alloc` dengan abort, sebab sebelumnya tidak membutuhkan allocator.
Akibatnya startup berhenti dengan result `0x515b` sebelum NRO dijalankan dan
sebelum log runtime baru dapat ditulis.

Forwarder v2 menggunakan allocator normal libnx/newlib dengan heap privat
16 KiB di BSS forwarder. Metadata reservasi tetap ada saat heap aplikasi
dipetakan untuk NRO dan saat NRO kembali ke forwarder. NPDM 39-bit, system
resource 16 MiB, Title ID, icon, target NRO dan kontrak GPU-budget tidak berubah.

Log yang diterima pada laporan crash ini masih memuat anchor native
`0x29e18510`, heap sekitar 2 GiB dan error alokasi Vulkan dari sesi game yang
telah berjalan. Isinya tidak merekam kegagalan forwarder sebelum NRO. Karena
itu diagnosis startup ini didasarkan pada reproduksi binary forwarder v1.

## Verifikasi

Tes Unicorn menjalankan ELF ARM64 lama dan baru, termasuk kode libnx/newlib
untuk malloc, sbrk, reservasi alamat, pembacaan ROMFS/NRO dan penyiapan ABI
handoff. File NRO yang dimuat adalah NRO low-window v1 yang sama.

- ELF v1 mereproduksi abort `0x515b` pada alokasi reservasi, sebelum map NRO.
- ELF v2 mencapai handoff NRO pada alamat di atas 4 GiB.
- Kandidat alamat rendah ditolak; kandidat tinggi dapat dipakai.
- Reload NRO berhasil dengan reservasi yang sama, tanpa alokasi ulang metadata.
- Source heap dibuat tidak dapat diakses setelah map, sesuai kepemilikan alias.
- Alokasi melampaui heap privat mengembalikan NULL; alokasi dan free berikutnya
  tetap bekerja tanpa merusak reservasi.
- NPDM, NACP, icon dan target sama persis dengan v1; NSO yang diuji diverifikasi
  terdapat di NSP hasil packing.

Layanan Horizon, pemetaan kernel dan RNG dimodelkan dalam tes PC. Setelah paket
ini dicoba, pengguna sudah mengonfirmasi launcher terbuka di Switch. Gameplay
masih memerlukan pengujian setelah update NRO untuk urutan inisialisasi.

Jika masih berhenti sebelum launcher muncul, laporan terbaru di
`sd:/atmosphere/crash_reports/` lebih berguna daripada `crash.log` runtime yang
belum diperbarui. Jika launcher/game sudah berjalan, gunakan log baru dari
`sd:/switch/sleepingdogs-fex/`.
