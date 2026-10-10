# Sleeping Dogs: semaphore dan objek queue saat freeze

**Catatan v4:** ditemukan bug startup pada akses CPU TLS sebelum WoW64 siap.
Gunakan [perbaikan v5](low-window-sync-startup-fix.md) untuk percobaan baru.
Catatan di bawah menjelaskan rancangan dan hasil pengujian awal v4; tes awal
tersebut belum mencakup CPU TLS kosong.

Paket: `sleepingdogs-fex-low-window-sync-watch.zip`.
Paket ini **mengembalikan Fastest** dan mengganti NRO dengan pencatatan semaphore
yang lebih terarah. Belum ada perbaikan freeze yang terkonfirmasi pada perangkat.

## Pasang dan coba

1. Tutup Sleeping Dogs sepenuhnya dari HOME.
2. Ekstrak ZIP, lalu timpa folder `switch/` ke root SD.
3. Buka launcher yang sama, pilih **Launch Debug**, lalu **New Game** dengan
   renderer dan pengaturan grafis yang sama.
4. Jika macet, tunggu **60–90 detik sejak macet**, lalu tutup dari HOME dan kirim
   `switch/sleepingdogs-fex/fex-runtime.log` yang baru. Jika aplikasi crash,
   sertakan `crash.log` dari sesi tersebut.

Gunakan instalasi low-window yang sebelumnya sudah mencapai menu. Tidak perlu
memasang NSP atau reboot tambahan selama kernel low-window itu masih aktif.
Game, save, DLL FEX, DXVK, Hekate, dan kernel tidak ditimpa oleh paket ini.
Folder `source/` dan laporan adalah bahan pemeriksaan di PC; cukup salin `switch/`.

Penanda yang diharapkan:

```text
[BUILD] sleepingdogs-fextendo-0.1.0-low-window-v4-sync-watch
[SD-FEX-MODE] source=launcher/fex-mode.txt: fastest profile=2 guest_tests=0
[SD-WATCH] v3 sync lifecycle + first-invalid object; debug detail=600s;
```

## Hasil perbandingan Fast

Log Fast SHA256 `5a6918b09c9794a78efe26ed4a4b4a494760ff2f1afe03bca63691328fd12c0b`
memastikan scalar/vector/memcpy TSO semuanya aktif. Pengguna melaporkan lebih
lambat dan tetap macet. Present berhenti pada 1609; umur frame terakhir bertambah
dari 3642 ms pada detik 105 menjadi 33559 ms pada detik 135. Thread 4 dan 72
mengulang wait pada **handle yang sama, `0x6d4ffff0`**, melalui stack game yang
sama seperti percobaan Fastest. Heap native masih sekitar 1008 MiB dan VKMEM
tetap `oom=0`.

Sampel Fast kebetulan menangkap state `entered`, bukan status saat return.
`STATUS_INVALID_HANDLE` sudah tertangkap pada sesi Fastest sebelumnya. NRO v4
merekam kejadian return invalid secara langsung, sehingga tidak bergantung pada
sampling yang kebetulan jatuh di antara return dan retry berikutnya.

Mengaktifkan TSO saja tidak menghilangkan masalah pada percobaan ini. Asal nilai
handle tersebut masih belum diketahui; tidak ada alasan dari hasil ini untuk
mempertahankan pengorbanan performa Fast pada percobaan berikutnya.

## Bukti tambahan yang direkam

- `[SD-SYNC]`: create/open semaphore, close untuk handle semaphore yang telah
  dilacak, dan return invalid pertama untuk wait dengan handle bernilai tinggi.
- `[SD-SYNC-REG]` / `[SD-SYNC-MEM]`: saved register x86, stack/frame, serta
  kandidat queue dan objek semaphore pada kegagalan pertama.
- `[SD-SYNC-OBJECT]`: status pembacaan queue/objek. Interpretasi queue hanya
  diaktifkan jika byte fungsi game dan Wine cocok dengan versi yang diperiksa.
- `[SD-SYNC-SUMMARY]`: jumlah rekaman yang dikirim, riwayat tertimpa, registry
  penuh, dan jumlah capture invalid. Counter overflow harus ikut dinilai.

Ring menyimpan 256 kejadian, registry paling banyak 256 handle, dan snapshot
invalid paling banyak delapan pasangan thread/handle, maksimal dua nilai per
thread. Retry untuk nilai yang sama tidak membaca memori atau mengambil mutex
diagnosis berulang kali. Pembacaan memakai pemeriksaan view/proteksi halaman
Wine; tidak ada penulisan memori guest. Collector tidak mengalokasikan memori
dinamis, tidak mempause thread, dan tidak menulis file pada jalur syscall.
Monitor mengeluarkan rekaman setelah mutex collector dilepas dan di luar
penghentian sementara thread milik sampler v3.

Status syscall, handle, dan aturan sinkronisasi tetap berlaku seperti sebelumnya.
Pencatatan ini mengamati syscall dari PE; tidak mengklaim mengamati seluruh
operasi internal Wine. Snapshot bukan salinan atomik semua thread: thread lain
dapat mengubah objek di antara pembacaan. Jalankan New Game dalam sepuluh menit
sejak Launch Debug agar pengamatan detail masih aktif.

## Verifikasi

Sembilan kelompok tes ASan/UBSan lulus untuk collector dan bridge yang dipakai
NRO, termasuk reuse handle, close gagal, invalid-wait flood, pointer/proteksi
tidak terbaca, signature berbeda, index tidak valid, overflow, serta producer
bersamaan. Jalur wait dari EXE game dan kernelbase asli dijalankan di Unicorn
untuk memeriksa bahwa ESI queue disimpan di **EBP-4** dan EDI tetap menjadi index.
File game di disk tidak diubah. Fixture itu menyediakan nilai handle invalid;
hasilnya membuktikan lokasi data yang dibaca, bukan penyebab korupsi.

Tes monitor/sampler, launcher, dan preflight/admission ARM64 dijalankan pada
sumber/ELF v4. Pemeriksaan paket memastikan adapter FEX dan source native lain
di luar overlay diagnosis tetap sama dengan v3. CRC dan SHA setiap anggota ZIP
diperiksa. Hasil tersebut belum menggantikan uji game pada Switch.

Jika perlu kembali ke NRO v3 sambil tetap memakai Fastest, tutup aplikasi lalu
timpa `switch/` dari `sleepingdogs-fex-low-window-sync-watch-rollback.zip`.
