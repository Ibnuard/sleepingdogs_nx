# Native ARM64 DXVK probe v1

[Documentation](README.md) · [Current status](STATUS.md)

This experiment builds the actual DXVK Native D3D11/DXGI implementation for
Horizon ARM64 and tests a small marshaling backend on Linux. A standalone
Horizon diagnostic NRO is now linked with the existing real Mesa/NVK driver,
dated **2026-10-11**. Sleeping Dogs still uses the
x86 DXVK renderer in v18; this probe is not a launcher option or a game update.

## Results

| Check | Result and scope |
| --- | --- |
| Horizon static archive | Built with devkitA64 GCC 16.1.0; all 202 ELF members are AArch64 |
| Horizon diagnostic NRO | Linked with v14.1 Mesa/NVK and libnx; 21,741,624 bytes; supplied Switch H1 capture reports PASS |
| Final executable | AArch64 PIE, native TLS and C++ initializers present; no unresolved symbols; real DXVK, NVK, NAK and libnx scanout symbols verified |
| Vulkan loader | Horizon object imports `vkGetInstanceProcAddr` directly; no dynamic Vulkan loader is required by that path |
| Wire layout | A 64-byte packet, identical field offsets under i686 MinGW, Linux x86-64 and Horizon ARM64 compilers |
| Linux native D3D11 device | Feature level 11_0 on Mesa lavapipe / llvmpipe 26.0.3, LLVM 21.1.8 |
| Buffer Map/Unmap | A 1,024-byte pattern survives shadow upload, native copy and staging readback |
| 720p shader draw | All 921,600 pixels match the expected RGBA color within one quantization step |
| DXGI presentation | 60 successful `Present(0, 0)` calls to the XCB test window |
| Invalid requests | 25 rejected cases, including out-of-arena pointers, insufficient Map capacity, stale handles, wrong object types and overlapping active shadows |
| Host checks | 166 successful calls/assertions, plus those 25 rejected requests |
| Switch H1 device / buffer / draw | FL11_0, 1,024-byte buffer pattern, all 921,600 pixels correct; 644 checks |
| Switch H1 presentation | 300 FIFO Present calls in 5.029 seconds; 1280×720, three Vulkan swapchain images |
| Sleeping Dogs FPS | No native game run or FPS gain measured |

The Linux test uses real DXVK Native and software Vulkan, with a host arena
above 4 GiB exposed through modeled guest addresses starting at `0x10000000`.
It does **not** execute an x86 guest through FEX. The i686 check compiles the
packet layout only. Present calls establish API success, not observed scanout
or a frame-rate benchmark. Vulkan validation layers were not used.

Receipts: [Horizon archive](../reports/native-dxvk-probe-v1-horizon.json),
[Horizon executable](../reports/native-dxvk-horizon-v1.json),
[diagnostic package verification](../reports/native-dxvk-horizon-v1-package.json),
[host build](../reports/native-dxvk-probe-v1-host.json), and
[host correctness test](../reports/native-dxvk-probe-v1-test.json).

The supplied Switch capture is preserved in the
[H1 hardware analysis](../reports/native-dxvk-h1-73faa8ebc4ef.json) and its
[raw probe log](../reports/native-dxvk-h1-73faa8ebc4ef/probe.txt).
It reports application mode (`applet_type=0`), handheld operation mode, the
real Tegra X1 / NVK GM20B device, a native arena at `0x8b530de20` and an
explicitly modeled guest base at `0x10000000`. Native Map/shader/readback and
FIFO presentation completed with a normal exit marker. No real x86/FEX guest
or COM proxy was exercised. The approximately 59.65 synthetic presents/second
are not Sleeping Dogs FPS. Clock telemetry and a visual scanout confirmation
were not supplied. Build-time receipts retain their original pre-test flags;
the separate capture records the later hardware evidence.

## What was implemented

- An isolated CMake recipe for DXVK's native headers, D3D11, DXGI, internal
  D3D10 dependencies, DXBC-SPIRV and libdisplay-info. D3D9 is outside this probe.
- A diagnostic WSI driver: XCB on Linux, `VK_NN_vi_surface` with a trusted
  libnx native window on Horizon. Both paths have now completed the probe.
- Horizon compatibility adaptations for the static Vulkan loader, executable
  name, unavailable optional POSIX thread naming and default thread priority.
  Native worker threads remain enabled. The unified archive uses one D3D11 logger
  singleton rather than separate DLL logger instances.
- A bounded dispatcher for device creation, buffers, RGBA8 textures, shaders,
  render-target views, a fullscreen-triangle pipeline, copy/readback, release,
  a 1280×720 swapchain and presentation.
- Original HLSL test shaders, compiled by Windows `d3dcompiler_47.dll` into
  the checked header. No game or Lossless Scaling shaders are used.
- A standalone libnx executable with separate diagnostic files, buffer and
  720p pixel-readback checks, and 300 FIFO presentation calls. This is not
  connected to Wine, FEX, the game launcher or the game's forwarder.

