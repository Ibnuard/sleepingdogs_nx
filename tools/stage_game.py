"""Create a local ready-to-copy SD tree, preserving every original game file."""
import argparse
import shutil
from pathlib import Path
from port_common import ROOT, DEFAULT_GAME, GAME_EXE, GAME_DIR, APP_ID, VERSION, sha, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, default=DEFAULT_GAME)
    parser.add_argument('--package', type=Path, default=ROOT / f'dist/{APP_ID}-{VERSION}-sd')
    parser.add_argument('--output', type=Path, default=ROOT / f'dist/{APP_ID}-ready')
    args = parser.parse_args()
    source, package, output = args.game.resolve(), args.package.resolve(), args.output.resolve()
    if output.exists() or output == source or source in output.parents:
        raise SystemExit('Choose a new output directory outside the source game')
    if not (source / GAME_EXE).is_file():
        raise SystemExit('HKShip.exe is missing')
    shutil.copytree(package, output)
    game = output / 'switch' / APP_ID / 'drive_c' / GAME_DIR
    managed = {'d3d9.dll', 'd3d11.dll', 'dxgi.dll', 'dxvk.conf'}
    files, skipped = {}, []
    for src in sorted(source.rglob('*')):
        if not src.is_file():
            continue
        relative = src.relative_to(source)
        if len(relative.parts) == 1 and relative.name.lower() in managed:
            skipped.append(str(relative))
            continue
        if src.stat().st_size > 0xffffffff:
            raise SystemExit(f'File exceeds FAT32 size limit: {relative}')
        dst = game / relative
        if dst.exists():
            raise SystemExit(f'Runtime file conflict: {relative}')
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if src.stat().st_size != dst.stat().st_size:
            raise SystemExit(f'Incomplete copy: {relative}')
        files[str(relative)] = {'bytes': src.stat().st_size}
        if src.suffix.lower() in ('.exe', '.dll', '.dat', '.ini', '.vdf'):
            digest = sha(src)
            if sha(dst) != digest:
                raise SystemExit(f'Copied file changed: {relative}')
            files[str(relative)]['sha256'] = digest
        print(f'Copied {relative}', flush=True)
    (game / 'COPY-YOUR-GAME-HERE.txt').unlink()
    report = {'game_included': True, 'source': str(source), 'files': files,
              'preserved_runtime_files': sorted(managed), 'skipped_conflicts': skipped,
              'total_game_bytes': sum(p['bytes'] for p in files.values()),
              'hardware_tested': False}
    write_json(output / 'local-game-report.json', report)
    print(f'Ready: {output}')


if __name__ == '__main__':
    main()
