# Sleeping Dogs: New Game / streaming memory v1

The user reached the main menu and New Game loading with the previous GPU-budget
update. The new logs show the paired loader and 256 MiB native GPU pool active.
At the transition toward the first 3D scene, a 5,242,880-byte allocation fails.
The GPU pool has 5,636,096 bytes free in separate holes; its largest hole is only
2,097,152 bytes. The normal allocator finds at most 720,952 aligned bytes.
DXVK reports 256 MiB allocated / 241 MiB used. Those Vulkan statistics exclude
some driver backing allocations and are not the native heap budget.

The first guest exception remains HKShip.exe `0x00e5897a`, `rep movsd` writing
to `0x40`, after DXVK reports a failed deferred Map. The later `0x0071d2ab`
exception occurs during error handling. The last periodic normal-heap snapshot
precedes the failure; its roughly 99 MiB available must not be treated as the
amount available at the actual OOM. The run used GUI mode.

## Change

DXVK sdstream1 gives mapped allocations larger than 2 MiB their own backing.
Previously even large buffers first entered the shared pool, where a small
allocation could retain that backing after the large buffer retired. Normal
reference ownership remains responsible for releasing it; live commands keep
their allocation. Resource lengths, mapping flags and alignment are preserved.
`NoAllocation` still only reuses existing allocations. The existing deferred
Map/Update error handling remains in place.

The native pool remains 256 MiB. Its lower 192 MiB handles general requests;
the upper 64 MiB is preferred for requests above 2 MiB. Large requests may
overflow to the lower region and then ordinary newlib. Small requests try the
lower region and ordinary newlib first. Only when both normal allocation paths
fail may they borrow the upper region, retaining a contiguous 16 MiB free run.
This guard applies to small borrowers; live large allocations can consume it.
No live pointer or GPU mapping is moved. A legacy/downsized pool keeps its
previous behavior. Failure diagnostics now record each region's largest hole
and contemporaneous normal-heap free/unclaimed bytes.

This targets a source-level lifetime/fragmentation mechanism consistent with
the log. The log does not prove every large-buffer lifetime, and total process
memory remains limited to 2 GiB. Dedicated backings and region boundaries can
also change allocation overhead; hardware testing is still required.

## Install

Close FEXTendo completely from HOME. Copy the entire `switch/` directory from
`dist/sleepingdogs-fex-streaming-memory-fix.zip` onto the SD card **last**, after
any base/ready package. It updates the NRO and all seven managed renderer DLL
copies together. Select DXVK 3.1.1 and Launch Debug, then try New Game.

The previous GPU-budget NSP is already active in these logs, so it does not
need reinstalling. The ZIP carries that identical NSP for fresh installations;
it still needs installing once when upgrading from an older base. Its old NRO
hash in `forwarder/build.json` records the original build, not a requirement to
use the old NRO. `launcher/streaming-memory-fix.json` records compatibility.

Expected new markers:

```
[SD-GPU-STREAM] v1 total_mib=256 large_mib=64 threshold_mib=2 borrow_guard_mib=16
[SD-DXVK-STREAM] v1 mapped > 2 MiB dedicated; no small suballocations
```

Fastest, the four compiler scratch pairs, the 1,000 MiB guest arena, existing
Wine/FEX fixes, user settings and game data are preserved. The async renderer
is unchanged and does not use the new DXVK allocation path.

`dist/sleepingdogs-fex-streaming-memory-rollback.zip` restores the previous
GPU-budget NRO and sdmem1 renderer together. Copy its entire `switch/` folder
while closed. It retains the same forwarder; no NSP rollback is needed.

## Validation and scope

- ASan/UBSan runs the production native arena helper, including full-size
  allocations, alignment, exhaustion, reuse, guarded borrowing, invalid frees,
  legacy fallback and 1,024 concurrent allocation lifetimes.
- The host DXVK test compiles the actual allocation dispatch, chunk creation
  and page allocator from old and new sources. Vulkan allocation and final
  resource destruction are modeled. It reproduces small allocations retaining
  an old 5 MiB backing, then checks isolation and 512 large-backing retirements
  across 256 cycles in the new path.
- Unicorn executes the actual ARM64 native allocator/newlib under synthetic
  pressure. The old pool fails a fragmented 5 MiB request; the new reserved
  region succeeds and recycles 64 times with CPU/GPU sentinels intact. This is
  an allocator workload, not a replay of the entire game allocation trace.
- The shipping x86 D3D11 DLL is checked for deferred Map/Update failure, cleared
  outputs, successful command ownership and preserved live commands on remap
  failure. Vulkan creation and logging boundaries are modeled.
- Packaging verifies exact source reconstruction, stripped executable sections,
  DLL imports/exports, paired receipts and cumulative payload preservation.
  Fresh install, mixed-version rejection, rollback, reinstall and the launcher
  C renderer gate are checked against the final archives.

Inputs and findings: `reports/streaming-memory-analysis.json`. Test details and
artifact hashes: `reports/streaming-*-check.json`, `reports/streaming-package.json`.
No result here establishes successful 3D gameplay on Switch.
