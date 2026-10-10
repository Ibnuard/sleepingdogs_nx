# Sleeping Dogs FEXTendo v15: native presentation, DXVK batching, optional LSFG

This is a hardware test candidate at 1280x720. Native FPS improvement and stable
30 FPS are **not yet measured**. Test native rendering with LSFG OFF first.

## What the latest log actually shows

Input SHA256: `e0004d2a7fe4b0f45ede8e85751edf9e7c5b21e9871a50d867dc63a8b19b5677`.
The 30-second diagnostic capture reports about 17.48 FPS. The final seven
10-second windows total 1,014 frames over 70.695 seconds: 14.34 FPS, with window
rates between 12.81 and 15.80. These are different intervals, not conflicting
measurements. The presenting thread's CPU time is not total game CPU time.

Present 1 is 1280x720. Present 2 reports a 1292x732 client and SUBOPTIMAL. Wine
then creates a 1292x732 swapchain and scales it into 1280x720 screen buffers.
Later present samples retain that size. A decorated minimum size surviving the
game's switch to borderless fullscreen is the working explanation; the extra
scaling itself is directly logged. The native patch targets that extra work.

Shader compilation has finished in several low-FPS windows. GPU semaphore waits
are not GPU timestamps, and their durations overlap other threads. The log alone
does not prove whether GPU shader execution, driver submission, memory bandwidth,
or a CPU critical thread is dominant. Aggregate CPU activity cannot rule out a
single-thread bottleneck. No promise of 30 FPS follows from these counters.

## Native FPS changes

1. Wine now corrects the game's actual borderless Win32 geometry to 1280x720
   after WM_WINDOWPOSCHANGING and before client-rectangle calculation. The guard
   only applies to the unowned, visible `OrangeLotusWindowClass` window with equal
   small padding on both dimensions. Decorated windows, other applications,
   already-correct 720p and 960x540 are excluded. With the corrected extent, the
   existing Wine path no longer allocates/executes the extra scaling pass.
2. DXVK `3.1.1-sdbatch2` extends the existing Performance preset's bounded
   automatic submission batching from 12 to 24 chunks while at least two
   submissions remain unfinished. The estimated-cost limit stays 1500. Explicit
   Present, Map/readback and query flush handling and barriers are unchanged.
   The DXVK option still defaults OFF; the existing Sleeping Dogs Performance
   preset enables `d3d11.sdSubmissionBatching = True`.
3. If Wine cannot retrieve the window rectangle, its surface-capabilities path
   retains the driver's valid answer instead of using an uninitialized RECT.
   This is a correctness fix, not an asserted FPS gain.

FEX remains this project's own pes13-fex-derived port. Its allocator, translated
code, synchronization fixes and CPU topology are unchanged in v15. Mesa retains
the verified v14.1 driver/cache identity and v14 compiler changes. Recent
Autorun/Mesa changes already represented in those builds are not counted again
as new optimizations. No shared SDK installation was edited.

Expected native log markers:

```
[SD-NATIVE-V15] fullscreen geometry correction=1
[SD-NATIVE-V15] borderless extent 1292x732 -> 1280x720
[SD-NATIVE-V15] swapchain=1280x720 host=1280x720 extra_scale=0
[SD-DXVK-BATCH] v2
[SD-LSFG-V15] configured off; native presentation
```

The borderless-correction message only appears if the oversized window occurs.
Correct 1280x720 from the start does not need it. The old v11 diagnostic and
v14.1 Mesa banners remain because those components are intentionally retained.

## LSFG launcher integration

Settings -> Frame Generation exposes LSFG 2x and Motion resolution (12.5%,
25%, 50%). Default is OFF and 25%. Performance mode is fixed ON. Changes apply
on the next launch. The supplied Lossless.dll is read as data, never executed;
45 LSFG 3.1 shader resources are converted offline into the checked shader pack.
The original DLL and archive are not copied to the SD card.

The native Vulkan bridge captures completed game frames, computes an intermediate
frame, presents it, reacquires a screen buffer and presents the real frame. It
checks capabilities and the pack before initializing; unsupported initialization
falls back before consuming the game's semaphore. Warm-up and generated-frame
markers distinguish actually active generation from a launcher toggle. Concurrent
game acquire and per-present mode override paths bypass generation and reset
history. Present failure after consuming work is returned as an error, never
retried using an already-consumed semaphore.

