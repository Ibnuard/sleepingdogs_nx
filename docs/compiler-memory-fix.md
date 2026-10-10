# Compiler memory fix v1

The 21:33 device logs in `dist/sleepingdogs-fex-memory-budget-fix/` confirm that
the 128 MiB GPU reserve and small-stack recovery are active. Eight stack retries
succeed. FEX then terminates on another 16 MiB compiler scratch allocation.
At that instant the general heap reports 26,395,136 bytes available, but neither
a contiguous allocation nor the existing fragmented-page fallback can satisfy
the request. The GPU reserve has reached 128 MiB earlier in this run. This is
still memory pressure; these logs do not establish a new guest exception.
The input SHA256s and exact evidence lines are in `reports/compiler-memory-analysis.json`.

Four available CPU cores do not bound concurrent compiler lifetimes. A compiler
can be preempted while owning a 16 MiB IR buffer. The existing FEX pool correctly
refuses to steal owned buffers and can then request a fifth allocation. The new
permit covers both normal and single-step compilation, before decoder setup and
before the shared code-invalidation lock. Four independent mutexes bound active
compilers to four. RAII releases the permit on cache hits and early returns.
Waiting holds no compiler buffer or invalidation lock. JIT backend internal
restart jumps remain inside the scope. No guest-thread or execution-core limit
is changed. Contention is logged at a bounded rate as `SD-COMPILER-WAIT`.
Retiring clients also publish FREE under the pool mutex. Previously an unclaimer
waiting for that mutex could expose a buffer in neither reusable list/state,
temporarily forcing pool growth. The recheck under the lock preserves a new
owner when another client wins the reclaim race.

The decoder formerly allocated 65536 entries, or 8 MiB, for every buffer even
when MaxInst is 500. It now requests the page-rounded space for its instruction
limit, capped at the same 65536-entry ceiling. Fastest therefore requests 64 KiB.
A pre-write bound also covers resumed/early-exit loop paths. Larger configured
limits still allocate larger buffers; block instruction limits and IR capacity
are unchanged. The zero-instruction dispatch-error return now releases both
decoder and IR ownership. The native reservation changes from four 8/16 MiB
pairs to four 64 KiB/16 MiB pairs, saving exactly 33,292,288 bytes (31.75 MiB).
GPU capacity, guest arena, native stack policy, debug-register/DEP handling,
renderers, original game, saves, and Fastest settings retain their previous behavior.

Validation performed:

- ASan/UBSan on the production permit and actual FEX pool/client code: old fifth
  owner fails; fifth gated compiler waits and progresses; 32 threads complete
  8000 compiler lifetimes with at most four live buffers and no failed allocation.
  A controlled retirement/reclaim race preserves the new owner without growth.
- Actual ARM64 DLL `CompileBlock`: four paused compilers hold the four permits;
  a fifth waits before acquiring the invalidation lock, resumes after release,
  and all cache-hit returns unlock. NT/mutex scheduling and lookup results modeled.
- Actual DLL decoder: 12 decode limits, five large setup limits, 64 KiB native
  callback, pause/resume, multiblock, invalid opcode, and full-capacity guards.
  Tail canaries stay intact. Original game entry and three startup worker paths
  execute through the real x86 decoder, with NT/heap/config boundaries modeled.
- Old/new NRO allocator and reserve instructions: exact 31.75 MiB saving; four
  complete workspaces remain usable with the ordinary heap exhausted; 64 recycle
  cycles preserve the other buffers. sbrk, locks, and diagnostic I/O modeled.
- Actual rebuilt DLL breakpoint emitter passes its 67-case regression; imports,
  exports, frame offsets, and disabled eager spare remain compatible.
- Both native and FEX changes reconstruct byte-for-byte from the previous
  verified sources. Cumulative ZIP and rollback payload hashes are checked.

These are host and binary checks, not a replay of the entire Switch allocation
history. The permit bounds memory but may add compile-time waiting during bursts;
device boot, performance, menu, and gameplay remain unconfirmed. Other memory
consumers can still exhaust the fixed process heap.

Install `dist/sleepingdogs-fex-compiler-memory-fix.zip` last over the base/ready
package, with the application fully closed from HOME. Copy **all** of `switch/`:
the NRO and `drive_c/windows/system32/libwow64fex.dll` must match. Use the existing
Sleeping Dogs forwarder and Launch Debug. Expect both `SD-COMPILER-MEM` markers
(`native=v1` and `fex=v1`). Rollback ZIP restores both prior runtime payloads and
their receipts. Existing logs in the tested package directory are preserved.
