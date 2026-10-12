# Native DXVK H4 v8.1: guest transport and Light 720p correction

This candidate removes repeated Wine critical-section calls from the initialized
PE32-to-native dispatch path and fixes Light rejecting the supplied
`GlobalSetting=-1`. Resolution remains 1280×720. A subsequent Light session
reaches gameplay, with user-reported 20–22 FPS and crowded lows near 16.
This remains an experiment; stable 30 FPS and production readiness are unproven.

The subsequent [v9 candidate](native-dxvk-h4-v9-memory-batching.md) implements
the immediate probe, Map and batching experiments described below.

## Subsequent Light 720p capture

The [preserved Light observation](../reports/native-dxvk-h4-v8.1-light-observation.json)
records the supplied v8.1 native game route with Light applied at 1280×720.
The user reports 20–22 FPS, crowded-area lows near 16, and peak 30 with a
restricted view. The last five complete 600-interval Present windows pool
to **20.67 FPS**; individual window averages range from 18.57 to 24.96 FPS.
No bridge failure or device-lost error is captured. This does not establish
a clean exit, a fresh v8.1 COM pass, or a matched scene/clock comparison.
The separately supplied `runtime.log` is byte-identical to the old v3 COM
runtime. The v8 normal-settings session and this Light session cannot isolate
the endpoint optimization's contribution from quality or scene changes.

The last progress interval whose endpoints both have zero active maps spans
94 Presents: **8,609 bridge calls, 1,344 draws and 9 MiB copied per Present**,
rounded for readability. These are sampled workload counts, not a CPU/GPU
profiler. In particular, neither low sampled gate waiters nor high draw counts
alone identifies the limiting thread or GPU stage.

The remaining candidates, in order of investigation, are:

1. **Per-call bridge work.** `Context::write` currently invokes Wine read
   validation and then write validation. In the pinned Wine source, the write
   helper already reads and writes each probed byte. A single validated
   read/write probe may remove repeated exception setup and memory touches.
   It needs actual Wine fault/protection tests, keeping overflow checks and
   failure propagation. Further command batching could reduce transitions,
   but must preserve guest pointer data, object lifetime, thread ordering and
   synchronous boundaries; it is a separate, larger change.
2. **Map shadow traffic.** Copy-out still transfers full mapped buffers;
   WRITE_DISCARD also zero-fills the guest shadow, which is not counted in
   `copy_bytes`. [D3D11 defines previous WRITE_DISCARD contents as undefined](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/ne-d3d11-d3d11_map),
   making repeated zero-fill worth measuring and testing independently.
   Preserving map modes must retain their data, and skipping zero-fill does
   not remove the full copy-out. Zero-copy needs a guest-addressable native
   allocation path, not simply exposing a 64-bit pointer.
3. **Bounded automatic DXVK flushing.** The native binary already contains
   `d3d11.sdSubmissionBatching`, but this session logs `enabled=0`. The last
   cumulative record has 19,712 non-empty context flushes: 6,680 explicit,
   254 synchronization, 23 strong hints and 12,755 weak hints. The existing
   opt-in changes automatic hints only while at least two submissions are
   pending, below 24 chunks and the cost cap. It preserves mandatory flushes.
   Flush totals do not measure GPU time or predict a gain; compare enabled
   and disabled at the same scene, quality and clocks before changing defaults.

These candidates have not been applied by this capture review. The delivered
v8.1 folder remains unchanged. At 20–22 FPS, reaching 30 requires roughly
27–33% less elapsed time per frame; a 16 FPS crowded view needs about 47%
less. A peak of 30 therefore does not imply that stable 30 is a small change.

## Evidence and change

The [v8 capture and observation](../reports/native-dxvk-h4-v8-gameplay-observation.json)
preserve the user's normal-settings session. Reported results are typical
17–20 FPS, crowded running 13–16, confined peak 26, with only 1–2 FPS improvement.
The last five complete Present windows pool to **18.76 FPS**. The last sampled
interval contains 838,144 bridge calls, 135,695 draws and 87 Presents: about
**9,634 calls and 1,560 draws per Present**. It also copies exactly **9 MiB per
Present** through Map shadows. These are workload counts, not CPU/GPU timing or
a controlled comparison. The supplied COM files match the old v3 capture.

