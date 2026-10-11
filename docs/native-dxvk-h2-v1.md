# Native DXVK H2: real PE32 guest bridge

[Documentation](README.md) · [H1 renderer result](native-dxvk-probe-v1.md)

The supplied Switch H1 capture passed 644 checks: native D3D11 FL11_0,
1 KiB buffer readback, all 921,600 pixels of a 1280×720 shader draw, and
300 FIFO presents in 5.029 seconds. H1 used a modeled guest-address arena;
it did not execute an x86 program. Its presentation rate is not game FPS.

H2 adds an original, deliberately limited PE32 client and `sdndx.dll` to test
the existing Wine/FEX Unix-call path against the same native ARM64 DXVK
library and Mesa/NVK v14.1 driver. H2 is an offscreen correctness test.
It does not replace the game's D3D11 DLLs or expose a native renderer option
in the launcher. Sleeping Dogs and LSFG are not exercised by this test.

## Implementation

- The CRT-free x86 client allocates an 8 MiB arena with `VirtualAlloc` and
  passes its actual 32-bit address through Wine/FEX. The native side accesses
  that same allocation; H1's modeled-address translation is not used here.
- `sdndx.dll` requests `MemoryWineUnixFuncs` (1000). Wine's WOW64 memory
  thunk converts this to host class 1001; requesting 1001 directly from
  PE32 would be rejected. The query returns an opaque 64-bit Unix-library
  handle, as required by Wine's ABI. It is not a COM object pointer.
- A task-owned `virtual.c` overlay registers `sdndx.dll` in Wine's existing
  static WOW64 table. The existing FEX/native Unix dispatcher is retained.
  The DLL bounds the operation index before calling the dispatcher.
  The Box64-specific `wine_nx_call_ntdll_wow64` helper is not the active
  gate in this FEX runtime; it is not introduced or claimed as tested.
- INIT, DISPATCH and CLOSE have fixed 32-bit layouts. Native session and
  D3D object tokens have generations. Native COM pointers stay on the host.
  Requests and arena pages are checked with the actual Wine memory helpers.
- The first 4 KiB of the arena is reserved for protocol metadata. Map
  shadows may not overlap it. Read mappings copy into the guest arena;
  write-discard shadows copy back at Unmap. RowPitch is preserved.
- The guest tests buffer readback, shader/texture/view creation, draw,
  all 720p pixels, resource release and stale-session rejection. Swapchain,
  backbuffer and Present operations return E_NOTIMPL in H2.
- The diagnostic runtime boots the test client directly, writes its own
  logs, uses two native compiler threads and sets `DXVK_SHADER_CACHE_PATH`.
  The existing FEX context preflight is retained. Unrelated fault stress
  and game launcher paths are bypassed for this diagnostic only.

The arena belongs to one controlled guest thread and must remain allocated
and writable until CLOSE returns. The page checks do not pin memory against
concurrent `VirtualFree`/`VirtualProtect`. This is not a production COM ABI.
H2 also rechecks all arena pages on dispatch, which is intentionally unsuitable
for a game draw hot path. Production mapping, lifetime and synchronization
rules need a separate design and measurements.

## Validation and remaining limits

The host regression uses real DXVK on software Vulkan, a real low-address
`mmap` allocation and modeled Wine permission callbacks. It verifies the
1 KiB pattern and all 921,600 pixels and rejects 17 invalid requests.
It calls the Unix-entry table directly, so it does not establish that the
actual Switch Wine/FEX gate works. See the [host regression report](../reports/native-dxvk-h2-v1-host.json).

