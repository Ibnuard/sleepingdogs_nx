# Native DXVK H4 v3: investigate the sponsor-screen freeze

[Documentation](README.md) · [H4 COM implementation](native-dxvk-h4-v1.md) · [Current status](STATUS.md)

H4 v2 passed the real PE32 COM self-test on Switch and presented the game's
first native frame. The game then froze on the static sponsor/legal screen,
before the animated splash. **H4 v3 is a diagnostic candidate for that freeze;
it has not yet been tested on Switch and does not establish a performance gain.**

## What the v2 files showed

The [observation record](../reports/native-dxvk-h4-v2-sponsor-observation.json)
distinguishes two runs read from the user's SD card:

| Session | Observed evidence |
| --- | --- |
| COM self-test | `drive_c/native-dxvk-h4-result.json`, guest log and `native-dxvk-h4/runtime.log` agree on v2 PASS and clean exit |
| COM checks | 1,845,687 checks, 2,048 buffer bytes, 80 BC1 mip/array bytes, both 720p readbacks with zero bad pixels |
| COM presentation | 300 Present calls in 5,044 ms; 302 draws; zero remaining external bridge interfaces/maps and zero bridge failures |
| Game GUI startup | v2 marker, completed launcher handoff, successful window dimensions and ARM64 D3D11 device creation |
| Game last bridge snapshot | 8,094 calls, one draw, one Present, 4,517 live interfaces, two maps, 37,748,736 bytes copied; no bridge failure |
| Game swapchain | 1280×720, three images, `VK_PRESENT_MODE_IMMEDIATE_KHR`, effective `dxgi.syncInterval = 0` |
| User observation | Static sponsor page; HUD 0.0 FPS and console unresponsive; forced restart roughly five seconds after visible freeze |

The SD card was ejected before the original bytes or installed NRO hash could
be archived. This is a transcribed observation, **not an immutable raw capture
or authentication of the running binary**. The three COM files support the
observed COM completion. The DXVK log belonged to the later game run: both
modes use `native-dxvk-h4/HKShip.exe_d3d11.log`, which gets overwritten.

The game log does not show device loss or exhausted allocators at the last
available snapshot. It also contains long JIT compilation work and ends with
some nontext bytes after the forced restart. Neither establishes the freeze's
cause. V2 has no call-level BEGIN/END markers, so its two outstanding maps do
not prove that Map, Unmap, Present or any particular lock is stuck.

## What v3 changes

The successful synthetic presentation paths used FIFO configuration, while
this game run used IMMEDIATE. V3 tests that difference by setting
`dxgi.syncInterval = 1` in all six native configuration templates (renderer
default plus five presets). Only that option changes relative to each
canonical native profile. Both x86 renderer configurations remain canonical.
The selected mode must still be confirmed in the actual DXVK log; this is
a testable hypothesis, not a confirmed IMMEDIATE defect.

The native bridge also records `[SD-NDX-CALL] BEGIN` and `END` for initial
Map, Unmap, BindMap, AbortMap, Present, GetData and Flush calls, plus other
device-context calls after the first Present. Records include call and thread
identity, method, object, arguments, result, map/copy counters and elapsed
wall time. Logging stops after three completed Presents or 128 traced calls.
This bounds startup I/O; **wall time includes the logging itself and is not
GPU timing**. This build is intended to diagnose startup, not benchmark it.

A BEGIN without a matching END identifies an unfinished operation in the
available log, not necessarily a deadlock. Logging starts after bridge lock
acquisition and packet validation; a hang before those steps, in guest-side
Map allocation, or after the trace limit may have no matching BEGIN. The
analyzer reports these limits and does not infer a root cause from a gap.

The v2 joined framebuffer handoff remains in place. Resolution stays 720p,
clock settings are untouched, native mode forces LSFG OFF, and the existing
Map shadow-copy semantics and bridge ABI remain unchanged.

## Install and validate on Switch

Use **`dist/sd-dxvk-native-h4-v3-update/`**, a ready folder without a ZIP.
It updates a working complete v18 installation using the same full-memory,
low-window forwarder as H3. Back up the NRO and customized profile templates.

1. Close the application fully from HOME. Copy **only `switch/`** from the
   v3 folder to SD root. This selects the automatic COM self-test.
