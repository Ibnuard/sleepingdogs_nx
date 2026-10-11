# Native DXVK H4 v8: Map reuse and Light 720p

[Documentation](README.md) · [Current status](STATUS.md) · [Previous v7](native-dxvk-h4-v7-objects.md)

V7 is reported to run around 20 FPS, with peaks near 25 in confined views and
drops around 13 while running through crowds. V8 combines bounded reuse of
guest Map allocations with an optional lower-detail game preset at **1280×720**.
V8 gameplay and its FPS effect have not been tested on Switch.

## Latest evidence

The [v7 observation](../reports/native-dxvk-h4-v7-gameplay-observation.json)
preserves all five supplied files. Its final five 600-Present windows are
18.52, 18.36, 18.93, 17.05 and 23.64 FPS, pooled at **19.07 FPS**. The log
records native v7, Performance, 720p, FIFO and LSFG OFF, with no recorded
bridge fault or device loss. It does not identify scenes or current clocks.
The reported improvement is not a controlled comparison against v6 or x86.

The last sampled interval contains about 7,022 bridge calls, 1,067 draws and
exactly 9 MiB of Map copies per Present. These counts suggest useful work to
reduce but do not assign frame time to the CPU, bridge, GPU or memory bus.
Startup memory counters do not establish gameplay memory exhaustion.

All three supplied COM files are byte-identical **v3** evidence. They do not
validate the v7 self-test. A fresh v8 COM result is required before game tests.
The game capture ends with live resources and two maps, without clean-exit
evidence; this alone establishes neither a leak nor clean sustained lifetime.

## Bounded guest Map reuse

Previously each successful Map allocated a record and a fresh guest
VirtualAlloc span, then freed both on Unmap. V8 keeps up to four inactive
exact-size entries, bounded to 16 MiB of requested buffer capacity. Active
maps are never reused. Oversized allocations bypass the cache; old inactive
entries are evicted when the count or byte limit would be exceeded.

Guest allocation failure drains idle entries and retries once. Native Map
out-of-memory also permits one retry after draining idle memory; other error
statuses retain their existing handling. Allocation, freeing and native calls
happen outside the proxy lock. Cache entries retain memory only, not COM
context/resource references. OS process teardown reclaims the remaining idle
cache; no work is added to loader-detach callbacks.

The native BindMap still validates the complete writable shadow before use.
READ, WRITE, READ_WRITE and WRITE_NO_OVERWRITE keep their existing full copy-in.
WRITE_DISCARD zeros the reused shadow on the native side, preserving the former
fresh-VirtualAlloc initialization behavior.
Copy-out and native Unmap remain unchanged. This is **not zero-copy Map** and
does not remove the measured 9 MiB-per-Present copy traffic.

## Game detail controls

The [original executable audit](../reports/original-game-display-settings-audit.json)
identifies the original PE32 XML reader, serializer and built-in preset switch
by executable/code-range hashes. The existing DXVK Performance profile only
changes renderer configuration; it does not lower game world detail.

**Settings → Game detail** adds three choices:

| Choice | Behavior |
| --- | --- |
| Game settings | Retain current game options and stop applying Light on launch |
| Light 720p | Apply the minimum values from the first built-in game preset at 1280×720 |
| Restore original | Restore the XML saved before the first Light application and disable enforcement |

Light writes these numeric values in the existing `Data/DisplaySettings.xml`:

```text
ResolutionWidth=1280  ResolutionHeight=720
AAQuality=0          HighResTextures=0
ShadowRes=0          ShadowFilter=0
MotionBlur=0         SSAO=0
WorldDensity=0       GlobalSetting=0
```

`GlobalSetting=0` retains the individually read options: values 1–4 apply
built-in presets after the individual fields have been loaded. This matters
when a higher preset would otherwise overwrite a manually reduced setting.
The boolean texture field uses numeric 0/1. `AAQuality=0` is the minimum preset
value, not a claim that all anti-aliasing is disabled.

The original game's [texture-pack documentation](https://store.steampowered.com/app/202181/Sleeping_Dogs__High_Resolution_Texture_Pack/)
confirms that high-resolution textures are selected through game options.
The exact numeric fields above come from the inspected original executable,
not the Definitive Edition configuration format. WorldDensity changes the
game's world-detail setting; this audit does not establish an exact pedestrian
count, and does not implement removal of mission characters or game simulation.

The helper preserves the existing adapter, monitor, refresh ratio, fullscreen,
VSync, stereo and other supported field contents. `UserOptions.dat` and saves
are never edited. It validates the XML before replacing it, keeps the first
original bytes in `DisplaySettings.xml.fextendo-original`, and uses staged,
recoverable replacement for Horizon's rename behavior. Unsupported/malformed
XML is rejected with an actionable launcher error. The tests model write,
sync and rename failures; physical SD power-loss durability still needs hardware.

Missing XML is deliberately not synthesized: the inspected initializer has
zero adapter/refresh fields, and downstream display-mode recovery has not
been established. Select Game settings, launch once and save Display Options,
then enable Light. Stopping enforcement does not restore prior quality;
use Restore original for that. If every quality option was already minimum,
this preset has no demonstrated additional benefit. The `undefined` graphics
label remains unresolved.

