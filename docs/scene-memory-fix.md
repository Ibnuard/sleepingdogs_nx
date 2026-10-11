# Scene loading: two compiler workspaces

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

The latest full logs are pinned in `reports/scene-memory-analysis.json`.
GPU-pressure recovery ran 13 times, lending about 23 MiB. At the final failure
the 256 MiB native GPU pool had 1,114,112 bytes free, but its largest run was
983,040 bytes. DXVK requested 1,048,576 bytes; Vulkan returned -1. The native
heap reported 42,607,088 free bytes spread across fragments and only 20,480
unclaimed bytes. A free-byte total does not guarantee a contiguous allocation.

DXVK reported 276 MiB allocated and 269 MiB used. The pool occupancy overlaps
these resources; do not add both totals. The process quota was still 2 GiB and
also pays for the 1000 MiB game arena, Wine, FEX, stacks and native backing.
The first guest fault is now `d3d11.dll!dxvk::DxvkBuffer`, EIP `0x100d147e`:
`mov ecx,[eax+0x20]` with EAX zero, immediately following failed allocation.
The previous free-pool guard correction remains active.

This patch reduces protected compiler workspace pairs and simultaneous FEX
compiler leases from four to two. Each pair retains its full 16 MiB IR and
64 KiB default decoder buffer, saving 33,685,504 bytes (32.125 MiB) of payload.
The actual ARM64 newlib allocator measures 33,685,568 bytes including allocator
overhead. Waiting compilers take their lease before the invalidation lock or
workspace ownership; both surviving pairs remain permanently protected.

FEX Fastest remains selected (500 instructions, multiblock and existing memory
ordering choices). The legacy crash header's `Stable` label is not the FEX
preset: the runtime explicitly logs `FEX3-PRESET fastest`. Guest execution can
still use four cores. Cold compilation/loading may take longer with two
compilers. The quota, game arena, GPU pool, renderer DLLs and forwarder stay
at their previously tested values. Saving this memory does not establish that
all 3D gameplay fits; another exhaustion or a different crash is possible.

## Validation

- ASan/UBSan: production FEX pools and leases, 32 threads and 8000 paired
  lifetimes; at most two IR/decoder buffers, no refusal, preserved data, queued
  progress and exception cleanup.
- Actual native ARM64 allocator/reserve code: identical quota and persistent
  workload. The old build fails a 1 MiB GPU request; the new build accommodates
  16 additional 1 MiB resources. Both compiler pairs remain usable across 64
  recycling operations after exhausting the ordinary heap.
- Actual FEX ARM64 DLL: the third compiler waits before the invalidation lock,
  resumes after release, and cache returns release both permits. Decoder bounds,
  game instruction samples and 67 debug-register emitter cases pass.
- Source reconstruction and hashes restrict changes to native reserve sizing,
  two-permit scheduling and build markers. Package checks cover matching NRO/FEX,
  preservation of other DLLs/settings/game files, and restoration of both sides.

Kernel allocation, scheduler/NT boundaries and selected host I/O are modeled.
These tests do not reproduce the unknown complete hardware allocation trace.
Switch gameplay has not been tested for this candidate.

## Installation

Close Sleeping Dogs from HOME. Copy the complete `switch/` directory from
`dist/sleepingdogs-fex-scene-memory-fix.zip` to SD root **last**. The NRO and
`drive_c/windows/system32/libwow64fex.dll` must be replaced together. The current
GPU-budget NSP remains valid; reinstall only if starting from an older forwarder.
Select DXVK 3.1.1 and Launch Debug, then test New Game through the first 3D scene.
Expected log markers:

```
[SD-COMPILER-MEM] native=v2 decoder_reserve_kib=64 ir_reserve_mib=16 pairs=2
[SD-COMPILER-MEM] fex=v2 compile_slots=2 decoder=instruction-limit ir_mib=16
```

The update contains all preceding fixes and no game assets, save or user setting
overrides. `dist/sleepingdogs-fex-scene-memory-rollback.zip` restores the prior
NRO, four-workspace FEX and receipts together. Send both new logs after any
remaining failure.
