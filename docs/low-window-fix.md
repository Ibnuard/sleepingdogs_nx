# Sleeping Dogs: low-window v1

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

**Koreksi startup:** NSP v1 di ZIP ini telah dilaporkan crash langsung dari HOME.
Bug allocator forwarder berhasil direproduksi dari binary. Setelah menyalin
paket basis, instal NSP **StartupFix** dari
`sleepingdogs-fex-low-window-startup-fix.zip` sebagai penggantinya.
Lihat [perbaikan startup](low-window-startup-fix.md). ZIP basis asli dipertahankan
untuk riwayat dan pemeriksaan; jangan memakai NSP v1 untuk pengujian berikutnya.

Paket uji ini khusus HOS 22.5.0, Atmosphère 1.11.2 dan Horizon-OC 2.5.1, sesuai file boot yang diberikan. Pengujian di PC sudah dilakukan; keberhasilan boot/loading 3D dengan NSP yang diperbaiki di Switch belum dikonfirmasi.

## Instalasi

1. Simpan `sleepingdogs-fex-low-window-rollback.zip` di PC. Tutup game sepenuhnya.
2. Salin folder `atmosphere`, `bootloader`, dan `switch` dari ZIP update ke root SD, gabungkan dengan folder yang ada. Ini update untuk instalasi Sleeping Dogs FEXTendo yang sudah ada; file game tidak disertakan.
3. Instal `forwarder/FEXTendo-SleepingDogs-39bit-LowWindow-StartupFix.nsp` dari ZIP perbaikan startup sebagai pengganti forwarder Sleeping Dogs lama. Title ID tetap `059a3db219b42000`. Mengganti NRO saja belum cukup.
4. Reboot ke Hekate. Pilih **More configs → CFW EMUMMC SD Low Window**.
5. Jalankan Sleeping Dogs dari ikon HOME tersebut, lalu coba New Game. Profil FEX tetap **Fastest**; pengaturan pengguna, EXE game, DLL game, save, FEX DLL, dan DXVK tidak diganti oleh perubahan low-window ini.

`bootloader/hekate_ipl.ini`, `atmosphere/package3`, `atmosphere/exosphere.bin` dan `atmosphere/kips/hoc.kip` yang ada tetap dipakai/tersimpan di tempat semula. Entry baru memakai kernel dan loader HOC di `atmosphere/sleepingdogs-low-window/`. Konfigurasi CUST dari HOC pengguna disalin persis setelah kode di luar konfigurasi dicocokkan dengan rilis 2.5.1.

## Apa yang berubah

- Kernel dan loader AMS 1.11.2 memakai patch low-window AutorunHQ dengan whitelist tambahan khusus Title ID Sleeping Dogs. Whitelist Autorun asli tetap ada. Perubahan tata letak berlaku di cabang proses 39-bit; title lain memakai aturan sebelumnya.
- Forwarder meminta ruang alamat 39-bit dan 16 MiB system resource. Native Wine/FEX/Mesa/libnx memakai alamat di atas 4 GiB. Pemeriksaan awal menguji kode RX pada `0x00400000` dan alias RW/NONE/RW pada `0xffff0000`, memeriksa quota lebih dari 2 GiB, dan menolak peluncuran jika persyaratan tidak terpenuhi.
- Arena data game 1000 MiB berada di `0x30000000–0x6e800000` (ujung eksklusif), dipetakan dari satu backing heap di atas 4 GiB. Guard Wine dipasang sebelum alokasi guest. Backing yang masih dimiliki kernel tidak dibebaskan jika unmap gagal.

Alamat virtual 39-bit bukan tambahan RAM fisik. Ini menghilangkan batas proses 2 GiB dari mode 32-bit no-alias. Pada Switch 4 GiB, sebagian RAM tetap dipakai sistem; seluruh 4 GiB tidak tersedia sebagai heap game. Kebutuhan VRAM minimum PC 512 MiB tidak mencakup Wine, FEX, cache JIT, data game, dan driver yang memakai RAM Switch yang sama.

## Log yang dibutuhkan

Sesudah mencoba, periksa `switch/sleepingdogs-fex/fex-runtime.log`:

```
[SD-LOWVA] v1 host=200000+7fffe00000 quota=... title=059a3db219b42000
[SD-LOWVA] RX execute low=400000 PASS
[SD-LOWVA] RW/NONE/RW alias low=ffff0000 PASS
[SD-LOWVA] PASS: native above 4 GiB; guest low window available
[SD-ALIAS] v1 requested=1048576000 reserved=1048576000 low=0x30000000 high=...
```

Jika gagal, kirim log lengkap dan `crash.log` bila ada. Baris `quota` menunjukkan batas RAM aktual dari kernel. Launcher menampilkan penolakan terarah jika entry/forwarder tidak cocok atau arena gagal, sebelum EXE game dimuat.

## Rollback

1. Salin folder `switch` dari ZIP rollback ke root SD, gabungkan/timpa file runtime yang sama.
2. Instal ulang `forwarder/FEXTendo-SleepingDogs-32bit.nsp` dari ZIP rollback.
3. Reboot Hekate lalu pilih entry **CFW (EMUMMC)** yang lama. Entry ini tetap menunjuk ke kernel `package3` dan HOC lama. Jangan pilih entry low-window saat memakai runtime/forwarder rollback.

Tidak perlu menghapus atau mengganti game maupun save. Salinan INI dan HOC asli juga disimpan di folder `backup-input` dalam ZIP rollback untuk referensi, bukan untuk disalin otomatis.

## Sumber dan pemeriksaan

- [AutorunHQ, revisi cbb0e4e](https://github.com/autorunhq/autorun/tree/cbb0e4e6e7fa7f47f328d92441f51bfb507f266f/horizon-wine/mesosphere)
- [Atmosphère 1.11.2](https://github.com/Atmosphere-NX/Atmosphere/releases/tag/1.11.2)
- [Horizon-OC 2.5.1](https://github.com/Horizon-OC/Horizon-OC/releases/tag/2.5.1)
- [Konfigurasi Hekate: More configs, kernel dan kip1](https://github.com/CTCaer/hekate/blob/master/README.md#bootloader-configuration)

Receipt build, perubahan source, hasil uji, dan SHA-256 disertakan dalam paket. Uji host menjalankan proteksi/alias Linux dengan backing bersama, dan Unicorn menjalankan instruksi ARM64 dari ELF runtime sambil memodelkan SVC. Keduanya tidak menggantikan pengujian kernel, GPU, atau boot pada Switch.
