# Native ARM64 DXVK probe v1

[Documentation](README.md) · [Current status](STATUS.md)

This experiment builds the actual DXVK Native D3D11/DXGI implementation for
Horizon ARM64 and tests a small marshaling backend on Linux. It is the first
native-renderer milestone, dated **2026-10-11**. Sleeping Dogs still uses the
x86 DXVK renderer in v18; this probe is not a launcher option or a game update.

## Results

| Check | Result and scope |
| --- | --- |
| Horizon static archive | Built with devkitA64 GCC 16.1.0; all 202 ELF members are AArch64 |
| Vulkan loader | Horizon object imports `vkGetInstanceProcAddr` directly; no dynamic Vulkan loader is required by that path |
| Wire layout | A 64-byte packet, identical field offsets under i686 MinGW, Linux x86-64 and Horizon ARM64 compilers |
| Linux native D3D11 device | Feature level 11_0 on Mesa lavapipe / llvmpipe 26.0.3, LLVM 21.1.8 |
| Buffer Map/Unmap | A 1,024-byte pattern survives shadow upload, native copy and staging readback |
| 720p shader draw | All 921,600 pixels match the expected RGBA color within one quantization step |
| DXGI presentation | 60 successful `Present(0, 0)` calls to the XCB test window |
| Invalid requests | 25 rejected cases, including out-of-arena pointers, insufficient Map capacity, stale handles, wrong object types and overlapping active shadows |
| Host checks | 166 successful calls/assertions, plus those 25 rejected requests |
| Switch runtime / FPS | Not tested; no FPS gain measured |

The Linux test uses real DXVK Native and software Vulkan, with a host arena
above 4 GiB exposed through modeled guest addresses starting at `0x10000000`.
It does **not** execute an x86 guest through FEX. The i686 check compiles the
packet layout only. Present calls establish API success, not observed scanout
or a frame-rate benchmark. Vulkan validation layers were not used.

Receipts: [Horizon build](../reports/native-dxvk-probe-v1-horizon.json),
[host build](../reports/native-dxvk-probe-v1-host.json), and
[host correctness test](../reports/native-dxvk-probe-v1-test.json).

## What was implemented

- An isolated CMake recipe for DXVK's native headers, D3D11, DXGI, internal
  D3D10 dependencies, DXBC-SPIRV and libdisplay-info. D3D9 is outside this probe.
- A diagnostic WSI driver: XCB on Linux, `VK_NN_vi_surface` with a trusted
  libnx native window on Horizon. Only the XCB path has run.
- Horizon compatibility adaptations for the static Vulkan loader, executable
  name and default thread priority. The unified archive uses one D3D11 logger
  singleton rather than separate DLL logger instances.
- A bounded dispatcher for device creation, buffers, RGBA8 textures, shaders,
  render-target views, a fullscreen-triangle pipeline, copy/readback, release,
  a 1280×720 swapchain and presentation.
- Original HLSL test shaders, compiled by Windows `d3dcompiler_47.dll` into
  the checked header. No game or Lossless Scaling shaders are used.

Original probe sources are in [src/native_dxvk](../src/native_dxvk).
The [input manifest](../vendor/dxvk/native-probe-v1-inputs.json) pins 1,203
files from the existing **3.1.1-sdbatch2** renderer source, including the
project's earlier memory/submission patches. The
[adaptation patch](../vendor/dxvk/native-probe-v1.patch) records the changes
to that source. Upstream base and dependency notices remain in
[THIRD_PARTY.md](../THIRD_PARTY.md).

## Guest-pointer design

The packet contains only 32-bit words: ABI version, operation, object token,
flags, eight arguments and four results. Native COM pointers remain in a
128-entry host table. Tokens include a generation counter so released handles
cannot immediately alias replacement objects.

