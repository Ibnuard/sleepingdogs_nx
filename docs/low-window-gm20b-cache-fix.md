# Sleeping Dogs FEXTendo v14.1 — koreksi cache v14

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

Target tetap 720p. Log terbaru sesuai laporan gameplay sekitar 15–17 FPS, dengan peak 24 FPS yang dilihat pengguna. Ada kesalahan pada build v14: identitas cache pipeline berubah, tetapi objek pembuat Vulkan instance masih menggunakan ID v13 untuk cache disk Mesa. Ini kesalahan integrasi build kami; klaim pada dokumen v14 bahwa seluruh cache shader GPU sudah terpisah ternyata tidak benar.

v14.1 memperbaiki build tersebut. **Belum ada pengukuran FPS v14.1 pada Switch, dan 30 FPS belum tercapai dalam bukti yang tersedia.** Ini koreksi kesempatan uji kedua, tanpa perubahan tambahan pada kebijakan optimasi shader.

## Memasang dan menguji

1. Tutup game/FEXTendo sepenuhnya dari HOME.
2. Ekstrak seluruh folder `switch` dari `sleepingdogs-fex-low-window-gm20b-cache-fix.zip` ke root SD dan timpa.
3. Gunakan **DXVK 3.1.1 → Performance → Launch GUI → 1280×720**. HUD Off/FPS/Full tetap tersedia. Gunakan clock yang sama selama perbandingan; acuan sebelumnya CPU 1728, GPU 768, RAM 1600 MHz.
4. Mainkan rute yang biasanya berat sekali untuk pemanasan cache. Kompilasi shader pertama dapat menimbulkan stutter. Simpan log sesi ini sebelum menjalankan sesi berikutnya.
5. Tutup sepenuhnya, buka lagi, lalu uji rute yang sama selama 2–3 menit. Untuk pengukuran sambil diam, gunakan posisi serta arah kamera yang sama. Simpan log sesi kedua untuk menilai FPS setelah cache terisi.

Marker baru yang harus muncul:

```text
[SD-NVK-V14.1] instance/disk cache_id=1e3909c6aaf647614822cc8a3ee58d9e99a9e3e1; matches v14.1 pipeline identity
```

Marker `[SD-NVK-V14] shader compiler SM53` tetap benar karena compiler sama dengan v14. Banner runtime v11 juga tetap berasal dari objek Wine/FEX yang tidak diubah. Saat cache baru masih kosong, log diharapkan mencatat cache miss, penghitung kompilasi NAK bertambah, dan sampel `[SD-NVK-V14] shader=...`. Pada sesi yang sudah hangat, cache hit dan minim kompilasi justru normal. Marker versi saja tidak membuktikan shader baru telah dikompilasi.

Cache lama tidak perlu dihapus; build baru memakai namespace berbeda. Cache IR DXVK boleh tetap digunakan, sebab bukan hasil kode mesin GPU NAK. Paket tidak memuat game/save dan tidak mengubah clock.

Rollback yang disertakan, `sleepingdogs-fex-low-window-gm20b-cache-fix-rollback-v13.zip`, memulihkan runtime v13 beserta receipt-nya. Tutup aplikasi dan timpa folder `switch` untuk memakainya. Cache terpisah memungkinkan v13 kembali memakai cache lamanya.

## Temuan dari log v14

Input `FootballNX-Anfield-Test-v1/anfield-update/fex-runtime.log` berisi sesi Sleeping Dogs/HKShip. Salinan asli disimpan dengan SHA-256 `efbe9428c2adddca87b2d1d111bd1d47c585f30879287ab000d8c6a61138057d`.

| Pengukuran | Hasil |
|---|---:|
| Resolusi tercatat | 1280×720 |
| Capture 30 detik | 17,05 FPS / 58,66 ms per interval present |
| Bagian akhir di bawah 30 FPS, tanpa jendela transisi pertama | 15,31 FPS berbobot waktu |
| Tujuh jendela terakhir | 14,69 FPS berbobot waktu |
| Cache disk driver | 2.484 hit, 0 miss |
| Penghitung selesai kompilasi NAK | 0 |
| Sampel shader baru / marker ZCULL aktif | 0 / 0 |

