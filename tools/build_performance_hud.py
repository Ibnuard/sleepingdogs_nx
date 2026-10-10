"""Continue the verified v6 native tree; preserve its package and edited sources."""
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
from sleepingdogs_performance_hud import apply, BUILD, MARKER, FILES
import f1_base_build as base

V6_SHA = '3cd1e3f0070eacde87e3fa9953dc7f83c3b12d9d1ab744d4c49816afebd303b4'
INPUTS = ('tools/build_performance_hud.py', 'tools/sleepingdogs_performance_hud.py',
          'tools/f1_dx_hud.h', 'src/low_window/sd_frame_summary.h')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args()
    package = ROOT / 'dist/sleepingdogs-fex-low-window-cpu-topology-fix.zip'
    assert sha(package) == V6_SHA
    with zipfile.ZipFile(package) as z:
        previous = json.loads(z.read('source/low-window-cpu-topology-fix/native.json'))
        old_nro = z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    assert sha(ROOT / 'local/symbols/sleepingdogs-low-window-v6.elf') == previous['elf_sha256']
    for name, digest in previous['build_inputs'].items():
        assert sha(ROOT / name) == digest, name
    inputs = dict(previous['build_inputs'])
    inputs.update({n: sha(ROOT / n) for n in INPUTS})
    work, source = a.work, a.work / 'native-source'
    stamp = work / 'performance-hud-prepared.json'
    if not stamp.exists():
        assert manifest(source) == previous['source_files'], 'v6 source changed'
        assert manifest(work / 'fex-adapter') == previous['adapter_files'], 'v6 adapter changed'
        backup = work / 'performance-hud-v6-source'
        assert not backup.exists(), 'Preserve previous backup'
        for name in FILES:
            if (source / name).exists():
                dest = backup / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / name, dest)
        apply(source)
        write_json(stamp, dict(inputs=inputs, source=manifest(source),
                             adapter=previous['adapter_files'], base_zip_sha256=V6_SHA))
    prepared = json.loads(stamp.read_text())
    assert prepared['inputs'] == inputs and prepared['base_zip_sha256'] == V6_SHA
    assert manifest(source) == prepared['source']
    assert manifest(work / 'fex-adapter') == prepared['adapter']
    changed = {n for n, h in prepared['source'].items() if previous['source_files'].get(n) != h}
    assert changed == FILES and not set(previous['source_files']) - set(prepared['source'])
    size = struct.unpack_from('<I', old_nro, 0x18)[0]
    assert old_nro[size:size+4] == b'ASET'
    io, il, no, nl = struct.unpack_from('<4Q', old_nro, size+8)
    icon, nacp = work/'nro-icon.jpg', work/'sleepingdogs-fex.nacp'
    icon.write_bytes(old_nro[size+io:size+io+il])
    nacp.write_bytes(old_nro[size+no:size+no+nl])
    print('Verified v6; building v7 HUD / optional Performance / lighter normal launch', flush=True)
    with (work/'performance-hud-build.log').open('w') as log:
        original_run = base.run
        def logged_run(command, **kwargs):
            kwargs.setdefault('stdout', log)
            kwargs.setdefault('stderr', subprocess.STDOUT)
            return original_run(command, **kwargs)
        base.run = logged_run
        with contextlib.redirect_stdout(log):
            elf, _ = base.build_nro(work, source, Path('/home/blekjek/pes13-build'), a.jobs, icon=icon)
    out = ROOT/'dist/low-window-performance-hud'
    out.mkdir(parents=True, exist_ok=True)
    nro = out/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro', str(elf), str(nro),
                    '--nacp='+str(nacp), '--icon='+str(icon)], check=True)
    shutil.copy2(elf, ROOT/'local/symbols/sleepingdogs-low-window-v7.elf')
    data = nro.read_bytes()
    for marker in (MARKER.encode(), b'DXVK HUD', b'dxvk.hud = %s', b'[SD-FRAME]',
                   b'[SD-CPU-TOPOLOGY] v1', b'[SD-LOWVA] v1', b'[SD-SYNC] v1'):
        assert marker in data, marker
    assert manifest(source) == prepared['source']
    assert manifest(work/'fex-adapter') == prepared['adapter']
    for name, digest in inputs.items(): assert sha(ROOT/name) == digest, name
    receipt = dict(previous, build=BUILD, nro_sha256=sha(nro), elf_sha256=sha(elf),
                   build_inputs=inputs, source_files=prepared['source'],
                   source_changes={n:prepared['source'][n] for n in sorted(changed)},
                   previous_package_sha256=V6_SHA, hardware_tested=False,
                   hud_modes=['None','FPS','Full'], performance_profile_optional=True,
                   normal_launch_detailed_watch=False, startup_cpu_guard=True)
    write_json(out/'native.json', receipt)
    print('Built', BUILD, receipt['nro_sha256'], flush=True)


if __name__ == '__main__': main()