The build recipe reproduces the complete v18 ELF before applying the overlay,
compiles the ABI for both PE32 and ARM64, checks DLL names/exports and CRT-free
imports, and links/audits the native renderer, Unix dispatcher and FEX context
symbols in the resulting Horizon executable. Build/host PASS is distinct from
the guest's result JSON on Switch. The supplied **H2 Switch capture now passes**:
1,096 checks, five expected rejections, 35 actual Wine/FEX bridge calls,
1,024 verified buffer bytes and all 921,600 correct 720p pixels. Its actual
shared guest/native arena is `0x01a80000`, and both session generations close
before a zero guest exit. See the [preserved hardware capture](../reports/native-dxvk-h2-748072991d01.json).
The two failing D3D HRESULTs deliberately test the unsupported offscreen
swapchain and a stale resource. The shader cache was created successfully;
the final GPU arena has zero live allocations, with 24 allocations returned.
Clocks and a running binary hash are not authenticated by these logs.
No game FPS is measured. The [build receipt](../reports/native-dxvk-h2-v1-build.json)
and [package verification](../reports/native-dxvk-h2-v1-package.json) record
the NRO, PE32 binaries, original v18 rollback and source hashes.

## Switch test

Use the local `sd-dxvk-native-h2-v1-update/` folder on an existing working
Sleeping Dogs/FEXTendo v18 installation. The folder is a diagnostic update,
not a complete game/runtime installation.

1. Fully close FEXTendo from HOME. Back up your SD copy of
   `switch/sleepingdogs-fex/sleepingdogs-fex.nro` before copying the update.
2. Copy only its `switch/` folder to SD root. This replaces the NRO
   and adds `drive_c/sd-native-dxvk-guest.exe` and `drive_c/sdndx.dll`.
3. Start it using the same working Sleeping Dogs low-window/full-memory
   forwarder used for gameplay. H1's standalone hbmenu route does not test
   this runtime's low-address prerequisites. Do not use Album/applet mode.
4. The console identifies **Native DXVK H2**. This test does not launch the
   game or display the rendered test image. Wait for the guest-exit message;
   then fully close from HOME. If it stalls, retain the logs before relaunch.
5. Collect these files from SD:
   - `switch/sleepingdogs-fex/drive_c/native-dxvk-h2-result.json`
   - `switch/sleepingdogs-fex/drive_c/native-dxvk-h2-guest.log`
   - `switch/sleepingdogs-fex/native-dxvk-h2/runtime.log`
   - `switch/sleepingdogs-fex/native-dxvk-h2/sd-dxvk-native-probe_d3d11.log`
6. Restore your backed-up game NRO to resume gameplay. The folder also contains
   the hash-verified original v18 NRO under `rollback-v18/`; it is a fallback
   for an installation using that exact v18 build. The added diagnostic files
   can remain on SD; the restored runtime does not select them.

Use reference clocks CPU 1728 / GPU 768 / RAM 1600 MHz if available.
The test does not set clocks. Readback correctness is the acceptance criterion;
the test has no game FPS measurement or frame-generation output.
Each run overwrites H2 logs/results; preserve a failed run before retrying.

## Rebuild

Run under the existing WSL toolchain without changing global SDK or baseline
inputs:

```sh
python3 tools/test_native_dxvk_h2_host.py
python3 tools/build_native_dxvk_h2.py
python3 tools/analyze_native_dxvk_h2.py --log-dir /path/to/copied-four-files
```

The required v18 source/objects and H1 libraries remain prepared local inputs;
this is not a self-contained clean-clone build. Source and header hashes,
exact commands, ELF/PE checks and baseline reproduction are recorded in the
build receipt. Only original diagnostic sources and Wine overlay patches are
added to this experiment; the FEX engine, baseline runtime and installed SDK
are not edited.

The historical H2 packager produces a ZIP; it is retained to reproduce that
artifact, not used for new deliveries. The [H3 packager](native-dxvk-h3-v1.md)
produces a ready folder only.

H2 hardware success validates a small guest-to-native rendering subset. Full
x86 COM interfaces, D3D11/DXGI coverage, HWND/swapchain conversion, production
resource lifetime rules and profiling are still needed before the game can
use native DXVK. A route to stable 30 FPS has not been demonstrated.
The [H3 diagnostic](native-dxvk-h3-v1.md) next tests guest-driven native
swapchain/backbuffer/Present with a trusted Horizon window.