Peak sesaat 24 FPS tidak dapat dipastikan dari rata-rata jendela 10 detik. Adegan, kamera, dan clock belum dikonfirmasi identik dengan tes sebelumnya, sehingga tidak dihitung persentase peningkatan kausal.

Semua cache hit dan tidak adanya kompilasi sesuai dengan penggunaan ulang shader lama, tetapi log tidak menyimpan tanggal atau isi setiap file cache. Bukti cacat build diperoleh langsung dari source dan eksekusi kode ARM64: disk cache v14 memakai ID v13, sedangkan pipeline memakai ID v14.

Sekitar 6,61 submit per interval present tidak berarti biaya 6,61 frame. Waktu panggilan submit hanya sekitar 0,604 detik dalam capture 30 detik. Wait semaphore dapat tumpang tindih dengan GPU/thread lain dan bukan waktu GPU yang bisa langsung dikurangkan. Kompilasi FEX setelah detik 200 sekitar 1,77 detik selama 145,18 detik, bukan bukti penyebab seluruh keterlambatan. Data ini belum membuktikan bottleneck tunggal CPU/GPU. Tidak ada marker ZCULL aktif, sehingga fitur tersebut belum dikonfirmasi bekerja pada sesi ini.

## Perbaikan dan pemeriksaan

`nvk_CreateInstance` menyimpan build ID di `driver_build_sha`. `nvk_physical_device_init_pipeline_cache` menggunakan nilai itu untuk timestamp/namespace `disk_cache_create`, sementara UUID pipeline menggunakan macro build ID di translation unit terpisah. Builder v14 sebelumnya hanya memperbarui yang kedua.

Builder v14.1 mengompilasi **kedua** translation unit dengan ID `1e3909c6aaf647614822cc8a3ee58d9e99a9e3e1` dan versi `26.2.2-sdv14.1-cache`. ID baru juga menolak cache pipeline v14 yang mungkin berisi shader hasil cache lama. Objek dimasukkan eksplisit sebelum archive agar linker tidak memilih salinan lama. Source physical device tetap sama persis dengan v14; source instance hanya menambah marker identitas. Seluruh 1.831 anggota archive driver lainnya, termasuk NAK/NIR, tetap byte-identical. Objek Wine/FEX, DLL DXVK, dan preset grafis dipertahankan.

Validasi:

- Link baseline mereproduksi ELF v14 yang identik sebelum kandidat dibangun; dependency sumber/header serta semua input native diperiksa hash-nya. SDK bersama tidak ditulis.
- Regression mengeksekusi fungsi ARM64 `nvk_CreateInstance` dan blok initializer cache physical device dari ELF asli. Alokasi, layanan Vulkan/DRI, compiler flags, serta disk I/O memakai fixture; konversi build ID, BLAKE3, dan format hex berjalan sebagai kode ARM64 asli. Kontrol v14 mendeteksi ID yang tidak cocok; v14.1 menghasilkan ID disk/pipeline yang cocok dan berbeda dari build sebelumnya.
- Pemeriksaan ARM64 yang diwarisi meliputi 5 kasus diagnostic, 22 kasus direct sync, 15 kasus low-VA/preflight, serta 4 kasus ABI wrapper NAK. Ini bukan pengujian GPU/render atau FPS.
- ZIP memeriksa CRC, SHA-256 setiap entry, preservasi runtime selain NRO/receipt, dan simulasi rollback ke v13. Source, patch, manifest build, dan laporan pengujian disertakan.

Aturan penjadwalan SM53, batas select NIR 8, dan koreksi FADD.SAT dari v14 tetap sama. Integrasi FEXTendo tetap port milik AndroSwitch Project / Ibnuard dari pes13-fex dengan engine FEX-Emu. Dampak FPS serta kebenaran render shader yang baru dikompilasi harus dinilai pada perangkat.
