"""Verify the local F1 SD tree and the user's copied game installation."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
from collections import deque

import pefile


ROOT = Path(__file__).resolve().parents[1]
PES = ROOT.parent / "pes13-nx"
sys.path.insert(0, str(PES / "tools"))
from nro_assets import inspect_nro  # noqa: E402


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(root):
    return {str(p.relative_to(root)).lower(): p.stat().st_size
            for p in root.rglob("*") if p.is_file()}


def api_set_map(path):
    """Read the package's actual Wine API-set aliases (namespace version 6)."""
    with pefile.PE(str(path)) as image:
        data = next(section.get_data() for section in image.sections
                    if section.Name.rstrip(b"\0") == b".apiset")
    version, size, _, count, entries, _, _ = struct.unpack_from("<7I", data)
    if version != 6 or size > len(data):
        raise SystemExit("Unsupported or damaged API-set schema")
    aliases = {}
    for index in range(count):
        _, name, length, _, values, value_count = struct.unpack_from("<6I", data, entries + index * 24)
        key = data[name:name + length].decode("utf-16le").lower() + ".dll"
        targets = {}
        for i in range(value_count):
            _, host, host_len, target, target_len = struct.unpack_from("<5I", data, values + i * 20)
            targets[data[host:host + host_len].decode("utf-16le").lower()] = \
                data[target:target + target_len].decode("utf-16le").lower()
        aliases[key] = targets
    return aliases


