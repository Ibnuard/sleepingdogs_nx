# Launcher v2: cached verification, mandatory Light 720p, native LSFG

[Documentation](README.md) · [Status](STATUS.md)

This follow-up fixes three concrete launcher problems. It retains Compact COM,
Native Ref v1, FEX context v1 and the native H4 v9 renderer. It makes no new
native-FPS claim. The [latest supplied game log](../reports/launcher-v1-game-7cadea575589.json)
confirms compact packets are used, without reported bridge faults, but the
last two 600-Present windows are **17.53 and 18.51 FPS**. Scenes/clocks are not
paired with a control run. The separate `runtime.log` is older COM-session data.

## Changes

**Runtime verification is cached after success.** The first launch of this
update hashes the runtime/assets. Later launches reuse that result if the
built-in catalog/build identity and each file's size/whole-second modification
time still match. Missing files, metadata changes, a different build/catalog,
invalid cache, or manual **Settings → System Check** cause a full scan.
Failed/cancelled verification invalidates the cache. Cache-write failure does
not block an otherwise successful launch; the next launch checks again.

The HOME application, title/memory allowance, current low-window boot layout
and actual mapping probes still run each process. A previously successful boot
cannot authorize a currently unpatched one. The small game installation check
and artwork loading remain. `system-check.log` reports `runtime_check=full`
or `runtime_check=cached`. Metadata detects ordinary installation changes;
same-size corruption with an unchanged timestamp requires a manual full check.
The cache is not a security or continuous-integrity guarantee.

**Light 1280×720 is required at every Play/Debug launch.** The Game detail
submenu and Original/Restore choices are removed. Legacy
`launcher/game-quality.txt` values are ignored, including malformed/zero values.
The existing validated XML helper applies the minimum supported world,
shadow/effect/texture values and normalizes GlobalSetting. It preserves the
original backup, unrelated XML fields, `UserOptions.dat` and saves. No live
game-memory patch prevents changing options within the running game; Light
720p is reapplied at its next launch.

**LSFG ON now reaches native DXVK.** H4 previously forced LSFG OFF, although
the launcher still displayed the saved ON preference. Wine's integration was
never called by native DXVK. The host loader adapter now provides the missing
device-feature, swapchain, acquire and present hooks. The existing Wine route
remains separate. Native backend-internal presents/acquires bypass both
adapters to avoid recursive generation and duplicate keyboard work; Wine
retains the keyboard hook because its generation stage runs earlier.

The adapter checks device/transfer support, tracks application-owned images,
and temporarily skips/reset history for an open keyboard, concurrent acquire,
additional acquired images, retired swapchains, or unsupported per-present
modes. It retains ordinary presentation in those cases. Internal reacquire
has a one-second bound; timeout is returned as an out-of-date swapchain, never
as a successful Present. Errors after consuming waits never retry the same
game semaphore. These choices follow Vulkan's
[Present](https://docs.vulkan.org/refpages/latest/refpages/source/vkQueuePresentKHR.html)
and [Acquire](https://docs.vulkan.org/refpages/latest/refpages/source/vkAcquireNextImageKHR.html)
ownership/synchronization rules.

Generation is optional and costs GPU work. The private test folder includes
the previously prepared shader pack from the user's own input. Proprietary
shader payloads are not committed to GitHub or offered as a public release.

## Install and verify

Close the application completely from HOME. From
`dist/sd-launcher-v2-update/`, copy **only the top-level `switch/` folder** to
the SD root and allow replacement. Normal installation needs no `start-game`
overlay. Existing game, save and LSFG preferences are preserved.

After one successful setup check, close/reopen to confirm
`runtime_check=cached` in `system-check.log`. Manual System Check still performs
the complete scan. Light 720p appears in the launch log without a quality menu.

For LSFG, choose **Settings → Frame Generation → ON** and Play. Confirm:

```
[SD-LSFG-NATIVE] requested=1 route=native ...
[SD-LSFG-NATIVE] swapchain attached; GPU initialization/history pending
[SD-LSFG-V15] 2x generating; first interpolated present submitted
```

Only the last line proves an interpolated present was submitted. Subsequent
`window_ms=... real=... generated=...` counters distinguish the two streams;
submission does not prove scanout. DXVK HUD and `[SD-NDX-FPS] source=game-present`
continue counting **real game frames**. Initialization, bypass and failure
reasons are logged separately. Send `fex-runtime.log`, `system-check.log` and
the matching `HKShip.exe_d3d11.log`; preserve OFF/ON runs separately.

`rollback-launcher-v1/` restores the preceding compact launcher; the older
Ref-v1 rollback and performance-on/off proxy comparisons remain available.
Choose one optional inner `switch/` overlay rather than copying all folders.

## Validation

The complete native host-loader → OSK → LSFG → raw Vulkan path executes on
lavapipe/Xvfb with Khronos validation: OFF, 2x at 25% and 12.5%, history warmup,
swapchain recreation, generated presents, Wine-path keyboard-hook retention,
and zero validation errors.
Device features are enabled on copies rather than mutating caller structures.
The real adapter also runs under ASan/UBSan with modeled concurrent/multiple
acquires, retirement, keyboard bypass, missing pack, consumed-wait failure and
resource cleanup. These are host tests, not Switch scanout/FPS measurements.

Launcher rendering/navigation, mandatory-Light routing, LSFG persistence,
cached/forced verification and existing keyboard/COM codec regressions are
checked. Linked ARM64 checks cover the heap policy and required integration
symbols. Build receipts pin the reused native renderer/FEX inputs. Build using
`tools/build_launcher_v2.py` in the prepared WSL environment, then
`tools/test_launcher_v2.py`, `tools/test_lsfg_native_v2.py` and the Windows
`tools/test_launcher_v2_binary.py` runner before `tools/package_launcher_v2.py`.
The prepared environment is still required; a clean clone is not a full SDK.

Switch LSFG behavior, pause/resume, clean exit and crowded-scene performance
need a new device test. **Stable 30 native FPS remains unachieved.**
