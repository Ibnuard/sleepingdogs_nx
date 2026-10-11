# Sleeping Dogs: debug-register loss after the first frames

> Experiment record. Setup steps and validation statements below describe
> this specific build when it was prepared. For current guidance, see
> [Installation](INSTALL.md), [Current status](STATUS.md), and
> [Development history](HISTORY.md).

The latest hardware log is Sleeping Dogs even though it was saved under
`pes13-nx/dist/pes13-as39-bias-bench-v1/`. Its SHA256 is
`9cd2dc8a9d649e486517bc859f8d1570a6f6f0c6df77a9220c874f17d61f4286`.
The DEP notification and earlier execution-breakpoint support are active.

## Evidence and cause

The log first arms DR0–DR3 at `004c0a8a`, `005b2e92`, `0061ce88`, and
`0068d35a`. Numerous `80000004` events and four presents follow. While creating
the Havok worker, the main thread raises the conventional thread-name exception
`406d1388`. Its context already has DR0–DR3, DR6 and DR7 all zero. The subsequent
access violation has `EIP=003a4f82`, a zero SEH handler, and erased stack words.
The renderer continues presenting while the main thread recurses into null SEH.

The context-group mask in `horizon_transfer_i386_context` is correct. The defect
is a missing mirror of debug state into **Wine's x86 private TEB cache**. Shipped
guest `ntdll.dll!RtlRaiseException` calls `raise_exception_full_context`, which
reads six debug fields at TEB32 offsets `0x1dc..0x1f0`, adds the DEBUG_REGISTERS
flag, and submits them to `NtRaiseException`. Native SetContext previously
updated only the WoW64 CPU area. Thus the valid breakpoints are overwritten with
stale cached zeros by an ordinary software exception.

The original game site at `00b2373b` calls DR0, expecting its normal #DB handler.
The handler at `00b74470` returns to `00b2374f` with EAX zero. Without that event,
a nonzero result takes the branch at `00b23753` that clears stack/SEH words and
returns through the leftover pointer `003a4f78`. The next ten bytes of heap
execution match the logged `003a4f82` fault. The negative replay supplies the
nonzero checker result; it does not emulate the checker's entire body.

## Change

After a successful native self-thread context update that requests debug
registers, mirror the accepted canonical fields to the current guest TEB.
The helper checks its layout against the pinned Wine ABI. Partial contexts,
failed updates, unsupported XSTATE, and remote threads do not modify the cache.
An explicitly requested clear still clears the cache and CPU registers.
No breakpoint address or game-specific return value is forced by the fix.

The standard source-preparation path includes the fix. The new build is isolated
at `/home/blekjek/sleepingdogs-debug-cache-v1`. Guest DLLs, FEX, DEP policy,
named pipes, direct arena and Fastest settings are retained from the cumulative
DEP package. The original game executable and companion DLLs are unchanged.

Diagnostics v3 skip thread-name exceptions as well as ordinary debug events,
so the persistent first snapshot can capture an actual fault. Repetitive Wine
SEH backtrace warnings are limited to 128 lines; other warnings and errors remain.

## Validation and limits

- Native ARM64 build succeeds. Actual old/new ELF SetContext instructions and
  the shipped x86 RtlRaiseException run in Unicorn. Old binary: six zeros. New
  binary: all six registers retained. The unchanged game call site and VEH then
  preserve the stack and reach `00b2376d`.
- All 64 context-group combinations plus 12 edge cases pass, including explicit
  disable, source/destination alias, absent guest TEB, errors and two other
  software exception codes. Eight prior original-game handler cases still pass.
- ASan/UBSan passes with actual Wine types, 10,000 cache updates, second-thread
  isolation and byte guards around all unowned TEB fields. Six diagnostic groups
  pass, including 2,000 ignored debug/thread-name events and log limits.
- Packaging reconstructs the modified compilation units from the earlier source
  layers and checks byte equality, payload preservation and ZIP checksums.

The Unicorn boundary substitutes native TLS/CPU lookup, logging and memory-copy
helpers; it does not boot Wine, render a game, or reproduce Switch scheduling.
Menu and gameplay must still be tested on hardware.

## Install

Close FEXTendo from HOME. Copy **all of `switch/`** from
`dist/sleepingdogs-fex-debug-cache-fix.zip` over the SD card, **after** the base
package/ready folder and earlier patches. Use the same forwarder; no NSP
reinstall. Launch Debug and look for `[SD-TEB-DEBUG] build=v1` and
`[SD-TEB-DEBUG] sync`. Fastest remains selected.

If the next run fails, collect both `fex-runtime.log` and `crash.log` from
`switch/sleepingdogs-fex/`. The optional
`dist/sleepingdogs-fex-debug-cache-rollback.zip` restores the preceding DEP
runtime and receipts.

Build: `python3 tools/build_debug_cache.py --work <fresh-directory>` under the
existing WSL/devkitPro environment. Test with `tests/check_debug_cache.py`,
`tests/check_debug_cache_binary.py` and `tests/check_fault_trace.py`; package
with `tools/package_debug_cache.py`. Source-bound receipts are in `reports/`.
