"""Build the paired FEX decoder/compile permit and native reserve update."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
from port_common import ROOT, APPROVED, DEFAULT_GAME, GAME_EXE, sha, write_json
from build_fex_debug import PIN
from sleepingdogs_fex_debug import apply as apply_debug
from sleepingdogs_compiler_memory import apply_fex
from build_launcher import prepare, build_nro
from build_memory_budget import FILES, ADAPTER_FILES
from sleepingdogs_fault_trace import apply as apply_faults


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-compiler-memory-v2'))
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args(); work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    dep = Path('/home/blekjek/pes13-build')
    fex = work / 'fex'; source, adapter = fex / 'source', fex / 'adapter'
    out = ROOT / 'dist/compiler-memory-fix'; out.mkdir(exist_ok=True)
    base = dep / 'fex-experiment/source'
    assert subprocess.check_output(['git', '-C', str(base), 'rev-parse', 'HEAD'], text=True).strip() == PIN
    subprocess.run(['git', '-C', str(base), 'diff', '--quiet', 'HEAD'], check=True)
    approved = dep / 'production-input-fix/approved/source'
    manifest = json.loads((APPROVED / 'runtime-manifest.json').read_text())['files']
    inputs = {}
    for folder in ('generated/fex', 'src/fex'):
        for path in sorted((approved / folder).rglob('*')):
            if path.is_file():
                n = path.relative_to(approved).as_posix()
                inputs[n] = sha(path); assert inputs[n] == manifest['source/' + n], n
    identity = {'pin': PIN, 'approved': inputs, 'local': {str(p.relative_to(ROOT)): sha(p) for p in
        [ROOT / 'tools/sleepingdogs_fex_debug.py', ROOT / 'tools/sleepingdogs_compiler_memory.py',
         ROOT / 'src/sd_fex_workspace.h', *sorted((ROOT / 'src').glob('sd_fex_debug*'))]}}
    stamp = fex / 'prepared.json'
    if not stamp.exists():
        assert not source.exists(), 'Use a fresh work directory'
        shutil.copytree(base, source, symlinks=True, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        shutil.copytree(approved / 'generated/fex', source, dirs_exist_ok=True)
        shutil.copytree(approved / 'src/fex', adapter)
        changes = apply_debug(source, adapter); changes.update(apply_fex(source, adapter))
        write_json(stamp, {'inputs': identity, 'patched': changes})
    prepared = json.loads(stamp.read_text()); assert prepared['inputs'] == identity
    for n, digest in prepared['patched'].items(): assert sha(source / n) == digest, n
    tc = dep / 'toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64'
    build = fex / 'build'; temp = fex / 'tmp'; temp.mkdir(exist_ok=True)
    env = dict(os.environ, PATH=str(tc / 'bin') + os.pathsep + os.environ['PATH'], TMPDIR=str(temp))
    print('Building bounded compiler FEX DLL', flush=True)
    with (fex / 'build.log').open('a') as log:
        if not (build / 'build.ninja').exists():
            subprocess.run(['cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja',
                '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_TOOLCHAIN_FILE=' + str(source / 'Data/CMake/toolchain_mingw.cmake'),
                '-DMINGW_TRIPLE=aarch64-w64-mingw32', '-DENABLE_LTO=OFF', '-DBUILD_TESTING=OFF',
                '-DENABLE_JEMALLOC_GLIBC_ALLOC=OFF', '-DENABLE_ASSERTIONS=OFF', '-DENABLE_CCACHE=OFF',
                '-DENABLE_OFFLINE_TELEMETRY=OFF', '-DENABLE_GDB_SYMBOLS=OFF', '-DRANGES_NATIVE=OFF',
                '-DTUNE_CPU=cortex-a57', '-DTUNE_ARCH=armv8-a', '-DOVERRIDE_VERSION=sleepingdogs-fex-cmem1',
                '-DOVERRIDE_HASH=' + PIN, '-DPES13_HORIZON_DIR=' + str(adapter)],
                env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['cmake', '--build', str(build), '--target', 'wow64fex', '-j', str(a.jobs)],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    dll = build / 'Bin/libwow64fex.dll'; shutil.copy2(dll, out / dll.name)
    assert b'[SD-COMPILER-MEM] fex=v1' in dll.read_bytes()
    write_json(out / 'fex.json', {'build': 'sleepingdogs-compiler-memory-v1',
        'inputs': identity, 'source_changes': prepared['patched'],
        'adapter_files': {p.name: sha(p) for p in sorted(adapter.iterdir()) if p.is_file()},
        'dll_sha256': sha(dll), 'dll_bytes': dll.stat().st_size,
        'previous_dll_sha256': sha(ROOT / 'vendor/fex/libwow64fex-sd-debug.dll'),
        'compile_slots': 4, 'ir_bytes_unchanged': 16777216, 'decoder_default_bytes': 65536,
        'profile': 'fastest (unchanged)', 'hardware_tested': False})
    print('Building native compact decoder reserves', flush=True)
    source, metadata = prepare(work, DEFAULT_GAME / GAME_EXE)
    native_stamp = work / 'fault-prepared.json'
    if not native_stamp.exists():
        apply_faults(source); write_json(native_stamp, {n: sha(source / n) for n in FILES})
    for n, digest in json.loads(native_stamp.read_text()).items(): assert sha(source / n) == digest
    elf, nro = build_nro(work, source, dep, a.jobs)
    assert b'[SD-COMPILER-MEM] native=v1' in nro.read_bytes()
    shutil.copy2(nro, out / nro.name)
    shutil.copy2(elf, ROOT / 'local/symbols/sleepingdogs-compiler-memory.elf')
    write_json(out / 'native.json', {'build': 'sleepingdogs-compiler-memory-v1',
        'nro_sha256': sha(nro), 'elf_sha256': sha(elf), 'game': metadata,
        'scratch_reserve_bytes': 67371008, 'previous_scratch_reserve_bytes': 100663296,
        'decoder_reserve_bytes': 65536, 'ir_reserve_bytes': 16777216, 'pairs': 4,
        'source_files': {n: sha(source / n) for n in FILES},
        'adapter_files': {n: sha(work / 'fex-adapter' / n) for n in ADAPTER_FILES},
        'prepared': json.loads((work / 'sleepingdogs-prepared.json').read_text()),
        'hardware_tested': False})
    print(json.dumps({'nro': sha(nro), 'dll': sha(dll)}), flush=True)

if __name__ == '__main__': main()
