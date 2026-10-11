# Native DXVK H4 v2: release the launcher before native rendering

[Documentation](README.md) · [COM implementation](native-dxvk-h4-v1.md) · [Current status](STATUS.md)

The supplied start-game capture stops at `FAIL trusted native window`, before
native D3D11 device creation or a presented frame. H4 v2 fixes a missing screen
handoff in that route and adds specific window failure diagnostics. It is a
new **Switch test candidate**, with no confirmed H4 COM/game pass or FPS gain.

## Evidence and cause

The [preserved capture](../reports/native-dxvk-h4-startup-95efa6101d4f.json)
records native renderer selection, Launch Debug, a successful low-address
memory check, and native exit code 1. The user confirmed that they had gone
directly to `start-game` without running the H4 COM test. The failure occurs
before Wine/FEX starts the game. No native-device or Present marker appears.

The launcher normally keeps its framebuffer while preparing the game. Wine's
existing surface-acquisition route calls `fx_handoff()`, which stops and joins
the UI thread; its cleanup closes the framebuffer. H4 v1's native route called
`sd_com_native_window()` directly and skipped that step. This affects both GUI
and Debug. The diagnostic route skips the launcher, so testing only its console
handoff would miss the game-route defect.

[libnx's window implementation](https://github.com/switchbrew/libnx/blob/master/nx/source/display/native_window.c)
rejects `nwindowSetDimensions` when dimensions and configured buffer slots are
already present. The actual H4 functions reproduce that old call-order failure
in the host regression using a modeled libnx window. **The v1 capture does not
record the libnx Result or authenticate the exact running NRO**, so its numeric
error cannot be reconstructed from the log. The inherited F1 version/renderer
label in `crash.log` also does not identify the selected native renderer.

## Change

- Both native game launch and the COM test call the existing joined launcher
  handoff, release any active console, and then prepare the 1280×720 NWindow.
- Native mode prevents Wine GDI framebuffer initialization/locking, compositor
  startup and GL window acquisition from taking the same screen later. Existing
  x86 renderer selections keep their previous handoff path.
- Runtime logs identify `native-dxvk-h4-v2` before attempting the window. They
  distinguish a failed launcher handoff, wrong applet type, invalid window,
  and a failed dimension call, including its Result and configured slots.
- The COM result and NACP identify v2 (`0.1.0-h4.2`). The old v1 folder and its
  receipts remain separate. No resolution, clock or frame-generation change
  is part of this fix.

## Switch validation

Use **`dist/sd-dxvk-native-h4-v2-update/`** with the working complete v18
installation and the low-window/full-memory forwarder that passed H3. This
is a folder update, with no ZIP and no game data. Back up the installed NRO
and any customized launcher profile templates before copying.

1. Fully close the application from HOME. Copy **only `switch/`** from the v2
   folder to SD root. It enables the automatic COM self-test.
2. Run it and wait for `H4 COM test exited: 00000000` and a fresh result with
   `status: PASS` and `build: native-dxvk-h4-v2`. The test includes two 720p
   readbacks and 300 blue-screen Present calls. If it fails or hangs, preserve
   the logs before another run and diagnose that failure before starting HKShip.
3. Preserve these four files under `switch/sleepingdogs-fex/`:
   `drive_c/native-dxvk-h4-result.json`, `drive_c/native-dxvk-h4-guest.log`,
   `native-dxvk-h4/runtime.log`, and `native-dxvk-h4/HKShip_d3d11.log`.
4. After COM PASS, close from HOME and copy **`start-game/switch/`** to SD root.
   Choose DXVK Native ARM64, Launch GUI, 1280×720 and the FPS HUD. Native mode
   forces LSFG OFF. Keep the comparison clocks CPU 1728 / GPU 768 / RAM 1600 MHz;
   the build itself does not change clocks.
5. Validate menu, load, gameplay, crowded areas, transitions, pause/resume and
   exit. Repeat startup with Launch Debug to cover the reported route. Preserve
   `fex-runtime.log`, `native-dxvk-h4/HKShip_d3d11.log`, and `crash.log` if present.
   Compare gameplay in the same scene/camera with warm caches. Menu or self-test
   FPS is not gameplay evidence.

Expected startup markers, in order:

```text
[SD-NDX-COM] BUILD native-dxvk-h4-v2 mode=SleepingDogs ...
[FEXTENDO] launcher stopped and framebuffer released before 3D handoff
[SD-NDX-WINDOW] handoff complete launcher_owned=0 console_active=0
[SD-NDX-WINDOW] dimensions rc=00000000 slots=0 ... size=1280x720
[SD-NDX-COM] D3D11CreateDevice ... native=ARM64
[SD-NDX-COM] FIRST_PRESENT real COM path ...
```

The COM test's mode is `COM-self-test`; it has no launcher-stopped line because
it skips the launcher. Native Present windows remain aggregate diagnostics,
not proof of playable correctness or stable 30 FPS.

To repeat COM, copy `start-com-test/switch/` after saving the previous logs.
For full rollback, close from HOME and copy `rollback-v18/switch/`. That restores
the pinned v18 NRO, legacy renderer selection and matching game graphics DLLs.

## Local checks and rebuild

The [window regression](../reports/native-dxvk-h4-v2-window-check.json) runs the
actual overlaid handoff functions and `com_horizon.cpp` under ASan/UBSan. Its ten
cases cover the old failure order, GUI, Debug, diagnostic console, failed UI
handoff, wrong applet, invalid window, another buffer owner, dimension failure
and retry, and cached-window reuse. The stop/join uses a real pthread; UI cleanup,
libnx and Result values are modeled. It does not execute a Horizon display.

The [native host check](../reports/native-dxvk-h4-v2-host-test.json),
[compiled ABI check](../reports/native-dxvk-h4-v2-abi-check.json),
[launcher check](../reports/native-dxvk-h4-v2-launcher-check.json), and
[game import check](../reports/native-dxvk-h4-v2-game-imports.json) retain the
[H4 v1 validation boundaries](native-dxvk-h4-v1.md#completed-local-validation).
The [build receipt](../reports/native-dxvk-h4-v2-build.json) and
[folder receipt](../reports/native-dxvk-h4-v2-folder.json) record exact inputs,
sources, overlays, NRO and manifest hashes. None asserts a hardware FPS gain.

Prepared local Wine/FEX/Mesa/SDK objects and pinned legacy renderer DLLs are
required. Current tools produce v2 in an isolated work directory; they do not
rebuild or overwrite the v1 delivery folder.

```sh
python3 tools/test_native_dxvk_h4_window.py
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

The current analyzer requires v2 markers; it rejects stale v1 results. The
packager verifies test/source hashes and overlay round trips, and refuses to
overwrite altered payloads or added user logs. Production still requires H4
COM success, actual game API coverage, long-session correctness and matched
native-FPS evidence on Switch.
