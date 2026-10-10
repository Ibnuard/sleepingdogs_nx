# Reuse retired large mapped buffers

SS/09 confirms the two-compiler Fastest build is active. DXVK reaches 300 MiB
allocated / 291 MiB used before a 5,242,880-byte mapped buffer allocation fails.
The native GPU pool has 3,276,800 free bytes, largest run 1,114,112 bytes. The
last failure snapshot reports 45,896,096 free general-heap bytes split across
fragments, plus 1,216,512 unclaimed bytes. These pools share one process quota;
free totals do not establish that one contiguous 5 MiB block is available.

The deferred Map correctly returns E_OUTOFMEMORY. The game subsequently executes
`rep movsd` at `HKShip.exe+0xa5897a` (EIP `0x00e5897a`), writing to `0x40`.
Its later exception during error handling is secondary. Full snapshots and
selected numbered evidence are recorded in `reports/buffer-reuse-analysis.json`.

The previous dedicated-buffer fix releases each large mapped allocation after
its final reference. SS/09 shows thousands of allocations/frees, including long
256-allocation intervals adding 1152 MiB of cumulative allocations. Repeatedly
returning such backing to the native heap makes later large requests vulnerable
to fragmentation. This patch retains a bounded set of fully retired buffers.

DXVK sdrecycle1 reuses only the same memory type and exact full backing size,
between 2 and 8 MiB. At most one idle entry per size/type, four entries total,
and 16 MiB idle globally are retained. Live references, command lists, views,
resource sizes and mapping properties keep their original lifetimes. External,
imported, image and sparse resources are excluded. Existing zeroMappedMemory
behavior also clears the retained buffers when requested.

The cache is drained by the allocator's existing full-trim path before its
allocation-failure retry, and during destruction. Used and allocated statistics
distinguish idle cached backing from live resources. This is reuse of existing
backing, not additional process memory. It may not resolve a later peak where
all suitable buffers are still live or the complete scene exceeds the quota.

The lifetime rules follow [D3D11 deferred mapping](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/mapping-on-deferred-contexts)
and [Vulkan memory lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkFreeMemory.html).
Only the final reference's ordinary free path may offer a buffer to this cache.

## Checks and limits

- ASan/UBSan execute the actual DXVK allocate/free/trim methods, cache helper and
  page allocator with modeled Vulkan backing: old fragmented-allocation failure,
  2000 reuse cycles, exact size/type matching, distinct live resource versions,
  byte/slot/duplicate bounds, pressure drain, clearing, excluded resource kinds,
  and eight threads with 8000 lifetimes.
- The shipping x86 D3D11 DLL executes 256 reuse cycles, real allocation dispatch,
  retirement and cache trimming, with offsets derived from its production C++
  compiler. No fresh allocation occurs on a hit. Live references cannot lend
  their memory; accounting and teardown return to zero.
- Deferred Map still returns a real failure without inventing storage; successful
  calls retain their recorded command reference. Renderer exports/imports,
  source reconstruction, installation, launcher preflight and rollback are checked.

Vulkan calls, SRW locks and selected diagnostic/destructor boundaries are modeled.
This is not a replay of the complete hardware allocation trace. Gameplay on
Switch has not yet been verified for this candidate.

## Installation

Close the game from HOME. Copy the **complete** `switch/` folder from
`sleepingdogs-fex-buffer-reuse-fix.zip` to SD root last. It includes all preceding
patches; both installed and launcher-stored renderer DLLs must be replaced.
The NRO/FEX pair stays at scene-memory v1 and Fastest stays active. Keep the
current GPU-budget NSP; no reinstall is needed for that forwarder.

Select DXVK 3.1.1 and Launch Debug, then New Game. Look for:

```
[SD-DXVK-RECYCLE] v1 retired-only exact-size-type max_idle_mib=16
[SD-DXVK-RECYCLE] event=reuse ...
```

The second line appears only after a real cache hit. If it still fails, send
both new logs. `sleepingdogs-fex-buffer-reuse-rollback.zip` restores the previous
DXVK renderer set and receipts; native runtime and forwarder remain the same.