## Local validation

- [Map wrappers](../reports/native-dxvk-h4-v8-guest-maps.json): actual PE32
  code on Windows with a modeled native endpoint; copy directions, dirty
  DISCARD reuse, simultaneous/concurrent maps, bounds, eviction, failure/abort,
  bounded retry and reference cleanup. In 32 modeled cycles using overlapping
  4 MiB and 5 MiB buffers, v7 allocates 64 buffers; v8 allocates two. This fixture
  is not a measurement of Wine/FEX, Switch memory management or game FPS.
- [Native host](../reports/native-dxvk-h4-v8-host-test.json): actual DXVK/lavapipe
  rendering and readback, including dirty DISCARD initialization and no writes
  before pointer validation, plus inherited Map/BC1/COM ownership coverage.
- [Game settings](../reports/native-dxvk-h4-v8-game-quality.json) and
  [launcher UI](../reports/native-dxvk-h4-v8-game-quality-ui.json): XML changes,
  original preservation, restoration, malformed input and modeled I/O failures;
  actual menu navigation and host rendering. These do not execute the game parser.
- [Build](../reports/native-dxvk-h4-v8-build.json),
  [ABI](../reports/native-dxvk-h4-v8-abi-check.json),
  [imports](../reports/native-dxvk-h4-v8-game-imports.json),
  [renderer transactions](../reports/native-dxvk-h4-v8-launcher-check.json),
  [PE32 outputs](../reports/native-dxvk-h4-v8-guest-output-check.json),
  [lookup](../reports/native-dxvk-h4-v8-guest-lookup.json),
  [arrays](../reports/native-dxvk-h4-v8-array-check.json),
  [logging](../reports/native-dxvk-h4-v8-logging-check.json),
  [window handoff](../reports/native-dxvk-h4-v8-window-check.json), and
  [folder receipt](../reports/native-dxvk-h4-v8-folder.json) bind the candidate
  to its sources and local checks. The retained dispatcher comparison remains
  a narrow [v6/current host fixture](../reports/native-dxvk-h4-v8-dispatch-benchmark.json).

## Install and compare

Use **`dist/sd-dxvk-native-h4-v8-update/`**, without a ZIP, over the existing
complete installation and working low-window/full-memory forwarder.

1. Close from HOME, back up the NRO, and copy `switch/` to SD root. Require a
   fresh **native-dxvk-h4-v8 PASS** result: exit `00000000`, 72 sampler-slot checks,
   16 DSV guards, both 720p readbacks and 300 Presents. Save COM result, guest,
   runtime and renderer logs before launching the game.
2. Copy `start-game-light/switch/` for native ARM64 plus Light 720p. Alternatively,
   `start-game/switch/` tests Map reuse with current game options. Restart fully
   and use GUI, Performance, FPS HUD, 1280×720 and the reference clocks
   CPU 1728 / GPU 768 / RAM 1600 MHz. The build does not set clocks.
3. Warm the cache and compare the same save, location, camera and crowd route.
   Test pause/resume and a normal exit. Keep peaks separate from typical FPS.
4. Save `fex-runtime.log`, `native-dxvk-h4/HKShip.exe_d3d11.log` and a fresh
   crash log if needed. `[SD-GAME-QUALITY]` identifies the applied mode/values;
   `[SD-NDX-PERF] map_shadow_cache=16MiB/4` identifies the new memory path.

`start-com-test/switch/` repeats COM. Restore original quality in the launcher
before using `rollback-v18/switch/` if a complete return to previous settings
is wanted. The rollback disables Light preference but cannot restore the
per-device XML backup by a static file copy. Previous v7 remains separate.

## Rebuild

Prepared pinned Wine/FEX/Mesa/SDK inputs are required. Current tools target v8.
The map comparison requires commit `e0995ccfc2819d20b5df8f60bff784996fb479c1`;
the inherited lookup/dispatcher controls use v6 and output controls use v4.

Run with Windows Python:

```powershell
python tools/test_native_dxvk_h4_guest_outputs.py
python tools/test_native_dxvk_h4_guest_lookup.py
python tools/test_native_dxvk_h4_guest_maps.py
```

Run with WSL Ubuntu:

```sh
python3 tools/test_native_dxvk_h4_game_quality.py
python3 tools/test_native_dxvk_h4_game_quality_ui.py
python3 tools/build_native_dxvk_h4.py
python3 tools/test_native_dxvk_h4_host.py
python3 tools/test_native_dxvk_h4_arrays.py
python3 tools/benchmark_native_dxvk_h4_dispatch.py
python3 tools/check_native_dxvk_h4_abi.py
python3 tools/test_native_dxvk_h4_window.py
python3 tools/test_native_dxvk_h4_logging.py
python3 tools/check_native_dxvk_h4_launcher.py
python3 tools/check_native_dxvk_h4_imports.py
python3 tests/check_native_dxvk_h4_capture.py
python3 tools/package_native_dxvk_h4.py
```

The analyzer defaults to v8; use `--expected-build native-dxvk-h4-v7` for the
previous capture. Local checks do not establish stable 30 FPS or production
readiness. Sustained hardware resource lifetime and matched gameplay remain open.
