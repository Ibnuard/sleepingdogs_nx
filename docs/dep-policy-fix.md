# Sleeping Dogs: guest execute-policy notification

The device log from the named-pipe build reaches four Vulkan presents. Present
2 returns SUBOPTIMAL and the renderer recreates its swapchain; present 3 and 4
return success. The main thread then repeatedly raises access violations.

Evidence from `dist/sleepingdogs-fex-named-pipe-fix/fex-runtime.log`:

- Wine logs `disabling no-exec because of L"HKShip.exe"`. The original EXE has
  DLL characteristics `0x8000`, without NX_COMPAT (`0x100`).
- FEX dispatcher slot 0 begins at `0xfad01000`; the fault occurs at
  `0xfad012d4`, with reconstructed guest EIP `0x003a4f78`, ESP `0x0166f674`.
- The next route is a software re-raise through the saved `BTCpuSimulate`
  context (`0xff685890`). That address is an `add` instruction, not evidence
  of a second physical fault at that instruction. Later reconstructed EIPs
  are zero, with shrinking guest stacks.
- The first four detailed snapshots had already been consumed by normal
  single-step exceptions; the heap bytes and original caller are unavailable.

The pinned FEX DLL exports `BTCpuNotifyProcessExecuteFlagsChange`. Its existing
implementation maintains guest executable ranges, invalidates old translations
when DEP changes, and tracks writable promoted pages for self-modifying code.
The previous WoW64 DLL neither looked up nor called that export. Its
`wow64_NtSetInformationProcess(ProcessExecuteFlags)` only called native Wine.
This leaves FEX and Wine with different execute policies, consistent with the
heap execution fault. The contents and intended purpose of the heap address
are still unknown; device retesting is required to confirm this fixes the crash.

The bridge now loads the optional export, synchronizes accepted policy after
CPU initialization, and notifies after successful changes for the current
process, including a real handle to self. It queries the effective policy from
Wine rather than forcing flags. A lock orders simultaneous guest updates.
Native API errors are preserved; rejected changes, failed queries, remote
process handles and backends without the export never receive a notification.
No host Windows security settings are changed. Policy semantics reference:
[Microsoft SetProcessDEPPolicy](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setprocessdeppolicy).

The native NRO's diagnostic recorder now reserves its four snapshots for
non-debug exceptions and captures up to 64 readable bytes at guest EIP. Reads
remain permission checked and cannot cross a memory-region boundary. The first
snapshot persists in the existing final 4 KiB of `crash.log`. Wine errors and
warnings remain visible after bounded trace counters fill. Exception handling
and guest contexts are unchanged by this diagnostic code.

Validation:

- Actual bridge C, ASan/UBSan: initialization, both policy directions, real
  self and remote handles, errors, missing backend; 4,000 concurrent updates.
- Actual new WoW64 ARM64 DLL under Unicorn: 14 policy cases plus all 9
  self-context regression cases. The old binary reproduces policy desync.
  Export ABI and dependent DLL names are unchanged. NT APIs are modeled.
- Actual unchanged FEX ARM64 DLL under Unicorn: the logged heap address is
  initially denied, promoted with SMC tracking for accepted DEP-disable, and
  denied again after re-enable. Read-only promotion, no-access/reserved-page
  exclusion, original RX preservation, and invalidation are checked. Memory
  queries, locks and code-cache invalidation endpoints are modeled.
- Fault recorder, ASan/UBSan: 2,000 debug exceptions before a real fault,
  guarded instruction reads, stack/SEH capture, bounded persistence and error
  handling, context/errno preservation.
- Clean native and WoW64 cross-builds, source reconstruction, cumulative ZIP
  checksums and complete runtime package validation.

Builds use `/home/blekjek/sleepingdogs-dep-v1/{native,wow64}`. Reproduce with
`tools/build_dep_fix.py --component native` and `--component wow64` under WSL;
run tests and `tools/package_dep_fix.py` afterwards. The previous source and
binary artifacts remain available. Ordinary launcher builds also include the
bridge through `wow64_context_fix.py`.

Install `dist/sleepingdogs-fex-dep-policy-fix.zip` last, overwriting the complete
`switch/` tree onto the SD root while the application is closed. The cumulative
patch retains named pipes, FEX debug registers, the direct data arena, both
renderer runtimes and self-context support. Fastest and existing settings are
preserved. No game EXE/DLL, save, registry hive or NSP is included.
Choose Launch Debug and check `[SD-DEP] change flags=00000002 backend notified`.
If another failure occurs, collect both `fex-runtime.log` and `crash.log`.
The rollback ZIP restores the tested named-pipe NRO and prior WoW64 DLL.

Build and host checks do not establish Switch boot/menu/gameplay success.
