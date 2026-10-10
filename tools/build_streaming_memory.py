"""Build native segregation and large mapped DXVK allocations in fresh trees."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, sha, write_json
from build_launcher import prepare, build_nro
from build_gpu_budget import FILES as GPU_FILES, ADAPTER_FILES
from sleepingdogs_fault_trace import apply as apply_faults
from build_dxvk_memory import manifest
from sleepingdogs_streaming_memory import apply_dxvk, DXVK_FILES, MARKER

FILES = GPU_FILES + ('wine-nx-probe/source/sd_gpu_stream.h',)


def native(work, out, jobs):
    source, metadata = prepare(work, DEFAULT_GAME / GAME_EXE)
    stamp = work / 'fault-prepared.json'
    if not stamp.exists():
        apply_faults(source); write_json(stamp, {n: sha(source / n) for n in FILES})
    for n, digest in json.loads(stamp.read_text()).items(): assert sha(source / n) == digest, n
    with (work / 'native-build.log').open('a') as log:
        # Link recipe emits verbose compiler diagnostics. Preserve them locally.
        import contextlib
        with contextlib.redirect_stdout(log):
            # C subprocess output is redirected at fd level by the calling CLI.
            elf, nro = build_nro(work, source, Path('/home/blekjek/pes13-build'), jobs)
    for marker in (b'[SD-GPU-STREAM] v1', b'[SD-GPU-BUDGET] v1', b'[SD-COMPILER-MEM] native=v1',
                   b'[SD-FIRSTFAULT] build=v3', b'fastest'):
        assert marker in nro.read_bytes(), marker
    shutil.copy2(nro, out / nro.name)
    shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-streaming-memory.elf')
    write_json(out / 'native.json', {'build': 'sleepingdogs-streaming-memory-v1',
        'nro_sha256': sha(nro), 'elf_sha256': sha(elf), 'game': metadata,
        'gpu_preallocation_bytes': 268435456, 'large_reserve_bytes': 67108864,
        'borrow_guard_bytes': 16777216, 'threshold_bytes': 2097152,
        'source_files': {n: sha(source / n) for n in FILES},
        'adapter_files': {n: sha(work / 'fex-adapter' / n) for n in ADAPTER_FILES},
        'prepared': json.loads((work / 'sleepingdogs-prepared.json').read_text()), 'hardware_tested': False})
    print('Native streaming budget:', sha(nro), flush=True)


def dxvk(work, out, jobs):
    previous = Path('/home/blekjek/sleepingdogs-dxvk-memory-v2'); base = previous / 'source'
    baseline = json.loads((ROOT / 'dist/dxvk-memory-fix/build.json').read_text())
    assert manifest(base) == baseline['source_files']
    work = work / 'dxvk'; work.mkdir(exist_ok=True)
    source, build = work / 'source', work / 'build-x32'
    inputs = {'base': baseline['source_files'], 'patch_sha256': sha(ROOT / 'tools/sleepingdogs_streaming_memory.py'),
              'builder_sha256': sha(Path(__file__)), 'cross_sha256': sha(previous / 'cross-x32.txt')}
    stamp = work / 'prepared.json'
    if not stamp.exists():
        assert not source.exists(), 'Use a fresh work directory'
        shutil.copytree(base, source, symlinks=True); apply_dxvk(source)
        shutil.copy2(previous / 'cross-x32.txt', work / 'cross-x32.txt')
        write_json(stamp, {'inputs': inputs, 'source_files': manifest(source)})
    prepared = json.loads(stamp.read_text()); assert prepared['inputs'] == inputs
    assert prepared['source_files'] == manifest(source)
    changed = {n: h for n, h in prepared['source_files'].items() if inputs['base'].get(n) != h}
    assert set(changed) == set(DXVK_FILES)
    tc = Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64')
    shaders = Path('/home/blekjek/f1-dxvk-small-chunks/shader-tools/usr/bin')
    env = dict(os.environ, PATH=str(tc / 'bin') + os.pathsep + str(shaders) + os.pathsep + os.environ['PATH'])
    with (work / 'build.log').open('a') as log:
        if not (build / 'build.ninja').exists():
            subprocess.run(['meson', 'setup', str(build), str(source), '--cross-file', str(work / 'cross-x32.txt'),
                '--buildtype=release', '-Denable_d3d10=false', '-Db_lto=false'], env=env,
                stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['ninja', '-C', str(build), '-j', str(jobs)], env=env,
            stdout=log, stderr=subprocess.STDOUT, check=True)
    files = {}; stage = out / 'x32'; stage.mkdir(exist_ok=True)
    for name in ('d3d9', 'd3d11', 'dxgi'):
        dll = build / 'src' / name / (name + '.dll'); shutil.copy2(dll, out / dll.name)
        subprocess.run([str(tc / 'bin/llvm-strip'), '--strip-debug', '-o', str(stage / dll.name), str(dll)], check=True)
        assert MARKER.encode() in (stage / dll.name).read_bytes()
        files[dll.name] = {'sha256': sha(stage / dll.name), 'bytes': (stage / dll.name).stat().st_size,
                          'raw_sha256': sha(dll)}
    write_json(out / 'dxvk.json', {'build': 'sleepingdogs-dxvk-sdstream1', 'commit': baseline['commit'],
        'files': files, 'inputs': inputs, 'source_files': prepared['source_files'], 'changed': changed,
        'threshold_bytes': 2097152, 'resource_sizes_unchanged': True, 'hardware_tested': False})
    print(json.dumps(files), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-streaming-memory-v1'))
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--component', choices=('native', 'dxvk'), required=True)
    a = p.parse_args(); work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    out = ROOT / 'dist/streaming-memory-fix'; out.mkdir(exist_ok=True)
    (native if a.component == 'native' else dxvk)(work, out, a.jobs)


if __name__ == '__main__': main()
