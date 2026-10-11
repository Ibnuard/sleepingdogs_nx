# Native DXVK H4 v7: faster object lookup and temporary arrays

[Documentation](README.md) · [Current status](STATUS.md) · [Previous v6](native-dxvk-h4-v6-dispatch.md)

The user reports that v6 reduces slow motion, with gameplay usually around
16–17 FPS, a peak near 22 when looking up/down and 12–13 facing crowds. Its
last four 600-Present windows average **16.67 FPS** together. V7 targets two
remaining costs in the bridge: linear proxy searches and temporary native
pointer-array allocations. Subsequent [v7 feedback and logs](../reports/native-dxvk-h4-v7-gameplay-observation.json)
report around 20 FPS, peak 25 and crowded-running lows near 13; the last five
Present windows pool to 19.07 FPS. This is not a matched benchmark. Current
tools target [v8 Map reuse and Light 720p](native-dxvk-h4-v8-game-detail.md).

## Evidence and scope

The [v6 observation](../reports/native-dxvk-h4-v6-gameplay-observation.json)
preserves all three supplied files and separates the older v3 COM runtime
from the current game logs. Native v6, Performance, 1280×720, FIFO and LSFG OFF
appear in the game capture. It records no bridge fault or device loss.
The latest FPS marker reaches 4,201 Presents; the latest earlier statistics
line is at 4,167 Presents, with 21,092,352 calls and 3,333,943 draws. There is
no shutdown record, so these are not complete session totals.

The last counter interval contains about 5,911 calls, 765 draws and exactly
9 MiB of Map copies per Present. These counters do not measure how much frame
time is spent on the CPU, bridge or GPU. Scene labels and current clock
telemetry are absent; the camera-dependent rates come from the user. They
support testing object-heavy rendering but do not isolate one bottleneck.

## Implementation

The PE32 proxy previously searched one linked list whenever it wrapped a
returned native interface. Final release also searched that list. V7 uses
4,096 buckets keyed by the full generation-bearing token and interface type,
plus intrusive links for removal. Lookup still compares the complete key
after hashing. It preserves proxy identity, null results, lock ordering and
native-reference rollback on allocation failure. This path is used by COM
outputs; it is not invoked for every draw or setter.

The table uses 16 KiB in PE32 and adds 12 bytes per proxy (about 188 KiB at
16,000 proxies). Native live-interface counters are not a census of PE32
proxies. The lazy Unix-entry initialization and its existing lock remain.

Native conversions formerly allocated a `std::vector` for each pointer-array
argument. The 143 generated temporary arrays now use scoped inline storage
through 128 pointers, initialize the live prefix, and retain a throwing heap
fallback for larger supported arrays. They own temporary storage only;
AddRef/Release behavior and guest-memory checks are retained. The bridge
still supports up to 16,384 array entries where the API permits them.

V6 diagnostic sampling, Map shadows/copies, FIFO, native worker scheduling
and 720p remain in place. The new runtime marker is
`[SD-NDX-PERF] proxy_lookup=hash native_pointer_array_inline=128`.

## Local checks

- [Proxy lookup](../reports/native-dxvk-h4-v7-guest-lookup.json): real PE32
  code on Windows with a modeled native endpoint; populated lookup, identity,
  collisions, token generations, aliases, release, allocation failure and
  concurrent wrapping. Timings describe this host fixture, not Wine/FEX.
- [Array storage](../reports/native-dxvk-h4-v7-array-check.json): ASan/UBSan
  covers 0, 1, 12, 128, 129 and 16,384 entries, null initialization, allocation
  failure and exception cleanup. In 10,000 modeled short binding calls,
  the old vector makes 10,000 allocations and inline storage makes zero.
- [Native dispatcher measurement](../reports/native-dxvk-h4-v7-dispatch-benchmark.json):
  actual DXVK `PSSetSamplers` calls with 12 null bindings, alternating v6 and
  v7 on the host. Device creation and binding readback are outside timing.
  A repeated unchanged binding isolates conversion cost; it is not a game workload.