2. Run it. Confirm `H4 COM test exited: 00000000` and a fresh result with
   `status: PASS`, `build: native-dxvk-h4-v3`. The test exercises the modified
   build before starting the game. If it hangs or fails, preserve its logs.
3. **Save all four COM files before starting the game:**
   `drive_c/native-dxvk-h4-result.json`, `drive_c/native-dxvk-h4-guest.log`,
   `native-dxvk-h4/runtime.log`, and `native-dxvk-h4/HKShip.exe_d3d11.log`,
   relative to `switch/sleepingdogs-fex/`. The fourth file will be overwritten.
4. After COM PASS, close from HOME and copy **`start-game/switch/`** to SD root.
   Select DXVK Native ARM64, Launch GUI, Performance and FPS HUD, at 1280×720.
   Keep the reference CPU 1728 / GPU 768 / RAM 1600 MHz for comparison.
5. Check whether the game passes the sponsor page and animated splash into
   the menu. If it does, test loading a save, gameplay, crowded areas, scene
   changes, pause/resume and exit. Save `fex-runtime.log`,
   `native-dxvk-h4/HKShip.exe_d3d11.log` and `crash.log` if present. Record the
   last visible screen and whether HOME responds if it freezes again.

The game log should identify `BUILD native-dxvk-h4-v3 mode=SleepingDogs`, a
successful `[SD-NDX-WINDOW]` handoff, `native=ARM64`, and `FIRST_PRESENT`.
The DXVK log should identify `dxgi.syncInterval = 1` and
`VK_PRESENT_MODE_FIFO_KHR`. BEGIN/END records should expose the first calls
around that frame. Reaching the menu alone is not gameplay validation.

Use `start-com-test/switch/` to repeat the COM test. `rollback-v18/switch/`
restores the pinned v18 NRO, x86 D3D11/DXGI pair and selection. Always close
from HOME before replacing files. The v1/v2 folders are preserved separately.

## Build, checks and capture analysis

Prepared pinned Wine/FEX/Mesa/SDK objects and legacy renderer inputs remain
required. Work is isolated in `/home/blekjek/sleepingdogs-native-dxvk-h4-v3`.

```sh
python3 tools/test_native_dxvk_h4_window.py
python3 tools/build_native_dxvk_h4.py
python3 tools/test_native_dxvk_h4_host.py
python3 tools/check_native_dxvk_h4_abi.py
python3 tools/check_native_dxvk_h4_launcher.py
python3 tools/check_native_dxvk_h4_imports.py
python3 tests/check_native_dxvk_h4_capture.py
python3 tools/package_native_dxvk_h4.py
python3 tools/analyze_native_dxvk_h4.py --mode com --log-dir /path/to/saved-com-files
python3 tools/analyze_native_dxvk_h4.py --mode game --runtime-root /path/to/copied-runtime
```

The analyzer prefers the actual `.exe_d3d11.log` name, with the old filename
accepted for archived captures. `--dxvk-log` accepts an explicitly saved log.
Its config path must match COM versus game mode, preventing the later game's
renderer log from certifying an earlier COM run. This check cannot authenticate
two files from the exact same session. V3 additionally requires observed FIFO
configuration and presentation; `--expected-build native-dxvk-h4-v2` is
available for older captures. Missing or unmatched call traces are reported
without certifying a freeze cause.

The [host receipt](../reports/native-dxvk-h4-v3-host-test.json) checks native
COM correctness with DXVK/lavapipe and bounded trace pairs. The
[window regression](../reports/native-dxvk-h4-v3-window-check.json) preserves
the ten modeled handoff cases under ASan/UBSan. The
[launcher test](../reports/native-dxvk-h4-v3-launcher-check.json) verifies
all profiles, native-only sync changes, and the existing transaction/fallback.
[ABI](../reports/native-dxvk-h4-v3-abi-check.json) and
[game import](../reports/native-dxvk-h4-v3-game-imports.json) checks keep their
existing boundaries. The [build](../reports/native-dxvk-h4-v3-build.json) and
[folder](../reports/native-dxvk-h4-v3-folder.json) receipts identify exact inputs
and outputs. Their hardware flags describe v3, not the earlier v2 COM result.

Actual game API coverage, stable startup, long-session resource lifetime and
matched native game FPS remain production gates. **Stable 30 FPS is unproven.**
