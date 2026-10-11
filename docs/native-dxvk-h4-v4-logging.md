# Native DXVK H4 v4: remove synchronous diagnostic I/O from bridge calls

[Documentation](README.md) · [COM implementation](native-dxvk-h4-v1.md) · [Current status](STATUS.md)

Subsequent hardware feedback: v4 passed the sponsor/animation stage and recorded
1,020 native Presents, then crashed at Press Start. The current candidate is
[H4 v5](native-dxvk-h4-v5-com-outputs.md), which fixes COM output memory. This
page retains the original v4 implementation and validation record; current
build/package/analyzer tools target v5.

The v3 COM client completed on Switch, but the game still froze at the sponsor
page with FIFO active. V4 moves routine native runtime file logging out of the
bridge call and replaces the heavy startup observer with compact progress
records. **This fixes a blocking logging dependency found in source. Whether
it resolves the hardware freeze or improves gameplay remains untested.**

## Evidence from v3

The [analysis record](../reports/native-dxvk-h4-v3-sponsor-analysis.json) links
the preserved original files and distinguishes the COM and game sessions.

| Evidence | What it establishes |
| --- | --- |
| Prior COM result and guest log | v3 PASS: 1,845,687 checks, both 720p readbacks, 300 Presents, zero remaining external interfaces/maps or bridge failures |
| Newly supplied `runtime.log` | COM v3, matching final counters and clean exit; exact pairing with the prior guest files is not authenticated |
| `fex-runtime.log` | GUI game v3, successful window handoff and ARM64 device creation |
| Both `HKShip.exe_d3d11.log` copies | Identical game logs: 1280×720, three images, sync interval 1 and FIFO; neither is the missing COM renderer log |
| Startup trace | 128 BEGIN/END pairs, all complete; two successful Presents; trace limit reached |
| Observer | One diagnostic report took 31,643,012 microseconds including output and scheduling |
| User observation | About 30 seconds black screen, then about 30 seconds at the static sponsor page; console unresponsive and forced restart |

The trace contains long completed calls, including ClearRenderTargetView,
ExecuteCommandList, GetData and the first Present. Their durations include
synchronous logging and scheduling, so they are **not GPU timings**. There
is no captured device loss, bridge fault, allocator OOM or clean game exit.
The final traced call returned; the trace cap prevents locating the later
stall. Approximate screen durations cannot be aligned precisely to these logs.

In v3, normal `log_line` output takes the file mutex and calls `fprintf` and
`fflush` for every line. Bridge call tracing and counter reports reach that
function while holding the global COM mutex. Slow output can therefore hold
up every guest thread waiting to enter the native bridge. This dependency is
visible in source; its contribution to this freeze is not isolated by the log.

## What v4 changes

- Native runtime output enters a bounded 512-line queue. Producers try the
  queue lock once; on contention or overflow they increment a drop counter
  instead of waiting. The existing maintenance thread removes up to 32 lines,
  releases the queue lock, then writes and flushes a batch. No new thread is
  required. Queue and batch storage use about 0.53 MiB.
- The native startup monitor samples atomic bridge state every five seconds.
  `[SD-NDX-PROGRESS]` records totals from the last completed call and the number
  of callers waiting at the gate. `[SD-NDX-ACTIVE]` records entry/call/thread,
  method, object, arguments and phase (`validate`, `execute`, `result-copy`,
  or `idle`). It does not take the bridge mutex and continues after the original
  128-call trace limit. `idle` describes a completed call, not a stuck operation.
- Native mode skips the old bulk observer. Existing x86 renderers retain their
  logging and observer path. FIFO, 720p, clock settings, thread policy, shadow
  Map behavior and the COM ABI are retained from v3.

This queue covers runtime `log_line` file output. Existing UI log bookkeeping,
fatal/crash hooks, DXVK's own logger and other file paths are not made
asynchronous by this change. A stalled maintenance writer can still delay
flushes; the queue bounds memory and records drops when output resumes.
`[SD-NDX-LOG] dropped=N` means the capture omitted events. A forced restart can
lose a queued tail even without a drop marker. Missing END or progress lines
therefore cannot establish deadlock. These are diagnostic records, not a
hardware watchdog or frame-time benchmark.

## Install and validate on Switch

