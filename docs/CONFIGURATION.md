# Launcher and game settings

[Documentation](README.md) · [Installation](INSTALL.md) · [Current status](STATUS.md)

[Production v1](production-v1.md) retains these controls. **Normal Play creates
no diagnostic logs**; settings, caches, registry, saves and last played still
persist. Enable **Settings → Show debug launch** and select **Launch Debug**
when following any log-based checks below. Old logs are not deleted or refreshed
by normal Play. The public package excludes the optional private LSFG pack and
does not change the saved LSFG setting.

The [launcher v4 candidate](launcher-v4.md) retains **Settings → Keyboard**,
**System Check**, and **Show debug launch**. Debug is hidden until enabled.
Successful full runtime hashing is cached across launches; updates, changed
file metadata and manual System Check trigger a full scan. Current HOME and
low-memory mapping checks still run each process. **Light 720p is mandatory**;
there is no Original/Game detail selection. LSFG now also connects to native
DXVK instead of silently being forced off. V3 fixes v2 rejecting FIFO present
metadata; its later Switch capture confirms generated submissions but reports
lower native FPS. V4 preserves that fix and the user's saved LSFG preference;
it focuses on native COM and scheduling overhead.

## Native-FPS baseline

The current native candidate uses **DXVK Native ARM64**, **Light 720p**,
**FEX Fastest**, **LSFG OFF**, and normal Launch / Launch GUI. The retained
x86 comparison uses **DXVK 3.1.1**. Use the same graphics profile, game quality, camera and
clocks when comparing builds. Stable and Performance have not shown a
consistent improvement over one another in the reported hardware tests.

## Graphics and renderer

| Control | Effect |
| --- | --- |
| Game detail | Light 1280×720 enforced at each launch; no quality selector in launcher v2 |
| Settings → Graphics | Selects a DXVK configuration profile: Balanced, Low latency, Stable, Quality or Performance |
| Settings → Renderer | Selects the DXVK 3.1.1 family or DXVK 2.7.1 async; the H4 candidate adds experimental DXVK Native ARM64 |
| FEX mode | Selects the CPU-translation profile; Fastest is the current test baseline |
| In-game Resolution | Selects the game's render resolution, including 1280×720 and 960×540 |
| In-game Advanced Options | Controls game quality settings independently of launcher profiles |

Launcher graphics profiles affect options such as filtering, requested sync
interval and queue depth. They do not set the number of pedestrians, world
detail or a named in-game quality preset. The Performance profile can also
increase queued frames and input latency; its name is not a measured FPS claim.

Present-mode experiments can modify the underlying profile files. A profile
label alone does not prove that FIFO or IMMEDIATE is active; check the runtime
log. Preserve those files when comparing NRO-only changes.

`UserOptions.dat` belongs to the game and is not rewritten by the launcher.
The persistent `Graphics Level: undefined` issue is covered in
[Troubleshooting](TROUBLESHOOTING.md#graphics-level-is-undefined).

The earlier H4 builds forced LSFG OFF for the native renderer. Launcher v2
adds the missing native presentation adapter. Native profiles retain FIFO;
verify the selected route and active mode in the runtime/DXVK logs. Hardware
COM completion has been observed, but it does not prove every later build's
gameplay or LSFG behavior. See [status](STATUS.md) for the separate test records.

## Light 720p game detail

Launcher v2 applies the Light profile automatically before Play/Debug. It
lowers WorldDensity, shadow resolution/filtering, motion blur, SSAO, AA quality
and high-resolution textures to the minimum supported numeric values, with
**1280×720** and `GlobalSetting=0`. AA at minimum does not mean all AA is disabled.
Legacy `launcher/game-quality.txt` is ignored. There is no Restore option in
the current launcher; in-game changes are overwritten by Light on next launch.

An existing valid `drive_c/SleepingDogs/Data/DisplaySettings.xml` is required.
The first original remains backed up as `.fextendo-original`; unrelated XML
fields, `UserOptions.dat` and saves are preserved. Missing/unsupported XML
blocks launch and needs a valid original game settings file. If every value
was already minimum, enforcing Light does not imply another FPS gain.

## DXVK HUD

Open **Settings → DXVK HUD**, select a mode, and confirm with A.

| Mode | Display |
| --- | --- |
| None | No DXVK overlay |
| FPS | Game-frame FPS counter |
| Full | Available DXVK statistics, including frame times, draw calls and load estimates |

The HUD also works with normal Launch; Launch Debug is not required. Use FPS
for routine comparisons and Full when gathering detailed evidence. GPU-load
estimates and video-memory occupancy do not, by themselves, identify the
limiting part of the frame.

## Optional LSFG

**Settings → Frame Generation** exposes LSFG 2x and motion resolution
**12.5% / 25% / 50%**. Defaults are OFF and 25%; the integration uses its
validated Performance path. Changes apply on the next launch.

LSFG inserts generated display frames between game frames. It does not raise
native game FPS or speed up game simulation, and it adds GPU work and latency.
Its motion resolution does not change the game's 720p render resolution.

The experimental integration requires a compatible shader pack prepared from
the user's own Lossless Scaling input. Proprietary shader payloads are not
included in the source repository. See the [v15 integration record](native-v15-lsfg.md)
for the implementation and source attribution.

A toggle showing ON is not proof that generation ran. The implementation can
bypass generation for unsupported presentation paths. Look for
`first interpolated present submitted` in the log; repeated `bypass` messages
mean that path is not producing generated frames. DXVK's HUD counts game
frames, and submission counters do not verify frames actually scanned out.

Keep LSFG OFF when measuring native performance. No useful hardware benefit
has been established in the current test record.

## Developer comparison switches

The [native H4 v9 candidate](native-dxvk-h4-v9-memory-batching.md) enables
`d3d11.sdSubmissionBatching` only for native Performance. Its `batch-off/`
and `batch-on/` overlays change that single option without changing Light
720p or the other v9 runtime optimizations. Close from HOME, copy the selected
overlay's `switch/` folder, and select Performance again. Other native profiles
and both x86 renderer defaults retain their previous batching behavior.

These are optional files in `switch/sleepingdogs-fex/`, not settings required
for installation. Write the value followed by a newline, then close from HOME
and relaunch.

| File | Default / `1` | `0` |
| --- | --- | --- |
| `auto-affinity.txt` | v17 automatic placement for eligible application threads | Previous v16 pinning policy |
| `apc-targeted-wake.txt` | v18 targeted queued-APC notifier, active with sync mode 2 | Previous broad queued-APC notifier |

Removing either file restores its default. Explicit thread affinity and other
protected cases retain their own policies. Details are in the
[v17 scheduler](scheduler-v17.md) and [v18 APC](apc-v18.md) experiment records.