`Map()` currently uses an explicit shadow span inside the supplied guest
arena. Read mappings copy native memory into that span. Write-discard mappings
copy back at `Unmap()`. Texture sizes use the actual row pitch. Range overflow,
insufficient capacity, overlapping active shadows, double mapping and releasing
mapped resources are rejected. The supported modes are READ, READ_WRITE and
WRITE_DISCARD; WRITE and WRITE_NO_OVERWRITE are not implemented.

This is a correctness path. Shadow copies add memory traffic and can consume
the benefit of moving DXVK off FEX. The eventual game path needs measurements
of direct low-window mappings/imports versus copies, including resource
lifetime and synchronization. Neither zero-copy Map nor native NVK import is
validated by this software-driver test.

## Rebuilding in the current local workspace

This is a local development recipe, not a self-contained clean-clone build.
It requires the prepared v15 renderer source and its preparation receipt,
the glslang tool already used by the project, devkitA64/libnx for Horizon,
and the recorded i686 LLVM-MinGW toolchain for the guest layout check.
For Linux it also needs CMake/Ninja, a C/C++ compiler, XCB headers/library,
Vulkan with lavapipe, Xvfb and xauth. The builder currently expects XCB headers
under `<work>/host-deps/usr/include`; this workspace extracted `libxcb1-dev`
there without modifying the SDK or package-manager state.

From the repository root under WSL/Linux:

```sh
python3 tools/build_native_dxvk_probe.py --target horizon --jobs 4
python3 tools/build_native_dxvk_probe.py --target host --jobs 4 --reuse-prepared
python3 tools/test_native_dxvk_probe.py
python3 tools/export_native_dxvk_probe.py
```

Default work directory: `/home/blekjek/sleepingdogs-dxvk-arm64-v1`.
Source input: `/home/blekjek/sleepingdogs-dxvk-native-v15/source`.
Run with a user that can write the work directory; the recorded build used
WSL Ubuntu's root user. `--work` and `--source` can select other matching inputs.
Do not run preparation concurrently: it restores adapted source files.
After preparation, host and Horizon builds may use `--reuse-prepared`, which
verifies the shared inputs without rewriting them.

Receipts and test logs are generated in `local/native-dxvk-probe-v1/`.
The runner checks source/archive hashes, uses a temporary authenticated Xvfb
display, forces lavapipe and closes its display when finished. It does not
use the game prefix or shared WSLg socket directory. To regenerate the original
DXBC header on Windows, run `tools/compile_native_probe_shaders.py` and rebuild
the host test afterward.

## Remaining integration work

1. Link and run an isolated Horizon diagnostic with the real Mesa/NVK driver,
   libnx window, runtime allocator/TLS support and native threads. The ARM64
   archive has **not** been linked into a final executable or NRO.
2. Register a probe Unix-call table through Wine's existing static WOW64
   bridge and execute requests from a real PE32/FEX guest. The current packet
   dispatcher has no Wine table registration or x86 COM proxies.
3. Implement the D3D11/DXGI COM interfaces needed by the game, with explicit
   x86/native struct conversion, reference lifetime and callbacks. Native
   `WCHAR` and pointers cannot be copied as if they had Windows x86 layouts.
4. Budget native heap/resource memory against the allocations being replaced;
   connect host DXVK threads to the existing scheduler and diagnostics. The
   probe's default-priority adaptation is not v17 thread scheduling integration.
5. Compare the same 720p scene at CPU 1728 / GPU 768 / RAM 1600 MHz with LSFG
   OFF, measuring native game FPS, CPU renderer time, Map copy cost, GPU
   timestamps and presentation separately.

The diagnostic WSI intentionally supplies no EDID. Its log records monitor
fallback and blank display metadata; lavapipe also lacks the external-memory
features queried by DXVK. An upstream native `CloseHandle` stub is reported.
These warnings do not invalidate the tested draw/readback results, but they
must not be treated as validation of production display or handle behavior.

This prototype establishes a working native source build and a tested small
API subset. It does not establish game compatibility, reduced memory use or
a route guaranteed to reach 30 FPS.
