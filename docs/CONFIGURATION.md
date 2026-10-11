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

The [H4 native candidate](native-dxvk-h4-v1.md) needs a passing COM self-test
before game validation. Its swapchain stays at 1280×720 and LSFG is forced
OFF without changing the stored LSFG preference. Both existing x86 renderer
choices remain available for comparisons. H4 has not yet established Switch
gameplay correctness or an FPS gain.

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
