# Sleeping Dogs FEXTendo v12 — uji penggabungan submit DXVK

Paket uji ini mempertahankan NRO v11 dan memasang DXVK `3.1.1-sdbatch1`.
Target tetap **1280×720**. Perubahan membatasi submit otomatis kecil saat
antrean GPU masih memiliki minimal dua submission yang belum selesai.
Peningkatan FPS belum diukur di Switch; ini belum menjamin 30 FPS.

## Memasang

1. Tutup game/FEXTendo sepenuhnya dari HOME.
2. Ekstrak **seluruh folder `switch`** dari ZIP ke root SD, timpa file update.
   Salin DLL di folder launcher dan `drive_c` bersama-sama.
3. Pilih **DXVK 3.1.1 → Performance → Launch GUI**, resolusi 720p.
   HUD Off/FPS/Full tetap tersedia. Tidak perlu memasang ulang forwarder.
4. Pakai CPU **1728**, GPU **768**, RAM **1600 MHz** sepanjang perbandingan.
   Paket tidak mengubah clock.

Ini update untuk instalasi yang sudah berhasil memakai v11, bukan installer
game lengkap. NRO masih menampilkan versi v11; penanda perubahan renderer
di log adalah `DXVK: 3.1.1-sdbatch1` dan `[SD-DXVK-BATCH] v1 enabled=1`.

## Membandingkan On/Off

Mainkan rute yang sama sekitar dua menit di 720p. Simpan `fex-runtime.log`
sebelum menjalankan sesi berikutnya. Untuk perbandingan, tutup game lalu
ubah satu baris dalam file berikut di SD:

`switch/sleepingdogs-fex/launcher/presets/performance/dxvk-3.1.1/dxvk.conf`

```ini
d3d11.sdSubmissionBatching = False
```

Jalankan kembali Performance pada lokasi dan arah kamera yang sama.
`True` mengaktifkan lagi. Opsi yang hilang atau tidak valid mengikuti
default Off. Mode ini hanya aktif pada driver NVK dan tidak berlaku pada
renderer 2.7.1-async. Counter tetap dicatat pada On dan Off agar dapat dibandingkan.

Paket rollback `sleepingdogs-fex-low-window-submit-batching-rollback.zip`
mengembalikan DLL `sdrecycle1` dan preset Performance v11. Tutup aplikasi,
ekstrak seluruh folder `switch`, lalu timpa. ZIP v11 saja tidak mengganti
DLL renderer, sehingga gunakan rollback ini untuk pembatalan penuh.

## Dasar perubahan

Log pengguna SHA-256 `d00be9c4bb287a9365b4339a39b20cc1977a1f88b5aa27dcd32e51fb43f65de7`
memuat capture 30 detik pada 720p: 463 interval Present, rata-rata
64,63 ms (15,47 FPS), 3.478 pemanggilan submit Vulkan, sekitar 7,51 per
interval Present. Thread submit memakai 0,2495 detik CPU dan 6,4214 detik
waktu dinding di pemanggilan submit. Angka waktu dinding termasuk penantian;
bukan biaya yang pasti dapat dihilangkan atau waktu eksekusi GPU.

Game kemudian benar-benar beralih ke 960×540. Empat jendela sesudah transisi
masih 11,53–14,16 FPS. Adegan/kamera tidak terkonfirmasi sama, dan capture
per-thread sudah selesai sebelum pergantian resolusi. Karena itu data ini
belum menjadi perbandingan resolusi yang terkontrol.

GPU 99% dan RAM sekitar 6 GB/s berasal dari Status Monitor/Tesla menurut
pengguna. GB/s menunjukkan lalu lintas memori, bukan kapasitas RAM yang
terpakai. Angka tersebut tidak dicatat oleh log dan belum membuktikan
bandwidth maksimum atau satu penyebab tunggal. CPU yang tidak penuh juga
bisa berarti thread sedang menunggu dependensi.

## Batas implementasi

- Hanya hint otomatis kecil yang ditunda: kurang dari 12 chunk, minimal
  dua submission belum selesai, dan biaya perkiraan di bawah batas asli.
- Saat antrean menyusut, batch mencapai batas, atau ada sinkronisasi
  readback, keputusan asli kembali dipakai. Flush eksplisit, Present,
  Map/readback, pagar memori, shader, dan batas alokasi tetap mengikuti
  jalur sebelumnya.
- Satu log agregat per 256 flush konteks mencatat explicit/sync/strong/weak
  dan `deferred_hints`. Counter terakhir menghitung permintaan hint yang
  ditunda, **bukan** jumlah submit yang berhasil dihilangkan. Bandingkan
  jumlah submit per frame dan FPS pada adegan yang sama.
- Jika game kebanyakan melakukan flush wajib, manfaat mode ini dapat kecil
  atau nol. Batch lebih besar juga dapat mengubah latency/pacing; gunakan
  Off atau rollback bila pengalaman memburuk.

Model heuristik berasal dari [DXVK pada commit yang dipakai](https://github.com/doitsujin/dxvk/blob/b1a1c99ab52b687cf950d62c88bc2fa316b41663/src/util/util_flush.cpp).
Driver Switch melakukan pekerjaan cache pada batas submit; lihat
[implementasi GM20B yang diperiksa](https://github.com/danfromtico/mesa-switch/blob/b297e230ef88c6c88df2561becf864f979f494a6/src/nouveau/horizon/nouveau_horizon_gm20b.c).
Mengurangi batas submit yang tidak wajib merupakan hipotesis optimasi,
bukan bukti bahwa seluruh waktu frame berasal dari driver.

## Validasi dan asal source

Uji host ASan/UBSan membandingkan tracker produksi dengan versi lama,
termasuk mode Off, progres readback, batas batching, dan wraparound ID.
Uji PE32 menjalankan fungsi tracker dari DLL yang dikemas. Launcher C v11
diuji agar opsi bertahan ketika preset dan HUD diterapkan dan DLL lama
diganti. Hash, interface DLL, dan isi ZIP diperiksa. Semua ini belum
menggantikan pengujian gameplay/performa pada perangkat.

Port FEXTendo Switch tetap berasal dari AndroSwitch Project / Ibnuard,
berbasis pes13-fex proyek ini dan engine FEX-Emu. DXVK adalah karya
kontributor DXVK; modifikasi `sdbatch1` dibatasi pada eksperimen ini.
Source yang berubah, source dasar, lisensi, receipt, dan laporan pengujian
tersedia di `source/dxvk-submit-batching/` dalam ZIP. SDK bersama tidak diubah.
