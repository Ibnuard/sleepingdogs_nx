"""Finalize the local runtime ZIP with the matching verified HOME forwarder."""
from pathlib import Path
import json
import os
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import APPROVED, APP_ID, VERSION, sha, write_json


def main():
    output = ROOT / f'dist/{APP_ID}-{VERSION}-sd'
    report_path = output / 'build-report.json'
    report = json.loads(report_path.read_text())
    nro = output / 'switch' / APP_ID / f'{APP_ID}.nro'
    paired = b'[SD-GPU-BUDGET] v1 paired_loader=' in nro.read_bytes()
    forwarder = ROOT / ('dist/gpu-budget-fix/forwarder' if paired else 'dist/forwarder')
    receipt = json.loads((forwarder / 'build.json').read_text())
    if paired and receipt.get('loader_overlay') != 'sleepingdogs-gpu-budget-v1':
        raise RuntimeError('GPU budget NRO requires the updated paired loader')
    if receipt['nro_sha256'] != sha(nro) or not receipt['packed_payload_verified']:
        raise RuntimeError('Forwarder was built for a different NRO')
    if sha(forwarder / receipt['nsp']) != receipt['sha256']:
        raise RuntimeError('Forwarder changed after verification')
    shutil.copy2(forwarder / receipt['nsp'], output / receipt['nsp'])
    shutil.copytree(forwarder, output / 'forwarder', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('*.nsp'))
    shutil.copytree(ROOT / 'forwarder/hbl', output / 'forwarder/source/hbl', dirs_exist_ok=True)
    shutil.copy2(ROOT / 'forwarder/build_forwarder.py', output / 'forwarder/source/build_forwarder.py')
    if paired:
        for relative in ('src/sd_gpu_budget.h', 'tools/sleepingdogs_gpu_budget.py'):
            destination = output / 'forwarder/source' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
    shutil.copytree(APPROVED / 'licenses', output / 'licenses/approved-runtime', dirs_exist_ok=True)
    shutil.copy2(ROOT / 'README.md', output / 'README.md')
    report['forwarder'] = receipt
    report['files'] = {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob('*'))
                       if p.is_file() and p.name not in ('build-report.json', 'SHA256SUMS.txt')}
    write_json(report_path, report)
    files = [p for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS.txt']
    (output / 'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(output).as_posix()}\n' for p in files),
                                         encoding='utf-8', newline='\n')
    archive = output.with_name(output.name + '.zip')
    temporary = archive.with_name(archive.name + '.new')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(output.rglob('*')):
            if p.is_file() or not any(p.iterdir()):
                z.write(p, p.relative_to(output).as_posix())
    with zipfile.ZipFile(temporary) as z:
        if z.testzip() is not None:
            raise RuntimeError('ZIP CRC verification failed')
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest, name = line.split('  ', 1)
            import hashlib
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise RuntimeError(f'ZIP checksum mismatch: {name}')
        names = z.namelist()
        if any(name.lower().endswith(('.keys', '/hkship.exe', '.big', '.bix')) for name in names):
            raise RuntimeError('Game data or keyset leaked into the runtime-only archive')
    os.replace(temporary, archive)
    write_json(ROOT / 'reports/distribution.json', {'archive': archive.name,
        'sha256': sha(archive), 'bytes': archive.stat().st_size, 'files': len(files) + 1,
        'nro_sha256': sha(nro), 'forwarder': receipt, 'game_included': False,
        'checksums_verified': True, 'hardware_tested': False})
    print(f'Final verified runtime archive: {archive} ({archive.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
