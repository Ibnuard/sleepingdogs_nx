# Sleeping Dogs v6 — CPU topology / loading freeze

Paket: `dist/sleepingdogs-fex-low-window-cpu-topology-fix.zip`.
Ini update untuk instalasi low-window yang sudah mencapai menu/loading,
termasuk forwarder **FEXTendo Memory v1** pada boot **FEXTendo Memory v1 TEST**.

## Pasang

1. Tutup Sleeping Dogs sepenuhnya dari HOME.
2. Ekstrak folder `switch/` dari ZIP ke root SD dan timpa file yang sama.
   NRO tujuan: `switch/sleepingdogs-fex/sleepingdogs-fex.nro`.
3. Buka dari HOME, pilih DXVK 3.1.1 dan Launch Debug, lalu New Game.

Profil tetap **Fastest**. Boot FEXTendo Memory yang sekarang tetap digunakan;
untuk update NRO ini tidak perlu reboot atau install ulang NSP.
Paket hanya memperbarui NRO, pilihan profil, dan metadata launcher.

Log harus menunjukkan build `low-window-v6-cpu-topology-fix` dan:

```text
[SD-CPU-TOPOLOGY] v1 logical=4 cores=4 mask=f legacy_records=6 ex_bytes=...
```

Jika masih macet, simpan `fex-runtime.log` baru. Jika aplikasi tertutup,
simpan juga `crash.log`. Log v6 diperlukan untuk melihat apakah masalah
semaphore sudah terlewati dan apakah ada masalah berikutnya saat membuat adegan.

## Penyebab yang ditemukan

Log v5 yang dikirim 9 Oktober memperlihatkan Present berhenti pada 2442 frame.
Heap masih tersedia sekitar **1011,7 MiB**; penghitung OOM GPU tetap nol.
Low-window aktif dan probe awal lulus. Dua thread membaca indeks semaphore
**-34** dan terus menerima `STATUS_INVALID_HANDLE` untuk `0x6d4ffff0`.

Dump antrean menunjukkan jumlah worker `0`, nilai default indeks `0xffffffde`,
dan tabel worker masih berisi pola `0xde`. Di Wine-NX v5,
`GetLogicalProcessorInformation` berakhir pada backend yang belum diimplementasi.
Kode asli HKShip mengganti jumlah CPU dari GetSystemInfo dengan hitungan dari
API tersebut tanpa menangani kegagalannya, sehingga jumlahnya menjadi nol.
Inisialisasi tabel worker dilewati; byte `0xde` kemudian dibaca sebagai -34
dan dipakai untuk mengakses sebelum awal array semaphore.

v6 menambahkan backend topologi CPU Horizon pada Wine native: jumlah core
sesuai PEB/GetSystemInfo, satu thread per core, satu package, satu NUMA node,
dan satu processor group. Format lama dan Ex diisi melalui helper Wine yang
sama. Ukuran buffer dan jalur kegagalan tetap mengikuti API Wine.
Tidak ada patch EXE game atau perubahan FEX, DXVK, kernel, dan forwarder.

## Validasi dan batasnya

Replay menjalankan fungsi ARM64 dari ELF v5/v6, serta CPU probe,
inisialisasi tabel antrean, dan pembacaan indeks dari HKShip asli di Unicorn.
`GetLogicalProcessorInformation` x86 kernelbase juga dieksekusi. PEB,
allocator, pthread_once, layanan platform, dan konversi struktur WoW64
dimodelkan; ini bukan boot Switch atau gameplay penuh.

- v5: API gagal, game menghitung 0 worker, indeks menjadi -34.
- v6: game menghitung 4 worker, indeks menjadi `1, 0, 0, 0`.
- Query buffer kosong/kecil/cukup, format legacy/Ex, mask CPU,
  jumlah CPU tidak valid, serta kegagalan alokasi diperiksa.
- Guard startup observer dan preflight low-window diuji pada ELF v6.
- Paket memverifikasi hash source, NRO/ELF, profil, dan seluruh isi ZIP.

Perbaikan jalur ini lulus replay; **kelanjutan loading sampai gameplay tetap
perlu dikonfirmasi di Switch**. Jumlah worker yang kini benar dapat membuat
game mencapai alokasi atau pekerjaan lain yang sebelumnya belum dijalankan.

Laporan: `reports/low-window-v6-cpu-topology.json` dan
`reports/loading-freeze-v5-cpu-topology-analysis.json`.
Rollback: timpa kembali folder `switch/` dari
`dist/sleepingdogs-fex-low-window-sync-startup-fix.zip` (v5).