The low-resolution motion pass does not change the game's 1280x720 resolution.
LSFG adds GPU cost and latency; it may lower native FPS on this GPU. It does not
speed up game simulation or remove slow motion caused by low native FPS. DXVK's
HUD reports game frames; LSFG's log reports real/generated present submissions,
which do not prove the number of frames scanned out to the display.

Quality mode is excluded from the launcher because the host output check found
border artifacts in that path at 12.5%. Only the Performance path passed the
current checks. Motion reconstruction quality and frame pacing on Switch still
require hardware evaluation. This is not a guarantee of correct interpolation
for every game scene.

## Install and compare

1. Close FEXTendo completely from HOME. Extract the update ZIP and merge its
   entire `switch` folder into the SD root, overwriting the included files.
   Copy the folder, not just the NRO: this update also contains the DXVK DLLs.
2. Use DXVK 3.1.1, Performance, Launch GUI, 1280x720 and LSFG OFF. Keep the same
   CPU/GPU/RAM clocks throughout each comparison (the reported baseline was
   1728/768/1600 MHz). Do not change game settings between the two runs.
3. Warm the same route once, then compare a fixed camera and the same crowded
   route for at least 60 seconds. Save `fex-runtime.log` before another launch
   overwrites it. Confirm the native markers above.
4. After saving that native result, optionally turn LSFG 2x ON at 25%, relaunch,
   and compare responsiveness and display smoothness. Its first initialization
   may compile shaders. Look for `first interpolated present submitted`.

Existing saves, game assets, UserOptions.dat, clocks, profile selection and HUD
selection are not included in the update. Existing LSFG preferences are retained;
the first installation defaults OFF. The DXVK HUD Off/FPS/Full menu is retained.
This package updates an already installed Sleeping Dogs FEXTendo, not a fresh
installation. It does not address the game's `undefined` graphics-preset label.

The rollback ZIP restores the exact v14.1 NRO, its launcher metadata and the
previous sdbatch1 DLLs. Close from HOME and merge its `switch` folder the same
way. The new shader pack/cache can remain unused on SD. For developer A/B of
geometry only, `launcher/native-present.txt` containing `0` disables the guard;
remove it or set `1` to restore the default. Neither package writes this override.

## Validation and source provenance

Passed on the host: fullscreen guard/scaling tests, stateful submission tracker
tests under ASan/UBSan, execution of actual PE32 tracker code, DLL import/export
compatibility, final ARM64 NRO/ELF and inherited cache/synchronization checks,
launcher persistence/navigation, SPIR-V validation and malformed-pack checks.
The actual LSFG backend ran on software Vulkan at all three Performance motion
resolutions. The production bridge passed off/2x/swapchain-recreation tests with
zero Khronos validation errors. These checks do not measure Switch FPS.

Source snapshots and build receipts are in `source/native-v15-lsfg/` in the ZIP.
They include the modified backend, the DXBC converter source, full DXVK sources
with dependencies, Wine changes, build recipes, licenses and reports. Build
scripts use the existing local cross-compilation workspace and its pinned
v14.1 inputs; this update source bundle is not a complete SDK installation.
Historical source folders describe earlier versions; current behavior is here.

- [Autorun presentation glue](https://github.com/autorunhq/autorun/tree/cbb0e4e6e7fa7f47f328d92441f51bfb507f266f), GPL-3.0-or-later.
- [Horizon backend adaptation](https://github.com/autorunhq/switch-dev/tree/28b2fe1bc39ef1f4c4fe217c430a6908e7d4c7e8/lsfg).
- [LSFG-VK archive](https://git.lsfg-vk.dev/lsfg-vk-archive.git), revision `8b0da2661c6f3473a7fccc8ba643880050e71642`, GPLv3.
- [DXBC converter](https://github.com/PancakeTAS/dxbc/tree/78ab59a8aaeb43cd1b0a5e91ba86722433a10b78), zlib/libpng license.
- [DXVK base](https://github.com/doitsujin/dxvk/tree/b1a1c99ab52b687cf950d62c88bc2fa316b41663), zlib license; project memory/submission patches retained.
- [Wine surface RECT fix](https://github.com/autorunhq/autorun/commit/c4016d89d2ca).
- [Mesa Switch](https://github.com/danfromtico/mesa-switch), retained v14.1 build rather than an unverified replacement.

The shader pack is derived from the user's supplied proprietary DLL for this
personal test package; it is not part of the GPL source or a public redistribution.
