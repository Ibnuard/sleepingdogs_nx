# Native DXVK H4 v5: correct COM output memory

[Documentation](README.md) · [COM implementation](native-dxvk-h4-v1.md) · [Current status](STATUS.md)

Subsequent feedback: the user reports v5 now reaches gameplay around 15 FPS.
The [preserved observation](../reports/native-dxvk-h4-v5-gameplay-observation.json)
records the native route and last two Present windows, while the supplied COM
runtime remains older v3 data. The current candidate is
[H4 v8](native-dxvk-h4-v8-game-detail.md). This page retains the original v5
pre-test record; current build/package/analyzer tools target v8.

V4 now reaches the animated startup and “Press Start”, then exits with a guest
access violation. V5 fixes two reproducible COM output defects found while
tracing that crash. **The local regression checks pass; the fix has not been
tested on Switch, and native gameplay or a 30 FPS gain is not established.**

## What the latest capture establishes

The [analysis](../reports/native-dxvk-h4-v4-press-start-analysis.json) links the
preserved original logs and separates observations from the proposed cause.

| Evidence | Meaning |
| --- | --- |
| V4 GUI game runtime | Native device/window handoff succeeded; 1,020 Presents and 19,516 draws before exit |
| Renderer log | Native ARM64 DXVK, NVK GM20B, 1280×720, three images and FIFO |
| Guest first fault | `c0000005`, EIP `fffc9c07`, reading `000111a2`; EAX `0001119e`, sampler count 12 |
| Local v4 PE32 disassembly | Matching code bytes at RVA `9c07` in `PSSetSamplers`: checking proxy magic at `[eax+4]` |
| User observation | Animation progressed to “Press Start”, then crashed |
| Supplied `runtime.log` | Byte-identical older v3 COM runtime; it does not validate a v4 COM test |

The invalid value looks like a native bridge handle rather than a COM proxy
pointer. The matching instruction locates the failing conversion, but neither
the exact running DLL nor the earlier writer of this value is authenticated.
No device-loss or bridge `FAULT`/`UNSUPPORTED` event appears in this capture.
Final zero references/maps are recorded after shutdown cleanup; they do not
establish allocation health before the fault.

One 600-interval Present window averages about 56 FPS. It includes startup
and menu frames, with no identified gameplay scene. It is not gameplay FPS.

## Corrected behavior

`OMGetRenderTargets` returns an RTV array and one depth/stencil pointer. The
generator previously applied `NumViews` to both outputs, overwriting up to
seven adjacent PE32 words when eight RTVs were requested, or skipping the DSV
when zero RTVs were requested. V5 binds counts to the named array and always
gives the DSV one slot, including the combined RTV/UAV getter. This matches
the [Microsoft D3D11 API contract](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-id3d11devicecontext-omgetrendertargets).

Previously, native output handles were written directly into game-owned COM
outputs and replaced with proxy pointers after the bridge returned. V5 uses
private scratch storage for typed COM getters/creators, IID-selected outputs,
QueryInterface, factory/device creation and private-interface retrieval. Only
wrapped PE32 objects are published. Null slots and proxy identity are retained;
unpublished native references are released on failure. This removes transient
handle exposure, without claiming an entire output array is atomically published.

Both defects are reproduced in the old wrappers by the PE32 regression test.
Whether either defect produced the particular value in this game session is
still an inference. V5 does not accept native handles as valid COM pointers.

## Local validation and limits

- [PE32 output regression](../reports/native-dxvk-h4-v5-guest-output-check.json):
  executes the actual wrappers on Windows against a modeled Unix endpoint.
  V5 passes; v4 separately fails scalar DSV guards and transient publication.
  Sampler identity/setter, QueryInterface, factory/device, private interface,
  failed-output reference cleanup and heap scratch storage are covered. The
  129-slot case stresses transport storage, not a valid D3D11 sampler range.
- [Native host check](../reports/native-dxvk-h4-v5-host-test.json): actual
  DXVK/lavapipe with modeled Wine permissions passes 7,384,876 checks, including
  scalar DSV guards and a valid 12-slot sampler roundtrip. It does not execute
  PE32/FEX or the Switch driver.
