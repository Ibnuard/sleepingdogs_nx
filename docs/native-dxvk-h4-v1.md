# Native DXVK H4: x86 COM proxies and game launch candidate

[Documentation](README.md) · [H3 Switch result](native-dxvk-h3-v1.md) · [Current status](STATUS.md)

**Historical v1 record.** The first game capture failed before native device
creation because the launcher framebuffer had not been handed off. Use the
[H4 v3 candidate and current instructions](native-dxvk-h4-v3-sponsor.md).
V1's folder and receipts are preserved. V2 subsequently passed the Switch
COM self-test and native window handoff, but the game froze at its sponsor page.

H4 implements the Windows D3D11/DXGI COM connection and a **DXVK Native ARM64**
launcher choice for the original `HKShip.exe`. It is ready for a Switch COM
self-test followed by game validation. **At v1 packaging, H4 guest execution,
Sleeping Dogs gameplay and an FPS gain had not been verified on Switch.** H1–H3's
successful hardware results remain separate prerequisites.

```text
Sleeping Dogs x86
  → Wine + FEX
  → PE32 d3d11.dll / dxgi.dll / sdndx4.dll proxies
  → native ARM64 DXVK D3D11/DXGI implementation
  → native Vulkan / Mesa NVK
  → Tegra GPU
```

Wine still provides Windows services; FEX still executes the game and its
remaining x86 modules. DXVK's C++ renderer and worker threads execute as
ARM64. The NRO links directly to the existing native Vulkan driver. This
experiment does not replace Wine, port the game or add frame generation.

## Implementation and boundaries

- The original proxy generator uses pinned native headers and Wine IDL
  signatures. Its inventory has **47 interfaces and 588 vtable entries**,
  including inherited entries. That is an implementation inventory, not 588
  independently validated methods or proof of the game's complete API coverage.
- Fixed-width ABI 4 packets carry 32-bit addresses and generation-tagged object
  tokens. Native pointers never become guest COM pointers. QueryInterface
  preserves canonical IUnknown identity; native acquired references and guest
  proxies have separate reference accounting. Slots retire before generation
  wraparound. Shutdown rejects stale/new calls and cleans owned maps/references.
- Plain forwarded structures are checked for size and alignment on PE32 and
  ARM64. Explicit adapters handle pointer-bearing initial data, input layouts,
  stream-output declarations, mapped data, private interfaces, DXGI descriptions,
  UTF-16 strings, HWND metadata and size_t outputs.
- Map returns a low-address guest `VirtualAlloc` shadow until Unmap, with
  resource/context references retained through that lifetime. Writable modes
  copy back before native Unmap. NO_OVERWRITE preserves the untouched bytes;
  full shadow copying can still be expensive. This is **not zero-copy Map**.
- A recursive native gate protects the registry. Guest proxy locks are released
  before native calls, including AddRef/Release, to avoid deadlock with another
  thread while Multithread::Enter is held. Balanced Enter/Leave remains a caller
  requirement. Host worker names, masks and priorities are logged; no new native
  affinity tuning is claimed.
- The native swapchain uses the trusted libnx window at **1280×720**. Guest HWND
  and fullscreen state are metadata, including live QueryInterface aliases.
  Console ownership is released before native rendering.
- Game imports are checked against the actual DLL exports. This `HKShip.exe`
  imports `D3D11CreateDevice` and `CreateDXGIFactory1`. That static check cannot
  prove dynamic QueryInterface calls, formats, shader/state combinations or
  draw variants used during gameplay.
- External shared handles, software adapters, GDI surfaces, IDXGISurface Map,
  and newer D3D11/DXGI/video interfaces remain unsupported. Unknown IIDs return
  E_NOINTERFACE and are logged once per IID, up to 64 distinct IIDs. They may be
  optional feature probes. Unsupported calls and bridge faults have separate
  runtime markers; native graphics loading never silently falls back to Wine's
  builtin D3D11/DXGI implementation.

## Launcher and recovery

The candidate retains **DXVK 3.1.1**, **DXVK 2.7.1 async** and adds
**DXVK Native ARM64**. All three use one eight-target renderer transaction,
including the `sdndx4.dll` companion. Missing inputs prevent installation;
failed renames and interrupted commits restore the previous files. Recovery
also accepts the older five- and seven-target journals.

The two legacy binary sets retain their pinned versions. Five canonical
configuration templates per renderer are regenerated from the project's
existing profile recipes; customized template files should be backed up.
Stored HUD/graphics preferences and `UserOptions.dat` are not replaced.
None / FPS / Full HUD remains available. **LSFG is forced OFF for native
DXVK**, even when its stored preference is ON, so comparisons use original
frames. Native DXVK uses an isolated shader-cache/log directory and the real
HKShip application profile.

## Completed local validation

