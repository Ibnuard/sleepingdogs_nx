"""Build a private pinned FEX tree with approved overlays and x86 #DB support."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess

from port_common import ROOT, APPROVED, sha, write_json
from sleepingdogs_fex_debug import apply

PIN = 'e2f973fe931e6dc2ce523795e51ca1ac3ca85816'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-fex-debug-v1'))
    p.add_argument('--dependencies', type=Path, default=Path('/home/blekjek/pes13-build'))
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--refresh', action='store_true', help='Reapply changed overlay to a verified private build tree')
    a = p.parse_args()
    work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    base = a.dependencies / 'fex-experiment/source'
    head = subprocess.check_output(['git', '-C', str(base), 'rev-parse', 'HEAD'], text=True).strip()
    assert head == PIN, head
    subprocess.run(['git', '-C', str(base), 'diff', '--quiet', 'HEAD'], check=True)
    approved = APPROVED / 'source'
    # Local Linux mirror avoids thousands of drvfs reads; verify every reused file.
    mirror = a.dependencies / 'production-input-fix/approved/source'
    if mirror.is_dir(): approved = mirror
    manifest = json.loads((APPROVED / 'runtime-manifest.json').read_text())['files']
    inputs = {}
    for folder in ('generated/fex', 'src/fex'):
        for path in sorted((approved / folder).rglob('*')):
            if not path.is_file(): continue
            name = path.relative_to(approved).as_posix()
            digest = sha(path)
            assert digest == manifest['source/' + name], name
            inputs[name] = digest
    identity = {'fex_commit': PIN, 'approved': inputs,
                'patch': sha(ROOT / 'tools/sleepingdogs_fex_debug.py'),
                'new_sources': {p.name: sha(p) for p in sorted((ROOT / 'src').glob('sd_fex_debug*'))}}
    source, adapter = work / 'source', work / 'adapter'
    stamp = work / 'prepared.json'
    if stamp.exists():
        previous = json.loads(stamp.read_text())
        if previous['inputs'] != identity:
            assert a.refresh, 'Inputs changed; use --refresh or a fresh work directory'
            assert previous['inputs']['fex_commit'] == PIN and previous['inputs']['approved'] == inputs
            for name, digest in previous['patched'].items():
                assert sha(source / name) == digest, 'Untracked source edit: ' + name
                original = approved / 'generated/fex' / name
                if not original.is_file(): original = base / name
                shutil.copy2(original, source / name)
            shutil.copytree(approved / 'src/fex', adapter, dirs_exist_ok=True)
            changes = apply(source, adapter)
            write_json(stamp, {'inputs': identity, 'patched': changes})
    else:
        assert not source.exists(), 'Untracked build tree'
        print('Copying pinned FEX source and approved adapters', flush=True)
        shutil.copytree(base, source, symlinks=True, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        shutil.copytree(approved / 'generated/fex', source, dirs_exist_ok=True)
        shutil.copytree(approved / 'src/fex', adapter)
        changes = apply(source, adapter)
        write_json(stamp, {'inputs': identity, 'patched': changes})
    tc = a.dependencies / 'toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64'
    build = work / 'build'
    temp = work / 'tmp'; temp.mkdir(exist_ok=True)
    env = dict(os.environ, PATH=str(tc / 'bin') + os.pathsep + os.environ['PATH'], TMPDIR=str(temp))
    print(f'Building FEX debug-register support; log: {work / "build.log"}', flush=True)
    with (work / 'build.log').open('a') as log:
        if not (build / 'build.ninja').exists():
            subprocess.run(['cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja',
                '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_TOOLCHAIN_FILE=' + str(source / 'Data/CMake/toolchain_mingw.cmake'),
                '-DMINGW_TRIPLE=aarch64-w64-mingw32', '-DENABLE_LTO=OFF', '-DBUILD_TESTING=OFF',
                '-DENABLE_JEMALLOC_GLIBC_ALLOC=OFF', '-DENABLE_ASSERTIONS=OFF', '-DENABLE_CCACHE=OFF',
                '-DENABLE_OFFLINE_TELEMETRY=OFF', '-DENABLE_GDB_SYMBOLS=OFF', '-DRANGES_NATIVE=OFF',
                '-DTUNE_CPU=cortex-a57', '-DTUNE_ARCH=armv8-a', '-DOVERRIDE_VERSION=sleepingdogs-fex-db1',
                '-DOVERRIDE_HASH=' + PIN, '-DPES13_HORIZON_DIR=' + str(adapter)],
                env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['cmake', '--build', str(build), '--target', 'wow64fex', '-j', str(a.jobs)],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    dll = build / 'Bin/libwow64fex.dll'
    out = ROOT / 'dist/fex-debug-fix'; out.mkdir(exist_ok=True)
    shutil.copy2(dll, out / dll.name)
    receipt = {'build': 'sleepingdogs-fex-execution-breakpoints-v1', 'inputs': identity,
        'source_changes': json.loads(stamp.read_text())['patched'],
        'adapter_files': {p.name: sha(p) for p in sorted(adapter.iterdir()) if p.is_file()},
        'dll_sha256': sha(dll), 'dll_bytes': dll.stat().st_size,
        'base_dll_sha256': sha(ROOT / 'vendor/fex/libwow64fex-f1-demand.dll'),
        'compiler': subprocess.check_output([str(tc / 'bin/aarch64-w64-mingw32-clang'), '--version'], text=True).splitlines()[0],
        'profile': 'fastest (unchanged)', 'eager_spare_disabled': True,
        'scope': 'DR0-DR3 execution breakpoints; data and I/O watchpoints not implemented',
        'hardware_tested': False, 'game_boot_confirmed': False}
    write_json(out / 'build.json', receipt)
    print(json.dumps({'dll': str(out / dll.name), 'sha256': sha(dll)}), flush=True)

if __name__ == '__main__': main()
