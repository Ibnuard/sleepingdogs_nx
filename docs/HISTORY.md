# Development history

[Documentation](README.md) · [Current status](STATUS.md)

This index preserves the technical record of the port. Each linked note
describes its own candidate, tests and installation context. The current
[installation guide](INSTALL.md) takes precedence over old setup instructions;
the notes are not a list of patches to install in sequence.

## Current runtime and recent experiments

| Iteration | Record |
| --- | --- |
| Native Ref v1 | [Guest-local reference ownership](native-dxvk-ref-v1.md); avoids temporary FEX/Wine/native calls with native lifetime credits; PE32 checks pass, Switch FPS pending |
| FEX context v1 | [Exact x87 import shortcut](fex-context-v1.md); subsequent Light 720p capture confirms activation, slight improvement reported, final windows 20.56 FPS |
| Native DXVK H4 v9 | [Bridge probes, Map traffic and batching](native-dxvk-h4-v9-memory-batching.md); later Light 720p/batching capture pools to 20.59 FPS, no meaningful gain reported |
| Native DXVK H4 v8.1 | [Guest transport and Light fix](native-dxvk-h4-v8.1-transport.md); subsequent Light report 20–22 FPS, crowded lows 16, confined peak 30; last five Present windows 20.67 FPS |
| Native DXVK H4 v8 | [Map reuse and Light 720p](native-dxvk-h4-v8-game-detail.md); later feedback 17–20 FPS, Light rejected GlobalSetting=-1 |
| Native DXVK H4 v7 | [Object lookup and temporary arrays](native-dxvk-h4-v7-objects.md); subsequent user report around 20 FPS, peak 25 and crowded-running lows near 13 |
| Native DXVK H4 v6 | [Reduce bridge diagnostic cost](native-dxvk-h4-v6-dispatch.md); user reports less slow motion, 16–17 FPS; final log windows average 16.67 FPS |
| Native DXVK H4 v5 | [Correct COM output memory](native-dxvk-h4-v5-com-outputs.md); local checks pass; subsequent user report reaches gameplay around 15 FPS |
| Native DXVK H4 v4 | [Queued logging and ongoing progress](native-dxvk-h4-v4-logging.md); subsequently 1,020 native Presents before Press Start crash |
| Native DXVK H4 v3 | [Sponsor freeze investigation](native-dxvk-h4-v3-sponsor.md); COM PASS observed, game still freezes with FIFO; 128 traced calls all completed |
| Native DXVK H4 v2 | [Launcher-to-native screen handoff fix](native-dxvk-h4-v2-window.md); subsequent COM PASS observed on Switch, game presents one frame then freezes before animated splash |
| Native DXVK H4 v1 | [x86 COM bridge and native game launch candidate](native-dxvk-h4-v1.md); built and locally checked, H4 Switch/game/FPS validation pending; folder delivery only |
| Native DXVK H3 v1 | [Guest-driven native swapchain/Present](native-dxvk-h3-v1.md); supplied Switch capture passes 2,331 checks and 300 Present calls, folder delivery only; no game COM integration |
| Native DXVK H2 v1 | [PE32 Wine/FEX bridge diagnostic](native-dxvk-h2-v1.md); supplied Switch capture passes 1,096 checks and both readbacks |
| Native DXVK probe v1 / H1 | [ARM64 build, host tests and successful standalone Switch capture](native-dxvk-probe-v1.md); no real x86 guest or game integration |
| v18 | [Targeted queued-APC notification](apc-v18.md) |
| v17 | [Automatic application-core scheduling](scheduler-v17.md) |
| v17 comparison | [FIFO versus IMMEDIATE presentation](present-ab-v17.md) |
| v16 | [Scoped Wine synchronization notifications](sync-notify-v16.md) |
| v15 | [Native presentation, DXVK batching and optional LSFG](native-v15-lsfg.md) |

The v17 scheduler has positive user feedback; v18 has not established an
additional FPS gain. The v15 "native" label refers to presentation, not
native ARM64 DXVK. See [Current status](STATUS.md) for the measured limits.

## Rendering and performance investigation

| Iteration | Record |
| --- | --- |
| v14.1 | [Mesa/NVK cache-identity correction](low-window-gm20b-cache-fix.md) |
| v14 | [GM20B shader compiler experiment](low-window-gm20b-shaders.md) |
| v13 | [Mesa backports](low-window-mesa-backport.md) and [DXVK research](v13-dxvk-research.md) |
| v12 | [DXVK submission batching](low-window-submit-batching.md) |
| v11 | [Frame diagnostics](low-window-frame-diagnostics.md) |
| v10 | [Direct synchronization](low-window-direct-sync.md) |
| v9 | [Shader worker placement and allocation reuse](low-window-shader-optimizations.md) |
| v8 | [Performance counters](low-window-perf-counters.md) |
| v7 | [DXVK HUD and Performance profile](low-window-performance-hud.md) |

## Low-window boot and gameplay bring-up

| Area | Record |
| --- | --- |
| Gameplay worker topology | [v6 CPU topology fix](low-window-cpu-topology-fix.md) |
| Startup observer | [v5 sync startup guard](low-window-sync-startup-fix.md) |
| Loading synchronization | [Semaphore and queue investigation](low-window-sync-watch.md) |
| Memory ordering | [TSO comparison](low-window-tso-test.md) |
| Loading diagnostics | [Loading watch](low-window-loading-watch.md) |
| Launch admission | [Memory preparation and launch order](low-window-launch-order-fix.md) |
| Generic memory descriptor | [FEXTendo Memory v1 forwarder](forwarder-memory-v1.md) |
| Earlier forwarder | [Low-window startup fix](low-window-startup-fix.md) |
| Initial layout | [Original low-window experiment](low-window-fix.md) |

## Earlier compatibility and memory work

These notes concern the original baseline and earlier startup/scene problems.
Their 32-bit installation instructions are historical.

| Area | Records |
| --- | --- |
| Guest exceptions | [Execution breakpoints](debug-register-fix.md), [debug-register cache](debug-cache-fix.md), [suspended thread context](thread-debug-fix.md), [execute-policy notification](dep-policy-fix.md) |
| Local IPC | [Named pipes](named-pipe-fix.md) |
| CPU/native memory | [Native headroom](memory-budget-fix.md), [compiler memory](compiler-memory-fix.md), [scene compiler workspaces](scene-memory-fix.md) |
| Renderer memory | [DXVK allocation sizing](dxvk-memory-fix.md), [GPU budget](gpu-budget-fix.md), [GPU pressure](gpu-pressure-fix.md), [streaming allocation](streaming-memory-fix.md), [retired buffer reuse](buffer-reuse-fix.md) |

## Preserved source records

- [Legacy project notes](LEGACY-PROJECT-NOTES.md): the old README's complete
  patch chronology, including the initial baseline and recovery packages.
- [Inherited PES13 third-party notices](PES13-THIRD-PARTY.md): the original
  attribution snapshot; use [current credits](../THIRD_PARTY.md) for this port.
- [Initial import receipt](../reports/upstream-inputs.json): hashes of the
  reusable F1 helpers and the approved runtime/source inputs.
- [Reports](../reports/): build, binary, analysis and package evidence. Paths
  inside reports refer to their original workspace, and a PASS is scoped to
  the check described by that report.
