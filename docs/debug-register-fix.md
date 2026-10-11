# Sleeping Dogs: exception breakpoint saat startup

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

Log perangkat terbaru memperlihatkan arena 1.000 MiB berhasil dialokasikan.
Exception pertama adalah execute AV pada `EIP=fffffffe`, dengan `DR7=0x155`,
DR0=`004c0a8a`, DR1=`005b2e92`, DR2=`0061ce88`, DR3=`0068d35a`.
Dispatcher WoW64 valid (`ff34e4e8`); frame SEH game `0166fe8c` sudah bernilai nol.

Disassembly HKShip.exe asli menunjukkan call di `007d46ad` menuju DR0.
Jika return-nya bukan nol, kode `007d46b3..007d46cc` menghapus stack hingga EBP,
termasuk SEH, lalu `ret` mengambil saved EDI `fffffffe`. Handler asli game di
`00b74470` menerima `EXCEPTION_SINGLE_STEP` dan mengembalikan context dengan
EAX nol serta EIP/ESP melewati call. Runtime sebelumnya menyimpan debug register
dalam WOW64_CONTEXT, tetapi tidak menguji alamatnya saat menerjemahkan instruksi.

## Perubahan runtime

- Daftar alamat yang pernah membutuhkan pemeriksaan berlaku untuk proses karena
  cache kode FEX dipakai bersama. Penambahan alamat menginvalidasi halaman terkait
  melalui mekanisme FEX yang juga membersihkan cache thread dan call/return.
- Instruksi pada alamat tersebut memiliki guard ARM64 sebelum instruksi guest.
  Guard membaca DR0–DR3 dan enable mask milik thread yang sedang berjalan.
  L/G enable serta RW/LEN diperiksa; data/I/O watchpoint tidak diubah menjadi
  breakpoint eksekusi. Dukungan data/I/O watchpoint belum ditambahkan.
- Guard mempertahankan register guest dan NZCV, menyimpan guest EIP tepat pada
  instruksi yang belum dijalankan, lalu memakai jalur exception FEX/Wine yang ada.
  DR6 merekam slot yang terkena; GD dibersihkan. Handler game tetap asli.
- Alamat resume dengan RF juga mendapat guard agar RF melewati pemeriksaan
  breakpoint sekali pada instruksi pertama yang dilanjutkan. Pemeriksaan ini
  tidak mengaktifkan single-step global. Detail arsitektur mengacu pada
  [Intel SDM Volume 3B, bagian debug exceptions](https://cdrdv2-public.intel.com/858456/253669-088-sdm-vol-3b.pdf).
- Optimizer flag diberi tahu bahwa guard membaca semua flag. Cache kode di disk
  tidak dipakai setelah alamat debug terdaftar, agar kode tanpa guard tidak
  dimuat kembali. Instruksi lainnya tidak mendapat perbandingan DR saat runtime.
- Profil Fastest, x87, TSO, SMC, cache awal 128 MiB, dan pengalokasian cache
  sesuai kebutuhan dipertahankan. Prime spare tetap fungsi kosong seperti patch
  sebelumnya. ABI impor/ekspor DLL dan header bridge host tidak berubah.

Perubahan umum berada dalam runtime emulator; tidak ada alamat game di logika
patch, perubahan HKShip.exe, penggantian hasil pemeriksaan game, atau DLL game.

## Build dan validasi

`tools/build_fex_debug.py` menyalin FEX commit
`e2f973fe931e6dc2ce523795e51ca1ac3ca85816`, memverifikasi overlay approved terhadap
manifest rilis PES13, lalu menerapkan patch di direktori Sleeping Dogs sendiri.
`--refresh` hanya boleh menimpa file patch yang hash-nya masih cocok dengan
receipt build sebelumnya. Proyek asal PES13/F1 tidak diedit.

Pengujian yang dijalankan:

- 257 kombinasi decode DR7 dan pemeriksaan context/registry sebenarnya dengan
  ASan/UBSan, termasuk dua thread mendaftarkan alamat bersamaan, invalidasi hanya
  untuk alamat baru, enable/disable, RF, dan pembaruan DR6.
- 185 skenario pada keluaran emitter ARM64 yang sama: hit/non-hit, semua slot,
  enable mask, alamat baru, RF, state thread berbeda, register/flag, metadata
  exception, serta pemulihan stack spill hanya pada jalur trap.
- 67 skenario tambahan pada kode ARM64 yang dikeluarkan **fungsi emitter dalam
  DLL hasil build sebenarnya**. Batas allocator, memcpy, dan write-alias di-mock;
  logika emitter dan guard dieksekusi oleh Unicorn. Offset class/frame diperiksa
  dengan compiler ARM64 produksi. Impor/ekspor cocok dengan DLL sebelumnya.
- Delapan skenario dengan kode call site dan VEH x86 asli. Kasus negatif memakai
  return nonzero yang terlihat pada log (bukan menjalankan seluruh fungsi checker);
  kasus positif menjalankan handler asli dan menjaga stack. EXE dibaca saja.

Perintah: `tests/build_fex_debug_check.py` di WSL, kemudian
`tests/check_fex_debug_binary.py` dan `tests/check_game_debug_exception.py`
dengan Python yang menyediakan pefile, capstone, dan Unicorn.
Receipt/report disimpan dalam `dist/fex-debug-fix/` dan `reports/fex-debug-*.json`.

Ini membuktikan jalur exception yang sebelumnya hilang serta integritas paket.
Pengujian host belum membuktikan seluruh startup, rendering, atau gameplay di Switch.
