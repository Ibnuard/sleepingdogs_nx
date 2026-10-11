# DXVK memory fix v1

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

The 22:07 device log on 7 October confirms the compiler-memory pair is active.
The user now reaches the Sleeping Dogs logo / transition toward the menu.
There is no compiler-scratch STOP. Vulkan allocations of 8 MiB and then 5 MiB
fail. DXVK reports 231 MiB allocated and 182 MiB used, with the shared native
heap showing 40,118,160 bytes available but no sufficiently large contiguous
range. Those aggregate figures do not reveal the entire allocation history.

The first guest fault is `d3d11.dll+0x73556`, a read of `[ebx+0x28]` with EBX=0.
COFF symbols and instruction replay identify `D3D11DeferredContext::MapBuffer`:
the allocation returned no slice, and the old function dereferenced it. This is
a later failure than the previous compiler-memory exhaustion. Input hashes are
in `reports/dxvk-memory-analysis.json`; original logs are preserved separately.

The new `3.1.1-sdmem1` renderer keeps the pinned f1mem2 allocator and reduces its
ordinary chunk cap to 2 MiB. Both initial and subsequent chunk sizes respect the
cap. Larger resources still receive at least their full required size, rounded
to 64 KiB pages. A 5 MiB discard buffer can therefore use a 5 MiB backing chunk
from its first allocation, instead of first taking 8 MiB and retaining a 3 MiB
tail. Small resources continue sharing chunks. Memory properties, page ownership,
mapping and GPU synchronization are unchanged. This can increase Vulkan allocation
count; device performance and the total memory saved still need hardware testing.

Deferred MapBuffer now returns `E_OUTOFMEMORY` with zeroed output on allocation
failure, without adding a command or map-cache entry. Its void update helper
checks that failure before copying. This prevents the observed null dereference;
it cannot make an exhausted allocation succeed, and a game can still terminate
after an OOM result. The allocator change aims to reduce that pressure earlier.

Checks performed:

- ASan/UBSan compiles the actual old/new chunk function and DXVK page/pool
  allocator. Resource bounds, page rounding through 32 MiB, failed allocations,
  release and reuse pass. A synthetic 80 MiB backing budget admits ten old versus
  sixteen new live 5 MiB slices. This is not a replay of all device allocations.
- The actual deferred Map/update source reproduces the old null failure and
  passes new OOM, successful map, queued ownership, NO_OVERWRITE and invalid-mode
  cases under sanitizers.
- Real x86 DLL instructions reproduce the exact old `0x73556`/`0x28` fault.
  The new stripped shipping DLL returns the correct HRESULT on four sizes,
  protects the failed-update path, preserves existing commands after a failed
  remap, and records a successful map with the correct retained references.
  Resource creation and diagnostic formatting are modeled at their boundaries.
- All three DLL import/export interfaces match the previous renderer. The three
  changed sources reconstruct from the pinned base. Only debug sections are
  stripped; COFF symbols remain for crash analysis.
- A fresh complete install checks both renderer sets, dependencies and matching
  receipts. Mixed DLL sets must fail verification. Renderer rollback restores
  f1mem2 while retaining the compiler and native fixes.

Install `dist/sleepingdogs-fex-dxvk-memory-fix.zip` **last** over the existing
package, with the application fully closed from HOME. Copy all of `switch/`,
including both the active game-directory DXVK DLLs and the launcher renderer
copies. Choose **DXVK 3.1.1**, then **Launch Debug**. The log should contain
`[SD-DXVK-MEM] v1 pool cap=2 MiB`. Fastest and all previous runtime fixes remain.
The cumulative update contains no original game files, saves, logs or user
settings. The existing Sleeping Dogs forwarder is sufficient.

`dist/sleepingdogs-fex-dxvk-memory-rollback.zip` restores the prior renderer in
both locations. Successful menu/gameplay on Switch is not yet confirmed.
