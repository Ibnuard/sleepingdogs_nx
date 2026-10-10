"""Identify a supplied v14 NRO and stage the already-tested v14.1 delta."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile
from port_common import ROOT,sha,write_json

OLD='e35c1a35e170b8e532895f5fee8daadc78d281e7cca3ab84123c1768160324c5'
NEW='69021fdc43afcef9aed9713e50f5bb5a1a5e8865f3e842bab9fb636cb5d39f71'
ZIP14='e9c51827334ba1d1fdbac0aed9bba61a30fea5c258eb78037b76e77329e8a11e'
ZIP141='aef7051cd368e806260163afead4925be8b27c290ae6c99a83ee84d4cf3ed5bf'
PREFIX='switch/sleepingdogs-fex/'
NRO=PREFIX+'sleepingdogs-fex.nro'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('nro',type=Path)
    args=parser.parse_args()
    supplied=args.nro.read_bytes();assert hashlib.sha256(supplied).hexdigest()==OLD
    previous=ROOT/'dist/sleepingdogs-fex-low-window-gm20b-shaders.zip'
    corrected=ROOT/'dist/sleepingdogs-fex-low-window-gm20b-cache-fix.zip'
    assert sha(previous)==ZIP14 and sha(corrected)==ZIP141
    with zipfile.ZipFile(previous) as z:
        before={n:z.read(n) for n in z.namelist() if n.startswith(PREFIX)}
    with zipfile.ZipFile(corrected) as z:
        after={n:z.read(n) for n in z.namelist() if n.startswith(PREFIX)}
        sources={n:z.read(n) for n in z.namelist() if n.startswith('source/')}
    assert supplied==before[NRO]
    assert hashlib.sha256(after[NRO]).hexdigest()==NEW
    assert b'[SD-NVK-V14.1]' not in supplied and b'[SD-NVK-V14.1]' in after[NRO]
    changed={n:d for n,d in after.items() if before.get(n)!=d}
    assert set(before)<=set(after)
    assert all(n==NRO or n.startswith(PREFIX+'launcher/') and n.endswith('.json') for n in changed)
    overlay=dict(before);overlay.update(changed);assert overlay==after
    entries={**sources,**changed}
    entries['README-PASANG.txt']='''Sleeping Dogs FEXTendo v14.1 — UPDATE DARI v14

Ini NRO v14.1 yang sudah dibangun dan diuji sebelumnya, bukan optimasi baru.
NRO yang dikirim untuk pemeriksaan cocok persis dengan v14 lama.

1. Tutup FEXTendo sepenuhnya dari HOME.
2. Ekstrak folder switch dari ZIP ini ke ROOT SD, lalu pilih timpa/replace.
   Tujuan akhirnya: SD:/switch/sleepingdogs-fex/sleepingdogs-fex.nro
   Jangan menaruh folder switch di dalam folder switch yang sudah ada.
3. Tetap gunakan DXVK 3.1.1, Performance, Launch GUI, 1280x720, clock yang sama.
4. Log baru harus memuat [SD-NVK-V14.1] instance/disk cache_id=1e3909c6aaf647614822cc8a3ee58d9e99a9e3e1
5. Mainkan rute sekali untuk pemanasan shader. Simpan log pertama, buka ulang,
   lalu ukur rute yang sama. Cache baru dapat membuat sesi pertama tersendat.

SHA-256 NRO v14.1:
69021fdc43afcef9aed9713e50f5bb5a1a5e8865f3e842bab9fb636cb5d39f71
SHA-256 NRO v14 lama yang diperiksa:
e35c1a35e170b8e532895f5fee8daadc78d281e7cca3ab84123c1768160324c5

Kedua file berukuran sama; nama, ukuran, dan tanggal file tidak membuktikan versi.
Update hanya memuat NRO dan metadata launcher yang berubah. DLL, game, save,
pilihan launcher, dan cache lama tidak diubah. Source disertakan sebagai arsip.
Target 30 FPS belum terbukti di perangkat. Detail koreksi berada di:
source/low-window-gm20b-cache-fix/docs/low-window-gm20b-cache-fix.md
'''.encode('utf-8')
    entries['source/v141-update/tools/prepare_v141_nro_update.py']=Path(__file__).read_bytes()
    entries['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(d).hexdigest()}  {n}\n'
        for n,d in sorted(entries.items())).encode()
    target=ROOT/'dist/sleepingdogs-fex-v14.1-update.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for n,d in sorted(entries.items()):z.writestr(n,d)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None and z.read(NRO)==after[NRO]
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            h,n=line.split('  ',1);assert hashlib.sha256(z.read(n)).hexdigest()==h
    assert sha(args.nro)==OLD and sha(previous)==ZIP14 and sha(corrected)==ZIP141
    report=dict(status='VERIFIED',supplied_path=str(args.nro.resolve()),supplied_sha256=OLD,
        supplied_bytes=len(supplied),identified_build='v14',byte_identical_to_original_v14=True,
        marker_v141_in_supplied=False,expected_v141_sha256=NEW,marker_v141_in_replacement=True,
        supplied_file_unchanged=True,original_packages_unchanged=True,new_runtime_build=False,
        overlay_matches_previously_verified_v141=True,changed_runtime_paths=sorted(changed),
        output=dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size),
        script_sha256=sha(Path(__file__)),hardware_performance_of_v141_still_unmeasured=True)
    write_json(ROOT/'reports/deployed-nro-e35c1a35e170.json',report)
    print(json.dumps({k:report[k] for k in ('identified_build','supplied_sha256','expected_v141_sha256','output')},indent=2))


if __name__=='__main__':main()
