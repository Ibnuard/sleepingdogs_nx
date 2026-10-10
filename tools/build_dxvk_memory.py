"""Build the Sleeping Dogs DXVK memory overlay in a fresh isolated tree."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from port_common import ROOT, sha, write_json
from sleepingdogs_dxvk_memory import apply, FILES, COMMIT, MARKER


def manifest(base):
    return {p.relative_to(base).as_posix(): sha(p) for p in sorted(base.rglob('*'))
            if p.is_file() and '.git' not in p.relative_to(base).parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-dxvk-memory-v2'))
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    work = args.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    previous = Path('/home/blekjek/f1-dxvk-compact-chunks')
    base = previous / 'source'
    receipt = json.loads((ROOT / 'vendor/dxvk/dxvk-3.1.1-f1mem2.json').read_text())
    assert receipt['source']['commit'] == COMMIT
    assert sha(base / FILES[0]) == receipt['source']['patched_memory_sha256']
    assert sha(ROOT / 'tools/dxvk_compact_chunks.py') == receipt['source']['patch_sha256']
    assert sha(ROOT / 'tools/dxvk_small_chunks.py') == receipt['source']['base_patch_sha256']
    for name, meta in receipt['files'].items(): assert sha(previous / 'x32' / name) == meta['sha256']
    inputs = {'base': manifest(base), 'patch_sha256': sha(ROOT / 'tools/sleepingdogs_dxvk_memory.py'),
              'builder_sha256': sha(Path(__file__)), 'cross_sha256': sha(previous / 'cross-x32.txt')}
    source, build = work / 'source', work / 'build-x32'
    stamp = work / 'prepared.json'
    if not stamp.exists():
        assert not source.exists(), 'Use a fresh work directory'
        shutil.copytree(base, source, symlinks=True, ignore=shutil.ignore_patterns('.git'))
        apply(source)
        shutil.copy2(previous / 'cross-x32.txt', work / 'cross-x32.txt')
        write_json(stamp, {'inputs': inputs, 'source_files': manifest(source)})
    prepared = json.loads(stamp.read_text())
    assert prepared['inputs'] == inputs
    assert manifest(source) == prepared['source_files']
    changed = {n: h for n, h in prepared['source_files'].items() if inputs['base'].get(n) != h}
    assert set(changed) == set(FILES), changed.keys()
    tc = Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64')
    shaders = Path('/home/blekjek/f1-dxvk-small-chunks/shader-tools/usr/bin')
    env = dict(os.environ, PATH=str(tc / 'bin') + os.pathsep + str(shaders) + os.pathsep + os.environ['PATH'])
    with (work / 'build.log').open('a') as log:
        if not (build / 'build.ninja').exists():
            subprocess.run(['meson', 'setup', str(build), str(source), '--cross-file', str(work / 'cross-x32.txt'),
                            '--buildtype=release', '-Denable_d3d10=false', '-Db_lto=false'],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['ninja', '-C', str(build), '-j', str(args.jobs)],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    out = ROOT / 'dist/dxvk-memory-fix'; out.mkdir(exist_ok=True)
    files = {}
    for name in ('d3d9', 'd3d11', 'dxgi'):
        dll = build / 'src' / name / (name + '.dll')
        assert MARKER.encode() in dll.read_bytes(), name
        shutil.copy2(dll, out / dll.name)
        files[dll.name] = {'sha256': sha(dll), 'bytes': dll.stat().st_size}
    write_json(out / 'build.json', {'build': 'sleepingdogs-dxvk-sdmem1', 'commit': COMMIT,
        'base_archive_sha256': receipt['archive_sha256'], 'previous_files': receipt['files'],
        'files': files, 'inputs': inputs, 'source_files': prepared['source_files'], 'changed': changed,
        'pool_cap_bytes': 2097152, 'resource_sizes_unchanged': True, 'hardware_tested': False})
    print(json.dumps(files), flush=True)


if __name__ == '__main__': main()
