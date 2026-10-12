# Launcher and game settings

[Documentation](README.md) · [Installation](INSTALL.md) · [Current status](STATUS.md)

## Native-FPS baseline

Use **DXVK 3.1.1**, **FEX Fastest**, **LSFG OFF**, **1280×720**, and normal
Launch / Launch GUI. Use the same graphics profile, game quality, camera and
clocks when comparing builds. Stable and Performance have not shown a
consistent improvement over one another in the reported hardware tests.

## Graphics and renderer

| Control | Effect |
| --- | --- |
| Settings → Game detail (H4 v8) | Game settings, reversible Light 720p, or Restore original |
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

The [H4 v8.1 native candidate](native-dxvk-h4-v8.1-transport.md) needs a passing COM self-test
before game validation. Its swapchain stays at 1280×720 and LSFG is forced
OFF without changing the stored LSFG preference. Both existing x86 renderer
choices remain available for comparisons. V8 retains `dxgi.syncInterval = 1`
in every native profile; confirm FIFO in the DXVK log. V4 passed the sponsor
stage and crashed at Press Start; v5 fixes scalar DSV and COM output memory.
V6 subsequently improves reported gameplay to 16–17 FPS, with 12–13 facing
crowds. V7 is reported around 20 FPS, peak 25 and crowded-running lows near 13.
V8 adds bounded Map reuse and optional lower game detail. V8.1 removes repeated
guest discovery locking and fixes the supplied XML rejection; its Switch test is pending.
Other profile options and x86 profiles stay canonical. H4 v2/v3 COM completion
was observed on Switch. A native FPS gain and production readiness remain unproven.

## Light 720p game detail

The H4 v8 menu **Settings → Game detail → Light 720p** lowers WorldDensity,
shadow resolution/filtering, motion blur, SSAO, AA quality and high-resolution
textures to the first built-in preset's minimum numeric values. Resolution
stays **1280×720**. `GlobalSetting=0` prevents a higher preset from overriding
those individual fields. AA at minimum is not a claim of AA entirely disabled.

An existing valid `drive_c/SleepingDogs/Data/DisplaySettings.xml` is required.
The first original is backed up alongside it as `.fextendo-original`. Other
supported display fields, `UserOptions.dat` and saves are preserved. If XML
is missing, select Game settings, save Display Options in game once, then
enable Light. An unsupported file is rejected instead of guessed.

Game settings stops enforcement and retains the current file. **Restore
original** restores pre-Light quality and disables the preset. If all quality
values were already minimum, Light has no demonstrated additional benefit.
V8.1 accepts GlobalSetting=-1 and normalizes it to 0 for Light. The captured
file already has zero individual fields; the original executable's unsigned
preset reader can fall back to preset 2 for minus-prefixed text. This is a
static finding, not a measurement of live quality or FPS. Compare the same
route and camera; v8.1 FPS remains unmeasured.

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
