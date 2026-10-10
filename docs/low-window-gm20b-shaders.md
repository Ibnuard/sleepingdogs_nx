# Sleeping Dogs FEXTendo v14 — kesempatan uji 2 dari 2

Target tetap **720p, 30 FPS gameplay**. v14 mengubah compiler shader GM20B di atas driver v13 yang sudah berhasil dipakai. **Belum ada pengukuran FPS v14 pada Switch.** Pengujian host dan binary tidak membuktikan target 30 FPS tercapai.

## Memasang

1. Tutup game/FEXTendo sepenuhnya dari HOME.
2. Ekstrak seluruh folder `switch` dari `sleepingdogs-fex-low-window-gm20b-shaders.zip` ke root SD dan timpa.
3. Gunakan **DXVK 3.1.1 → Performance → Launch GUI**, resolusi **1280×720**. HUD Off/FPS/Full tetap tersedia; forwarder tidak perlu dipasang ulang.
4. Untuk pembanding, gunakan clock sebelumnya: CPU **1728**, GPU **768**, RAM **1600 MHz**. Paket tidak mengubah clock.
5. Lewati loading, jalankan rute yang sama sekali untuk pemanasan shader, lalu ukur ulang 2–3 menit di rute itu. Saat membandingkan FPS diam, gunakan posisi dan arah kamera yang sama. Simpan `fex-runtime.log` sebelum sesi berikutnya.

Identitas baru di log: **`[SD-NVK-V14] shader compiler SM53`**. Banner runtime lama masih menyebut v11; angka versi Vulkan yang ditampilkan DXVK masih dapat berupa `26.2.2`. Receipt paket memuat versi lengkap `26.2.2-sdv14-shader` dan build ID. Identitas cache shader GPU diubah, sehingga shader lama tidak digunakan sebagai hasil compiler baru. Cache DXVK/SPIR-V masih dapat digunakan. Pemanasan pertama bisa tersendat.

Untuk kembali ke hasil v13 yang sudah kamu tes, tutup aplikasi dan ekstrak `sleepingdogs-fex-low-window-gm20b-shaders-rollback.zip` ke root SD, lalu timpa. Paket tidak memuat game atau save.

## Bukti dari log terbaru

Log `SS/08/fex-runtime.log`, SHA-256 `1fdd9558041bc2f70edf802d620e01330c21c34534c48554591b29a11f06fdea`, telah disimpan tanpa perubahan.

| Pengukuran | Hasil |
|---|---:|
| Resolusi dalam log | 1280×720 |
| Capture 30 detik | 17,29 FPS / 57,85 ms per interval present |
| Tujuh jendela terakhir | 17,24 FPS berbobot waktu |
| Rentang tujuh jendela terakhir | 15,51–19,76 FPS |
| Pemanggilan submit / interval present dalam capture | 6,47 |
| Total waktu di pemanggilan submit selama capture | 0,857 detik |
| Kompilasi kode FEX setelah detik 200 | 0,447 detik selama 170,188 detik |

Laporan pengguna 17–20 FPS konsisten dengan beberapa bagian log, tetapi tidak berarti stabil sepanjang sesi. Target 30 FPS memerlukan sekitar 33,3 ms per frame; capture sekarang masih sekitar 57,8 ms. Angka compile/submit adalah waktu dinding panggilan yang dapat tumpang tindih antar-thread, bukan durasi render GPU yang boleh langsung dikurangkan dari frame time.

Tipe memori `DEVICE_LOCAL` tanpa `HOST_VISIBLE` memastikan kebijakan memori v13 terpasang. Tidak ada marker ZCULL di log tersebut: jalur stderr Mesa tidak masuk ke file ini. Karena itu **penggunaan ZCULL v13 belum dapat dikonfirmasi dari log**, meski kode dan tipe memorinya sudah terpasang. v14 mengirim marker satu kali per mode melalui fungsi trace runtime yang memang dipakai log, tanpa menulis setiap draw.

Perbandingan v12 dan v13 bukan benchmark berpasangan: adegan, posisi kamera, pemanasan cache, dan clock sesi terakhir belum dikonfirmasi identik. Tidak dihitung persentase kenaikan kausal dari kedua log.

## Perubahan v14

