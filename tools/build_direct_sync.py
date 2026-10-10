"""Build the v10 direct-sync adaptation on the hash-verified local FEXTendo v9."""
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
from sleepingdogs_direct_sync import apply, BUILD, MARKER, FILES, COPIES
from verify_shader_abi import verify
import f1_base_build as base

V9_SHA = '06d09aa6eea05cc38158c6a72c5782320c83ea2db4e8815ad272d56375f9063d'
INPUTS = tuple(sorted(set(COPIES.values()) | {'tools/build_direct_sync.py', 'tools/sleepingdogs_direct_sync.py'}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args()
    package = ROOT / 'dist/sleepingdogs-fex-low-window-shader-optimizations.zip'
    assert sha(package) == V9_SHA
    with zipfile.ZipFile(package) as z:
        previous = json.loads(z.read('source/low-window-shader-optimizations/native.json'))
        old_nro = z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    assert sha(ROOT/'local/symbols/sleepingdogs-low-window-v9.elf') == previous['elf_sha256']
    for name, digest in previous['build_inputs'].items():
        assert sha(ROOT/name) == digest, name
    tests = json.loads((ROOT/'reports/low-window-v10-direct-sync.json').read_text())
    assert tests['status'] == 'PASS'
    for name, digest in tests['sources'].items():
        assert sha(ROOT/name) == digest, ('stale tests', name)
    inputs = dict(previous['build_inputs'])
    inputs.update({name:sha(ROOT/name) for name in INPUTS})
    abi = verify()
    assert abi == previous['shader_abi'], 'Unrelated shader ABI changed'
    work, source = a.work, a.work/'native-source'
    stamp, backup = work/'direct-sync-prepared.json', work/'direct-sync-v9-source'
    if stamp.exists():
        old = json.loads(stamp.read_text())
        assert old['base_zip_sha256'] == V9_SHA
        assert manifest(source) == old['source'], 'Unexpected source changes after preparation'
        if old['inputs'] != inputs:
            for name in FILES:
                if name in previous['source_files']:
                    assert sha(backup/name) == previous['source_files'][name]
                    shutil.copy2(backup/name, source/name)
            apply(source)
            write_json(stamp, dict(inputs=inputs, source=manifest(source), adapter=previous['adapter_files'], base_zip_sha256=V9_SHA))
    else:
        assert manifest(source) == previous['source_files'], 'v9 native source changed'
        assert manifest(work/'fex-adapter') == previous['adapter_files'], 'FEXTendo adapter changed'
        assert not backup.exists(), 'Preserve previous source backup'
        for name in FILES:
            if (source/name).exists():
                dest=backup/name; dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source/name, dest)
        apply(source)
        write_json(stamp, dict(inputs=inputs, source=manifest(source), adapter=previous['adapter_files'], base_zip_sha256=V9_SHA))
    prepared = json.loads(stamp.read_text())
    assert prepared['inputs'] == inputs
    assert manifest(source) == prepared['source']
    assert manifest(work/'fex-adapter') == prepared['adapter']
    changed = {n for n,h in prepared['source'].items() if previous['source_files'].get(n) != h}
    assert changed == FILES and not set(previous['source_files'])-set(prepared['source'])
    for name, digest in tests['source_files'].items():
        assert prepared['source'][name] == digest, ('overlay differs from tested source', name)
    size = struct.unpack_from('<I', old_nro, 0x18)[0]
    assert old_nro[size:size+4] == b'ASET'
    io,il,no,nl = struct.unpack_from('<4Q', old_nro, size+8)
    icon, nacp = work/'nro-icon.jpg', work/'sleepingdogs-fex.nacp'
    icon.write_bytes(old_nro[size+io:size+io+il]); nacp.write_bytes(old_nro[size+no:size+no+nl])
    print('Verified v9 source, FEXTendo adapter and SDK ABI; compiling direct synchronization', flush=True)
    with (work/'direct-sync-build.log').open('w') as log:
        original_run = base.run
        def logged_run(command, **kwargs):
            kwargs.setdefault('stdout',log); kwargs.setdefault('stderr',subprocess.STDOUT)
            return original_run(command, **kwargs)
        base.run=logged_run
        with contextlib.redirect_stdout(log):
            elf,_ = base.build_nro(work,source,Path('/home/blekjek/pes13-build'),a.jobs,icon=icon)
    out = ROOT/'dist/low-window-direct-sync'; out.mkdir(parents=True,exist_ok=True)
    nro = out/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro',str(elf),str(nro),'--nacp='+str(nacp),'--icon='+str(icon)],check=True)
    shutil.copy2(elf, ROOT/'local/symbols/sleepingdogs-low-window-v10.elf')
    data = nro.read_bytes()
    for marker in (MARKER.encode(),b'[SD-SYNC-MODE]',b'[SD-DIRECT-SYNC]',b'[SD-SHADER]',
                   b'[SD-PERF]',b'[SD-FRAME]',b'[SD-CPU-TOPOLOGY] v1',b'[SD-LOWVA] v1',b'[SD-SYNC] v1'):
        assert marker in data, marker
    assert manifest(source) == prepared['source']
    assert manifest(work/'fex-adapter') == prepared['adapter']
    for name,digest in inputs.items(): assert sha(ROOT/name)==digest,name
    receipt = dict(previous,build=BUILD,nro_sha256=sha(nro),elf_sha256=sha(elf),build_inputs=inputs,
        source_files=prepared['source'],source_changes={n:prepared['source'][n] for n in sorted(changed)},
        previous_package_sha256=V9_SHA,hardware_tested=False,performance_optimization=True,
        fps_gain_measured=False,cpu_gpu_scheduling_unchanged=False,cpu_translator_unchanged=True,
        synchronization_backend_unchanged=False,guest_dlls_unchanged=True,
        graphics_resolution_unchanged=True,target_resolution=[1280,720],
        sync_modes={'0':'original pipe/server','1':'direct dispatch, original waits','2':'direct dispatch, per-object queued waits'},
        sync_switch='sync-mode.txt',sync_default_without_file=0,sync_package_mode=2,
        backported_from_autorun=previous['backported_from_autorun']+[
            '17a558619724270c98b52b921a731f143bed7086','0625c79c9dbb7bc71fa6cf9a244cb6332a377eed'],
        original_startup_apc_suspend_handlers_preserved=True)
    write_json(out/'native.json',receipt)
    print('Built',BUILD,receipt['nro_sha256'],flush=True)


if __name__=='__main__': main()
