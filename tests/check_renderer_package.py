"""Run the shipped C launch gate on complete ZIP contents, with an optional patch."""
from pathlib import Path
import argparse
import importlib.util
import os
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'fextendo_renderer_check', ROOT / 'vendor/f1-tools/check_renderer_package.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
HARNESS = base.HARNESS.replace('F1_2013', 'SleepingDogs')


def extract(archive, root, patch=False):
    prefix = 'switch/sleepingdogs-fex/'
    configs = set()
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if not name.startswith(prefix):
                continue
            relative = name.removeprefix(prefix)
            if not relative.startswith(('launcher/renderers/', 'launcher/presets/')):
                if patch:
                    raise ValueError(f'Patch unexpectedly changes a user setting: {name}')
                continue
            if not relative.endswith(('.dll', '.conf')):
                continue
            if patch and not relative.endswith('.conf'):
                raise ValueError(f'Config patch contains a binary: {name}')
            target = (root / relative).resolve()
            if not target.is_relative_to(root):
                raise ValueError('Archive path escapes fixture')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
            if relative.endswith('.conf'):
                configs.add(relative)
    if len(configs) != 11:
        raise ValueError(f'Expected 11 launcher configs, found {len(configs)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--update', type=Path, required=True)
    parser.add_argument('--patch', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect-config-rejection', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    native = args.source / 'wine-nx-probe/source'
    source = (native / 'runtime.c').read_text()
    start = source.index('#ifndef FEXTENDO_PRESETS_H')
    end = source.index('\n#endif', source.index('#ifndef FEXTENDO_RENDERERS_H')) + len('\n#endif')
    block = source[start:end]
    assert '/drive_c/SleepingDogs/' in block and '/drive_c/F1_2013/' not in block
    file = out / 'renderer-preflight.c'
    exe = file.with_suffix('')
    file.write_text(base.PREAMBLE + block + HARNESS)
    compile_temp = out / 'compiler-tmp'
    compile_temp.mkdir(exist_ok=True)
    environment = dict(os.environ, TMPDIR=str(compile_temp))
    subprocess.run([shutil.which('clang') or shutil.which('cc'), '-std=c11', '-O1', '-g',
                    '-D_POSIX_C_SOURCE=200809L', '-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all', '-I', str(native), str(file), '-o', str(exe)],
                   check=True, env=environment)
    with tempfile.TemporaryDirectory(prefix='sleepingdogs-renderer-', dir=out) as temp:
        root = Path(temp)
        extract(args.update, root)
        if args.patch:
            extract(args.patch, root, patch=True)
        # Check DX11 settings as well as the original C launcher's D3D9 gate.
        for config in sorted(root.rglob('*.conf')):
            options = dict(line.split(' = ', 1) for line in config.read_text().splitlines()
                           if line.strip() and not line.lstrip().startswith('#'))
            assert options['dxgi.syncInterval'] == '1', config
            assert options['dxvk.enableDescriptorBuffer'] == 'False', config
            assert options['dxvk.enableDescriptorHeap'] == 'False', config
            assert options['dxvk.numCompilerThreads'] == '1', config
        subprocess.run([str(exe), str(root), str(int(args.expect_config_rejection))], check=True)


if __name__ == '__main__':
    main()
