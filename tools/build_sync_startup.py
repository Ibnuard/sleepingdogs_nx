"""Repair v4 from its pinned ZIP and verified build tree, retaining prior symbols.

Older dist baselines may have been removed. This explicit continuation checks
the complete v4 native and adapter manifests before changing the two files.
"""
from pathlib import Path
import argparse
import contextlib
import json
import shutil
import struct
import subprocess
import zipfile
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from f1_overlay import exact
from recover_sync_v3 import V4_SHA
import f1_base_build as base

BUILD = 'sleepingdogs-low-window-v5-sync-startup-fix'
EXPECTED = {'wine-nx-probe/source/sd_sync_bridge.inc', 'wine-nx-probe/source/runtime.c'}
CHANGED_INPUTS = {'src/low_window/sd_sync_bridge.inc', 'tools/low_window_sync.py', 'tools/build_low_window.py'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    package = ROOT / 'dist/sleepingdogs-fex-low-window-sync-watch.zip'
    assert sha(package) == V4_SHA
    work = args.work
    source = work / 'native-source'
    out = ROOT / 'dist/low-window-sync-startup-fix'
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as z:
        previous = json.loads(z.read('source/low-window-sync-watch/native.json'))
        old_nro = z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    assert sha(ROOT / 'local/symbols/sleepingdogs-low-window-v4.elf') == previous['elf_sha256']
    for name, digest in previous['build_inputs'].items():
        if name not in CHANGED_INPUTS:
            assert sha(ROOT / name) == digest, name
    inputs = {name: sha(ROOT / name) for name in previous['build_inputs']}
    inputs.update({name: sha(ROOT / name) for name in ('tools/build_sync_startup.py', 'tools/recover_sync_v3.py')})
    stamp = work / 'sync-startup-prepared.json'
    if not stamp.exists():
        assert manifest(source) == previous['source_files'], 'v4 native tree changed'
        assert manifest(work / 'fex-adapter') == previous['adapter_files'], 'v4 adapter changed'
        shutil.copy2(ROOT / 'src/low_window/sd_sync_bridge.inc', source / 'wine-nx-probe/source/sd_sync_bridge.inc')
        runtime = source / 'wine-nx-probe/source/runtime.c'
        runtime.write_text(exact(runtime.read_text(), 'low-window-v4-sync-watch', 'low-window-v5-sync-startup-fix'))
        prepared = {'inputs': inputs, 'source': manifest(source), 'adapter': previous['adapter_files'],
                    'base_zip_sha256': V4_SHA}
        write_json(stamp, prepared)
    prepared = json.loads(stamp.read_text())
    assert prepared['inputs'] == inputs and prepared['base_zip_sha256'] == V4_SHA
    assert manifest(source) == prepared['source']
    assert manifest(work / 'fex-adapter') == prepared['adapter']
    changed = {n for n, h in prepared['source'].items() if previous['source_files'].get(n) != h}
    assert changed == EXPECTED and not set(previous['source_files']) - set(prepared['source'])
    size = struct.unpack_from('<I', old_nro, 0x18)[0]
    assert old_nro[size:size+4] == b'ASET'
    icon_off, icon_len, nacp_off, nacp_len = struct.unpack_from('<4Q', old_nro, size+8)
    icon = work / 'nro-icon.jpg'
    nacp = work / 'sleepingdogs-fex.nacp'
    icon.write_bytes(old_nro[size+icon_off:size+icon_off+icon_len])
    nacp.write_bytes(old_nro[size+nacp_off:size+nacp_off+nacp_len])
    print('Verified complete v4 tree; building two-file startup repair', flush=True)
    with (work / 'sync-startup-build.log').open('w') as log:
        original_run = base.run
        def logged_run(command, **kwargs):
            kwargs.setdefault('stdout', log)
            kwargs.setdefault('stderr', subprocess.STDOUT)
            return original_run(command, **kwargs)
        base.run = logged_run
        with contextlib.redirect_stdout(log):
            elf, _ = base.build_nro(work, source, Path('/home/blekjek/pes13-build'), args.jobs, icon=icon)
    nro = out / 'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro', str(elf), str(nro),
                    '--nacp='+str(nacp), '--icon='+str(icon)], check=True)
    symbols = ROOT / 'local/symbols/sleepingdogs-low-window-v5.elf'
    shutil.copy2(elf, symbols)
    data = nro.read_bytes()
    for marker in (b'low-window-v5-sync-startup-fix', b'[SD-LOWVA] v1', b'[SD-INIT] v2',
                   b'[SD-SYNC] v1', b'[SD-WATCH] v3', b'fastest'):
        assert marker in data, marker
    assert manifest(source) == prepared['source'] and manifest(work / 'fex-adapter') == prepared['adapter']
    receipt = dict(previous, build=BUILD, nro_sha256=sha(nro), elf_sha256=sha(elf),
                   build_inputs=inputs, source_files=prepared['source'],
                   source_changes={n: prepared['source'][n] for n in sorted(changed)},
                   previous_package_sha256=V4_SHA, hardware_tested=False, startup_cpu_guard=True)
    write_json(out / 'native.json', receipt)
    print('Built', BUILD, receipt['nro_sha256'], flush=True)


if __name__ == '__main__':
    main()
