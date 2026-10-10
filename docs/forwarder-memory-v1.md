# Sleeping Dogs untuk FEXTendo Memory v1 TEST

Forwarder ini meminta layout **39-bit + guest low-window** lewat descriptor
`fxtmem` di ExeFS NSP, sesuai loader/kernel generik yang sudah lulus tes
CONTROL dan OPTIN-A/B. Forwarder Sleeping Dogs lama tidak membawa descriptor
ini, sehingga tidak memilih low-window saat memakai boot generik tersebut.

## Pemasangan

1. Tetap di boot entry **FEXTendo Memory v1 TEST** yang sedang dipakai.
2. Tutup Sleeping Dogs sepenuhnya dari HOME.
3. Install `forwarder/FEXTendo-SleepingDogs-39bit-FEXTendoMemory-v1.nsp`.
   Ini menggantikan forwarder Sleeping Dogs dengan Title ID yang sama;
   pilih replace/overwrite jika installer memintanya.
4. Buka tile Sleeping Dogs, lalu **Launch Debug**. Gunakan NRO low-window v5
   dari `sleepingdogs-fex-low-window-sync-startup-fix.zip` yang sudah disiapkan
   sebelumnya. Jika v5 sudah tersalin, tidak perlu menyalinnya lagi.

**Tidak perlu mengganti kernel, mengedit Hekate atau reboot lagi** selama
masih berada di sesi FEXTendo Memory v1 TEST. Paket ini hanya berisi forwarder
dan bahan pemeriksaan; tidak menimpa game, save, NRO atau profil Fastest.

Target tetap:

```text
Title ID: 059a3db219b42000
NRO: sdmc:/switch/sleepingdogs-fex/sleepingdogs-fex.nro
```

Konfirmasi melalui `switch/sleepingdogs-fex/fex-runtime.log`:

```text
[BUILD] sleepingdogs-fextendo-0.1.0-low-window-v5-sync-startup-fix
[SD-LOWVA] v1 host=200000+7fffe00000
[SD-LOWVA] PASS: native above 4 GiB; guest low window available
```

Baris `host=` juga memuat quota, Title ID dan hasil query. Runtime memeriksa
layout dan mapping sebelum mengizinkan game berjalan. Jika kernel/loader
yang aktif tidak menyediakan low-window, startup tetap ditolak oleh preflight.

Perubahan ini memperbaiki pemilihan layout pada boot generik; freeze menuju
3D masih memerlukan log percobaan berikutnya. Jika freeze, tunggu 60–90 detik
lalu kirim log terbaru; jika crash, sertakan `crash.log` bila tersedia.

## Pemeriksaan paket

- NSP dibuka kembali dan ExeFS aktual diurai. Satu-satunya file tambahan pada
  ExeFS adalah `fxtmem`, 32 byte, ABI 1/layout 1/flags 0/reserved 0.
- Descriptor identik dengan NSP OPTIN-A/B yang lulus pada perangkat. Descriptor
  tidak ada pada CONTROL dan NSP Sleeping Dogs lama.
- NPDM aktual tetap ARM64, 39-bit, tipe/pool application, system resource
  16 MiB, serta kedua tabel capability yang diperlukan.
- ELF/NSO forwarder identik dengan StartupFix sebelumnya. NPDM, NACP, ikon,
  Title ID, target dan argumen juga sama. Identitas game tidak digunakan
  sebagai whitelist oleh mekanisme pemilihan layout generik.
- Forwarder ARM64 dijalankan dengan NRO v5: kandidat alamat rendah dihindari,
  NRO dipetakan di atas 4 GiB, reservation guest bertahan saat reload, dan
  allocator bookkeeping tetap berada dalam BSS privat 16 KiB.

Uji ARM64 memakai model layanan Horizon; NSP baru ini masih perlu diuji di
Switch. Paket tidak mengklaim menyelesaikan freeze gameplay.

Build ulang dari workspace dan SDK yang sudah disiapkan:

```text
python3 forwarder/build_forwarder.py --fextendo-memory-v1 --keys <local-keyset> --nro <v5-nro> --work <fresh-work> --output <forwarder-output>
```

`--fextendo-memory-v1` otomatis mengaktifkan `--low-window`. Flag private
kernel bukan bit NPDM: loader membaca `fxtmem` sebelum membuat proses.