- **Penjadwalan shader SM53:** perkiraan latensi untuk pembacaan tekstur dan global load menjadi 200 siklus, agar compiler mencoba memisahkan pembacaan dari pemakaiannya. Ini hanya prioritas penjadwalan; scoreboard, barrier, batas register, shared/local memory, interpolasi, dan store memakai aturan sebelumnya. Nilai 200 adalah hipotesis optimasi, bukan hasil pengukuran latensi pada perangkat pengguna.
- **Percabangan kecil:** NIR boleh meratakan cabang ALU kecil hingga batas 8 pada SM53. Cabang besar, efek samping, dan akses yang tidak aman untuk dieksekusi spekulatif tetap mengikuti pengaman pass NIR. Ada risiko penggunaan register meningkat; keberhasilan pengujian host belum menentukan dampaknya pada shader Sleeping Dogs.
- **Koreksi FADD32I:** saturasi/clamp pada penjumlahan float dengan konstanta 32-bit tidak boleh hilang. Compiler memindahkan konstanta ke register saat bentuk immediate tidak dapat menyatakan saturasi. Ini perbaikan kebenaran gambar, bukan klaim penambahan FPS.
- **Diagnostik terbatas:** identitas driver, ZCULL sekali per mode, dan maksimal 16 sampel shader (jumlah register, local memory, ukuran kode) melalui trace FEXTendo. Sampel tidak mencakup semua shader dan bukan pengukuran GPU.

Basis v13, seluruh objek Wine/FEX, DXVK batching, allocator, dan preset grafis tetap digunakan. Source SDK bersama tidak diubah. Integrasi FEXTendo tetap port milik AndroSwitch Project / Ibnuard dari pes13-fex dengan engine FEX-Emu.

## Sumber dan pilihan yang tidak diterapkan

Ide compiler dibandingkan dengan [patch Mesa port NFSMW](https://github.com/StevensND/nfsmw-nx/blob/4e3ffc24fe80285189f2cea601606c529d5f1b97/mesa/mesa-switch-nfsmw.patch) dan [penjelasan penulis port](https://github.com/StevensND/nfsmw-nx/blob/4e3ffc24fe80285189f2cea601606c529d5f1b97/docs/mesa.md). Patch referensi disimpan dengan SHA-256 `b19a2010d1bb070b99f7c87b6da7ab61a267f40e8c4bee2c00d73b7189271d24`. Hasil game berbeda tidak dianggap jaminan hasil Sleeping Dogs.

Adaptasi ini sengaja lebih sempit: estimasi memori tidak dinaikkan untuk semua instruksi variabel dan arsitektur; hanya pembacaan tekstur/global pada SM53. Promosi UBO push-descriptor sudah ada pada basis kita. Pengalihan semua copy ke copy engine tidak dipilih karena penulis referensi sendiri mendokumentasikan hasil yang lebih lambat. Tidak melepas penggunaan TRANSFER_DST atau pengaman ZCULL: DXVK memang membuat resource dengan penggunaan transfer dan dapat memakainya. Tidak mengganti Wine/DXVK hanya berdasarkan nomor versi atau angka FPS game lain. Riset versi DXVK/Autorun sebelumnya tercatat di `docs/v13-dxvk-research.md`.

## Validasi dan batasannya

- Builder membandingkan setiap modul Rust yang disalin dengan manifest source v13 dan setiap dependency C yang terpakai; library driver lain tetap byte-identical.
- Semua dependency Rust, stdlib, binding, dan allocation shim dibandingkan byte-per-byte. ABI C NAK, wrapper allocator FEXTendo, dan toolchain Rust 1.93.1 dipertahankan.
- Test mengeksekusi fungsi keputusan penjadwalan dan legalisasi/encoding FADD dari source produksi dengan adapter operand. Ini **bukan** pengujian seluruh compiler Rust atau eksekusi shader pada GPU.
- Test NIR memakai pass Mesa asli untuk cabang ALU kecil, batas ukuran, efek samping, dan pembatasan arsitektur; harness memakai ASan/UBSan.
- Sebelum relink kandidat, command link v13 harus mereproduksi ELF v13 yang sama persis. Objek NAK baru dimasukkan eksplisit agar archive GL/EGL tidak mengambil compiler lama.
- Regression binary ARM64 memeriksa jalur diagnostic, direct sync, alokasi low-VA, dan wrapper NAK/allocator yang diwarisi. ZIP memverifikasi CRC, semua hash entry, dan simulasi rollback ke runtime v13.

Manifest, source perubahan, source baseline, patch, laporan pengujian, dan skrip build disertakan di folder `source`. Verifikasi render, kestabilan, FPS, serta slow motion tetap memerlukan pengujian perangkat. Jika hasil tidak membaik atau muncul rendering salah, gunakan rollback v13.
