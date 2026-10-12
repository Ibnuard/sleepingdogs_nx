# Compact COM v1 and launcher preparation

[Documentation](README.md) · [Status](STATUS.md)

This candidate combines a real rendering-transport optimization with the
requested release launcher work. It retains native H4 v9 DXVK/NVK, FEX
context v1, local COM references and Light **1280×720**. It is a test update
for an already working Sleeping Dogs installation, not a public release.
Stable 30 FPS has not been demonstrated.

## Performance change

The latest [captured game log](../reports/native-dxvk-h4-game-6dad1eee57ca.json)
confirms the native route without bridge faults or device loss. Later 600-frame
windows take about 29.5–31.6 seconds, approximately 20.3–19.0 FPS. Crowded
intervals contain roughly 6,000–9,600 bridge calls per frame. Map traffic remains
9 MiB per frame. These samples are not matched camera/clock A/B measurements.
The user reports an improvement with the preceding candidate; the separate
reference-counter log was not supplied, so its exact contribution is unknown.

Compact COM v1 targets 46 input-only context setter/draw methods. The x86
wrapper initializes the 32-byte header and the arguments it actually sends,
instead of clearing all 160 bytes. The native dispatcher copies those inputs
and returns the 12-byte result area. For DrawIndexed, initialized guest packet
storage falls from 160 to 44 bytes, and guest/native packet copies from 320 to 56 bytes.
Those are byte counts for this call, not an FPS prediction.

The whole packet still receives a fresh Wine writable-range probe. The host
checks ABI, method and exact argument count, zeroes omitted fields locally,
and runs the unchanged typed adapters and object/pointer validation. Calls
remain synchronous and ordered. Map, queries, resource creation and Present
use the original packet format; copies, fences and ownership are preserved.
The existing DXVK and FEX optimizations stay active.

The new NRO also accepts the previous full packets. `performance-off/` restores
the exact Native Ref v1 DLL while keeping the same new launcher/NRO; the
checker explicitly accepts both approved hashes. `performance-on/` restores
compact packets. Do not install the compact DLL on an old NRO.

## Launcher

The keyboard is pinned to PES13 commit
[`38750c20`](https://github.com/Ibnuard/pes13_nx/tree/38750c20a303f9fc6c373edaada0fad3c86d5b4b).
It renders over the game frame and supports editable fields, touch, controller
input, Unicode delivery, focus cancellation and input release. The host Vulkan
adapter covers native DXVK and Wine Vulkan. Closed overlays do not allocate,
copy pixels or submit GPU work. Opening it allocates bounded per-image staging
buffers, which remain until the swapchain is destroyed.

- **Settings → Keyboard:** shortcut, position and hold time. Default shortcut
  is L + R + Left Stick, instant. Y moves the overlay; B closes it. Capture is
  optional and replaces screenshots while that gameplay session is active.
- **Settings → Show debug launch:** off by default. Enabling it adds Launch
  Debug after the normal home tiles. The choice persists.
- **System Check:** runs before home and can be repeated from Settings.
  It checks Application mode, the Sleeping Dogs title/memory allowance, the
  active 39-bit layout and actual low-window mapping probes, game files, and
  SHA-256 hashes of the supplied runtime/assets. Missing/inactive low-memory
  support blocks Play. A file marker alone never passes this check.

The checker uses an embedded font, so missing SD artwork does not hide the
error. Its report is `system-check.log`. Retry is read-only. This candidate
does not download PES13 runtime files or install kernel/loader patches.
Use the existing matching FEXTendo Memory environment and Sleeping Dogs HOME
forwarder described in [Installation](INSTALL.md#boot-and-forwarder).

## Installation and comparison

Use `dist/sd-launcher-compact-v1-update/`; no ZIP is produced. Close the
application completely from HOME, then copy **only its top-level `switch/`**
to the SD root. It includes the matching NRO, compact proxy, FEX module,
verified runtime DLLs and launcher assets. Game archives and saves are absent.
Other options and the installed boot patch remain prerequisites.

The default opens the GUI, selects native DXVK and Light 720p, and hides Debug.
Do not copy every subfolder at once. `start-com-test/` enables the synthetic
COM check; after it completes, `start-game/` returns to the GUI. Hardware COM,
keyboard and gameplay validation are still required before public release.

For FPS, compare performance-on/off on the same NRO, scene, camera, profile
and CPU 1728 / GPU 768 / RAM 1600 MHz. Keep 720p and LSFG off; allow shader
warmup. Capture an open street, a crowd/run and a narrow view separately.
`[SD-NDX-WIRE] compact-v1 calls=` confirms use of the optimized route; zero
compact calls is expected with the comparison DLL.

Send the fresh `fex-runtime.log`, `system-check.log`,
`native-dxvk-h4/HKShip.exe_d3d11.log`, and `drive_c/native-dxvk-ref-v1.log`.
For the COM check, also retain its result JSON, guest log and runtime log.
`rollback-ref-v1/` restores the prior NRO/proxy while retaining FEX context v1.

## Validation boundaries

The tests execute real generated PE32 wrappers on Windows and actual native
DXVK through software Vulkan on the host. They also check poisoned omitted
arguments, invalid counts, resource ownership, rendering readback and existing
Map behavior. Launcher UI, file validation, keyboard delivery and a strict
Vulkan synchronization/resource model run under ASan/UBSan. The linked ARM64
heap gate is tested separately with modeled kernel calls. These checks do
not measure Switch FPS or certify physical keyboard/presentation behavior.

Build with `tools/build_native_dxvk_compact.py`, then
`tools/build_launcher_v1.py` in the prepared WSL environment. Run the
`test_launcher_v1.py`, `test_launcher_binary.py`, and compact host/guest tests;
the guest runner builds under WSL and executes under Windows. Exact inputs,
generated sources and commands are recorded in the build receipts. The build
reuses pinned prior native objects; a clean clone alone is not a full SDK.
