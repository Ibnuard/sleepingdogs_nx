# Native DXVK H3: guest-driven native presentation

[Documentation](README.md) · [H2 hardware result](native-dxvk-h2-v1.md)

H2 passed on the supplied Switch capture: the actual PE32 client used Wine/FEX
to call ARM64 DXVK, verified a 1 KiB buffer and all 921,600 offscreen 720p pixels,
rejected five invalid requests and closed two session generations. The actual
guest/native shared arena was `0x01a80000`. The capture and hashes are preserved
in [the hardware report](../reports/native-dxvk-h2-748072991d01.json).

H3 extends that bounded diagnostic to a native 1280×720 swapchain. The PE32
client draws and reads back the real backbuffer before issuing 300 FIFO Present
calls through Wine/FEX. It should display the same solid blue test image as H1,
then restore the console. It still uses diagnostic packets, not x86 COM
interfaces. Sleeping Dogs is not launched and no game FPS improvement is claimed.

## Implementation

- An isolated Wine overlay registers `sdndx3.dll` with the existing static
  WOW64 table. The CRT-free guest is `sd-native-dxvk-h3-guest.exe`. H1/H2 source,
  native renderer archive, v18 inputs and the installed SDK are retained.
- Before executing the guest, the runtime releases its text-console framebuffer
  with `consoleExit`. It then obtains and validates the trusted libnx default
  `NWindow` at 1280×720. No guest HWND or arbitrary guest pointer becomes a
  native window. The native session is destroyed before console restoration.
  See [libnx console ownership](https://switchbrew.github.io/libnx/console_8h.html)
  and [default window lifetime](https://switchbrew.github.io/libnx/native__window_8h.html).
- The client retains its actual 8 MiB `VirtualAlloc` arena until CLOSE. The
  fixed-width H2 transport, session generations and native object tokens are
  retained. Each native session accepts only one swapchain, even after Release.
- Draw and Present access only host-owned tokens; they no longer scan the full
  guest arena. The actual Wine helpers still check request/response metadata
  on every dispatch and recheck all arena pages for shaders, Map and Unmap.
  The successful rendering sequence needs **11 full arena scans**, rather
  than scanning 8 MiB for every draw and present request. This is a diagnostic
  bridge change; it does not optimize the existing game's x86 DXVK path.
- The client verifies both the offscreen image and the swapchain backbuffer:
  921,600 pixels each, retaining the actual mapped row pitch. It then calls
  `Present(1, 0)` 300 times. [DXGI Present's sync interval](https://learn.microsoft.com/en-us/windows/win32/api/dxgi/nf-dxgi-idxgiswapchain-present)
  is passed to the unchanged H1 native backend. Unsupported interval 2 and a
  released swapchain token are deliberately rejected.
- Fresh RUNNING/PASS/FAIL JSON and separate logs distinguish an unfinished run
  from a result. Native progress markers record the first and every 60th
  successful Present. Guest progress writes also preserve a stall location.
- Stats record successful present count, synthetic-loop elapsed microseconds,
  full arena scans and time inside native validation/copy and renderer dispatch.
  Validation timing excludes guest marshaling, FEX gate transit and native log
  emission. Renderer dispatch includes Map/readback and Present waits; it is
  **not a GPU timestamp**. Loop elapsed time includes guest progress I/O.

Memory checks do not pin pages against another thread's VirtualFree/VirtualProtect.
The single controlled caller must retain its allocation unchanged through CLOSE.
Production COM, resource lifetime, callbacks, thread scheduling and native mapping
remain separate integration work. The cached token path must not be exposed to
the game without that work.

## Validation

The [host fixture](../reports/native-dxvk-h3-v1-host.json) uses real DXVK on
lavapipe, a real low-address allocation and a private authenticated Xvfb window.
It passes 7,373,187 checks, both full 720p readbacks, the 1 KiB pattern,
60 synthetic presents, 23 rejected requests and a second device/swapchain
creation. Modeled payload permissions are denied during Draw/Present to verify
that these token-only calls do not query payload pages; Map is still rejected.
The fixture directly calls the native table, so it does not test actual Wine/FEX
execution or Switch display ownership.

The [build receipt](../reports/native-dxvk-h3-v1-build.json) records complete v18
ELF reproduction, PE32/ARM64 layout checks, CRT-free imports, the exact native
library/driver and the final AArch64 PIE with no unresolved nonweak symbols.
The [folder receipt](../reports/native-dxvk-h3-v1-folder.json) verifies all staged
files and reconstructs both Wine overlays from their pinned source inputs.

The supplied **H3 Switch capture passes** all analyzer conditions. The
[hardware report](../reports/native-dxvk-h3-36d3933d1d46.json) preserves the
original four files and their hashes. The actual PE32 client makes **651
Wine/FEX bridge calls**, completes **2,331 checks**, verifies the 1 KiB buffer
and all **921,600 pixels in each of the two images**, and rejects seven
deliberately invalid requests. The guest/native arena is `0x01a80000`.
The native swapchain is 1280×720, RGBA8, FIFO, with three images.

All **300 Present calls complete in 5.034225 seconds**, and both session
generations close before the guest exits zero. Only 11 full arena scans occur.
The recorded native validation/copy time is 1,890 microseconds cumulatively;
it is not the full guest-to-host bridge cost. The 5,900,428 microseconds of
native dispatch include setup, readbacks and FIFO waits. Neither figure is a
GPU timestamp or a Sleeping Dogs performance measurement. H3 does not launch
the game or implement COM proxies.

The logs do not authenticate clocks or the running binary hash, nor directly
confirm that scanout was visible. The user's feedback reports a successful
test without specifying that observation. The memory counters are an active-run
snapshot, so this capture does not establish zero live allocations after CLOSE
or long-session leak freedom. Optional-interface/display-metadata warnings and
the native backend's unimplemented `CloseHandle` stub also remain integration
audit items. Build and folder receipts retain their original build-time flags;
the separate hardware report records the later test.

## Switch test: folder only

Use the local **`dist/sd-dxvk-native-h3-v1-update/`** folder. It contains a
diagnostic update for your working v18 installation, not a complete runtime.

1. Fully close FEXTendo from HOME and back up the current game NRO on SD.
2. Copy **only `switch/`** from the ready folder to SD root, replacing
   `switch/sleepingdogs-fex/sleepingdogs-fex.nro`. It adds two uniquely named
   PE32 files in `drive_c/`. Keep the remaining runtime files from your working
   installation.
3. Launch with the same low-window/full-memory Sleeping Dogs forwarder that
   passed H2. Use reference clocks CPU 1728 / GPU 768 / RAM 1600 MHz. The test
   does not change clocks. Album/applet mode does not meet the prerequisites.
4. The startup console identifies **Native DXVK H3**. It may go black while
   initializing, then show a solid blue test image for roughly five seconds.
   Wait for `H3 guest exited: 00000000`, then close from HOME. If it stalls,
   preserve the logs before retrying.
5. Copy these four files from SD; also report whether the blue image appeared:
   - `switch/sleepingdogs-fex/drive_c/native-dxvk-h3-result.json`
   - `switch/sleepingdogs-fex/drive_c/native-dxvk-h3-guest.log`
   - `switch/sleepingdogs-fex/native-dxvk-h3/runtime.log`
   - `switch/sleepingdogs-fex/native-dxvk-h3/sd-dxvk-native-probe_d3d11.log`
6. Restore the game NRO you backed up. `rollback-v18/` contains the exact
   original v18 NRO as a fallback for installations using that build. Do not
   copy rollback and update together.

Each run overwrites H3 results/logs. An API-level PASS cannot by itself confirm
that the image was visible; visual confirmation remains a separate observation.

## Rebuild and capture analysis

Run with the existing prepared WSL inputs:

```sh
python3 tools/test_native_dxvk_h3_host.py
python3 tools/build_native_dxvk_h3.py
python3 tools/package_native_dxvk_h3.py
python3 tools/analyze_native_dxvk_h3.py --log-dir /path/to/copied-four-files
```

The packager creates a ready folder with `switch/`, rollback, instructions,
checksums, notices, exact diagnostic sources and the inherited renderer/driver
source bundle. **It creates no ZIP.** It verifies an existing staged folder
before updating it and refuses unexpected or modified files, preserving any
hardware logs later copied into that folder. Prepared Wine/FEX/Mesa inputs are
still required; this is not a self-contained clean-clone build.

## Production readiness

H1, H2 and H3 establish the native renderer, real PE32 Wine/FEX transport and
native swapchain/Present for a controlled rendering subset on Switch. They
are completed experiment gates, not a production candidate. The largest
remaining work is connecting the game's actual Windows graphics interfaces
to that renderer.

Follow-up: [H4 implements COM proxies and the native launcher/game route](native-dxvk-h4-v1.md).
Its local build/host/ABI checks are separate from the hardware evidence still
needed below; the H3 capture itself remains unchanged.

| Remaining gate | Evidence needed before moving on |
| --- | --- |
| H4: real x86 COM bridge | A PE32 program uses D3D11/DXGI exports and x86 COM vtables, including QueryInterface/AddRef/Release, device/context/resources and a swapchain; struct layouts, returned pointers and mapped data cross the ABI correctly without diagnostic packet calls in the client. |
| Sleeping Dogs integration | Inventory and implement the API subset the original game actually uses; validate required formats, textures, shaders, states, draw variants and Map modes. Establish resource lifetime, low-address mapping, memory budgets and native-thread behavior. Reach the menu and playable scenes through native DXVK. |
| Production validation and rollout | Compare native game FPS and frame times in the same 720p scenes at CPU 1728 / GPU 768 / RAM 1600 MHz with LSFG OFF. Test longer sessions, scene changes, resource recreation and clean shutdown; provide a launcher fallback, reproducible runtime inputs and a verified ready folder. |

The diagnostic Draw path submits three vertices with a fixed pipeline. Its
Present loop does not include the game's rendering workload. No implementation
percentage, delivery date or stable 30 FPS result can be derived from its
roughly five-second run. A working native gameplay build is required to measure
the actual benefit; production readiness also requires stability and packaging
beyond an initial gameplay success. Future diagnostic deliveries remain folders,
with no new ZIP.