def audit_guest_dependencies(prefix, renderer=None):
    """Resolve DLLs, named/ordinal imports and forwarders inside F1's C: drive."""
    drive = prefix / "drive_c"
    game = drive / "SleepingDogs"
    system = drive / "windows/syswow64"
    aliases = api_set_map(drive / "windows/system32/apisetschema.dll")
    folders = (prefix / 'launcher/renderers' / renderer, game, system) if renderer else (game, system)
    search = [{p.name.lower(): p for p in folder.iterdir() if p.is_file()} for folder in folders]
    pending = deque([(game / "HKShip.exe", ["HKShip.exe"])])
    # The supplied install includes companions selected through LoadLibrary.
    # Audit their dependency graphs too without executing any Windows code.
    pending.extend((p, ["local game companion", p.name]) for p in game.iterdir()
                   if p.is_file() and p.suffix.lower() == '.dll'
                   and p.name.lower() not in ('d3d9.dll', 'd3d11.dll', 'dxgi.dll'))
    checked, used_aliases = set(), set()
    images, exports, resolved_exports = {}, {}, set()
    unavailable_delay_imports = set()
    import_count = 0
    # advapi32 loads its provider by registry name, outside the PE import graph.
    dynamic_exports = {"rsaenh.dll": (
        "CPAcquireContext", "CPCreateHash", "CPDecrypt", "CPDeriveKey",
        "CPDestroyHash", "CPDestroyKey", "CPEncrypt", "CPExportKey", "CPGenKey",
        "CPGenRandom", "CPGetHashParam", "CPGetKeyParam", "CPGetProvParam",
        "CPGetUserKey", "CPHashData", "CPHashSessionKey", "CPImportKey",
        "CPReleaseContext", "CPSetHashParam", "CPSetKeyParam", "CPSetProvParam",
        "CPSignHash", "CPVerifySignature"),
        "d3d9.dll": ("Direct3DCreate9", "Direct3DCreate9Ex"),
        "d3d11.dll": ("D3D11CreateDevice", "D3D11CreateDeviceAndSwapChain"),
        "dxgi.dll": ("CreateDXGIFactory", "CreateDXGIFactory1", "CreateDXGIFactory2"),
        "dsound.dll": ("DllGetClassObject", "DirectSoundCreate8"),
        "xaudio2_7.dll": ("DllGetClassObject",)}

    def label(path):
        return str(path.relative_to(drive) if path.is_relative_to(drive) else path.relative_to(prefix))

    def find_dll(name, importer):
        name = name.lower()
        if name in aliases:
            used_aliases.add(name)
            options = aliases[name]
            name = options.get(importer.name.lower(), options.get("", ""))
        return next((index[name] for index in search if name in index), None)

    def read_image(path):
        if path not in images:
            image = pefile.PE(str(path), fast_load=True)
            if image.FILE_HEADER.Machine != 0x14c:
                raise SystemExit(f"Non-x86 DLL in guest dependency chain: {path}")
            image.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY[name] for name in
                ("IMAGE_DIRECTORY_ENTRY_IMPORT", "IMAGE_DIRECTORY_ENTRY_EXPORT", "IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT")])
            symbols = {}
            if directory := getattr(image, "DIRECTORY_ENTRY_EXPORT", None):
                for entry in directory.symbols:
                    symbols[entry.ordinal] = entry
                    if entry.name:
                        symbols[entry.name] = entry
            exports[path] = symbols
            images[path] = image
        return images[path]

    def resolve_export(path, symbol, chain, visiting=()):
        key = (path, symbol)
        if key in resolved_exports:
            return
        if key in visiting:
            raise SystemExit(f"Cyclic export forwarder: {' -> '.join(chain)}")
        read_image(path)
        entry = exports[path].get(symbol)
        label = symbol.decode(errors="replace") if isinstance(symbol, bytes) else f"#{symbol}"
        if entry is None or not entry.address:
            raise SystemExit(f"Missing imported function: {' -> '.join(chain)}!{label}")
        if entry.forwarder:
            module, function = entry.forwarder.rsplit(b'.', 1)
            module = module.decode().lower()
            if not module.endswith('.dll'):
                module += '.dll'
            target = find_dll(module, path)
            if target is None:
                raise SystemExit(f"Missing forwarder DLL: {' -> '.join(chain + [module])}")
            pending.append((target, chain + [module]))
            forwarded = int(function[1:]) if function.startswith(b'#') else function
            resolve_export(target, forwarded, chain + [module], visiting + (key,))
        resolved_exports.add(key)

    for name, functions in dynamic_exports.items():
        target = find_dll(name, game / "HKShip.exe")
        if target is None:
            raise SystemExit(f"Missing dynamic Wine/graphics DLL: {name}")
        pending.append((target, ["dynamic LoadLibrary", name]))
        for name_of_function in functions:
            resolve_export(target, name_of_function.encode(), [name])

    while pending:
        path, chain = pending.popleft()
        if path in checked:
            continue
        checked.add(path)
        image = read_image(path)
        for item in getattr(image, "DIRECTORY_ENTRY_IMPORT", []):
            name = item.dll.decode().lower()
            target = find_dll(name, path)
            if target is None:
                raise SystemExit(f"Missing F1 dependency: {' -> '.join(chain + [name])}")
            pending.append((target, chain + [name]))
            for imported in item.imports:
                resolve_export(target, imported.name or imported.ordinal, chain + [name])
                import_count += 1
        # Delay-load imports are optional until a particular feature is used.
        # Record absent ones for correlation with device logs, without treating
        # unused Wine/game features as hard startup requirements.
        for item in getattr(image, "DIRECTORY_ENTRY_DELAY_IMPORT", []):
            if find_dll(item.dll.decode(), path) is None:
                unavailable_delay_imports.add((label(path), item.dll.decode()))
    for image in images.values():
        image.close()
    return {"module_count": len(checked), "api_set_aliases": len(used_aliases),
            "static_imports_resolved": import_count,
            "exports_resolved_including_forwarders": len(resolved_exports),
            "dynamic_providers": {name: len(exports) for name, exports in dynamic_exports.items()},
            "unavailable_delay_imports": sorted(unavailable_delay_imports),
            "modules": sorted(label(p) for p in checked)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path,
                        default=ROOT / "dist/f1-fex-ready/switch/f1-fex")
    parser.add_argument("--game", type=Path, default=ROOT / "F1 2013")
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    game = prefix / "drive_c/F1_2013"
    source = args.game.resolve()
    source_files, copied_files = inventory(source), inventory(game)
    missing = [name for name, size in source_files.items()
               if copied_files.get(name) != size]
    if missing:
        raise SystemExit(f"Game files missing or wrong size: {missing[:10]}")
    exe = game / "F1_2013.exe"
    if sha(exe) != sha(source / "F1_2013.exe"):
        raise SystemExit("F1 executable changed during copy")
    nro = prefix / "f1-fex.nro"
    nro_bytes = nro.read_bytes()
    metadata = inspect_nro(nro_bytes, expected_title="F1 2013 - FEXTendo",
                           expected_version="0.1.28")
    for needle in (b"switch/pes13-fex", "switch/pes13-fex".encode("utf-16le")):
        if needle in nro_bytes:
            raise SystemExit("NRO still contains a PES runtime path")
    expected_target = b"/F1_2013/F1_2013.exe"
    if expected_target not in nro_bytes or b"/PES13/pes2013.exe" in nro_bytes:
        raise SystemExit("NRO target does not point exclusively to F1_2013.exe")
    if b"400000-15ed000" not in nro_bytes or b"400000-1c9a000" in nro_bytes:
        raise SystemExit("Wine preload reservation does not match F1 image size")
    for label in (b"Launch Debug", b"Graphics", b"Keyboard", b"FEXTendo / F1 2013",
                  b"f1-fextendo-0.1.28-memory-map", b"[F1-MEMMAP]", b"[F1-MEMBUDGET]", b"[F1-VKDEVICE]", b"[F1-GPU-HEAP]", b"[F1-THREAD-BUDGET] stage=",
                  b"[F1-PAGES]", b"[F1-GUEST]", b"[F1-GUEST-FRAME]", b"[F1-GUEST-STACK]", b"[F1-VKMEM]",
                  b"/switch/f1-fex/crash.log", b"/switch/f1-fex/crash-previous.log",
                  b"unhandled-native-exception", b"vkCreateSwapchainKHR-enter",
                  b"thread-detach-windows-enter", b"thread-detach-tracking-return",
                  b"native-exit", b"native-_exit",
                  b"[F1-THREAD-LIMIT] stage=",
                  b"[F1-THREAD] stage=", b"[F1-RESOURCE] reason=",
                  b"[F1-SCRATCH]", b"[F1-AUDIO]", b"[F1-GRAPHICS]", b".pre-0.1.27.bak",
                  b"[F1-RESTART]", b"[F1-MODES]", b"last-game-return.bin", b"fex-runtime-previous.log",
                  b"[F1-RENDERER] %s", b"[WINE] %s", b"[F1-CRYPTO]", b"[F1-APC]",
                  b"[F1-DIALOG] title=", b"WINEDLLOVERRIDES=d3d9,d3d11,dxgi=n,b",
                  b"dlls=d3d9,d3d11,dxgi", b"DXVK_LOG_LEVEL=info",
                  b"[F1-PROGRESS]", b"[F1-CALL]", b"[F1-FILE]", b"[F1-PC]", b"[F1-STACK]",
                  b"%SystemRoot%\\system32\\rsaenh.dll",
                  b"DLL initialization failed (0xc0000142)"):
        if label not in nro_bytes:
            raise SystemExit(f"Launcher feature missing from NRO: {label!r}")
    pes_launcher = PES / "local/production-input-fix/approved/switch/pes13-fex/launcher"
    for name in ("logo.rgba", "wordmark.rgba"):
        if sha(prefix / "launcher" / name) != sha(pes_launcher / name):
            raise SystemExit(f"FEXTendo branding asset differs from PES: {name}")
    runtime = prefix / "drive_c/windows"
    must_have = [prefix / "launcher/background.rgba",
                 prefix / "share/wine/nls/locale.nls",
                 prefix / "launcher/renderers/dxvk-3.1.1/d3d9.dll",
                 prefix / "launcher/renderers/dxvk-2.7.1-async/d3d9.dll",
                 runtime / "system32/libwow64fex.dll",
                 runtime / "syswow64/d3dcompiler_43.dll",
                 runtime / "syswow64/d3dx9_43.dll",
                 runtime / "syswow64/rsaenh.dll", runtime / "syswow64/xaudio2_7.dll",
                 runtime / "syswow64/mfplat.dll", runtime / "syswow64/mfreadwrite.dll",
                 runtime / "syswow64/rtworkq.dll"]
    if missing_runtime := [str(path) for path in must_have if not path.is_file()]:
        raise SystemExit(f"Runtime files missing: {missing_runtime}")
    for dll in runtime.rglob("*.dll"):
        data = dll.read_bytes()
        if b"switch/pes13-fex" in data or "switch/pes13-fex".encode("utf-16le") in data:
            raise SystemExit(f"Runtime DLL still uses PES prefix: {dll}")
    image = pefile.PE(str(exe))
    if (image.FILE_HEADER.Machine, image.OPTIONAL_HEADER.ImageBase,
            image.OPTIONAL_HEADER.SizeOfImage) != (0x14c, 0x400000, 0x11ed000):
        raise SystemExit("Unexpected F1 PE image layout")
    imports = [entry.dll.decode(errors="replace") for entry in image.DIRECTORY_ENTRY_IMPORT]
    dependencies = audit_guest_dependencies(prefix)
    from dxvk_runtime import release_files, DLLS
    renderer_dependencies = {}
    for renderer, files in release_files().items():
        for name, data in files.items():
            if sha(prefix / 'launcher/renderers' / renderer / name) != hashlib.sha256(data).hexdigest():
                raise SystemExit(f"DXVK file differs from pinned upstream release: {renderer}/{name}")
        renderer_dependencies[renderer] = audit_guest_dependencies(prefix, renderer)
    installed = (prefix / 'launcher/renderer.txt').read_text().strip()
    renderer = ('dxvk-3.1.1', 'dxvk-2.7.1-async')[int(installed)]
    for name in DLLS:
        if sha(game / name) != sha(prefix / 'launcher/renderers' / renderer / name):
            raise SystemExit(f"Mixed installed DXVK set: {name}")
    report = {"passed": True, "hardware_tested": False,
              "game_files": len(source_files), "game_bytes": sum(source_files.values()),
              "nro_sha256": sha(nro), "game_exe_sha256": sha(exe),
              "nro_target": expected_target.decode(),
              "fextendo_branding_matches_pes": True,
              "runtime_prefix_isolated": True,
              "guest_dependencies": dependencies,
              "renderer_dependencies": renderer_dependencies,
              "direct_imports": imports, "nro_metadata": metadata}
    (prefix.parent.parent / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("passed", "hardware_tested", "game_files",
                                                   "game_bytes", "nro_sha256")}, indent=2))


if __name__ == "__main__":
    main()