Use **`dist/sd-dxvk-native-h4-v4-update/`**, a ready folder without a ZIP, on the
existing complete v18 installation and working full-memory/low-window forwarder.

1. Close from HOME and back up the installed NRO/custom profiles. Copy only
   **`switch/`** from the v4 folder to SD root. The first run is the COM test.
2. Confirm `H4 COM test exited: 00000000` and a fresh result with `status: PASS`
   and `build: native-dxvk-h4-v4`. Preserve its four files before game launch:
   `drive_c/native-dxvk-h4-result.json`, `drive_c/native-dxvk-h4-guest.log`,
   `native-dxvk-h4/runtime.log`, and `native-dxvk-h4/HKShip.exe_d3d11.log`,
   relative to `switch/sleepingdogs-fex/`. If it fails, stop at that result.
3. After PASS, close from HOME and copy **`start-game/switch/`** to SD root.
   Use Native ARM64, Launch GUI, Performance, FPS HUD and 1280×720. Compare at
   CPU 1728 / GPU 768 / RAM 1600 MHz. Native mode keeps LSFG off.
4. Check sponsor → splash → menu before loading a save. If startup succeeds,
   test gameplay, crowded areas, pause/resume and exit. Save `fex-runtime.log`,
   `native-dxvk-h4/HKShip.exe_d3d11.log` and `crash.log` if present. Record the
   last visible screen and whether HOME responds if another freeze occurs.

The game runtime should identify `BUILD native-dxvk-h4-v4 mode=SleepingDogs`,
`[SD-NDX-LOG] async queue=512`, and recurring progress/call-state records.
The DXVK log must still show FIFO. A COM pass or a menu frame is not gameplay
validation. No stable 30 FPS result is claimed.

`start-com-test/switch/` repeats the COM test. `rollback-v18/switch/` restores
the pinned v18 NRO, original x86 D3D11/DXGI pair and renderer selection.
Previous H4 delivery folders and their logs remain separate.

## Build, checks and capture analysis

Prepared pinned Wine/FEX/Mesa/SDK inputs are required. The builder reproduces
the v18 baseline and uses `/home/blekjek/sleepingdogs-native-dxvk-h4-v4`.

```sh
python3 tools/build_native_dxvk_h4.py
python3 tools/test_native_dxvk_h4_logging.py
python3 tools/test_native_dxvk_h4_window.py
python3 tools/test_native_dxvk_h4_host.py
python3 tools/check_native_dxvk_h4_abi.py
python3 tools/check_native_dxvk_h4_launcher.py
python3 tools/check_native_dxvk_h4_imports.py
python3 tests/check_native_dxvk_h4_capture.py
python3 tools/package_native_dxvk_h4.py
python3 tools/analyze_native_dxvk_h4.py --mode com --log-dir /path/to/saved-com-files
python3 tools/analyze_native_dxvk_h4.py --mode game --runtime-root /path/to/copied-runtime
```

The [logging test](../reports/native-dxvk-h4-v4-logging-check.json) exercises
the actual overlaid log functions under ASan/UBSan, a blocked output sink,
concurrent producers, overflow/truncation, legacy output and 20,000 coherent
atomic snapshot publications. It does not measure Horizon SD latency.
The [host COM test](../reports/native-dxvk-h4-v4-host-test.json) runs native
DXVK/lavapipe with modeled Wine permissions, not PE32/FEX or the game.
[Window](../reports/native-dxvk-h4-v4-window-check.json),
[ABI](../reports/native-dxvk-h4-v4-abi-check.json),
[launcher](../reports/native-dxvk-h4-v4-launcher-check.json) and
[import](../reports/native-dxvk-h4-v4-game-imports.json) checks retain their
existing scopes. [Build](../reports/native-dxvk-h4-v4-build.json) and
[folder](../reports/native-dxvk-h4-v4-folder.json) receipts bind the artifacts
to source and input hashes.

The analyzer defaults to v4, with explicit `--expected-build native-dxvk-h4-v3`
or `native-dxvk-h4-v2` for older captures. It rejects a game renderer log as COM
evidence, records queue drops and distinguishes idle from active phases.
Neither build markers nor these logs authenticate the exact running binary,
clock settings or pairing of every supplied file.
