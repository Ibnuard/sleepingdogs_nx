"""Build and stage an isolated F1 2013 FEX launcher from the local FEXTendo source receipt.

Run under WSL/Linux.  No game files are copied into the distributable tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from f1_overlay import apply as apply_f1_overlay, IMAGE_SIZE
from dxvk_runtime import stage_renderers, write_lf


ROOT = Path(__file__).resolve().parents[1]
PES = ROOT.parent / "pes13-nx"
APPROVED = PES / "local/production-input-fix/approved"
BASE = APPROVED / "switch/pes13-fex"
SOURCE_ARCHIVE = PES / "local/production-input-fix/wine-source.tar.gz"
GENERATED = APPROVED / "source/generated/wine/native-source"
OLD_INCLUDE_ROOT = "/Users/ibnuputra/Desktop/NDSClient/SW/pes13_nx/local/fex3/production-v1-launchfix/project/src/runtime/"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    print("+", " ".join(map(str, command)), flush=True)
    return subprocess.run([str(x) for x in command], check=True, **kwargs)


def pe_image_size(path: Path) -> int:
    with path.open("rb") as f:
        if f.read(2) != b"MZ":
            raise ValueError("F1 executable is not PE/MZ")
        f.seek(0x3c)
        offset = struct.unpack("<I", f.read(4))[0]
        f.seek(offset)
        if f.read(4) != b"PE\0\0":
            raise ValueError("F1 executable has no PE header")
        machine = struct.unpack("<H", f.read(2))[0]
        f.seek(offset + 24)
        magic = struct.unpack("<H", f.read(2))[0]
        f.seek(offset + 24 + 28)
        base = struct.unpack("<I", f.read(4))[0]
        f.seek(offset + 24 + 56)
        size = struct.unpack("<I", f.read(4))[0]
    if (machine, magic, base) != (0x14c, 0x10b, 0x400000):
        raise ValueError(f"Unexpected F1 PE layout: {(machine, magic, base)!r}")
    return size


def prepare_source(work: Path, game_exe: Path) -> Path:
    source = work / "native-source"
    stamp = work / "prepared.json"
    identity = {"source_archive_sha256": sha(SOURCE_ARCHIVE),
                "generated_runtime_sha256": sha(GENERATED / "wine-nx-probe/source/runtime.c"),
                "overlay_sha256": sha(ROOT / "tools/f1_overlay.py"),
                "settings_sha256": sha(ROOT / "tools/f1_settings.h"),
                "render_sha256": sha(ROOT / "tools/f1_render.inc"),
                "renderers_sha256": sha(ROOT / "tools/f1_renderers.inc"),
                "window_dialog_sha256": sha(ROOT / "tools/f1_window_dialog.inc"),
                "crypto_registry_sha256": sha(ROOT / "tools/f1_crypto_registry.h"),
                "startup_watch_sha256": sha(ROOT / "tools/f1_startup_watch.h"),
                "startup_monitor_sha256": sha(ROOT / "tools/f1_startup_monitor.inc"),
                "thread_snapshot_sha256": sha(ROOT / "tools/f1_thread_snapshot.inc"),
                "thread_diagnostics_sha256": sha(ROOT / "tools/f1_thread_diagnostics.c"),
                "fex_memory_inputs": {name: sha(ROOT / 'tools' / name) for name in
                                      ('f1_fex_memory.py', 'f1_fex_spare.py')},
                "native_stack_inputs": {name: sha(ROOT / 'tools' / name) for name in
                                        ('f1_native_stacks.c', 'f1_native_stacks.h', 'f1_thread_stack_overlay.py')},
                "thread_budget_sha256": sha(ROOT / "tools/f1_thread_budget.c"),
                "crash_sha256": sha(ROOT / "tools/f1_crash.c"),
                "crash_overlay_sha256": sha(ROOT / "tools/f1_crash_overlay.py"),
                "relaunch_inputs": {name: sha(ROOT / 'tools' / name) for name in
                                    ('f1_relaunch.c', 'f1_relaunch.h', 'f1_log_rotation.h', 'f1_relaunch_overlay.py')},
                "apc_queue_sha256": sha(ROOT / "tools/f1_apc_queue.h"),
                "apc_server_sha256": sha(ROOT / "tools/f1_apc_server.inc"),
                "apc_dispatch_sha256": sha(ROOT / "tools/f1_apc_dispatch.inc"),
                "memory_audio_overlay_sha256": sha(ROOT / "tools/f1_memory_audio_overlay.py"),
                "scratch_sha256": sha(ROOT / "tools/f1_scratch.h"),
                "native_heap_sha256": sha(ROOT / "tools/f1_native_heap.c"),
                "gpu_heap_inputs": {name: sha(ROOT / 'tools' / name) for name in
                                    ('f1_gpu_heap.c', 'f1_gpu_arena.h', 'gpu_heap_binding.py')},
                "crash_detail_sha256": sha(ROOT / "tools/f1_crash_detail.h"),
                "fex_mode_sha256": sha(ROOT / "tools/f1_fex_mode.h"),
                "native_heap_inputs": {p.name: sha(p) for p in sorted((ROOT / "tools/native_heap").iterdir())
                                       if p.is_file()},
                "scratch_pages_inputs": {p.name: sha(p) for p in sorted((ROOT / "tools/scratch_pages").iterdir())
                                         if p.is_file()},
                "audio_registry_sha256": sha(ROOT / "tools/f1_audio_registry.h"),
                "game_config_sha256": sha(ROOT / "tools/f1_game_config.h"),
                "circuit_overlay_sha256": sha(ROOT / "tools/f1_circuit_overlay.py"),
                "guest_failure_sha256": sha(ROOT / "tools/f1_guest_failure.h"),
                "vk_recovery_sha256": sha(ROOT / "tools/f1_vk_recovery.h"),
                "page_store_inputs": {p.name: sha(p) for p in sorted((ROOT / "tools/page_store").iterdir())
                                      if p.suffix in ('.py', '.h')},
                "adapter_jit_sha256": sha(APPROVED / "source/src/fex/horizon_jit.c"),
                "game_exe_sha256": sha(game_exe), "image_size": pe_image_size(game_exe)}
    if stamp.exists():
        if json.loads(stamp.read_text()) != identity:
            raise RuntimeError("Build inputs changed; use a fresh --work directory")
        rebase_includes(source)
        return source
    if source.exists():
        raise RuntimeError(f"Untracked source tree: {source}; use a fresh --work directory")
    source.mkdir(parents=True)
    run(["tar", "-xzf", SOURCE_ARCHIVE, "--strip-components=1", "-C", source])
    for file in GENERATED.rglob("*"):
        if file.is_file():
            target = source / file.relative_to(GENERATED)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
    rebase_includes(source)
    preload = source / "wine-nx-probe/source/pes13_preload.c"
    shutil.copy2(PES / "src/runtime/pes13_preload.c", preload)
    apply_f1_overlay(source, identity["image_size"])
    from f1_memory_audio_overlay import apply as apply_memory_audio, patch_scratch
    apply_memory_audio(source)
    from f1_circuit_overlay import apply as apply_circuit
    apply_circuit(source)
    from f1_relaunch_overlay import apply as apply_relaunch
    apply_relaunch(source)
    from f1_thread_stack_overlay import apply as apply_thread_stack
    apply_thread_stack(source)
    runtime_path = source / 'wine-nx-probe/source/runtime.c'
    text = runtime_path.read_text()
    marker = '    const unsigned fex_profile = pes13_fex_select_performance_profile('
    assert text.count(marker) == 1
    text = text.replace(marker, '    wine_nx_f1_native_stacks_init();\n    wine_nx_f1_gpu_heap_init();\n' + marker)
    text = text.replace('#include "f1_relaunch.h"', '#include "f1_relaunch.h"\n#include "f1_native_stacks.h"')
    text = text.replace('#include "f1_native_stacks.h"', '#include "f1_native_stacks.h"\nextern void wine_nx_f1_gpu_heap_init(void);')
    runtime_path.write_text(text)
    for name in ('f1_native_stacks.c', 'f1_native_stacks.h'):
        (source / 'wine-nx-probe/source' / name).write_bytes((ROOT / 'tools' / name).read_bytes())
    with (source / 'wine-nx-probe/CMakeLists.txt').open('a') as f:
        f.write('\ntarget_sources(wine-nx-runtime PRIVATE source/f1_native_stacks.c)\n')
        f.write('target_link_options(wine-nx-runtime PRIVATE -Wl,--wrap=threadClose)\n')
    adapter = work / "fex-adapter"
    shutil.copytree(APPROVED / "source/src/fex", adapter)
    from f1_fex_memory import apply as apply_fex_memory
    apply_fex_memory(adapter)
    jit = adapter / "horizon_jit.c"
    jit.write_text(patch_scratch(jit.read_text()))
    (adapter / "f1_scratch.h").write_bytes((ROOT / "tools/f1_scratch.h").read_bytes())
    shutil.copytree(ROOT / "tools/scratch_pages", adapter / "scratch_pages")
    # Replace libnx's complete manager ABI so all Wine/FEX/thread reservations
    # use one lock and list. The archive's original virtmem.o is not extracted.
    virtmem = source / "wine-nx-probe/source/fextendo_virtmem.c"
    virtmem.write_bytes((ROOT / "tools/scratch_pages/fextendo_virtmem.c").read_bytes())
    cmake = source / "wine-nx-probe/CMakeLists.txt"
    with cmake.open('a') as f:
        f.write('\ntarget_sources(wine-nx-runtime PRIVATE source/fextendo_virtmem.c source/f1_native_heap.c)\n')
        f.write('target_link_options(wine-nx-runtime PRIVATE -Wl,--wrap=write)\n')
    runtime_dir = source / "wine-nx-probe/source"
    for name in ('f1_native_heap.c', 'f1_crash_detail.h', 'f1_fex_mode.h'):
        (runtime_dir / name).write_bytes((ROOT / 'tools' / name).read_bytes())
    (runtime_dir / 'f1_gpu_heap.c').write_bytes((ROOT / 'tools/f1_gpu_heap.c').read_bytes())
    (runtime_dir / 'f1_gpu_arena.h').write_bytes((ROOT / 'tools/f1_gpu_arena.h').read_bytes())
    shutil.copytree(ROOT / 'tools/native_heap', runtime_dir / 'native_heap',
                    ignore=shutil.ignore_patterns('__pycache__'))
    from f1_overlay import exact
    runtime=runtime_dir/'runtime.c'
    data=runtime.read_text()
    old='''    const unsigned fex_profile = pes13_fex_select_performance_profile(guest_tests,
        wine_nx_config_file_bool(RUNTIME_DIR "/fex-fast.txt", 1),
        wine_nx_config_file_bool(RUNTIME_DIR "/fex-fastest.txt", 0),
        wine_nx_config_file_bool(RUNTIME_DIR "/fex-relaxed-vectors.txt", 0));'''
    data=exact(data,old,'    const unsigned fex_profile = f1_select_fex_profile(guest_tests);')
    data=exact(data,'int main( int argc, char **argv )', '#include "f1_fex_mode.h"\n\nint main( int argc, char **argv )')
    runtime.write_text(data)
    stamp.write_text(json.dumps(identity, indent=2) + "\n")
    return source


def rebase_includes(source: Path):
    new_root = str(APPROVED / "source/src/runtime") + "/"
    for file in GENERATED.rglob("*"):
        if file.suffix not in (".c", ".h") or not file.is_file():
            continue
        target = source / file.relative_to(GENERATED)
        data = target.read_text()
        if OLD_INCLUDE_ROOT in data:
            target.write_text(data.replace(OLD_INCLUDE_ROOT, new_root))
    registry = source / "dlls/ntdll/unix/pes13_registry.h"
    if not registry.exists():
        shutil.copy2(APPROVED / "source/src/runtime/pes13_registry.h", registry)
    runtime_headers = source / "wine-nx-probe/source"
    for header in (APPROVED / "source/src/runtime").glob("*.h"):
        target = runtime_headers / header.name
        if not target.exists():
            shutil.copy2(header, target)


def build_nro(work: Path, source: Path, base_build: Path, jobs: int) -> tuple[Path, Path]:
    devkit = Path("/opt/devkitpro")
    mesa = base_build / "mesa-vulkan/install/opt/devkitpro/portlibs/switch/lib"
    pe = base_build / "pe"
    if not (mesa / "libvulkan.a").is_file() or not (pe / "include").is_dir():
        raise RuntimeError("PES13 WSL build dependencies are missing")
    sdk = devkit / "devkitA64/bin"
    # The reserved caller-stack ABI was reviewed against these exact libnx
    # objects (TLS/reent padding, failed-create cleanup and pthread close).
    native_stack_sdk = {}
    for name, expected in {
        'thread.o': 'cba25872a0d58f30fc66b868a3eee80360e1ee647e0fc21e3346072fa0a96785',
        'newlib.o': '49b209c664eb670d1aaeb0c0ce5319b4b84e6a1da92dbd45033b17c54ce94815',
        'alloc.o': '5f4403dded5dbb28e9e4a6407bd5a8a64f21814f9694e498906d401f4c7fa63f',
    }.items():
        data = subprocess.check_output([sdk / 'aarch64-none-elf-ar', 'p', devkit / 'libnx/lib/libnx.a', name])
        native_stack_sdk[name] = hashlib.sha256(data).hexdigest()
        assert native_stack_sdk[name] == expected, f'Unreviewed native stack ABI: {name}'
    (work / 'native-stack-sdk.json').write_text(json.dumps(native_stack_sdk, indent=2) + '\n')
    tc = base_build / "toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin"
    from native_heap.rust_patches import apply as rust_apply, NAK_SHA256
    from native_heap.mesa_patches import apply as mesa_apply, LIB_SHA256
    assert sha(mesa / 'libnak_rs.a') == NAK_SHA256, 'Unreviewed Rust allocator ABI'
    assert sha(mesa / 'libmesa_util.a') == LIB_SHA256, 'Unreviewed Mesa ralloc object'
    binding_path = work / 'native-heap-binding.json'
    if not binding_path.exists():
        feature = work / 'native-heap'; feature.mkdir(exist_ok=True)
        cmake = source / 'wine-nx-probe/CMakeLists.txt'
        rust_binding = rust_apply(mesa / 'libnak_rs.a', source / 'wine-nx-probe/source/native_heap', cmake)
        mesa_binding = mesa_apply(mesa / 'libmesa_util.a', feature, cmake, devkit)
        binding_path.write_text(json.dumps({'rust': rust_binding, 'mesa': mesa_binding}, indent=2)+'\n')
    gpu_receipt = work / 'gpu-heap-binding.json'
    if not gpu_receipt.exists():
        from gpu_heap_binding import apply as gpu_apply
        gpu_binding = gpu_apply(mesa / 'libvulkan.a', work / 'gpu-heap',
                               source / 'wine-nx-probe/CMakeLists.txt', devkit)
        gpu_receipt.write_text(json.dumps(gpu_binding, indent=2)+'\n')
    env = dict(os.environ, DEVKITPRO=str(devkit), DEVKITA64=str(devkit / "devkitA64"),
               PATH=f"{tc}:{sdk}:{devkit}/tools/bin:" + os.environ["PATH"])
    exception = work / "libnx-exception.o"
    with exception.open("wb") as f:
        run([sdk / "aarch64-none-elf-ar", "p", devkit / "libnx/lib/libnx.a", "exception.o"], stdout=f, env=env)
    run([sdk / "aarch64-none-elf-objcopy", "--redefine-sym",
         "__libnx_exception_entry=pes13_libnx_exception_entry", exception], env=env)
    build = work / "native-build"
    adapter = work / "fex-adapter"
    run(["cmake", "-S", source / "wine-nx-probe", "-B", build, "-G", "Ninja",
         "-DCMAKE_TOOLCHAIN_FILE=" + str(source / "wine-nx-probe/cmake/switch-devkitA64.cmake"),
         "-DWINE_NX_PE_BUILD_DIR=" + str(pe),
         "-DWINE_NX_BOX64_DYNAREC=OFF", "-DWINE_NX_BOX64_INTERPRETER=OFF",
         "-DWINE_NX_STOCK_MESA=OFF", "-DWINE_NX_MESA_SWITCH_DIR=" + str(mesa),
         "-DPES13_FEX_DIR=" + str(adapter),
         "-DPES13_LIBNX_EXCEPTION_OBJECT=" + str(exception),
         "-DCMAKE_BUILD_TYPE=Release"], env=env)
    run(["cmake", "--build", build, "--target", "wine-nx-runtime", "-j", jobs], env=env)
    elf = build / "wine-nx-runtime.elf"
    nacp = work / "f1-fex.nacp"
    nro = work / "f1-fex.nro"
    run([devkit / "tools/bin/nacptool", "--create", "F1 2013 - FEXTendo",
         "AndroSwitch Project", "0.1.28", nacp], env=env)
    run([devkit / "tools/bin/elf2nro", elf, nro, "--nacp=" + str(nacp),
         "--icon=" + str(ROOT / "dist/launcher/nro-icon.jpg")], env=env)
    return elf, nro


def build_runtime_dlls(work: Path, base_build: Path, jobs: int) -> list[Path]:
    build = work / "pe-build"
    build.mkdir(exist_ok=True)
    env = dict(os.environ, PATH=str(base_build / "toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin")
               + os.pathsep + os.environ["PATH"])
    if not (build / "Makefile").is_file():
        run([base_build / "source/configure", "-C", "--enable-archs=aarch64,i386",
             "--enable-winebox64=aarch64", "--without-x", "--without-freetype"],
            cwd=build, env=env)
    # rsaenh is loaded dynamically by advapi32, so static imports do not find it.
    names = ("d3dcompiler_43", "d3dx9_43", "rsaenh", "xaudio2_7", "mfplat", "mfreadwrite", "rtworkq")
    targets = [f"dlls/{name}/i386-windows/{name}.dll" for name in names]
    run(["make", "-C", build, "-j", jobs, *targets], env=env)
    return [build / target for target in targets]


def profile_config(profile: str, async_mode: bool) -> str:
    data = ["# F1 2013 FEX DXVK profile", "d3d9.presentInterval = 1", "dxgi.syncInterval = 1",
            "# Shared 2 GiB heap: advertise a modest graphics allowance to F1.",
            "dxgi.maxDeviceMemory = 512", "dxgi.maxSharedMemory = 128",
            "dxvk.numCompilerThreads = 1",
            "# Avoid the descriptor-copy std::thread and descriptor heaps during startup.",
            "dxvk.enableDescriptorBuffer = False", "dxvk.enableDescriptorHeap = False"]
    if async_mode:
        data.append("dxvk.enableAsync = True")
    if profile == "low-latency":
        data += ["d3d9.maxFrameLatency = 1", "d3d9.maxFrameRate = -1",
                 "dxgi.maxFrameLatency = 1", "dxgi.maxFrameRate = -1"]
    elif profile == "stable":
        data += ["d3d9.maxFrameLatency = 2", "d3d9.samplerAnisotropy = 0",
                 "dxgi.maxFrameLatency = 2", "d3d11.samplerAnisotropy = 0"]
    elif profile == "quality":
        data += ["d3d9.maxFrameLatency = 2", "d3d9.samplerAnisotropy = 4",
                 "dxgi.maxFrameLatency = 2", "d3d11.samplerAnisotropy = 4"]
    else:
        data += ["d3d9.maxFrameLatency = 2", "dxgi.maxFrameLatency = 2"]
    return "\n".join(data) + "\n"


def stage(nro: Path, output: Path, directx: list[Path], game_dir: Path | None = None):
    if output.exists():
        raise RuntimeError(f"Output already exists: {output}")
    prefix = output / "switch/f1-fex"
    shutil.copytree(BASE, prefix)
    (prefix / "pes13-fex.nro").unlink()
    game_target = prefix / "drive_c/F1_2013"
    shutil.copytree(prefix / "drive_c/PES13", game_target)
    shutil.rmtree(prefix / "drive_c/PES13")
    # PES profile files are not F1 settings.  No game/save data is distributed.
    for path in (prefix / "drive_c/KONAMI", prefix / "drive_c/users/steamuser/Documents/KONAMI"):
        if path.exists():
            shutil.rmtree(path)
    presets = prefix / "launcher/presets"
    shutil.rmtree(presets)
    for profile in ("balanced", "low-latency", "stable", "quality"):
        for renderer in ("dxvk-3.1.1", "dxvk-2.7.1-async"):
            path = presets / profile / renderer / "dxvk.conf"
            path.parent.mkdir(parents=True, exist_ok=True)
            write_lf(path, profile_config(profile, renderer.endswith("async")))
    write_lf(presets / "dxvk.conf", profile_config("balanced", False))
    write_lf(prefix / "launcher/selected.txt", "0\n")
    write_lf(prefix / "launcher/renderer-choice.txt", "0\n")
    write_lf(prefix / "launcher/fex-mode.txt", "fastest\n")
    renderer_receipt = stage_renderers(prefix, profile_config)
    for name in ("d3d9.dll", "d3d11.dll", "dxgi.dll", "dxvk.conf"):
        shutil.copy2(prefix / "launcher/renderers/dxvk-3.1.1" / name, game_target / name)
    for file in (ROOT / "dist/launcher").iterdir():
        if file.suffix in (".rgba", ".bin", ".jpg", ".json"):
            shutil.copy2(file, prefix / "launcher" / file.name)
    shutil.copy2(nro, prefix / "f1-fex.nro")
    for dll in directx:
        shutil.copy2(dll, prefix / "drive_c/windows/syswow64" / dll.name)
    (prefix / "configuration.ini").write_text(
        "# F1 2013 launcher; launcher/fex-mode.txt selects FEX Fastest.\n"
        "run_guest_tests=0\nproduction=1\nprofile=0\nno_balance=0\n"
        "controller_keyboard=0\ncontroller_gamepad=0\ncontroller_trace=0\n"
        "controller_test=0\nno_display_devices=0\nvulkan_probe=0\n"
        "fex_fast=1\nfex_fastest=1\n")
    if game_dir:
        for file in game_dir.rglob("*"):
            if file.is_file():
                destination = game_target / file.relative_to(game_dir)
                if destination.exists():
                    raise RuntimeError(f"Game file would overwrite runtime: {destination}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, destination)
    else:
        (game_target / "COPY-YOUR-F1-FILES-HERE.txt").write_text(
            "Copy the contents of your own F1 2013 PC installation here, including F1_2013.exe.\n")
    report = {"nro_sha256": sha(prefix / "f1-fex.nro"), "game_included": bool(game_dir),
              "hardware_tested": False, "runtime_source": str(APPROVED),
              "output": str(prefix), "dxvk_releases": renderer_receipt}
    if game_dir:
        report["game_exe_sha256"] = sha(game_target / "F1_2013.exe")
    (output / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, default=Path.home() / "f1-fex-build")
    parser.add_argument("--pes-build-root", type=Path,
                        default=Path("/home/blekjek/pes13-build"))
    parser.add_argument("--game", type=Path, default=ROOT / "F1 2013/F1_2013.exe")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/f1-fex-test")
    parser.add_argument("--include-game", action="store_true",
                        help="Copy the supplied local F1 installation into the SD tree")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("Run this build under WSL/Linux with devkitPro")
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    source = prepare_source(work, args.game.resolve())
    if args.prepare_only:
        print(json.dumps({"prepared_source": str(source), "image_size": hex(IMAGE_SIZE)}))
        return
    elf, nro = build_nro(work, source, args.pes_build_root.resolve(), args.jobs)
    directx = build_runtime_dlls(work, args.pes_build_root.resolve(), args.jobs)
    output = args.output.resolve()
    report = stage(nro, output, directx,
                   args.game.resolve().parent if args.include_game else None)
    report["elf_sha256"] = sha(elf)
    report["runtime_dlls_sha256"] = {p.name: sha(p) for p in directx}
    (output / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