- [Build](../reports/native-dxvk-h4-v5-build.json),
  [ABI](../reports/native-dxvk-h4-v5-abi-check.json),
  [imports](../reports/native-dxvk-h4-v5-game-imports.json),
  [launcher](../reports/native-dxvk-h4-v5-launcher-check.json),
  [window](../reports/native-dxvk-h4-v5-window-check.json) and
  [logging](../reports/native-dxvk-h4-v5-logging-check.json) checks pass in their
  existing local scopes. [Folder checksums](../reports/native-dxvk-h4-v5-folder.json)
  bind the delivered files to those receipts. None is a hardware game test.

The Switch COM client adds 72 sampler-slot checks across PS/VS/GS/HS/DS/CS and
16 scalar DSV/guard checks. Existing thread/reference, buffer/BC1 and two full
720p readbacks plus 300 Presents remain required. FIFO, 720p, clock policy,
shadow Map and the v4 queued logging/progress behavior are retained.

## Install and validate on Switch

Use **`dist/sd-dxvk-native-h4-v5-update/`**, without a ZIP, on the existing
complete v18 installation and working full-memory/low-window forwarder.

1. Close the application from HOME and back up the installed NRO. Copy only
   **`switch/`** to SD root. The first run is the COM test.
2. Require exit `00000000` and a fresh result with build `native-dxvk-h4-v5`,
   `status: PASS`, `sampler_roundtrip_slots_verified: 72`, and
   `dsv_guard_checks: 16`. Save the four COM files before launching the game:
   `drive_c/native-dxvk-h4-result.json`, `drive_c/native-dxvk-h4-guest.log`,
   `native-dxvk-h4/runtime.log`, and `native-dxvk-h4/HKShip.exe_d3d11.log`,
   relative to `switch/sleepingdogs-fex/`. If it fails, retain that capture.
3. After PASS, close from HOME and copy **`start-game/switch/`** to SD root.
   Use Native ARM64, Launch GUI, Performance, FPS HUD, 1280×720 and the reference
   CPU 1728 / GPU 768 / RAM 1600 MHz. The build does not set clocks; LSFG is off.
4. Check sponsor → animation → Press Start → main menu first. Then load a save
   and test the same route, crowded scenes, pause/resume and clean exit. Save
   `fex-runtime.log`, `native-dxvk-h4/HKShip.exe_d3d11.log`, and `crash.log` if
   present. Record the last visible screen if another failure occurs.

`start-com-test/switch/` repeats the synthetic test. `rollback-v18/switch/`
restores the pinned v18 NRO, x86 DLL pair and renderer selection. Prior H4
delivery folders and user logs remain separate.

## Rebuild and capture analysis

Prepared pinned Wine/FEX/Mesa/SDK inputs are required. Run the PE32 check with
**Windows Python**; it calls the pinned WSL llvm-mingw compiler and executes
the resulting PE32 files on Windows. Repository history must contain the v4
baseline commit recorded in its receipt. Run the other steps in WSL Ubuntu.

```powershell
python tools/test_native_dxvk_h4_guest_outputs.py
```

```sh
python3 tools/build_native_dxvk_h4.py
python3 tools/test_native_dxvk_h4_host.py
python3 tools/test_native_dxvk_h4_window.py
python3 tools/test_native_dxvk_h4_logging.py
python3 tools/check_native_dxvk_h4_abi.py
python3 tools/check_native_dxvk_h4_launcher.py
python3 tools/check_native_dxvk_h4_imports.py
python3 tests/check_native_dxvk_h4_capture.py
python3 tools/package_native_dxvk_h4.py
python3 tools/analyze_native_dxvk_h4.py --mode com --log-dir /path/to/saved-com-files
python3 tools/analyze_native_dxvk_h4.py --mode game --runtime-root /path/to/copied-runtime
```

At this iteration the builder used `/home/blekjek/sleepingdogs-native-dxvk-h4-v5`.
Current tools target v8; use `--expected-build native-dxvk-h4-v5` for these
captures or the corresponding v2/v3/v4 label. The COM stage/counters remain
required. `ROUTE_OBSERVED` only establishes a native
Present route and does not rule out a later crash. Queued logging can lose
events; clocks, exact binaries and cross-file session pairing remain separate
validation requirements. Production still requires playable, sustained native
gameplay and a matched FPS comparison.
