# Native DXVK H4 v6: reduce bridge diagnostic overhead

[Documentation](README.md) · [COM implementation](native-dxvk-h4-v1.md) · [Current status](STATUS.md)

Subsequent feedback: v6 improves reported gameplay to 16–17 FPS, with
12–13 facing crowds and peaks near 22. The [preserved observation](../reports/native-dxvk-h4-v6-gameplay-observation.json)
records 16.67 FPS over the final four windows. This page retains the original
v6 pre-test record; current tools target [H4 v8](native-dxvk-h4-v8-game-detail.md).

V5 now reaches gameplay according to the user. Its last two native Present
windows average **15.07 and 14.39 FPS**. V6 reduces diagnostic work in the
bridge's frequent calls; it builds and passes local checks. **V6 has not been
tested on Switch. No gameplay FPS increase or stable 30 FPS is established.**

## Native DXVK and the remaining cost

DXVK's D3D11 implementation now executes as ARM64 inside the NRO, bypassing
FEX translation of DXVK C++ code. The game still executes as x86 through FEX.
Its PE32 COM proxies convert pointers and structures, cross into the native
dispatcher and resolve native objects. The bridge still serializes native
calls, and `Map` uses a 32-bit guest shadow allocation with copies on Unmap.
The Switch GPU and NVK still perform the resulting rendering work.

Native DXVK therefore offers another optimization path, but its savings can
be consumed by bridging or memory movement. Native does not guarantee a
higher frame rate than the existing x86 path.

The [v5 observation](../reports/native-dxvk-h4-v5-gameplay-observation.json)
links the original supplied bytes and separates the older v3 COM runtime:

| Evidence | Scope |
| --- | --- |
| Final native counters | 9,891,728 calls, 1,633,666 draws, 3,045 Presents, zero recorded bridge failures |
| Last counter interval | 1,022,727 calls over 128 Presents: about 7,990 calls per frame |
| Map copy counter in that interval | About 9.07 MiB per Present; bytes copied, without a measured time attribution |
| Last two 600-interval windows | 15.07 and 14.39 FPS; scene names are absent |
| User visual report | Game reached gameplay; 3D scenes around 15 FPS |
| Supplied `runtime.log` | Byte-identical older v3 COM log; no fresh v5 COM result or guest file supplied |

The log contains no recorded device-loss, first-fault or guest-exit event.
The tail is still running: it does not establish a clean exit or a long
session. Remaining external references at that point do not prove a leak.
The earlier x86 peak near 25 FPS cannot be compared directly with these
window averages without matching scene, camera, clocks and shader-cache state.

## What v6 changes

V5 publishes a 24-field atomic diagnostic snapshot four times per COM call.
It also queries a clock on each call to decide whether a ten-second counter
report is due. These operations occur even for simple setters and draws.

V6 retains detailed snapshots for the first 128 entries, then samples ordinary
call state every 256 entries. Global bridge operations, device calls,
Present, Map, Unmap, Flush and transport faults still publish detailed state.
The periodic report checks its clock every 1,024 calls; explicitly requested
statistics and shutdown still report immediately. Actual counters, guest
pointer validation, object ownership, COM ordering and locking are retained.
FIFO, 720p, existing profiles, Map lifetime and worker clock policy are retained.

`[SD-NDX-PERF] progress_stride=256` identifies this change. Progress totals
describe the last **sampled** completed call. `phase=idle` means that sampled
call completed; an unsampled call may be running. A diagnostic gap, an idle
snapshot or a BEGIN without END does not establish a deadlock. Fault promotion
records the fault after it is detected; it is not a history of every ordinary
call preceding the fault. The bounded log queue can still lose output on restart.

## Local measurement and validation

The [dispatcher benchmark](../reports/native-dxvk-h4-v6-dispatch-benchmark.json)
runs one million actual native `GetType` calls on a DXVK context. It alternates
v5 and v6 in six processes per version, discards the first run of each, and
compares the remaining medians:

| Version | Median host cost per call |
| --- | --- |
| V5 | 620.139 ns |
| V6 | 66.536 ns |

This is about **9.32 times lower dispatch cost for this scalar host case**.
Device creation is outside the timed section; native DXVK and modeled Wine
permissions are exercised. It does not measure the PE32/FEX crossing, Horizon
scheduling, GPU work, all D3D11 methods or gameplay FPS. Snapshot freshness and
promotion of an unsampled invalid-object fault are checked after timing.

Other checks pass within their existing scopes:

- [Native render/COM host test](../reports/native-dxvk-h4-v6-host-test.json):
  7,384,876 checks, two full 720p readbacks, buffer/BC1 data, scalar DSV guards,
  sampler identity, concurrent ownership and 42 matched startup call pairs.
