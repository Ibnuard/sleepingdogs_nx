# Sleeping Dogs GPU pressure recovery v1

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

The latest SD-card logs confirm the streaming-memory NRO and sdstream1 renderer
were installed together. New Game still fails, now on small image/driver backing
allocations. The final DXVK report is 259 MiB allocated / 252 MiB used. The first
guest exception is D3D11 `0x101345d0`, in
`dxvk::DxvkImage::assignStorageWithUsage`, reading `NULL + 0x6c` after a failed
196,608-byte image allocation. The CS thread also cannot end its command buffer.

## What memory is unavailable

The current process quota is 2,147,483,648 bytes. The ordinary heap capacity is
2,070,040,576 bytes. That same heap provides the game's reserved 1,000 MiB arena,
native GPU backing, Wine memory, FEX work buffers and other runtime allocations.
The original PC specification lists **2 GB RAM and 512 MB graphics memory**
separately: [Square Enix's original-game requirements](https://support.eu.square-enix.com/faqarticle.php?id=5421&kid=64273&la=2).
A 512 MB VRAM minimum does not mean the entire game and translation runtime
fit within 512 MB, nor that a 512 MB reported adapter budget creates backing.

At failure the ordinary heap has 43,715,632 bytes free, with just 8,192 bytes
left to grow. It cannot satisfy the aligned requests; a 64 KiB recovery scan
finds at most 61,688 aligned bytes in its examined chunks. The native GPU pool
has 17,956,864 bytes free, including a 9 MiB contiguous run. These are different
allocator layers: pool free space is still held inside a live normal-heap
allocation. Do not add Vulkan usage to native pool occupancy as separate RAM.
The 256 MiB pool is also not a hard GPU limit: overflow uses ordinary newlib.

## Defect and correction

The previous streaming patch imposed a hard 16 MiB contiguous reserve after
each small emergency loan. Once live large resources reduced the largest free
run below 16 MiB, **every small loan failed**, even when other free runs easily
fit it. This policy introduced avoidable out-of-memory failures.

The new native helper first uses the same guarded preference. If it cannot
allocate, after both ordinary newlib allocation/recovery paths have already
failed, it searches all idle GPU runs using best fit. It may consume the reserve
or cross the preferred region boundary. Live allocations are never relocated,
discarded or overlapped. Normal allocation preferences and resource sizes stay
the same. Counters record emergency loans in existing bounded snapshots.

This fixes a demonstrated allocator error. It does not increase physical memory
or establish that later gameplay fits. The first 3D scene remains a hardware
test. DXVK, FEX and the paired forwarder binaries are identical to the previous
update. The renderer's secondary null-storage failure on genuine OOM is not
changed by this native allocation fix.

## Install and verify

Close FEXTendo from HOME and copy the **whole `switch/` folder** from
`dist/sleepingdogs-fex-gpu-pressure-fix.zip` to the SD root last. Choose DXVK
3.1.1, Launch Debug, then New Game. The previous GPU-budget NSP is already active
in these logs; no reinstall is needed. Fresh users coming from an older base
must install the identical GPU-budget NSP included in the cumulative ZIP once.
Fastest, user settings and original game files are preserved.

The new marker is:

```
[SD-GPU-PRESSURE] v1 soft_reserve=1; reuse idle GPU space before OOM
```

`[SD-GPU-PRESSURE-STATS] emergency_borrows=... requested_bytes=...` records actual
reserve use. The older stream marker still prints the preferred 16 MiB guard;
the new pressure marker means that preference may yield to a real allocation.

`dist/sleepingdogs-fex-gpu-pressure-rollback.zip` restores the previous streaming
NRO and receipts. Copy its whole `switch/` folder while closed; the renderer and
forwarder remain compatible. The SD card disconnected after the logs and binary
hashes were read, before a complete local copy was made. The analysis report
preserves the observed hashes and relevant excerpts, explicitly marked partial.

## Tests and limits

ASan/UBSan exercises the production helper with the logged capacity, occupancy
and largest free run. The layout of the three test holes is synthetic because
the complete hardware allocation trace is unavailable. Old guarded borrowing
fails; new 192 KiB loans succeed, choose smaller holes first and recycle. Tests
include all-free-space exhaustion, alignment, overflow, crossing the preference
boundary, legacy fallback and 1,024 concurrent allocation lifetimes.

The ARM64 test executes old/new production allocators and newlib in Unicorn,
with kernel/sbrk/log boundaries modeled. It keeps the game arena, four compiler
buffer pairs and live GPU data intact while exercising 64 KiB through 2 MiB
requests, 128 repeated loans and real pool exhaustion. Packaging reconstructs
the compiled source from the previous immutable build, verifies carried payloads
and tests fresh installation, mismatch rejection, rollback and reinstall.

Evidence: `reports/gpu-pressure-analysis.json`. Validation:
`reports/gpu-pressure-*-check.json` and `reports/gpu-pressure-package.json`.