## Horizon hardware diagnostic H1

Local artifact: `dist/sd-dxvk-native-probe-horizon-v1.zip`. Generated packages
are excluded from Git; this name does not imply a published GitHub release.
Copy its `switch/` folder to the SD root. The only SD payload is:

```text
switch/sd-dxvk-native-probe/sd-dxvk-native-probe.nro
```

Run **FEXTendo Native DXVK Probe** from hbmenu in application/full-memory mode:
hold R while opening a game from HOME, then select the probe. Album/applet mode
is rejected. The probe uses the normal libnx heap, its own native threads and
the existing v14.1 driver inputs; it does not reserve FEX's guest low-window
or use v17's thread scheduler. It does not change clocks. Keep the reference
OLED handheld / CPU 1728 / GPU 768 / RAM 1600 MHz conditions if available.

The test requires a D3D11 FL11_0 device, verifies a 1,024-byte buffer pattern
through native Map/copy/readback, draws the original shader to an offscreen
1280×720 texture, and verifies every pixel. It then presents a solid blue
image 300 times using `Present(1, 0)`, roughly five seconds at 60 Hz, and exits
to hbmenu. PLUS cancels during presentation. Shader/device startup can add time.
This tiny workload does not measure Sleeping Dogs FPS or prove a speedup.

Collect these files from `switch/sd-dxvk-native-probe/` after running:

- `result.json`: `PASS`, `FAIL` or `RUNNING` if interrupted before completion.
- `probe.log`: `[SD-NDX-H1]` stage markers and pixel/presentation results.
- `stderr.log`: runtime errors and driver output.
- `sd-dxvk-native-probe_d3d11.log`: DXVK device/configuration details.

The probe overwrites these diagnostic files and its own `probe.conf` on each
run. A hardware `PASS` must come from that run's `result.json`. Package/build
receipts are build evidence only. If the default libnx window fails during
startup before `main()`, there may be no new probe log; libnx documents this
[startup behavior](https://github.com/switchbrew/libnx/blob/master/nx/include/switch/display/native_window.h).
The SD log path is also unavailable if SD/file initialization fails.

NRO SHA-256: `53a99869ed1d01950361969d7e9c50cd95de4500155dde5338ff3260f4d33e84`.
The package contains original probe sources, all 1,203 pinned DXVK source
files with the native adaptations, versioned Mesa overlays, receipts, notices
and verified per-file checksums. The Mesa/SDK baseline is still an external
local build prerequisite; the package is not a self-contained clean-clone build.

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
python3 tools/build_native_dxvk_horizon.py
python3 tools/package_native_dxvk_horizon.py
```

Default work directory: `/home/blekjek/sleepingdogs-dxvk-arm64-v1`.
Source input: `/home/blekjek/sleepingdogs-dxvk-native-v15/source`.
Run with a user that can write the work directory; the recorded build used
WSL Ubuntu's root user. `--work` and `--source` can select other matching inputs.
Do not run preparation concurrently: it restores adapted source files.
After preparation, host and Horizon builds may use `--reuse-prepared`, which
verifies the shared inputs without rewriting them.

The Horizon executable additionally requires `local/apc-v18/native.json` and
its matching Mesa objects/libraries. The linker checks those pinned inputs,
records the resolved SDK/runtime libraries and compilation headers, and
inspects executable symbols/TLS and NRO/NACP bounds. A per-output lock prevents
concurrent linker runs. Packaging verifies hashes again and checks all ZIP
members, checksums and the dedicated SD payload path.

Receipts and test logs are generated in `local/native-dxvk-probe-v1/`.
The runner checks source/archive hashes, uses a temporary authenticated Xvfb
display, forces lavapipe and closes its display when finished. It does not
use the game prefix or shared WSLg socket directory. To regenerate the original
DXBC header on Windows, run `tools/compile_native_probe_shaders.py` and rebuild
the host test afterward.

## Remaining integration work

The [H2 PE32 bridge diagnostic](native-dxvk-h2-v1.md) now implements a small
real guest-to-native offscreen test. Its actual Switch Wine/FEX path now passes
the [supplied H2 capture](../reports/native-dxvk-h2-748072991d01.json).
The [H3 diagnostic](native-dxvk-h3-v1.md) next tests guest-driven native Present.
H1, H2 and H3 are separate
artifacts and neither is integrated with Sleeping Dogs.

1. Expand the successful H1 hardware subset before production use: handle
   lifetime, repeated device/swapchain recreation, memory pressure and visual
   scanout. H1 proves the supplied native device/draw/Map/present run, not
   general D3D11 compatibility or production handle behavior.
2. H2 now registers a probe Unix-call table through Wine's existing static
   WOW64 bridge and passes requests from a real PE32/FEX guest on Switch.
   H3 extends this route to presentation; x86 COM proxies remain unimplemented.
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
