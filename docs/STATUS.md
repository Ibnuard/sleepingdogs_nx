# Current status and test evidence

[Documentation](README.md) · [Development history](HISTORY.md)

Status reviewed **2026-10-11**. Version labels v7–v18 identify development
iterations; they are not a sequence of published GitHub releases.

## What works

The original x86 Sleeping Dogs PC game reaches gameplay through Wine/FEX on
Switch. The low-window memory path, launcher settings, controller input and
DXVK HUD have been exercised on hardware.

The latest test runtime is **v18 APC**, retaining the v17 scheduler. Its
graphics path uses **x86 DXVK 3.1.1-sdbatch2** and native ARM64
**Mesa 26.2.2-sdv14.1-cache / NVK GM20B**. The FEX Switch integration continues
FEXTendo's own PES13-derived port of upstream FEX-Emu.

## Performance evidence

| Observation | Result and scope |
| --- | --- |
| Reference device | Switch OLED, handheld; last confirmed comparison clocks CPU 1728 / GPU 768 / RAM 1600 MHz |
| v17 scheduler hardware feedback | User reported that slow motion was removed, roughly 20 FPS with peaks near 25 FPS |
| Subsequent gameplay feedback | Usually around 20–23 FPS, with scene-dependent dips including about 17 FPS |
| Latest v18 log capture | 600 frame intervals in 29.875 seconds: about 20.08 FPS / 49.79 ms per frame |
| Later sampled v18 windows | About 19.56 FPS overall; individual window averages roughly 17.13–23.60 FPS |
| Stable 30 FPS | Not achieved |

The v18 figures refer to the log with SHA-256
`f23acbf64463a6ac99c2a3e5f363332e6cb5fa607115bd0bab80920ede6e3b40`.
It records 1280×720, Performance and the FPS HUD. The clocks above come from
the user's last confirmed comparison settings, not clock telemetry in this
log. These captures are not a controlled game-wide benchmark; scene and
camera changes limit comparisons between runs.

The v18 APC feature was enabled, but its `accepted_notices` counter remained
zero in that session. The log therefore does not show a gameplay benefit from
that optimization. Host and ARM64 checks passing establish the tested code
behavior, not an FPS gain on Switch.

The session also had LSFG configured for 2x, but repeatedly logged a bypass
and no first-interpolated-present marker. Those results cannot be described
as working frame generation. An LSFG-OFF run is needed for a clean native-FPS
baseline without that presentation path and its repeated logging.

## Known issues and limits

- Crowded areas and more complex scenes remain slow. Stable/Performance,
  lower resolution and higher clocks have not established another consistent
  gain in the supplied comparisons.
- Every in-game **Graphics Level** preset can display `undefined`; the
  cause and its relationship to actual applied quality remain unresolved.
- LSFG is experimental. Its current evidence does not establish a useful
  hardware benefit or increased native game speed.
- CPU usage, GPU-load estimates and memory occupancy are insufficient to
  isolate the remaining frame bottleneck. Current logs lack GPU timestamp
  measurements for that attribution.
- **Native ARM64 DXVK is a prototype only.** The
  [v1 probe](native-dxvk-probe-v1.md) builds an ARM64 static library, passes
  host draw/readback tests and has passed the supplied standalone Switch H1
  capture: 644 checks, all 720p pixels correct and 300 FIFO presentation calls.
  It is not integrated with the game; its modeled guest arena does not execute
  a real x86/FEX guest. The v15 term "native presentation" refers to the host presentation
  bridge; its DXVK DLLs still execute as x86.
  The separate [H2 PE32 bridge diagnostic](native-dxvk-h2-v1.md) has passed
  the actual Switch Wine/FEX guest path: 1,096 checks, the 1 KiB buffer and all
  720p offscreen pixels match. The [H3 native Present diagnostic](native-dxvk-h3-v1.md)
  passes build/host tests and is delivered as a ready folder for its next
  hardware test. Neither diagnostic implements game COM interfaces.
- Only the original x86 game is targeted. Definitive Edition is unsupported.
- A complete GitHub runtime release and a self-contained clean-clone v18
  build are not yet provided. See [Installation](INSTALL.md) and [Building](BUILD.md).

## Next investigations

The open performance work is to measure time spent in game execution, translated
DXVK work and native presentation, then test changes on the same 720p scene.
The native ARM64 DXVK probe has passed the supplied standalone hardware test;
the H2 Wine/FEX guest bridge also passes the supplied hardware capture. The
next hardware gate is H3 guest-driven native swapchain/Present, followed by
x86 COM interfaces and host-thread integration. It is not an available launcher mode or a proven
route to 30 FPS. See the [probe record](native-dxvk-probe-v1.md) for exact coverage.

Memory statistics must also be interpreted at the correct layer: remaining
process heap quota is not the same as free space inside existing allocators.
The latest session retained allocator space and did not establish an OOM
condition as the cause of its frame rate.

For implementation details and build-time evidence, see the
[v17 scheduler record](scheduler-v17.md), [present-mode comparison](present-ab-v17.md),
[v18 APC record](apc-v18.md) and [v18 package verification](../reports/apc-v18-package.json).
The versioned notes retain their original pre-test statements; this page
records the subsequent hardware feedback.
