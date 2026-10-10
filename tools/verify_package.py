"""Check NRO metadata, renderer hashes, x86 imports and Sleeping Dogs isolation."""
import argparse
import json
import sys
from pathlib import Path
import pefile

from port_common import ROOT, PES, TITLE, VERSION, APP_ID, GAME_DIR, GAME_EXE, pe_info, sha, write_json
from f1_dependency_audit import audit_guest_dependencies
sys.path.insert(0, str(PES / 'tools'))
from nro_assets import inspect_nro


def verify(prefix):
    prefix = prefix.resolve()
    game = prefix / 'drive_c' / GAME_DIR
    metadata = pe_info(game / GAME_EXE)
    nro = prefix / f'{APP_ID}.nro'
    nro_metadata = inspect_nro(nro.read_bytes(), (prefix / 'launcher/nro-icon.jpg').read_bytes(),
                               expected_title=TITLE, expected_version=VERSION)
    if any((prefix / 'drive_c' / stale).exists() for stale in ('F1_2013', 'PES13', 'KONAMI')):
        raise RuntimeError('Another game prefix leaked into the Sleeping Dogs package')
    for token in (b'switch/f1-fex', b'switch/pes13-fex', b'F1_2013.exe', b'pes2013.exe', b'0x00cae1b0'):
        if token in nro.read_bytes():
            raise RuntimeError(f'Stale game identity in NRO: {token!r}')
    for name in ('Animation', 'AnimationNIS', 'Characters', 'Game', 'Global', 'SeekFreeBoot', 'UI', 'Vehicles'):
        for extension in ('big', 'bix'):
            if not (game / f'{name}.{extension}').is_file():
                raise RuntimeError(f'Missing game data: {name}.{extension}')
    for name in ('binkw32.dll', 'steam_api.dll'):
        if not (game / name).is_file():
            raise RuntimeError(f'Missing original game companion: {name}')
    receipts = json.loads((prefix / 'launcher/dxvk-releases.json').read_text())
    dependency_reports = {}
    for renderer, receipt in receipts.items():
        for name, expected in receipt['dlls'].items():
            if sha(prefix / 'launcher/renderers' / renderer / name) != expected:
                raise RuntimeError(f'Renderer hash mismatch: {renderer}/{name}')
        dependency_reports[renderer] = audit_guest_dependencies(prefix, renderer)
    active = receipts['dxvk-3.1.1']['dlls']
    for name, digest in active.items():
        if sha(game / name) != digest:
            raise RuntimeError(f'Unexpected active renderer DLL: {name}')
    renderer_patch = receipts['dxvk-3.1.1'].get('patch', {})
    if renderer_patch.get('build') in ('sleepingdogs-dxvk-sdmem1', 'sleepingdogs-dxvk-sdstream1', 'sleepingdogs-dxvk-sdrecycle1'):
        if renderer_patch['pool_cap_bytes'] != 2097152:
            raise RuntimeError('Unexpected Sleeping Dogs DXVK chunk budget')
        for name, digest in active.items():
            if (renderer_patch['files'][name]['sha256'] != digest or
                    b'[SD-DXVK-MEM] v1 pool cap=2 MiB' not in (game / name).read_bytes()):
                raise RuntimeError(f'Sleeping Dogs DXVK build receipt mismatch: {name}')
        if b'[SD-DXVK-MAP] deferred buffer allocation failed' not in (game / 'd3d11.dll').read_bytes():
            raise RuntimeError('Sleeping Dogs DXVK lacks deferred Map failure handling')
        if sha(prefix / 'drive_c/dxvk/d3d9.dll') != active['d3d9.dll']:
            raise RuntimeError('Shared D3D9 copy does not match the Sleeping Dogs renderer')
    streaming = prefix / 'launcher/streaming-memory-fix.json'
    if streaming.is_file():
        stream = json.loads(streaming.read_text())
        if not stream.get('rolled_back'):
            if (stream['nro_sha256'] != sha(nro) or stream['dxvk_dlls'] != active or
                stream['gpu_preallocation_bytes'] != 268435456 or stream['large_reserve_bytes'] != 67108864 or
                stream['borrow_guard_bytes'] != 16777216 or stream['threshold_bytes'] != 2097152 or
                b'[SD-GPU-STREAM] v1' not in nro.read_bytes() or
                renderer_patch.get('build') not in ('sleepingdogs-dxvk-sdstream1', 'sleepingdogs-dxvk-sdrecycle1') or
                any(b'[SD-DXVK-STREAM] v1' not in (game / n).read_bytes() for n in active)):
                raise RuntimeError('Streaming memory update requires its matching NRO and renderer set')
    recycle = prefix / 'launcher/buffer-reuse-fix.json'
    if recycle.is_file():
        item = json.loads(recycle.read_text())
        if not item.get('rolled_back'):
            if (item['dxvk_dlls'] != active or item['max_idle_bytes'] != 16777216 or
                    item['max_idle_count'] != 4 or item['retired_only'] is not True or
                    renderer_patch.get('build') != 'sleepingdogs-dxvk-sdrecycle1' or
                    renderer_patch.get('max_idle_bytes') != 16777216 or
                    any(b'[SD-DXVK-RECYCLE] v1 retired-only exact-size-type max_idle_mib=16' not in (game / n).read_bytes() for n in active)):
                raise RuntimeError('Buffer reuse update does not match its complete renderer set or cache budget')
    pressure = prefix / 'launcher/gpu-pressure-fix.json'
    if pressure.is_file():
        item = json.loads(pressure.read_text())
        if not item.get('rolled_back'):
            if (item['nro_sha256'] != sha(nro) or item['dxvk_dlls'] != active or
                    item['gpu_preallocation_bytes'] != 268435456 or item['reserve_is_soft'] is not True or
                    b'[SD-GPU-PRESSURE] v1 soft_reserve=1' not in nro.read_bytes()):
                raise RuntimeError('GPU pressure recovery does not match its NRO/renderer receipt')
    with pefile.PE(str(prefix / 'drive_c/windows/system32/libwow64fex.dll')) as fex:
        if fex.FILE_HEADER.Machine != 0xaa64:
            raise RuntimeError('FEX module must be ARM64')
    policy = json.loads((prefix / 'launcher/fex-memory-policy.json').read_text())
    if sha(prefix / 'drive_c/windows/system32/libwow64fex.dll') != policy['sha256']:
        raise RuntimeError('Wrong FEX module')
    if 'debug_register_build' in policy:
        debug_fix = json.loads((prefix / 'launcher/fex-debug-fix.json').read_text())
        if debug_fix['dll_sha256'] != policy['sha256'] or debug_fix != policy['debug_register_build']:
            raise RuntimeError('FEX debug-register receipt does not match the DLL')
        if b'[SD-DB] execution-breakpoints v1' not in (prefix / 'drive_c/windows/system32/libwow64fex.dll').read_bytes():
            raise RuntimeError('FEX DLL lacks execution-breakpoint support')
    context_fix = json.loads((prefix / 'launcher/wow64-context-fix.json').read_text())
    if sha(prefix / 'drive_c/windows/system32/wow64.dll') != context_fix['dll_sha256']:
        raise RuntimeError('WoW64 context fix does not match its build receipt')
    dep_receipt = prefix / 'launcher/dep-policy-fix.json'
    if dep_receipt.is_file():
        dep = json.loads(dep_receipt.read_text())
        if not dep.get('rolled_back'):
            wow = prefix / 'drive_c/windows/system32/wow64.dll'
            if dep['wow64_sha256'] != sha(wow) or dep['nro_sha256'] != sha(nro):
                raise RuntimeError('DEP policy bridge does not match runtime receipts')
            if b'BTCpuNotifyProcessExecuteFlagsChange' not in wow.read_bytes():
                raise RuntimeError('WoW64 DLL lacks CPU execute-policy notification')
    cache_receipt = prefix / 'launcher/debug-cache-fix.json'
    if cache_receipt.is_file():
        cache = json.loads(cache_receipt.read_text())
        if not cache.get('rolled_back'):
            if cache['nro_sha256'] != sha(nro) or b'[SD-TEB-DEBUG] build=v1' not in nro.read_bytes():
                raise RuntimeError('TEB debug-cache repair does not match its NRO receipt')
    thread_receipt = prefix / 'launcher/thread-debug-fix.json'
    if thread_receipt.is_file():
        thread_debug = json.loads(thread_receipt.read_text())
        if not thread_debug.get('rolled_back'):
            if thread_debug['nro_sha256'] != sha(nro) or b'[SD-THREAD-DEBUG] build=v1' not in nro.read_bytes():
                raise RuntimeError('Suspended-thread debug context does not match its NRO receipt')
    memory_fix = json.loads((prefix / 'launcher/direct-arena-fix.json').read_text())
    if memory_fix['nro_sha256'] != sha(nro) or memory_fix['arena_bytes'] != 1048576000:
        raise RuntimeError('Direct data arena does not match the NRO receipt')
    gpu_bytes = 268435456
    gpu_budget = prefix / 'launcher/gpu-budget-fix.json'
    paired_gpu = None
    if gpu_budget.is_file():
        item = json.loads(gpu_budget.read_text())
        if not item.get('rolled_back'):
            paired_gpu = item
            if (item['nro_sha256'] != sha(nro) or item['gpu_preallocation_bytes'] != 268435456 or
                    item['fallback_gpu_preallocation_bytes'] != 134217728 or
                    item['minimum_heap_bytes'] != 2046820352 or
                    item['loader_required'] != 'sleepingdogs-gpu-budget-v1' or
                    b'[SD-GPU-BUDGET] v1 paired_loader=' not in nro.read_bytes() or
                    b'sleepingdogs-gpu-budget-v1 reserve=32MiB' not in nro.read_bytes()):
                raise RuntimeError('Paired GPU budget does not match its NRO receipt')
    budget_receipt = prefix / 'launcher/memory-budget-fix.json'
    if budget_receipt.is_file():
        budget = json.loads(budget_receipt.read_text())
        if not budget.get('rolled_back'):
            gpu_bytes = 268435456 if paired_gpu else 134217728
            budget_marker = (b'[SD-MEMORY-BUDGET] build=v2 gpu_reserve_max_mib=256' if paired_gpu else
                             b'[SD-MEMORY-BUDGET] build=v1 gpu_reserve_mib=128')
            if (budget['nro_sha256'] != sha(nro) or budget['gpu_preallocation_bytes'] != gpu_bytes or
                    budget_marker not in nro.read_bytes()):
                raise RuntimeError('Native memory budget does not match its NRO receipt')
    if memory_fix['gpu_preallocation_bytes'] != gpu_bytes or memory_fix['virtual_alias_bytes'] != 0:
        raise RuntimeError('Incorrect Sleeping Dogs memory budget')
    compiler_receipt = prefix / 'launcher/compiler-memory-fix.json'
    if compiler_receipt.is_file():
        compiler = json.loads(compiler_receipt.read_text())
        if not compiler.get('rolled_back'):
            version = 2 if compiler.get('build') == 'sleepingdogs-compiler-memory-v2' else 1
            if (compiler['nro_sha256'] != sha(nro) or compiler['dll_sha256'] != policy['sha256'] or
                    compiler['compile_slots'] != (2 if version == 2 else 4) or
                    compiler['scratch_reserve_bytes'] != (33685504 if version == 2 else 67371008) or
                    f'[SD-COMPILER-MEM] native=v{version}'.encode() not in nro.read_bytes() or
                    f'[SD-COMPILER-MEM] fex=v{version}'.encode() not in (prefix / 'drive_c/windows/system32/libwow64fex.dll').read_bytes()):
                raise RuntimeError('Compiler memory update requires its matching NRO and FEX DLL')
    scene_receipt = prefix / 'launcher/scene-memory-fix.json'
    if scene_receipt.is_file():
        scene = json.loads(scene_receipt.read_text())
        if not scene.get('rolled_back'):
            if (scene['nro_sha256'] != sha(nro) or scene['dll_sha256'] != policy['sha256'] or
                    scene['compile_slots'] != 2 or scene['scratch_reserve_bytes'] != 33685504 or
                    not compiler_receipt.is_file() or compiler.get('build') != 'sleepingdogs-compiler-memory-v2'):
                raise RuntimeError('Scene memory update requires the matching two-workspace native/FEX pair')
    if b'[SD-DIRECT] allocated 1000 MiB RW' not in nro.read_bytes():
        raise RuntimeError('NRO has no direct data arena implementation')
    pipe_receipt = prefix / 'launcher/named-pipe-fix.json'
    if pipe_receipt.is_file():
        pipes = json.loads(pipe_receipt.read_text())
        if not pipes.get('rolled_back'):
            if pipes['nro_sha256'] != sha(nro) or b'[SD-PIPE] local named pipes v1' not in nro.read_bytes():
                raise RuntimeError('Named-pipe implementation does not match its NRO receipt')
    if (prefix / 'controller-gamepad.txt').read_text().strip() != '1':
        raise RuntimeError('Expected default XInput gamepad mode')
    return {'status': 'PASS', 'hardware_tested': False, 'game': metadata,
            'nro': nro_metadata, 'nro_sha256': sha(nro), 'dependencies': dependency_reports,
            'wow64_context_fix': context_fix['fix'], 'direct_arena_fix': memory_fix['fix']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, default=ROOT / f'dist/{APP_ID}-ready/switch/{APP_ID}')
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/package-check.json')
    args = parser.parse_args()
    report = verify(args.prefix)
    write_json(args.report, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
