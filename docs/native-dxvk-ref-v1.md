# Native DXVK Ref v1: remove temporary reference round trips

[Documentation](README.md) · [Current status](STATUS.md)

This candidate keeps the installed **H4 v9 NRO, FEX context v1 and 720p**.
It replaces the PE32 COM proxy and its self-test. The ready-copy directory
is `dist/sd-native-dxvk-ref-v1-update/`, without a ZIP. Its game performance
has **not** been measured on Switch; crowded 20+ FPS and stable 30 FPS are
targets, not demonstrated results.

## Evidence and change

The [latest capture](../reports/fex-context-v1-gameplay-observation.json)
confirms FEX context v1, native DXVK and Light 720p. The user reports a slight
improvement, normal views at 20–23 FPS, crowded views still around 16 and a
30 FPS peak only with a narrow view. The final five complete Present windows
pool to 20.56 FPS, versus 20.59 in the previous capture. Scenes and clocks
are not authenticated as matched A/B; the separately supplied COM runtime
is still byte-identical to an old v3 file.

The old proxy sends **every `AddRef` and `Release`** through FEX's full
context boundary, Wine's Unix dispatcher, the native COM gate and DXVK.
The new proxy counts temporary references locally:

- Native Create/Get/QueryInterface outputs contribute a local reference and
  one owned native reference, called a credit. Outputs retain their existing
  identity, generation checks, rollback and publication behavior.
- `AddRef` atomically increases the local count. It makes no native call.
- `Release` reconciles local references and credits under the existing guest
  proxy lock. It releases one native reference only if the remaining credits
  would exceed the remaining local owners. The final release unlinks the
  proxy and consumes its last native credit.
- A native release occurs **after dropping the guest lock**, with its token
  saved independently of the freed proxy. This avoids holding a guest lock
  behind a native `Multithread::Enter` owner. Concurrent output publication
  and final release remain serialized in the guest.

At rest, a live proxy has `1 <= native credits <= local references`. Native
outputs and explicit local references can be released in any order. A
pending native Release still owns its detached credit until it completes.
Native bindings, Map ownership, QueryInterface and object destruction retain
their native references; commands are not queued or skipped. All 47 interface
kinds use the same reference helpers. The extra proxy storage is four bytes.

This follows COM's per-interface lifetime rules; a proxy need not forward
every local reference operation to the object. See Microsoft's
[reference-counting rules](https://learn.microsoft.com/en-us/windows/win32/com/implementing-reference-counting)
and [proxy AddRef explanation](https://devblogs.microsoft.com/oldnewthing/20231228-00/?p=109198).
Reducing crossings addresses work around Wine/FEX as well as DXVK, but the
current capture does not establish what fraction of gameplay calls are
temporary references.

## Build and validation

The [builder](../tools/build_native_dxvk_refs.py) reproduces the delivered v9
proxy byte-for-byte from commit `407b3201a6ec7ee1596d600601c30119f36880f6`
before compiling the candidate with the same pinned toolchain. ABI 4 and
the native NRO stay unchanged. The candidate adds `SdComRefStats`, a guest-only
diagnostic export; it introduces no native protocol extension.

The [PE32 tests](../tools/test_native_dxvk_refs.py) execute the same guest
source snapshot compiled into the candidate. They cover 100,000 exact
reference pairs, mixed native/local ownership, eight-thread reference/output
churn, a blocked final native release concurrent with publication, and zero
references at teardown. Existing output, identity, Map and endpoint fixtures
also run against this snapshot. The native endpoint in these Windows tests
is modeled: they do not execute FEX or the Switch native renderer.

All six fixture variants pass. The reference workload makes 840,043 native
calls with the original proxy and 320,029 with the candidate: **520,014
crossings avoided**, with all native and guest references balanced. The
other candidate fixtures verify 16,000 simultaneous proxy identities, output
rollback, preserving Map copies, allocation-failure cleanup and 12-thread
endpoint discovery. See the [source-bound test receipt](../reports/native-dxvk-ref-v1-test.json).

The delivered COM client adds a separate **hardware** check: 2,048 balanced
reference pairs must cause zero native reference calls (4,096 avoided
crossings). A mixed-owner survivor must remain usable, all prior draw/readback
checks still run, and teardown must leave zero live interfaces/maps. This
hardware test still needs to be run. Local call-count savings are not an FPS
estimate or a measured game workload.

## Install, measure and restore

1. Close the application completely from HOME. Copy the main `switch/` to
   the SD root. Both proxy copies are supplied: the active game DLL and the
   launcher's native renderer DLL. Otherwise renderer selection could restore
   the old proxy. The NRO still identifies itself as h4.9.
2. Run the COM self-test. Save its result and guest log before starting the
   game. Require `PASS`, `reference_optimization: native-dxvk-ref-v1`,
   `reference_pairs: 2048`, `reference_crossings_saved: 4096`, zero live
   interfaces/maps and zero bridge failures.
3. Copy `start-game-light/switch/` after PASS. Use Native ARM64, Performance,
   Light 720p and FPS HUD. Compare the same warmed crowded view/route at fixed
   clocks; the earlier reference is CPU 1728 / GPU 768 / RAM 1600 MHz.
4. Save `fex-runtime.log`, `native-dxvk-h4/HKShip.exe_d3d11.log` and the new
   **`drive_c/native-dxvk-ref-v1.log`**, relative to `switch/sleepingdogs-fex/`.
   Include `native-dxvk-h4/runtime.log` only with its session context.

The new log contains cumulative local AddRefs, local Releases, native
Releases and adopted output references. It writes a short buffered line at
the first successful non-test Present, every 600 Presents, and when the COM
client requests statistics. It performs no per-frame flush or clock query.
Snapshots across active threads are approximate, and 32-bit counters can
wrap. `local_addrefs + local_releases` counts avoided native calls; it does
not measure saved milliseconds. For a frame interval use counter deltas.

For rollback or A/B, close HOME and copy **only** `ref-baseline/switch/`.
It restores the exact old v9 proxy and COM client while keeping FEX and
graphics settings. `ref-local/switch/` re-enables the candidate. Both overlays
disable automatic COM mode. Old log files may remain after rollback; check
the session and timestamp. Existing v9 and FEX delivery folders are preserved.