- [PE32 output regression](../reports/native-dxvk-h4-v6-guest-output-check.json):
  actual wrappers execute on Windows against a modeled native endpoint;
  current code passes and both v4 negative controls fail as expected.
- [Logging](../reports/native-dxvk-h4-v6-logging-check.json) and
  [window handoff](../reports/native-dxvk-h4-v6-window-check.json): sanitizer
  checks, blocked output, 20,000 coherent atomic snapshots and ten handoff cases.
- [ABI](../reports/native-dxvk-h4-v6-abi-check.json),
  [launcher](../reports/native-dxvk-h4-v6-launcher-check.json),
  [static game imports](../reports/native-dxvk-h4-v6-game-imports.json) and
  [build](../reports/native-dxvk-h4-v6-build.json): layouts, transactional
  renderer choices, proxy exports and pinned baseline reproduction.

The [folder receipt](../reports/native-dxvk-h4-v6-folder.json) binds the ready
files and source to these checks. Local checks do not validate the Switch
game session, live GPU timing or an FPS increase.

## Install and validate on Switch

Use **`dist/sd-dxvk-native-h4-v6-update/`**, without a ZIP, on the existing
complete installation and working full-memory/low-window forwarder.

1. Close the application from HOME and back up the installed NRO. Copy only
   **`switch/`** from the update folder to the SD root. The first run is COM.
2. Require exit `00000000` and a fresh result for `native-dxvk-h4-v6` with
   `status: PASS`, `sampler_roundtrip_slots_verified: 72`, and
   `dsv_guard_checks: 16`. Save `drive_c/native-dxvk-h4-result.json`,
   `drive_c/native-dxvk-h4-guest.log`, `native-dxvk-h4/runtime.log`, and
   `native-dxvk-h4/HKShip.exe_d3d11.log` before game launch overwrites that log.
   Paths are relative to `switch/sleepingdogs-fex/`.
3. After PASS, close from HOME and copy **`start-game/switch/`** to the SD root.
   Select Native ARM64, Launch GUI, Performance, FPS HUD and 1280×720. Keep
   CPU 1728 / GPU 768 / RAM 1600 MHz for comparison. This build does not set
   clocks; native mode forces LSFG off.
4. Test the same save, route and camera after the cache warms, including the
   crowded area, pause/resume and clean exit. Save `fex-runtime.log`,
   `native-dxvk-h4/HKShip.exe_d3d11.log`, and a new `crash.log` if one occurs.
   Record actual gameplay FPS and last visible screen if startup fails.

`start-com-test/switch/` repeats COM. `rollback-v18/switch/` restores the pinned
v18 NRO, x86 DLL pair and renderer selection. Prior delivery folders remain
separate. Production requires sustained gameplay, lifetime checks, dynamic API
coverage and a matched native-versus-x86 comparison; stable 30 FPS is still open.

## Rebuild and capture analysis

Prepared pinned Wine/FEX/Mesa/SDK inputs are required. The builder uses
`/home/blekjek/sleepingdogs-native-dxvk-h4-v6`. The benchmark also requires
Git history containing v5 commit `b51f1aa9f2388e43926430a2f311d05c3cff3729`;
the PE32 regression retains its v4 historical negative controls.

Run the PE32 check with Windows Python:

```powershell
python tools/test_native_dxvk_h4_guest_outputs.py
```

Run the other steps in WSL Ubuntu:

```sh
python3 tools/build_native_dxvk_h4.py
python3 tools/test_native_dxvk_h4_host.py
python3 tools/benchmark_native_dxvk_h4_dispatch.py
python3 tools/check_native_dxvk_h4_abi.py
python3 tools/test_native_dxvk_h4_window.py
python3 tools/test_native_dxvk_h4_logging.py
python3 tools/check_native_dxvk_h4_launcher.py
python3 tools/check_native_dxvk_h4_imports.py
python3 tests/check_native_dxvk_h4_capture.py
python3 tools/package_native_dxvk_h4.py
python3 tools/analyze_native_dxvk_h4.py --mode com --log-dir /path/to/saved-com-files
python3 tools/analyze_native_dxvk_h4.py --mode game --runtime-root /path/to/copied-runtime
```

At this iteration the analyzer defaulted to v6. Current tools target v8;
use `--expected-build native-dxvk-h4-v6` for these captures, or v5 (or
v2/v3/v4) for earlier captures. `ROUTE_OBSERVED` establishes a native Present
route without authenticating exact running binaries, clocks, visible scenes
or every file's session. Save fresh COM files before testing game launch.
