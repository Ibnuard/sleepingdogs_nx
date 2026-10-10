# GPU backing budget after START (2026-10-07)

The user confirms the sdmem1 build reaches the main menu and crashes after
START. The new logs are in `reports/gpu-budget-input/`; their original location
was `pes13-fex39/dist/pes13-fex39-0.5.0-SD/`, but the runtime identifies itself
as Sleeping Dogs. No PES project is changed.

## Evidence

- DXVK allocated/used falls from 231/182 MiB to 196/182 MiB with sdmem1.
- A 5,242,880-byte GPU allocation still fails. General heap availability is
  58,191,296 bytes at the failure snapshot, but its usable aligned candidates
  are below 1 MiB. The 128 MiB GPU pool also has no 5 MiB contiguous run (its
  later snapshot reports 6,029,312 free, largest 3,145,728).
- The deferred Map guard now logs the failure and returns E_OUTOFMEMORY. The
  game proceeds to `HKShip.exe` EIP `0x00e5897a`, `rep movsd`, destination
  `0x40`. The first fault is in game memcpy, rather than the old DXVK Map
  dereference. The next exception at `0x0071d2ab` is secondary.
- Process quota is 2 GiB. Reported used stays 2,043,723,776 bytes, leaving
  103,759,872 bytes outside the existing heap. The pinned loader's
  `calculateMaxHeapSize` explicitly subtracts 96 MiB after its 2 MiB allowance
  and alignment. This is separate from the fragmented free space in newlib.

## Change

The loader keeps a 32 MiB reserve instead of 96 MiB when quota is at least
2 GiB. Its existing allowance and rounding remain, adding exactly 64 MiB to
the kernel heap in that environment. Smaller quotas keep the previous policy.
The process memory limit, title ID, permissions, 32-bit address space, mapping
lifetime and NRO load/return mechanics remain unchanged.

The NRO preallocates up to 256 MiB of ordinary GPU heap rather than 128 MiB,
only with the exact versioned loader contract and at least 1952 MiB of usable
heap. The observed GPU live footprint is approximately 207 MiB, so this keeps
more scene allocations inside a pool that coalesces on release instead of
interleaving them with CPU allocations. Allocation failure still follows the
existing bounded halving/fallback path. The larger reservation is a hypothesis
for the observed scene; it cannot guarantee later scenes will fit.

An old/absent/malformed loader tag or insufficient heap retains 128 MiB.
The actual choice and reservation are logged as:

```
[SD-GPU-BUDGET] v1 paired_loader=1 heap=... target_mib=256 reserved_mib=256
```

No allocator ownership, NvMap lifetime, alignment, guest allocation size,
compiler workspace or game data is changed. FEX Fastest and four compiler
slots remain. FEX/Wine/DXVK DLLs in the cumulative update are byte-identical
to sdmem1. GPU memory is ordinary heap backing, never a CPU alias.

## Install

Close the application from HOME. Copy the entire `switch/` directory from
`dist/sleepingdogs-fex-gpu-budget-fix.zip` to the SD root last, and **reinstall
the `forwarder/FEXTendo-SleepingDogs-32bit.nsp` included in this update**.
Select DXVK 3.1.1 and Launch Debug. A `paired_loader=0` log means the larger
budget was not enabled. No game/save deletion is needed.

The rollback ZIP restores the preceding native NRO and includes the old NSP;
copy its `switch/` and reinstall its forwarder. Updated DXVK and FEX remain.

## Validation and limits

- ASan/UBSan executes the actual loader calculation, validates smaller quotas
  and partial updates, and checks the production GPU arena with 1024 concurrent
  allocation/free cycles and live data sentinels.
- Unicorn executes the old/new native ARM64 allocator instructions. A
  synthetic fragmented heap reproduces a rejected 5 MiB allocation with
  more than 48 MiB free; the paired allocation succeeds while four full IR
  buffers, four decoders and a 1000 MiB game allocation remain live. The test
  accounts for the changed native NRO footprint and checks pool reuse.
- Both actual forwarder ARM64 binaries run to `svcSetHeapSize` with modeled
  process information. Tests compare the exact requested sizes and retained
  quota, including low-memory hosts.
- The packer verifies the compiled NSO, NPDM, metadata and target bytes inside
  the NSP. A fresh base-plus-update installation validates all dependencies,
  receipts, unchanged preferences, mixed NRO rejection, rollback and reinstall.

These tests model kernel information and cannot execute real Horizon GPU/NvMap
operations. This is not a replay of every allocation from the game. The
updated Switch boot, START transition and gameplay still require hardware
validation; send both fresh logs if they fail.