In v8 every `proxy_call` enters and leaves `proxy_lock` just to retrieve an
endpoint that never changes after successful discovery. V8.1 publishes an
immutable descriptor containing the function and complete 64-bit handle. An
acquire load bypasses discovery and its lock on the hot path. First-use
discovery remains serialized and retryable; it uses a local handle until success. The
[compiler's acquire/release contract](https://gcc.gnu.org/onlinedocs/gcc/_005f_005fatomic-Builtins.html)
orders the complete handle publication before another thread uses it.

The captured FEX Fastest preset disables scalar/vector/memcpy TSO. To avoid
depending on ordinary-store ordering, publication uses a sequentially
consistent store (a locked x86 exchange, on first use only). Hot-path handle
and function loads retain an address dependency on the descriptor pointer.
The [pinned compiler/FEX audit](../reports/native-dxvk-h4-v8.1-endpoint-audit.json)
checks both properties and the native atomic swap implementation. See the
[Arm memory model](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20memory%20model%20guide.pdf?revision=58b1dd0a-3800-4218-b21a-f95a0332034c)
for address dependency ordering. These are static checks alongside Windows
race tests; they are not a hardware FEX stress result.

Proxy creation, reference accounting, native serialization, pointer validation,
and synchronous method order retain their existing protections. This is not a
batched or zero-copy bridge. The 16 MiB / four-entry idle Map cache, preserving
copies, and native WRITE_DISCARD zeroing remain as in v8.

The [actual PE32 transport test](../tools/test_native_dxvk_h4_guest_transport.py)
runs the current and pinned v8 source on Windows with modeled Wine discovery
and native dispatch. It checks eight 12-thread first-use races with deliberately
split handle writes, four discovery failure/retry paths, error propagation,
and hot dispatch while another thread holds the unrelated proxy-table lock.
The v8 control takes 10,000 lock pairs for 10,000 warm calls; current takes zero.
Separate uninstrumented runs time the full generated DrawIndexed wrapper.
See the [receipt](../reports/native-dxvk-h4-v8.1-guest-transport.json) for the
host timings and exact sources. These timings do not estimate Switch FPS.

## Supplied XML and Light

The archived XML is Version 1 at 1280×720. Its seven individual quality fields
are zero; GlobalSetting is -1. The previous helper rejected the latter as a
nonnumeric value. V8.1 accepts exactly this sentinel in GlobalSetting and writes
zero, with precise field diagnostics for other invalid values. Other negative
quality values remain rejected. For this particular file, the resulting Light
XML differs only in **GlobalSetting -1 → 0**. Backup and Restore original
preserve the original bytes, including the sentinel.

A [static audit of the original executable](../reports/original-game-global-setting-audit.json)
finds an unsigned-text reader that falls back to the initialized preset 2 when
the text begins with a minus. That preset can overwrite individual fields after
they are read. This is a reason not to infer live minimum quality solely from
the XML's zeros. We have not authenticated the game's in-memory quality values
or proved that this path caused the reported frame rate or `undefined` label.

The captured-file replay reproduces v8's rejection, then verifies successful
application, repeated use, and byte-exact restore with the corrected helper.
Filesystem failure/interruption checks and actual launcher UI tests also pass.
No game assets, executable, save, or UserOptions.dat are modified or distributed.

## Install and compare

Folder: `dist/sd-dxvk-native-h4-v8.1-update/` (no ZIP).

1. Close the app fully from HOME. Copy the top-level `switch/` folder to the SD
   root. Use the existing successful full-memory forwarder, not Album.
2. Run the COM self-test first. Expected result: `native-dxvk-h4-v8.1`, PASS,
   exit 00000000, 72 sampler slots and 16 DSV guards. Archive its result JSON,
   guest log, native runtime log and DXVK log before running the game.
3. To compare runtime cost first, apply `start-game/switch/` and keep the same
   game settings as v8. Then try `start-game-light/switch/` to include the Light
   correction. Both select native DXVK; the Settings menu can also select detail.
4. Use GUI, Performance, FPS HUD, 1280×720, and the same save, camera and crowded
   route after warming caches. Reference clocks are CPU 1728 / GPU 768 / RAM
   1600 MHz; this build does not change clocks. LSFG remains off for native.
5. Save `fex-runtime.log` and `native-dxvk-h4/HKShip.exe_d3d11.log` after each
   game run. Send a new `crash.log` if a crash occurs. Check pause/resume and
   normal exit, and report typical/minimum FPS in addition to peaks.

New runtime markers include `BUILD native-dxvk-h4-v8.1` and
`[SD-NDX-PERF] guest_endpoint=acquire-release`. This identifies the built route;
it is not cryptographic authentication of the running binary. Existing async
logging may lose its tail after a forced restart. Sampled progress counters do
not describe every live call, and Present windows may include menus/loading.

`Restore original` restores the original XML and disables Light. Choosing
`Game settings` alone stops applying Light but keeps current file values.
The v8 folder remains available for comparison; `rollback-v18/switch/` restores
the supplied x86 route and disables Light. Restore original quality first if
desired. Neither rollback procedure changes saves.

## Rebuild

Use the prepared SDK/Wine/FEX/Mesa and pinned native DXVK inputs described in
[Building](BUILD.md); this is not a self-contained clean-clone runtime build.
Run the Windows PE32 checks with Windows Python:

```text
python tools/test_native_dxvk_h4_guest_transport.py
python tools/test_native_dxvk_h4_guest_outputs.py
python tools/test_native_dxvk_h4_guest_lookup.py
python tools/test_native_dxvk_h4_guest_maps.py
```

Run the other checks and packaging in the prepared WSL environment:

```text
python3 tools/build_native_dxvk_h4.py
python3 tools/check_native_dxvk_h4_endpoint.py
python3 tools/check_native_dxvk_h4_abi.py
python3 tools/test_native_dxvk_h4_host.py
python3 tools/test_native_dxvk_h4_arrays.py
python3 tools/benchmark_native_dxvk_h4_dispatch.py
python3 tools/test_native_dxvk_h4_window.py
python3 tools/test_native_dxvk_h4_logging.py
python3 tools/test_native_dxvk_h4_game_quality.py
python3 tools/test_native_dxvk_h4_game_quality_ui.py
python3 tools/check_native_dxvk_h4_launcher.py
python3 tools/check_native_dxvk_h4_imports.py
python3 tests/check_native_dxvk_h4_capture.py
python3 tools/package_native_dxvk_h4.py
```

The packager checks source-bound receipts, binaries, copied evidence, patch
reproduction, renderer profiles and every distribution checksum. Fifteen
receipts include the new transport check. Local success does not establish
production readiness or a stable 30 FPS result.