- [Native render/COM](../reports/native-dxvk-h4-v7-host-test.json) and
  [PE32 output regression](../reports/native-dxvk-h4-v7-guest-output-check.json)
  retain render/readback, scalar DSV, sampler identity, ownership and v4
  negative controls.
- [Build](../reports/native-dxvk-h4-v7-build.json),
  [ABI](../reports/native-dxvk-h4-v7-abi-check.json),
  [imports](../reports/native-dxvk-h4-v7-game-imports.json),
  [launcher](../reports/native-dxvk-h4-v7-launcher-check.json),
  [window](../reports/native-dxvk-h4-v7-window-check.json),
  [logging](../reports/native-dxvk-h4-v7-logging-check.json) and
  [folder receipt](../reports/native-dxvk-h4-v7-folder.json) bind the candidate
  to its compiled artifacts and local checks.

None of these measurements establishes a Switch FPS gain. Native DXVK removes
translation of DXVK code; the x86 game, proxy conversion, guest/native calls,
Map copies and GPU work still contribute to each frame.

## Install and compare

Use **`dist/sd-dxvk-native-h4-v7-update/`**, a ready folder without a ZIP,
over the existing complete installation and working low-window forwarder.

1. Close from HOME, back up the installed NRO, then copy **`switch/`** to SD
   root. Require COM exit `00000000` and a fresh `native-dxvk-h4-v7` result
   with `status: PASS`, 72 sampler-slot checks and 16 DSV guard checks.
2. Save the COM files before game launch: `drive_c/native-dxvk-h4-result.json`,
   `drive_c/native-dxvk-h4-guest.log`, `native-dxvk-h4/runtime.log`, and
   `native-dxvk-h4/HKShip.exe_d3d11.log`, relative to `switch/sleepingdogs-fex/`.
3. After PASS, close from HOME and copy **`start-game/switch/`** to SD root.
   Use Native ARM64, Launch GUI, Performance, FPS HUD and 1280×720. Keep the
   reference clocks CPU 1728 / GPU 768 / RAM 1600 MHz; this build sets no clocks.
4. Warm the cache, then compare the same save, location and camera direction,
   especially the crowded view. Test pause/resume and clean exit too. Save
   `fex-runtime.log`, `native-dxvk-h4/HKShip.exe_d3d11.log` and a new `crash.log`
   if one appears. Report typical FPS separately from peaks.

`start-com-test/switch/` repeats COM. `rollback-v18/switch/` restores the pinned
x86 runtime. V6 remains in its separate folder for an adjacent-version test.
Stable 30 FPS and production readiness remain open hardware validation goals.

## Rebuild

Prepared pinned Wine/FEX/Mesa/SDK inputs are required. This recipe originally
targeted v7 in `/home/blekjek/sleepingdogs-native-dxvk-h4-v7`; current tools
target v8. Use commit `e0995ccfc2819d20b5df8f60bff784996fb479c1` for the original v7 tools. Host comparisons need the
v6 commit `b98557b28f0011c5eb75d934b20fe60b29cc1a18`; PE32 output controls also
need the v4 commit recorded in their receipt.

Windows Python:

```powershell
python tools/test_native_dxvk_h4_guest_outputs.py
python tools/test_native_dxvk_h4_guest_lookup.py
```

WSL Ubuntu:

```sh
python3 tools/build_native_dxvk_h4.py
python3 tools/test_native_dxvk_h4_arrays.py
python3 tools/test_native_dxvk_h4_host.py
python3 tools/benchmark_native_dxvk_h4_dispatch.py
python3 tools/check_native_dxvk_h4_abi.py
python3 tools/test_native_dxvk_h4_window.py
python3 tools/test_native_dxvk_h4_logging.py
python3 tools/check_native_dxvk_h4_launcher.py
python3 tools/check_native_dxvk_h4_imports.py
python3 tests/check_native_dxvk_h4_capture.py
python3 tools/package_native_dxvk_h4.py
```

The analyzer now defaults to v8; use `--expected-build native-dxvk-h4-v7` for v7. Use `--expected-build native-dxvk-h4-v6` for
previous captures. Sampled idle states do not describe every active call;
missing queued output does not establish deadlock. A matched gameplay test
and sustained resource lifetime checks are needed before production.
