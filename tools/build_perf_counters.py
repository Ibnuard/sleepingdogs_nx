"""Build v8 from the verified v7 tree, preserving its ZIP, ELF and source backup."""
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
from sleepingdogs_perf_counters import apply, BUILD, MARKER, FILES
import f1_base_build as base

V7_SHA = '85f5eacfbc88d295440a3aea93d7564f2211c7457ced3217546e48a318ddea09'
INPUTS = ('tools/build_perf_counters.py', 'tools/sleepingdogs_perf_counters.py',
          'src/low_window/sd_perf_summary.h')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    package = ROOT/'dist/sleepingdogs-fex-low-window-performance-hud.zip'
    assert sha(package) == V7_SHA
    with zipfile.ZipFile(package) as z:
        previous = json.loads(z.read('source/low-window-performance-hud/native.json'))
        old_nro = z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    assert sha(ROOT/'local/symbols/sleepingdogs-low-window-v7.elf') == previous['elf_sha256']
    for name, digest in previous['build_inputs'].items():
        assert sha(ROOT/name) == digest, name
    inputs = dict(previous['build_inputs'])
    inputs.update({name:sha(ROOT/name) for name in INPUTS})
    work, source = args.work, args.work/'native-source'
    stamp = work/'perf-counters-prepared.json'
    if not stamp.exists():
        assert manifest(source) == previous['source_files'], 'v7 source changed'
        assert manifest(work/'fex-adapter') == previous['adapter_files'], 'v7 adapter changed'
        backup = work/'perf-counters-v7-source'
        assert not backup.exists(), 'Preserve the previous backup'
        for name in FILES:
            if (source/name).exists():
                dest = backup/name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source/name, dest)
        apply(source)
        write_json(stamp, dict(inputs=inputs, source=manifest(source),
                   adapter=previous['adapter_files'], base_zip_sha256=V7_SHA))
    prepared = json.loads(stamp.read_text())
    assert prepared['inputs'] == inputs and prepared['base_zip_sha256'] == V7_SHA
    assert manifest(source) == prepared['source']
    assert manifest(work/'fex-adapter') == prepared['adapter']
    changed = {n for n,h in prepared['source'].items() if previous['source_files'].get(n) != h}
    assert changed == FILES and not set(previous['source_files'])-set(prepared['source'])
    size = struct.unpack_from('<I', old_nro, 0x18)[0]
    assert old_nro[size:size+4] == b'ASET'
    io, il, no, nl = struct.unpack_from('<4Q', old_nro, size+8)
    icon, nacp = work/'nro-icon.jpg', work/'sleepingdogs-fex.nacp'
    icon.write_bytes(old_nro[size+io:size+io+il])
    nacp.write_bytes(old_nro[size+no:size+no+nl])
    print('Verified v7; building opt-in v8 interval counters', flush=True)
    with (work/'perf-counters-build.log').open('w') as log:
        original_run = base.run
        def logged_run(command, **kwargs):
            kwargs.setdefault('stdout', log)
            kwargs.setdefault('stderr', subprocess.STDOUT)
            return original_run(command, **kwargs)
        base.run = logged_run
        with contextlib.redirect_stdout(log):
            elf, _ = base.build_nro(work, source, Path('/home/blekjek/pes13-build'), args.jobs, icon=icon)
    out = ROOT/'dist/low-window-perf-counters'
    out.mkdir(parents=True, exist_ok=True)
    nro = out/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro', str(elf), str(nro),
                    '--nacp='+str(nacp), '--icon='+str(icon)], check=True)
    shutil.copy2(elf, ROOT/'local/symbols/sleepingdogs-low-window-v8.elf')
    data = nro.read_bytes()
    for marker in (MARKER.encode(), b'[SD-PERF]', b'[SD-PERF-IO]', b'[SD-FRAME]',
                   b'[SD-CPU-TOPOLOGY] v1', b'[SD-LOWVA] v1', b'[SD-SYNC] v1'):
        assert marker in data, marker
    assert manifest(source) == prepared['source']
    assert manifest(work/'fex-adapter') == prepared['adapter']
    for name, digest in inputs.items():
        assert sha(ROOT/name) == digest, name
    receipt = dict(previous, build=BUILD, nro_sha256=sha(nro), elf_sha256=sha(elf),
        build_inputs=inputs, source_files=prepared['source'],
        source_changes={n:prepared['source'][n] for n in sorted(changed)},
        previous_package_sha256=V7_SHA, hardware_tested=False,
        performance_optimization=False, counters_opt_in=True, counter_interval_ms=10000,
        cpu_gpu_scheduling_unchanged=True, startup_cpu_guard=True)
    write_json(out/'native.json', receipt)
    print('Built', BUILD, receipt['nro_sha256'], flush=True)


if __name__ == '__main__':
    main()
