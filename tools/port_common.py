"""Shared, host-independent Sleeping Dogs port metadata and PE checks."""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[1]
PES = ROOT.parent / "pes13-nx"
APPROVED = PES / "local/production-input-fix/approved"
BASE = APPROVED / "switch/pes13-fex"
VERSION = "0.1.0"
APP_ID = "sleepingdogs-fex"
TITLE = "Sleeping Dogs - FEXTendo"
GAME_DIR = "SleepingDogs"
GAME_EXE = "HKShip.exe"
DEFAULT_GAME = ROOT.parent / "Sleeping Dogs"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def pe_info(path):
    """Reject PE64/Definitive Edition and malformed or unaligned PE32 layouts."""
    data = Path(path).read_bytes()
    if len(data) < 64 or data[:2] != b"MZ":
        raise ValueError("Expected an installed Sleeping Dogs PE32 HKShip.exe")
    nt = struct.unpack_from("<I", data, 0x3c)[0]
    if nt + 24 + 144 > len(data) or data[nt:nt + 4] != b"PE\0\0":
        raise ValueError("Invalid PE header")
    machine, sections = struct.unpack_from("<HH", data, nt + 4)
    optional_size, flags = struct.unpack_from("<HH", data, nt + 20)
    opt = nt + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    if machine != 0x14c or magic != 0x10b or optional_size < 144:
        raise ValueError("This port requires the original x86 game, not the x64 Definitive Edition")
    base = struct.unpack_from("<I", data, opt + 28)[0]
    size = struct.unpack_from("<I", data, opt + 56)[0]
    reloc_rva, reloc_size = struct.unpack_from("<II", data, opt + 136)
    if base != 0x400000 or not size or size % 4096 or base + size >= 0x80000000:
        raise ValueError(f"Unsupported fixed PE image range {base:#x}+{size:#x}")
    if opt + optional_size + 40 * sections > len(data):
        raise ValueError("Truncated PE section table")
    return {"sha256": sha(path), "machine": hex(machine), "image_base": base,
            "image_size": size, "image_end": base + size,
            "relocations_available": bool(reloc_rva and reloc_size and not flags & 1),
            "large_address_aware": bool(flags & 0x20),
            "address_space": "32-bit no-alias", "executable": GAME_EXE}


def profile_config(profile, async_mode=False):
    # The shared renderer gate checks this D3D9 option before installing the
    # complete D3D9/D3D11/DXGI set. Keep it alongside DXGI's D3D11 sync option.
    lines = ["# Sleeping Dogs / FEXTendo / conservative DX11 bring-up",
             "d3d9.presentInterval = 1", "dxgi.syncInterval = 1",
             "dxgi.maxDeviceMemory = 256",
             "dxgi.maxSharedMemory = 128", "dxvk.numCompilerThreads = 1",
             "dxvk.enableDescriptorBuffer = False", "dxvk.enableDescriptorHeap = False",
             "dxgi.maxFrameLatency = " + ("1" if profile == "low-latency" else "2")]
    if profile == "stable":
        lines.append("d3d11.samplerAnisotropy = 0")
    elif profile == "quality":
        lines.append("d3d11.samplerAnisotropy = 4")
    if async_mode:
        lines.append("dxvk.enableAsync = True")
    return "\n".join(lines) + "\n"
