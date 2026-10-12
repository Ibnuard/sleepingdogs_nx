# Troubleshooting

[Documentation](README.md) · [Installation](INSTALL.md) · [Current status](STATUS.md)

## Launcher will not start or memory preflight fails

Confirm that the current boot environment and Sleeping Dogs forwarder match
the [39-bit host + guest low-window requirements](INSTALL.md#boot-and-forwarder).
An NRO update cannot supply missing kernel/loader support. The old 32-bit
forwarder and another game's forwarder do not satisfy the current layout.

The expected memory check is:

```text
[SD-LOWVA] PASS: native above 4 GiB; guest low window available
```

If the log names an older build after updating, close the application from
HOME, confirm that the new NRO is at the forwarder's exact SD target, and
relaunch. Record the NRO SHA-256 as well as the build marker when reporting
a mismatch.

## Game is missing, exits or stops while loading

Confirm that `HKShip.exe` is the original x86 edition and is directly inside
`drive_c/SleepingDogs/`. Check that all BIG/BIX files, `Data/` and the rest of
the installed game files were copied. Keep the package's complete renderer
DLL set and Wine modules together.

Use Launch Debug for a reproduction, then save the log before another launch.
Do not apply an older startup fix merely because its document mentions a
similar symptom; the [history](HISTORY.md) contains multiple superseded builds.

## Graphics Level is undefined

All in-game preset labels have been reported as `undefined`. The cause remains
unresolved. Reading `Data/DisplaySettings.xml` succeeded in an earlier log,
but that does not establish which quality options the game applied.

Use the game's **Advanced Options** to inspect the actual settings. When
reporting this issue, include a screenshot of those options and the relevant
`Data/DisplaySettings.xml` from the tested installation. Preserve the original
configuration before experimenting. A launcher profile named Stable or
Performance does not repair the game's preset labels.

## Low FPS or no improvement from a setting

Current results do not establish stable 30 FPS. A crowded scene may be slower
than an empty area even when average GPU usage looks low. Around 300 MB of
video-memory occupancy measures capacity used, not memory throughput.

For a useful comparison:

1. Keep the same build, clocks and game quality; change one setting at a time.
2. Turn LSFG OFF and use normal Launch / Launch GUI with the FPS HUD.
3. Warm the scene, then repeat the same location, camera direction and route.
4. Save separate logs and note native FPS and visible stutter for each run.
5. Record whether clocks changed during the session and where each capture
   occurred. Separate menu FPS from gameplay FPS.

Lowering resolution has not produced a clear improvement in the user's tests.
That observation alone does not prove a single CPU or GPU bottleneck. Existing
frame and wait counters include waiting and scheduling; they are not GPU
timestamp measurements.

[Launcher v4](launcher-v4.md) targets repeated COM memory probes and render
workers blocked behind Present. `[SD-NDX-INLINE]` and `[SD-NDX-OVERLAP]` show
whether those paths are exercised. A rising avoided-probe/admitted-work count
does not itself demonstrate an FPS gain; compare the same crowded route.
The update preserves the saved LSFG switch for manual comparison.

## LSFG is on but does not help

H4 through launcher v1 forced LSFG OFF on native DXVK even when the stored
launcher preference was ON. Launcher v2 connects that route, but its first
hardware capture bypassed all interpolation because DXVK passed FIFO mode
metadata. [Launcher v3](launcher-v3.md) fixes that rejection.
Its subsequent hardware capture confirms generated submissions, but the user
reports worse native performance. The generated-frame count is not a scanout
or smoothness measurement.
Check for `first interpolated present submitted`; requested/initialized alone
is insufficient, and repeated bypass reasons mean interpolation is being
skipped. DXVK HUD reports real game FPS. See
[LSFG settings and limits](CONFIGURATION.md#optional-lsfg).

Compare native performance with LSFG OFF first. Frame generation cannot repair
slow game simulation caused by low native FPS.

## Logs and issue reports

Paths below are relative to `switch/sleepingdogs-fex/` on the SD card:

| File | Purpose |
| --- | --- |
| `fex-runtime.log` | Build identity, startup, memory, scheduler and frame summaries |
| `crash.log` | Crash details, when produced |
| `drive_c/SleepingDogs/HKShip_d3d11.log` | DXVK D3D11 diagnostics, when produced |
| `drive_c/SleepingDogs/HKShip_dxgi.log` | DXGI and presentation diagnostics, when produced |

Copy logs out before the next launch can replace them. Include the package
name/build marker, NRO hash if available, Switch model, handheld/docked mode,
CPU/GPU/RAM clocks, resolution, graphics profile, renderer, FEX mode, LSFG
setting, and reproduction steps. For a regression, identify the working and
failing builds and compare the same scene.

Attach logs to a [GitHub issue](https://github.com/Ibnuard/sleepingdogs_nx/issues)
with screenshots where relevant. Game executables, game archives, keys and
saves are not needed for a normal issue report.
