# Sleeping Dogs: perbaikan startup Launch Debug v5

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

Paket `sleepingdogs-fex-low-window-sync-startup-fix.zip` memperbaiki bug pada
pencatat debug v4 dan tetap memakai **Fastest**. Freeze saat loading menuju 3D
masih memerlukan hasil pengamatan dari Switch; paket ini belum mengklaim
memperbaiki freeze tersebut.

## Pasang

1. Tutup Sleeping Dogs sepenuhnya dari HOME.
2. Ekstrak ZIP ini di PC, lalu timpa folder `switch/` ke root SD.
3. Buka launcher yang sama, pilih **Launch Debug**, lalu coba **New Game**.
4. Jika macet saat menuju 3D, tunggu 60–90 detik sejak macet. Tutup aplikasi
   dan kirim `switch/sleepingdogs-fex/fex-runtime.log` terbaru. Jika crash,
   sertakan `crash.log` dari percobaan yang sama jika tersedia.

Tidak perlu NSP baru atau reboot tambahan selama masih memakai sesi kernel
low-window yang sebelumnya berhasil mencapai menu. Folder `source/` dan
laporan cukup disimpan di PC. Game dan save tidak ditimpa paket ini.

Penanda log:

```text
[BUILD] sleepingdogs-fextendo-0.1.0-low-window-v5-sync-startup-fix
[SD-FEX-MODE] source=launcher/fex-mode.txt: fastest profile=2 guest_tests=0
```

## Bug dan perubahan

Observer v4 memanggil `get_cpu_area(IMAGE_FILE_MACHINE_I386)` setelah syscall
tertentu, termasuk `NtClose` awal. Fungsi Wine tersebut mengecek `wow_peb`
global, lalu membaca `cpu->Machine` tanpa memeriksa apakah slot CPU TLS pada
thread saat ini sudah terisi. Selama bootstrap WoW64, kondisi global aktif
dengan slot per-thread kosong menyebabkan pembacaan alamat `0x2`.

Bridge v5 memeriksa TEB dan `TlsSlots[WOW64_TLS_CPURESERVED]` sebelum meminta
konteks x86. Capture dilewati jika konteks belum tersedia. Kuota capture
invalid-wait baru dipakai setelah konteks valid diperoleh, sehingga pengamatan
awal yang dilewati tidak menghilangkan bukti berikutnya.

Hanya `sd_sync_bridge.inc` dan penanda build di `runtime.c` berubah pada source
native dibanding v4. DLL dan adapter FEX, renderer, serta alokasi low-window
tetap memakai implementasi sebelumnya.

## Verifikasi dan batas hasil

- 12 kelompok tes collector/bridge dengan ASan dan UBSan, mencakup TEB kosong,
  CPU TLS belum siap, mesin non-x86, pemulihan setelah inisialisasi, lifecycle,
  pembatasan capture dan producer bersamaan.
- 21 kasus pada dispatcher ARM64 yang benar-benar ditautkan: binary v4
  mereproduksi fault alamat `0x2` pada close/create/open ketika CPU TLS kosong;
  v5 mengembalikan status syscall semula dan kembali merekam setelah siap.
- Tes preflight low-window ARM64 dan monitor loading dijalankan kembali pada
  binary/source v5. Manifest seluruh source dan adapter dibandingkan dengan
  paket v4 yang hash-nya dipatok. CRC dan SHA setiap anggota ZIP diperiksa.

TEB, TLS, syscall native, mutex dan keadaan sistem pada pengujian ARM64
disediakan sebagai fixture. Pengujian menjalankan dispatcher dan
`get_cpu_area` asli, tetapi tidak menjalankan game atau kernel Switch.
Laporan pengguna menyebut kode perkiraan `0x000005` setelah Launch Debug;
belum ada log sesi baru untuk mencocokkan fault perangkat dengan reproduksi
ini. Bug v4 sendiri sudah terbukti pada binary dan diperbaiki di v5.

Jika perlu kembali ke NRO v3 yang sebelumnya mencapai menu, gunakan
`sleepingdogs-fex-low-window-v3-recovery.zip`, tetap dengan Fastest. NRO
pemulihan direkonstruksi dari ELF tersimpan dan hash-nya sama persis dengan
rilis v3. Pemulihan ini juga belum memperbaiki freeze 3D.