| Check | Result and limits |
| --- | --- |
| Native build | v18 ELF reproduced exactly before overlay; PE32 proxy/test imports audited; ARM64 NRO links with no unresolved nonweak symbols |
| Real DXVK host fixture | 7,384,812 checks; both 720p image readbacks, 3,072 buffer bytes, 80 BC1 mip/array bytes, 60 synthetic presents and 2,000 reference pairs from four host threads |
| Pointer/lifetime cases | COM identity, DXGI parent chain and metadata aliases, descriptor/view arrays, private interfaces, Map modes, empty UpdateSubresource boxes, invalid/stale tokens and modeled permissions; host-only allocation fault injection checks both device/context adoption rollback paths; zero remaining external bridge interfaces/maps |
| Compiled layouts | 45 directly forwarded/wire types have matching PE32/ARM64 size and alignment; pointer-bearing types use separate adapters or are explicitly unsupported |
| Launcher | Three renderers, fifteen profiles, companion preflight, staging sync failure, rename rollback and interrupted eight-target recovery under ASan/UBSan with modeled Horizon rename/sync outcomes; not physical storage durability |
| Static game imports | Both imported graphics entry points are exported by the built proxy DLLs; dynamic COM/game behavior still pending |
| Capture analyzer | Synthetic negative fixtures reject incomplete, stale, partial and host-only results; even a 60 FPS Present window is never labeled confirmed gameplay |

The host renderer is lavapipe/llvmpipe with a private authenticated Xvfb
window and low mmap. It directly invokes the native bridge with modeled Wine
permissions. **It does not execute the PE32 proxies, FEX or Switch driver.**
Host timings are synthetic and are not a performance estimate for Switch.
The PE32 self-test adds actual guest reference threads to cover the proxy-lock
case when run on hardware; that part is not yet executed locally.

Receipts are [build](../reports/native-dxvk-h4-v1-build.json),
[host](../reports/native-dxvk-h4-v1-host-test.json),
[ABI](../reports/native-dxvk-h4-v1-abi-check.json),
[launcher](../reports/native-dxvk-h4-v1-launcher-check.json),
[imports](../reports/native-dxvk-h4-v1-game-imports.json) and
[folder](../reports/native-dxvk-h4-v1-folder.json). Original H1–H3 sources,
inputs, delivered NROs and capture records remain separate.

## Switch validation: one NRO, folder only

Use local **`dist/sd-dxvk-native-h4-v1-update/`**, an update for the working
v18 installation. It contains `switch/`, `start-game/`, `start-com-test/`,
`rollback-v18/`, checksums, sources/notices and `README-INSTALL.txt`; no ZIP.

1. Fully close from HOME and back up the installed NRO/template files. Copy
   **only `switch/`** to SD root. Keep the low-window/full-memory forwarder
   that passed H3 and the complete existing runtime/game installation.
2. Launch the automatic COM self-test: factory/adapter/device, concurrent
   references, buffers, BC1 mip/arrays, shaders/states/private interfaces,
   two 720p readbacks, then 300 blue-screen Present calls. Wait for
   `H4 COM test exited: 00000000` and a fresh result `PASS`.
3. Preserve `drive_c/native-dxvk-h4-result.json`,
   `drive_c/native-dxvk-h4-guest.log`, `native-dxvk-h4/runtime.log`, and
   `native-dxvk-h4/HKShip_d3d11.log`. A hang/failure needs diagnosis first.
4. After COM PASS, close from HOME and copy **`start-game/switch/`** to SD
   root. Those two selection files activate normal launcher/game mode.
   Choose DXVK Native ARM64, Launch GUI, 1280×720 and FPS HUD. Reference clocks
   remain CPU 1728 / GPU 768 / RAM 1600 MHz; the build does not alter clocks.
5. Test menu, loading, playable scenes, crowded areas, transitions, pause and
   exit. Compare the same route/camera/settings/clocks against DXVK 3.1.1 on
   the same H4 NRO, with warmed caches. Preserve `fex-runtime.log` and native
   DXVK log. Report visible output and **gameplay FPS** separately from menu FPS.

`[SD-NDX-COM] FIRST_PRESENT` proves native COM presentation reached the
backend. `[SD-NDX-FPS]` summarizes 600 native Present intervals with LSFG OFF;
menu/loading/pause can be mixed into those windows. Neither marker alone
establishes playable correctness or stable 30 FPS. Resource counts cover
bridge external interfaces/maps, not all internal DXVK/driver allocations.

For full restoration, close from HOME and copy **`rollback-v18/switch/`**.
It restores the pinned v18 NRO, legacy renderer selection and matching
D3D11/DXGI game DLLs. For another COM run, copy `start-com-test/switch/`.

## Rebuild and analyze

The commands below document the original v1 workflow. Current tools target v2;
use its [current recipe](native-dxvk-h4-v2-window.md#local-checks-and-rebuild),
which also requires the window-handoff regression check.

Prepared local v18/H1 Wine/FEX/Mesa/SDK inputs and pinned legacy renderer
binaries are still required. This is not a self-contained clean-clone build.

```sh
python3 tools/build_native_dxvk_h4.py
python3 tools/test_native_dxvk_h4_host.py
python3 tools/check_native_dxvk_h4_abi.py
python3 tools/check_native_dxvk_h4_launcher.py
python3 tools/check_native_dxvk_h4_imports.py
python3 tests/check_native_dxvk_h4_capture.py
python3 tools/package_native_dxvk_h4.py
python3 tools/analyze_native_dxvk_h4.py --mode com --log-dir /path/to/four-files
python3 tools/analyze_native_dxvk_h4.py --mode game --runtime-root /path/to/copied-runtime
```

Packaging verifies fresh source/binary/test hashes and reproduces all four
overlay patches. It preserves changed staged files and added hardware logs by
refusing to overwrite them. Game files, saves, keys and proprietary LSFG shader
payloads are not included. H4 is an integration candidate; production approval
still requires actual COM/game hardware captures, long-session resource checks
and reproducible native-FPS evidence.
