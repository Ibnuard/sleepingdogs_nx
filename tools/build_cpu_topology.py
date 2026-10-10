"""Continue the pinned v5 tree with Horizon CPU topology support only."""
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
import f1_base_build as base

BUILD = 'sleepingdogs-low-window-v6-cpu-topology-fix'
V5_SHA = '7ade825f06fa11cadd6204f2f6b2fd8e7e792af1524783611c9e3ababe810816'
EXPECTED = {'dlls/ntdll/unix/system.c', 'dlls/ntdll/unix/sd_cpu_topology.inc',
            'wine-nx-probe/source/runtime.c'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--refresh-inputs', action='store_true',
                        help='Refresh builder metadata only after verifying the prepared source is unchanged')
    args = parser.parse_args()
    package = ROOT / 'dist/sleepingdogs-fex-low-window-sync-startup-fix.zip'
    assert sha(package) == V5_SHA
    work = args.work
    source = work / 'native-source'
    out = ROOT / 'dist/low-window-cpu-topology-fix'
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as z:
        previous = json.loads(z.read('source/low-window-sync-startup-fix/native.json'))
        old_nro = z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    assert sha(ROOT / 'local/symbols/sleepingdogs-low-window-v5.elf') == previous['elf_sha256']
    for name, digest in previous['build_inputs'].items():
        assert sha(ROOT / name) == digest, name
    inputs = dict(previous['build_inputs'])
    inputs.update({name: sha(ROOT / name) for name in (
        'tools/build_cpu_topology.py', 'src/low_window/sd_cpu_topology.inc')})
    stamp = work / 'cpu-topology-prepared.json'
    if not stamp.exists():
        assert manifest(source) == previous['source_files'], 'v5 native tree changed'
        assert manifest(work / 'fex-adapter') == previous['adapter_files'], 'v5 adapter changed'
        # Preserve both original edited files; the v5 archive retains its full manifest.
        backup = work / 'cpu-topology-v5-source'
        for name in ('dlls/ntdll/unix/system.c', 'wine-nx-probe/source/runtime.c'):
            dst = backup / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            assert not dst.exists(), f'Preserve existing backup: {dst}'
            shutil.copy2(source / name, dst)
        p = source / 'dlls/ntdll/unix/system.c'
        text = exact(p.read_text(),
                     '#ifdef linux\n\n/* Helper function for counting bitmap values',
                     '#ifdef __SWITCH__\n\n#include "sd_cpu_topology.inc"\n\n'
                     '#elif defined(linux)\n\n/* Helper function for counting bitmap values')
        p.write_text(text)
        shutil.copy2(ROOT / 'src/low_window/sd_cpu_topology.inc', p.parent / 'sd_cpu_topology.inc')
        runtime = source / 'wine-nx-probe/source/runtime.c'
        runtime.write_text(exact(runtime.read_text(), 'low-window-v5-sync-startup-fix',
                                 'low-window-v6-cpu-topology-fix'))
        prepared = {'inputs': inputs, 'source': manifest(source), 'adapter': previous['adapter_files'],
                    'base_zip_sha256': V5_SHA}
        write_json(stamp, prepared)
    prepared = json.loads(stamp.read_text())
    if args.refresh_inputs:
        assert manifest(source) == prepared['source']
        assert manifest(work / 'fex-adapter') == prepared['adapter']
        changed_inputs = {n for n in inputs if inputs[n] != prepared['inputs'].get(n)}
        assert changed_inputs <= {'tools/build_cpu_topology.py', 'src/low_window/sd_cpu_topology.inc'}
        assert sha(source / 'dlls/ntdll/unix/sd_cpu_topology.inc') == inputs['src/low_window/sd_cpu_topology.inc']
        prepared['inputs'] = inputs
        write_json(stamp, prepared)
    assert prepared['inputs'] == inputs and prepared['base_zip_sha256'] == V5_SHA
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
    print('Verified full v5 source/adapter; building Horizon CPU topology', flush=True)
    with (work / 'cpu-topology-build.log').open('w') as log:
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
    symbols = ROOT / 'local/symbols/sleepingdogs-low-window-v6.elf'
    shutil.copy2(elf, symbols)
    data = nro.read_bytes()
    for marker in (b'low-window-v6-cpu-topology-fix', b'[SD-CPU-TOPOLOGY] v1',
                   b'[SD-LOWVA] v1', b'[SD-INIT] v2', b'[SD-SYNC] v1', b'fastest'):
        assert marker in data, marker
    assert manifest(source) == prepared['source'] and manifest(work / 'fex-adapter') == prepared['adapter']
    for name, digest in inputs.items():
        assert sha(ROOT / name) == digest, f'Input edited during build: {name}'
    receipt = dict(previous, build=BUILD, nro_sha256=sha(nro), elf_sha256=sha(elf),
                   build_inputs=inputs, source_files=prepared['source'],
                   source_changes={n: prepared['source'][n] for n in sorted(changed)},
                   previous_package_sha256=V5_SHA, hardware_tested=False,
                   cpu_topology_backend='Horizon PEB count; one thread per core', startup_cpu_guard=True)
    write_json(out / 'native.json', receipt)
    print('Built', BUILD, receipt['nro_sha256'], flush=True)


if __name__ == '__main__':
    main()
