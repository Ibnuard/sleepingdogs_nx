# Launcher v4: synchronous COM transport and native production work

[Documentation](README.md) · [Status](STATUS.md)

The [v3 hardware capture](../reports/launcher-v3-game-499c25d436b6.json)
confirms that LSFG generated submissions at 50% motion. The user reports a
regression. Later 600-frame game-Present windows span 17.48–19.69 FPS and pool
to 18.59 FPS; the preceding capture pools to 21.01 FPS. Scenes and clocks are
not paired, and the earlier capture bypassed LSFG, so this is not an isolated
measurement of either the state filter or frame-generation cost.

The target is **25–40 real FPS at 1280×720**, including crowded scenes. That
target has **not been established on Switch**. Host checks verify semantics,
not game speed. Saved LSFG ON/OFF and motion preferences are preserved.

## Audit findings

- A later interval contains roughly **7,000 COM calls per game frame**, with
  about 1,081 draws per frame. Most calls use the compact input transport.
  The v3 state filter skipped only **2.3859%** of the bindings it examined;
  all hits were samplers. The next candidate drops that broad cache.
- Every ordinary input array passes Wine's protected memory probe, which
  establishes an exception frame and checks memory. The packet already has
  its own complete writable-memory probe, so small arrays can share that
  checked storage during the synchronous call.
- Two WRITE_DISCARD maps copy about **9 MiB per frame**, including during
  simpler scenes. Reducing the copy blindly would violate resource contents;
  directly returning a 64-bit Vulkan mapping to this x86 game is not valid.
- The native monitor skipped the old Wine performance report, while inherited
  performance/frame-diagnostic settings still enabled its accounting. This
  work had no native consumer.
- Late FEX dispatch compilation totals increase by about 1.36 seconds over
  100 seconds; nested code compilation accounts for about 0.66 seconds.
  These counters do not measure translated game execution. They do not
  justify an allocator/compiler rewrite as a large remaining speedup.
- Native DXVK workers already have mask `f`, while ordinary Wine/FEX workers
  use mask `7`. The capture does not justify forcing all native work to core 3.
  Light already uses the original game's confirmed minimum values, including
  WorldDensity=0; unrecognized XML keys would not establish lower crowd cost.

## Candidate changes

**Inline COM arguments.** Thirty-two input-only binding methods place short
arrays directly in the existing 160-byte wire packet. Native dispatch reuses
the packet's validated payload range for those reads. The range is local to
the current thread and synchronous call; nested calls clear and restore it.
External pointers still take Wine's memory probe. Large arrays, sentinel
counts and unsupported shapes retain the previous transport.

Every draw and binding is still executed in order; there is no deferred guest
queue, native pointer exposed to x86, retained guest-array pointer, or cached
permission across calls. `[SD-NDX-INLINE]` counts accepted packets, reused
reads, remaining probes, sampler creations and format checks. Those counters
measure avoided work, not FPS.

**Native production counters.** Ordinary native launch no longer enables
unused Wine performance or frame-diagnostic accounting from legacy settings.
An explicit `native-performance-counters.txt` containing `1` enables counters
and their report consumer together. Genuine Debug/profile requests remain
available. The x86 renderer keeps its existing behavior. Scheduler maintenance
is unchanged and does not depend on that report.

**Deferred work during Present.** A pinned native swapchain can present while
the bridge admits methods on verified deferred contexts, including their
Map/BindMap/Unmap uploads. Immediate-context, device, swapchain, release and
shutdown operations remain serialized. The independent native reference keeps
the swapchain alive. Explicit Multithread Enter scopes retain the old locked
path; recursive admission is rejected instead of waiting with an outer lock.
`[SD-NDX-OVERLAP]` counts released Presents, admitted work and serialized waits.
These counters establish use of the path, not its hardware speedup.

## Install and evaluate

Close the application fully from HOME. Copy **only the top-level `switch/`**
from `dist/sd-launcher-v4-update/` to the SD root and replace files. No separate
start-game overlay is needed. Existing game data and saves are not included.
Light 720p, cached verification, mandatory low-memory validation, PES13 keyboard
and the Settings Debug toggle remain.

The update contains no `launcher/lsfg.txt`, so the saved LSFG preference stays
under the user's control. Compare real FPS with LSFG manually OFF, after
loading, on the same route and camera at CPU/GPU/RAM **1728/768/1600 MHz**.
Save a separate log for LSFG ON tests. DXVK HUD still counts game frames.

`comparison-compact/switch/` optionally restores the pre-filter Compact proxy
on the same v4 NRO. It changes both the active DLL and renderer source; both
hashes are accepted by the checker. Copy the main `switch/` again to restore
inline transport. This comparison isolates the proxy transport, not every
v4 runtime change. `rollback-launcher-v2/switch/` restores the previous paired
NRO/Compact proxy if needed. That old build retains its known native LSFG
bypass; it is a performance rollback, not a working-LSFG alternative.

Send `fex-runtime.log` and `HKShip.exe_d3d11.log` from each run. The supplied
`runtime.log` is still the old H4 v3 COM self-test and does not establish a new
game or COM result.

## Build and validation

Build `tools/build_native_dxvk_inline.py`, then `tools/build_launcher_v4.py`
in the prepared WSL environment. The v4 NRO accepts the inline proxy and the
previous Compact proxy; the new inline proxy needs its matching NRO.
Run the inline guest/native tests, runtime-policy tests, launcher regression
and linked ARM64 checks before `tools/package_launcher_v4.py`.

The composed candidate passed actual DXVK/lavapipe tests with **7,388,534
checks, 1,843,200 pixels and 63 Presents**. A deferred worker completed its
upload while raw Present was deliberately held; all 1,024 bytes survived GPU
readback. Competing immediate/global calls, another Present and Release
waited. Nested dispatch was rejected without deadlock, Present under explicit
Multithread Enter retained the old path, and teardown left no interfaces/maps.
Those host timings are synthetic and are not a Switch performance benchmark.

Actual PE32 wrappers passed all 32 methods, array lengths 0–128, 1,000 mutable
bindings, nesting and fallback cases against a modeled endpoint. Nine native
permission scenarios and ASan/UBSan scope/concurrency checks passed. The runtime
policy passed 160 compiled C cases. The linked ARM64 startup audit passed
seven heap scenarios with no unresolved strong symbols. Full receipts are in
[the validation record](../reports/launcher-v4-validation.json).

Source hashes and individual test receipts accompany the ready-copy folder.
LSFG's unchanged source hashes are tied to its previous real Vulkan validation;
that is not a new LSFG speed/quality measurement. The personal shader pack is
excluded from GitHub. No ZIP or public release is created.
