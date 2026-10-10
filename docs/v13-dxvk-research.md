# DXVK research for the first post-v12 trial

Research performed on 2026-10-09. This note records the alternatives examined; it does not claim a Switch performance result.

## Decision

Keep the tested DXVK `3.1.1-sdbatch1` for the first trial and prioritize the separately audited Mesa/NVK driver changes. The current log confirms `[SD-DXVK-BATCH] v1 enabled=1`; it does not support changing Wine, FEX, and DXVK versions simultaneously.

The Switch FEXTendo integration remains the user's AndroSwitch Project / Ibnuard port derived from their pes13-fex work. FEX-Emu is the translation engine. Researching Autorun does not change that provenance or make this an Autorun FEX port.

## Release and Autorun comparison

- [DXVK's latest release](https://github.com/doitsujin/dxvk/releases/tag/v3.1.1) remains 3.1.1, commit `b1a1c99ab52b687cf950d62c88bc2fa316b41663`, the base of our build. Upstream master was 67 commits ahead at inspection, ending at `1cad6cd11d8b0edf89113a0d8e4819ade33fbf9c`.
- [Autorun's bundled x86_64 DXVK manifest](https://github.com/autorunhq/autorun-horizon-dlls/blob/main/switch/wine/drive_c/dxvk64/dxvk-manifest.json) also declares 3.1.1 and the same base revision. Its [build script](https://github.com/autorunhq/autorun-horizon-dlls/blob/main/tools/build-dxvk.py) verifies an unmodified pinned source tree. This specific evidence concerns its x86_64 bundle, not every optional renderer or the user's x86 build.
- [Autorun's technical notes](https://github.com/autorunhq/autorun/blob/main/documentation/technical.md) describe a roughly 58 FPS D3D9 test and roughly 61 FPS Vulkan test, alongside game results such as 24–34 FPS WarCraft III and roughly 20–45 FPS NFS Underground 2 through wined3d. These different workloads do not establish a 30/60 FPS target for Sleeping Dogs.
- [Autorun also supports optional LSFG-VK interpolation](https://github.com/autorunhq/autorun#frame-generation). It requires the user's Lossless Scaling DLL; generated output frames are not evidence of equivalent game simulation/render throughput. No frame generation is proposed for this trial.

## Why not ignore explicit flushes

Upstream [commit `6fd968e97cecdcacaea2ca5516bd21a916730cdd`](https://github.com/doitsujin/dxvk/commit/6fd968e97cecdcacaea2ca5516bd21a916730cdd), dated October 5, adds `d3d11.ignoreExplicitFlush`, default false. It bypasses `RequestFlush` calls only when there is no event and the device is not 11on12.

Our current source, `src/d3d11/d3d11_swapchain.cpp:414`, calls `ExecuteFlush(ExplicitFlush, nullptr, true)` directly once per normal present. This bypasses `RequestFlush`. Consequently the aggregate `explicit` diagnostic includes obligatory present flushes and is not a count of application `ID3D11DeviceContext::Flush` calls. An explicit count near one per frame is not evidence that this new option can eliminate those submissions.

For example, the new log's cumulative flush counters from 5,376 to 8,448 show 3,072 context flushes: 875 explicit, 2,031 weak, 163 synchronization, and 3 strong. Later gameplay remains dominated by automatic weak hints. These counters cover a changing scene and are not an isolated benchmark or a count of Vulkan submissions.

The local batching guard already delays small automatic hints while at least two submissions are pending, retaining readback, query, present, explicit, queue-draining, and maximum-cost progress paths. Increasing the threshold from 12 to 20 chunks is a possible future controlled test, but its benefit is not established by this log: chunk counts and estimated cost at each accepted flush are not recorded. The native submit time has already fallen substantially in the main analysis. Another batching adjustment has less direct evidence than the newly identified GPU driver changes.

## Initializer improvements: promising for streaming, not selected yet

The following upstream sequence changes upload allocation and locking:

1. [`850a013cd3686f4d52cf526d67ad2d941e9e337b`](https://github.com/doitsujin/dxvk/commit/850a013cd3686f4d52cf526d67ad2d941e9e337b): avoids holding the initializer mutex while throttling on staging memory; replaces the linear staging allocator for this path with resource-local temporary buffers.
2. [`97a20610abc79b56acdeae13991be6acede023f4`](https://github.com/doitsujin/dxvk/commit/97a20610abc79b56acdeae13991be6acede023f4): increases maximum staging memory in flight from three to four per-submission budgets, 36 to 48 MiB for the current 32-bit configuration.
3. [`d6e0e94742c53715c076dd08dba3f7d0ed09db05`](https://github.com/doitsujin/dxvk/commit/d6e0e94742c53715c076dd08dba3f7d0ed09db05): serializes allocation requests to prevent starvation of large allocations.
4. [`3200bb10771bb0a88ce3a3700ce467ff90190a02`](https://github.com/doitsujin/dxvk/commit/3200bb10771bb0a88ce3a3700ce467ff90190a02): fixes an infinite loop when the allocation limit and requested size use inconsistent alignment.

The first commit must not be cherry-picked alone. The complete sequence changes allocation patterns in code interacting with our tested 32-bit low-VA and buffer-reuse work. The supplied runtime diagnostics do not measure initializer lock contention or staging throttles, so there is not yet evidence that this path dominates steady gameplay. Reserve it for a streaming-specific follow-up if the first trial supports that direction.

The October 9 [submission synchronization rewrite](https://github.com/doitsujin/dxvk/commit/1cad6cd11d8b0edf89113a0d8e4819ade33fbf9c) addresses an upstream correctness issue across queue and interop interfaces. It is not an established Sleeping Dogs speed fix and is not needed merely to obtain the small opt-in explicit-flush change.

## Other changes deliberately excluded

- Do not enable `dxvk.tilerMode` globally: it changes more than batching, including render-pass behavior, and GM20B is not a tile-based mobile architecture.
- Do not bypass resource barriers or enable `d3d11.relaxedBarriers` blindly. The [upstream configuration](https://github.com/doitsujin/dxvk/blob/v3.1.1/dxvk.conf) explicitly documents rendering risks from dropping hazards.
- Do not treat `dxgi.maxDeviceMemory` or `dxgi.maxSharedMemory` as actual GPU allocation limits; they change values reported to the application.
- Do not lower frame latency as a throughput optimization: it can reduce CPU/GPU overlap. The current maximum of three remains appropriate until measured otherwise.
- Do not replace the renderer solely because Autorun has an option to download another DXVK release. The concrete release/commit and workload behavior matter.

[DXVK's developer guidelines](https://github.com/doitsujin/dxvk/wiki/Developer-guidelines) explain why excess flushes, fine-grained resource updates, state changes, and upload/readback synchronization can be costly. They do not establish which of those paths is dominant in this untraced game; the above decisions distinguish source-level possibility from evidence in this run.
