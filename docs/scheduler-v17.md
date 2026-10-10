# Sleeping Dogs v17: automatic application-core scheduling

This is a reversible native Wine scheduler candidate, not a measured FPS fix.
The target remains 1280x720 with the project's own pes13-fex-derived FEX port.

## Evidence from the supplied v16 session

Input: `fex-runtime.log`, SHA256
`614bd031fb359b2aefed14ec0f73d3493ca67961bd7df398f2ebd2e1886a1a6c`.
The preserved analysis is `reports/gameplay-v11-614bd031fb35.json`.
The input hash in that report is authoritative.

The capture contains 479 present intervals in 29.953266 seconds: 15.99 FPS,
62.53 ms per interval. The later sampled windows remain around 13–17 FPS.
The v16 notification filter is active, but these observations and the user's
same-performance result do not establish a useful performance improvement.

Automatic game and DXVK workers still have individual single-core masks while
their registry entries say `fixed=0`. A busy game worker shares core 1 with
`dxvk-cs` later in the session. The old balancer works from sampled cumulative
CPU load, which need not capture runnable bursts on the critical path.
This suggests testing OS placement across application cores, but does not prove
that pinning is the principal bottleneck. Thread CPU times overlap and cannot
be added to calculate frame latency.

GPU utilisation around 60% can coexist with slow frames when upstream work or
dependencies leave gaps. Roughly 300 MB of video-memory occupancy is a capacity
measurement, not memory bandwidth. The log does not show an out-of-memory
condition. Neither number establishes that raising a memory budget would help.
Late fence waits also rise, so the GPU cannot be ruled out solely from averages.

## Change and safeguards

- New `auto-affinity.txt` setting: absent or `1` selects v17; `0` restores the
  prior scheduling policy after a full restart.
- Ordinary automatic Wine/FEX threads may run on the granted process cores
  intersected with mask `7` (cores 0–2). Initial preferred cores still rotate.
- The periodic pass preserves a valid preferred core and expands the allowed
  mask; it no longer feeds these threads into the single-core balancer.
- Accepted explicit affinity, shader scopes, pending affinity restores and
  active core-3 helpers retain their respective policies. Explicit remote group
  affinity is also recorded when v17 is enabled, including with shader affinity
  disabled. A failed native update remains protected and retryable.
- Server connection masks are published only after successful native application
  or a successful query confirming the desired mask. Failed queries/updates do
  not publish an assumed mask. An empty application-core intersection is left
  untouched. `no-balance.txt` still disables periodic updates.

The FEX engine, DXVK, Mesa, LSFG, resolution and graphics configuration are
unchanged. Broad masks permit migration; the Horizon kernel decides when to
schedule a runnable thread. This build does not change priorities or yield
semantics. Hardware behaviour and FPS improvement remain unmeasured.

## Install and compare

1. Close FEXTendo completely from HOME. Merge the update ZIP's `switch` folder
   into the SD root. No preference, save or game-data files are included.
2. Keep 720p, the same clocks and graphics settings. Set LSFG OFF to measure
   native rendering. Use a warmed, repeatable crowded scene and camera.
3. Confirm `sleepingdogs-fextendo-0.1.0-v17-scheduler` and
   `[SD-SCHED-V17] mode=auto coremask=process&7 periodic=1` in the runtime log.
   Eligible thread masks should become `7` when all three application cores
   are granted. The counters describe operations, not saved time or FPS.
4. Save the log before the next launch overwrites it. To compare the old policy
   within this NRO, write `0` and a newline into
   `switch/sleepingdogs-fex/auto-affinity.txt`, close from HOME and relaunch.
   The marker should say `mode=v16-pinned`. Remove the file or set `1` to enable.

If the new policy regresses or is unstable, the rollback ZIP restores the exact
delivered v16 NRO and affected metadata. v16 ignores `auto-affinity.txt`.

## Validation boundaries

The build first reproduces the delivered v16 ELF byte-for-byte, then recompiles
four owned translation units against the prepared overlay. Input hashes are
checked before packaging. Host sanitizer fixtures execute the production policy
and Wine affinity paths; ARM64 checks execute the candidate binary with mocked
kernel calls. Existing direct-sync, low-window, shader, cache-identity and LSFG
link checks guard inherited behaviour. ZIP manifests, CRCs and exact rollback
are verified. These checks do not emulate real multicore Horizon scheduling or
measure Switch gameplay. There is no claim of 30 FPS.
