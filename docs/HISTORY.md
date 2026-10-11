# Development history

[Documentation](README.md) · [Current status](STATUS.md)

This index preserves the technical record of the port. Each linked note
describes its own candidate, tests and installation context. The current
[installation guide](INSTALL.md) takes precedence over old setup instructions;
the notes are not a list of patches to install in sequence.

## Current runtime and recent experiments

| Iteration | Record |
| --- | --- |
| Native DXVK H3 v1 | [Guest-driven native swapchain/Present](native-dxvk-h3-v1.md); build and host tests pass, Switch test pending, folder delivery only |
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
