"""Build Sleeping Dogs FEXTendo with Wine-NX/FEX under WSL and devkitPro."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import zipfile

import f1_base_build as base
import f1_overlay
from dxvk_runtime import stage_renderers, write_lf
from port_common import (ROOT, PES, APPROVED, BASE, APP_ID, TITLE, VERSION,
                         GAME_DIR, GAME_EXE, DEFAULT_GAME, pe_info, sha,
                         profile_config, write_json)
from sleepingdogs_overlay import apply
from wow64_context_fix import build as build_wow64_context


def prepare(work, game):
    metadata = pe_info(game)
    inputs = {str(p.relative_to(ROOT)): sha(p)
              for directory in ('tools', 'src', 'config')
              for p in sorted((ROOT / directory).rglob('*'))
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    identity = {'version': VERSION, 'game': metadata, 'inputs': inputs}
    stamp = work / 'sleepingdogs-prepared.json'
    if stamp.exists():
        previous = json.loads(stamp.read_text())
        if previous['identity'] != identity:
            raise RuntimeError('Port inputs changed; choose a new --work directory')
        return work / 'native-source', metadata
    # The inherited overlay validates SizeOfImage; bind it to this audited EXE.
    f1_overlay.IMAGE_SIZE = metadata['image_size']
    source = base.prepare_source(work, game)
    changed = apply(source, work / 'fex-adapter', metadata)
    write_json(stamp, {'identity': identity, 'adapted_files': changed})
    return source, metadata


def build_nro(work, source, dependencies, jobs):
    # Reuse the reviewed native Wine/FEX/Mesa link recipe. Its intermediate NRO
    # is never shipped: regenerate metadata against the new title and icon.
    elf, _ = base.build_nro(work, source, dependencies, jobs)
    sdk = Path('/opt/devkitpro/tools/bin')
    nacp, nro = work / f'{APP_ID}.nacp', work / f'{APP_ID}.nro'
    base.run([sdk / 'nacptool', '--create', TITLE, 'AndroSwitch Project', VERSION, nacp])
    base.run([sdk / 'elf2nro', elf, nro, '--nacp=' + str(nacp),
              '--icon=' + str(ROOT / 'dist/launcher/nro-icon.jpg')])
    return elf, nro


def stage(nro, output, dlls, metadata, wow64, context_receipt):
    if output.exists():
        raise RuntimeError(f'Refusing to overwrite an existing SD package: {output}')
    prefix = output / 'switch' / APP_ID
    game = prefix / 'drive_c' / GAME_DIR
    game.mkdir(parents=True)
    # Copy only runtime-owned trees. Old game files, hives and saves never enter
    # the new prefix. Wine creates a fresh Sleeping Dogs user/session on launch.
    shutil.copytree(BASE / 'drive_c/windows', prefix / 'drive_c/windows')
    shutil.copytree(BASE / 'share', prefix / 'share')
    for dirname in ('users/steamuser/Documents', 'users/steamuser/AppData/Local', 'users/steamuser/AppData/Roaming', 'dxvk'):
        (prefix / 'drive_c' / dirname).mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'dist/launcher', prefix / 'launcher')
    presets = prefix / 'launcher/presets'
    for profile in ('balanced', 'low-latency', 'stable', 'quality'):
        for renderer in ('dxvk-3.1.1', 'dxvk-2.7.1-async'):
            path = presets / profile / renderer / 'dxvk.conf'
            path.parent.mkdir(parents=True, exist_ok=True)
            write_lf(path, profile_config(profile, renderer.endswith('async')))
    write_lf(presets / 'dxvk.conf', profile_config('stable'))
    renderers = stage_renderers(prefix, profile_config)
    write_json(prefix / 'launcher/streaming-memory-fix.json', {
        'build': 'sleepingdogs-streaming-memory-v1', 'nro_sha256': sha(nro),
        'dxvk_dlls': renderers['dxvk-3.1.1']['dlls'],
        'gpu_preallocation_bytes': 268435456, 'large_reserve_bytes': 67108864,
        'borrow_guard_bytes': 16777216, 'threshold_bytes': 2097152, 'hardware_tested': False})
    write_json(prefix / 'launcher/gpu-pressure-fix.json', {
        'build': 'sleepingdogs-gpu-pressure-v1', 'nro_sha256': sha(nro),
        'gpu_preallocation_bytes': 268435456, 'reserve_is_soft': True,
        'dxvk_dlls': renderers['dxvk-3.1.1']['dlls'], 'hardware_tested': False})
    write_json(prefix / 'launcher/buffer-reuse-fix.json', {
        'build': 'sleepingdogs-buffer-reuse-v1',
        'dxvk_dlls': renderers['dxvk-3.1.1']['dlls'],
        'max_idle_bytes': 16777216, 'max_idle_count': 4,
        'retired_only': True, 'hardware_tested': False})
    for name in ('d3d9.dll', 'd3d11.dll', 'dxgi.dll'):
        shutil.copy2(prefix / 'launcher/renderers/dxvk-3.1.1' / name, game / name)
    shutil.copy2(game / 'd3d9.dll', prefix / 'drive_c/dxvk/d3d9.dll')
    write_lf(game / 'dxvk.conf', profile_config('stable'))
    for dll in dlls:
        shutil.copy2(dll, prefix / 'drive_c/windows/syswow64' / dll.name)
    shutil.copy2(wow64, prefix / 'drive_c/windows/system32/wow64.dll')
    write_json(prefix / 'launcher/wow64-context-fix.json', context_receipt)
    write_json(prefix / 'launcher/debug-cache-fix.json', {
        'build': 'sleepingdogs-teb-debug-cache-v1', 'nro_sha256': sha(nro),
        'hardware_tested': False})
    write_json(prefix / 'launcher/thread-debug-fix.json', {
        'build': 'sleepingdogs-suspended-thread-debug-v1', 'nro_sha256': sha(nro),
        'hardware_tested': False})
    write_json(prefix / 'launcher/memory-budget-fix.json', {
        'build': 'sleepingdogs-native-headroom-v2', 'nro_sha256': sha(nro),
        'gpu_preallocation_bytes': 268435456, 'hardware_tested': False})
    write_json(prefix / 'launcher/gpu-budget-fix.json', {
        'build': 'sleepingdogs-gpu-budget-v1', 'nro_sha256': sha(nro),
        'gpu_preallocation_bytes': 268435456, 'fallback_gpu_preallocation_bytes': 134217728,
        'loader_required': 'sleepingdogs-gpu-budget-v1', 'minimum_heap_bytes': 2046820352,
        'forwarder_reinstall_required': True, 'hardware_tested': False})
    if 'dep_notification' in context_receipt:
        write_json(prefix / 'launcher/dep-policy-fix.json', {
            'build': 'sleepingdogs-wow64-dep-notification-v1',
            'wow64_sha256': sha(wow64), 'nro_sha256': sha(nro),
            'policy_forced': False, 'hardware_tested': False})
    fex = ROOT / 'vendor/fex/libwow64fex-sd-scene.dll'
    policy = json.loads((ROOT / 'vendor/fex/libwow64fex-sd-scene.json').read_text())
    if sha(fex) != policy['sha256']:
        raise RuntimeError('FEX binary differs from its pinned receipt')
    shutil.copy2(fex, prefix / 'drive_c/windows/system32/libwow64fex.dll')
    write_json(prefix / 'launcher/fex-memory-policy.json', policy)
    write_json(prefix / 'launcher/fex-debug-fix.json', policy['debug_register_build'])
    write_json(prefix / 'launcher/compiler-memory-fix.json', {
        'build': 'sleepingdogs-compiler-memory-v2', 'nro_sha256': sha(nro),
        'dll_sha256': sha(fex), 'compile_slots': 2, 'scratch_reserve_bytes': 33685504,
        'decoder_reserve_bytes': 65536, 'ir_reserve_bytes': 16777216, 'hardware_tested': False})
    write_json(prefix / 'launcher/scene-memory-fix.json', {
        'build': 'sleepingdogs-scene-memory-v1', 'nro_sha256': sha(nro),
        'dll_sha256': sha(fex), 'compile_slots': 2, 'scratch_reserve_bytes': 33685504,
        'profile': 'fastest', 'hardware_tested': False})
    shutil.copy2(nro, prefix / f'{APP_ID}.nro')
    memory_receipt = {'fix': 'sleepingdogs-direct-data-arena-v1', 'nro_sha256': sha(nro),
                      'arena_bytes': 1048576000, 'gpu_preallocation_bytes': 268435456,
                      'virtual_alias_bytes': 0, 'hardware_tested': False,
                      'sources': {name: sha(ROOT / name) for name in
                                  ('src/sd_guest_arena.c', 'src/sd_guest_arena.h',
                                   'src/sd_guest_view.inc', 'tools/sleepingdogs_memory.py')}}
    write_json(prefix / 'launcher/direct-arena-fix.json', memory_receipt)
    write_json(prefix / 'launcher/named-pipe-fix.json', {
        'build': 'sleepingdogs-local-named-pipe-v1', 'nro_sha256': sha(nro),
        'hardware_tested': False, 'game_boot_confirmed': False,
        'sources': {name: sha(ROOT / name) for name in
                    ('src/sd_named_pipe.inc', 'src/sd_named_pipe.h', 'tools/sleepingdogs_named_pipe.py')}})
    shutil.copy2(ROOT / 'config/configuration.ini', prefix / 'configuration.ini')
    settings = {'launcher/selected.txt': '2', 'launcher/renderer-choice.txt': '0',
                'launcher/renderer.txt': '0', 'launcher/fex-mode.txt': 'fastest',
                'launcher/report-memory-mb.txt': '0', 'controller-keyboard.txt': '0',
                'controller-gamepad.txt': '1', 'fex_short_trace_off': '',
                'fex_fast_api': '', 'fex_auto_core3': '', 'fex_dxvk_balance': '',
                'fex_polling': '', 'launcher/background-music.txt': '0'}
    for relative, value in settings.items():
        write_lf(prefix / relative, value + '\n' if value else '')
    write_lf(game / 'COPY-YOUR-GAME-HERE.txt',
             'Copy the contents of your installed original Sleeping Dogs PC game here.\n'
             'HKShip.exe, all BIG/BIX archives, Data/ and original game DLLs are required.\n'
             'Keep package-supplied d3d9.dll, d3d11.dll, dxgi.dll and dxvk.conf.\n')
    shutil.copy2(ROOT / 'README.md', output / 'README.md')
    licenses = output / 'licenses'
    licenses.mkdir()
    shutil.copy2(ROOT / 'LICENSE', licenses / 'FEXTendo-LGPL-2.1.txt')
    shutil.copy2(ROOT / 'docs/PES13-THIRD-PARTY.md', licenses / 'THIRD_PARTY.md')
    for p in sorted((PES / 'licenses').rglob('*')):
        if p.is_file():
            target = licenses / p.relative_to(PES / 'licenses')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    for p in (ROOT / 'vendor/dxvk').glob('*LICENSE*'):
        shutil.copy2(p, licenses / p.name)
    report = {'version': VERSION, 'title': TITLE, 'game_included': False,
              'hardware_tested': False, 'game': metadata, 'nro_sha256': sha(nro),
              'runtime_source': str(APPROVED), 'dxvk': renderers,
              'fex_sha256': sha(fex), 'address_space': '32-bit no-alias',
              'wow64_context_fix': context_receipt,
              'direct_arena_fix': memory_receipt,
              'runtime_dlls': {p.name: sha(p) for p in dlls},
              'files': {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    write_json(output / 'build-report.json', report)
    return report


def package(output):
    archive = output.with_name(output.name + '.zip')
    if archive.exists():
        raise RuntimeError(f'Archive already exists: {archive}')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(output.rglob('*')):
            if p.is_file() or not any(p.iterdir()):
                z.write(p, p.relative_to(output).as_posix())
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path.home() / 'sleepingdogs-fex-build')
    parser.add_argument('--pes-build-root', type=Path, default=Path('/home/blekjek/pes13-build'))
    parser.add_argument('--game', type=Path, default=DEFAULT_GAME / GAME_EXE)
    parser.add_argument('--output', type=Path, default=ROOT / f'dist/{APP_ID}-{VERSION}-sd')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--build-only', action='store_true')
    args = parser.parse_args()
    if os.name != 'posix':
        parser.error('Compile with WSL/Linux and the installed devkitPro toolchain')
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    source, metadata = prepare(work, args.game.resolve())
    write_json(ROOT / 'reports/game-pe.json', metadata)
    if args.prepare_only:
        print(json.dumps({'source': str(source), 'game': metadata}, indent=2))
        return
    elf, nro = build_nro(work, source, args.pes_build_root.resolve(), args.jobs)
    if args.build_only:
        print(json.dumps({'elf': str(elf), 'nro': str(nro)}, indent=2))
        return
    dlls = base.build_runtime_dlls(work, args.pes_build_root.resolve(), args.jobs)
    wow64, context_receipt = build_wow64_context(work / 'wow64-context', args.pes_build_root.resolve(), args.jobs)
    report = stage(nro, args.output.resolve(), dlls, metadata, wow64, context_receipt)
    report['elf_sha256'] = sha(elf)
    report['build_inputs'] = json.loads((work / 'sleepingdogs-prepared.json').read_text())['identity']
    write_json(args.output / 'build-report.json', report)
    print(json.dumps({'package': str(package(args.output)), 'nro_sha256': report['nro_sha256'],
                      'hardware_tested': False}, indent=2))


if __name__ == '__main__':
    main()
