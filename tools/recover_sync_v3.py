"""Recover the exact v3 NRO from preserved ELF and pinned v4 launcher assets."""
from pathlib import Path
import json
import zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import PREFIX, archive, encode

V4_SHA = '396877ad3697e0a11bb6d575af3da967b55cb07b05a9b187f0216afc13b13278'
V3_SHA = '12820073773794f1cf9659695291cedcc12efcf65259efdd81d8f64d756af750'


def main():
    base = ROOT / 'dist/sleepingdogs-fex-low-window-sync-watch.zip'
    assert sha(base) == V4_SHA
    nro = ROOT / 'dist/low-window-v3-recovery/sleepingdogs-fex.nro'
    assert sha(nro) == V3_SHA, 'elf2nro must reconstruct the exact released v3 NRO'
    with zipfile.ZipFile(base) as z:
        entries = {name: z.read(name) for name in z.namelist() if name.startswith(PREFIX)}
    entries[PREFIX + nro.name] = nro.read_bytes()
    entries[PREFIX + 'launcher/fex-mode.txt'] = b'fastest\n'
    for name, payload in list(entries.items()):
        if not name.endswith('.json'):
            continue
        receipt = json.loads(payload)
        if 'nro_sha256' in receipt:
            receipt['nro_sha256'] = V3_SHA
            receipt['additional_overlay'] = 'sleepingdogs-low-window-v3-recovered'
            if 'profile' in receipt:
                receipt['profile'] = 'fastest'
            entries[name] = encode(receipt)
    entries[PREFIX + 'launcher/sync-watch.json'] = encode({
        'rolled_back': True, 'nro_sha256': V3_SHA, 'profile': 'fastest',
        'build': 'sleepingdogs-low-window-v3-loading-watch'})
    entries['README.txt'] = (
        'Pemulihan NRO v3 yang sebelumnya dapat mencapai menu, profil Fastest.\n'
        'Tutup aplikasi dari HOME, lalu timpa folder switch/ ke root SD.\n'
        'Tidak perlu memasang NSP atau reboot jika kernel low-window masih aktif.\n'
        'Ini rollback startup; freeze saat menuju 3D belum diperbaiki.\n'
        'NRO dipulihkan dari ELF tersimpan dan cocok persis dengan SHA256 rilis v3.\n'
    ).encode()
    result = archive(ROOT / 'dist/sleepingdogs-fex-low-window-v3-recovery.zip', entries)
    write_json(ROOT / 'reports/low-window-v3-recovery.json', {
        'status': 'PASS', 'package': result, 'nro_sha256': V3_SHA,
        'reconstructed_byte_identical': True, 'source_package_sha256': V4_SHA})
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
