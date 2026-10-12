# Native DXVK H4 v9: bridge probes, Map traffic and submission batching

V9 implements the three immediate candidates identified in the
[v8.1 Light capture](../reports/native-dxvk-h4-v8.1-light-observation.json),
keeping 1280×720. The reference session was reported at 20–22 FPS, crowded
lows near 16 and confined-view peaks near 30; its final five Present windows
pool to 20.67 FPS. V9 has passed local checks, but its Switch FPS is unmeasured.

## Runtime changes

**One read/write probe per writable range.** The pinned Wine write helper
performs volatile read-modify-write probes at each page and the two endpoints,
inside its exception handler. The bridge now calls it directly, retaining
null/count behavior, lower-address and 32-bit end-address limits, overflow
checks and E_POINTER propagation. It does not cache permissions or remove the
native gate. Read-only inputs keep their read probe. This removes the separate
readability pass on every packet and writable output.

**No repeated zero-fill for WRITE_DISCARD.** The existing bounded shadow cache
still owns guest-addressable allocations. BindMap validates the entire range;
preserving modes still copy native data in, while DISCARD leaves initial bytes
undefined. Unmap still copies the complete writable range back. This follows
the [D3D11 DISCARD contract](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/ne-d3d11-d3d11_map).
It does not make the bridge zero-copy or reduce the observed full copy-out of
9 MiB per frame. Applications must initialize data they consume after DISCARD.
Periodic `[SD-NDX-MAP]` records count discarded mappings and skipped zero-fill
bytes; these are work counters, not measured time savings.

**Native Performance enables bounded submission batching.** The existing
24-chunk DXVK tracker was already linked but disabled by native profiles.
Performance now sets `d3d11.sdSubmissionBatching = True`; other native profiles
explicitly set False. The option is also on in the COM self-test. The policy
only defers automatic hints while at least two submissions are unfinished,
below 24 chunks and the existing cost cap. Mandatory flush and readback
progress paths retain their behavior. Both x86 renderer profiles are unchanged.

This does not batch x86 COM commands across calls. Such marshalling requires
owning pointer payloads and references, preserving inter-thread order, and
draining at synchronous methods. Direct native Map pointers also require a
32-bit-addressable allocator path. Neither is substituted for correct ordering
or copying in this candidate.

## Validation

- [Memory probes](../reports/native-dxvk-h4-v9-memory-probes.json): 233,256
  checks with actual bridge range methods and the pinned Wine probe bodies,
  including 27 page-protection layouts, inaccessible/read-only/unmapped pages,
  crossing page boundaries, overflow and concurrent fault recovery. For
  100,000 valid packet probes, v8.1 invokes 100,000 read and 100,000 write probes;
  v9 invokes zero separate reads and 100,000 write probes. POSIX signal recovery
  replaces Wine SEH in this host test; it does not validate Horizon exceptions.
- [Native DXVK/lavapipe](../reports/native-dxvk-h4-v9-host-test.json): 7,387,186
  checks, both 720p pixel readbacks, preservation modes, three repeated partial
  DISCARD GPU readbacks, reference/error paths and 63 matched startup trace
  pairs. This uses modeled Wine permissions and does not execute FEX.
- [PE32 Map checks](../reports/native-dxvk-h4-v9-guest-maps.json): actual guest
  wrappers on Windows, including overlapping/concurrent mappings, partial
  writes, cache limits and failure cleanup. The modeled 4+5 MiB cycle keeps
  two allocations in both v8.1 and v9; it measures the zero-fill change
  separately from v7's old allocation behavior. Host timings are not Switch FPS.
- [Batch tracker](../reports/native-dxvk-h4-v9-native-batch.json): the exact
  native tracker bodies pass 31,488 decision cases and 200,000 stateful
  comparisons, including the disabled-mode control, readback progress,
  chunk/cost bounds and submission-ID wraparound under ASan/UBSan.
- Existing PE32 transport, output, identity, inline-array, ABI, logging,
  window, XML persistence, launcher and import checks pass. Packaging requires
  17 source-bound build/test receipts, the endpoint audit and matching hashes.

The real PE32 COM client now checks eight native packet-protection cases and
183 bytes from repeated partial DISCARD readbacks. The former explicitly
exercises Wine/Horizon exception recovery on the device; the host fixture
cannot replace that result. Rejected packets fail before a COM operation is
counted, preserving the zero unexpected bridge-failures condition.

## Install and compare

Folder: `dist/sd-dxvk-native-h4-v9-update/`, without a ZIP.

1. Close from HOME and copy the main `switch/` folder to the SD root, using the
   established full-memory forwarder. Run COM first and retain its files.
   Require build `native-dxvk-h4-v9`, PASS, exit 00000000,
   `memory_guard_checks=8`, `discard_partial_bytes_verified=183`, 72 sampler
   slots and 16 DSV guards. Stop the game comparison if this check fails.
2. Copy `start-game-light/switch/`, then select GUI, Native ARM64, Performance,
   FPS HUD and Light 720p. LSFG remains off for native. Use the same clocks,
   warmed save, camera and crowded route as the v8.1 reference.
3. Compare `batch-off/switch/` and `batch-on/switch/`, fully closing from HOME
   between runs and selecting Performance again. They differ in one native
   Performance option; the bridge and Map optimizations remain active in both.
   The effective renderer log must show `[SD-DXVK-BATCH] v2 enabled=0` or `1`.
4. Keep each game's `fex-runtime.log` and
   `native-dxvk-h4/HKShip.exe_d3d11.log`; add a new crash log if relevant. Record
   ordinary/crowded FPS, pause/resume and normal exit, not only peak FPS.

Main `switch/` starts in COM mode. `start-game/switch/` selects current game
detail without reapplying Light; `start-com-test/switch/` re-enters COM.
`rollback-v8.1/switch/` restores the verified prior NRO, DLLs and all launcher
profiles and selects native Light gameplay. `rollback-v18/switch/` restores
the prior x86 route and disables applying Light. Use Restore original first
if the initial XML quality is desired. No game data, save or UserOptions.dat
is included or modified by these overlays.

`memory_probe=single-readwrite discard_zero_fill=off` identifies the new path.
Async logs may lose their tail after a forced restart. Present windows can
include menus/loading; counts do not attribute CPU/GPU/wait time. Stable 30 FPS,
sustained lifetime and production readiness still require hardware validation.

## Rebuild

Use the prepared inputs in [Building](BUILD.md). Alongside the existing H4
suite, run `tools/test_native_dxvk_h4_memory.py` and
`tools/test_native_dxvk_h4_batch.py` under WSL. Windows Python runs the PE32
guest tests. Package with `tools/package_native_dxvk_h4.py` only after the
build and all matching receipts pass. Preserve the v8.1 folder: the packager
verifies it as the source of the native rollback.

## Subsequent game capture

The [preserved v9 observation](../reports/native-dxvk-h4-v9-gameplay-observation.json)
confirms native ARM64 rendering, Light 1280×720, the memory changes and
batching ON. The user reports no meaningful FPS improvement. The last five
complete Present windows pool to 20.59 FPS, compared with 20.67 FPS for v8.1;
these are not authenticated same-scene/clock A/B runs. Deferred batching
hints and 55.30 GB of avoided zero-fill establish activity, not saved time.

The supplied COM runtime is byte-identical to the older v3 file, so it does
not validate a fresh v9 COM pass. The next [FEX context candidate](fex-context-v1.md)
investigates recurring guest/native context work while retaining this v9
NRO, DXVK and graphics configuration.
