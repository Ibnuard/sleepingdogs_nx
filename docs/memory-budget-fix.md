# Native memory headroom

The 21:11 `SS/08` run is different from the preceding native PC-zero fault.
`[SD-THREAD-DEBUG] build=v1` is present, multiple new threads receive DR0–DR3,
and execution passes the former tid 76 worker to audio/other workers through
tid 108. The fatal native exception section is blank. The runtime ends with
`STOP compiler scratch failed bytes=0x1000000` after thread creation failures
`c0000017` / libnx `0x559` / ENOMEM. The free-thread count remains 197–199.

The general heap capacity is 2,002,944,000 bytes. Around the failed creation,
only 27–31 MB is free in that heap, with no unclaimed tail. The most recent
GPU snapshot holds 268,435,456 bytes but uses only 112,525,312; its unused
reservation is 155,910,144 bytes (148.7 MiB). That is an earlier snapshot,
not an exact reconstruction of GPU usage at the final failure. The compiler
has consumed four protected 8/16 MiB workspace pairs and requests another
16 MiB buffer. Its existing allocation/page recovery cannot satisfy it.

The private Sleeping Dogs overlay now preallocates 128 MiB for GPU backing
instead of 256 MiB. The ordinary GPU allocator and free routing are unchanged;
128 MiB is not a limit on total GPU allocations. This leaves 128 MiB more
available for ordinary CPU allocations at equivalent live GPU demand within
the reservation. The game's 1000 MiB data arena, FEX workspace sizes, JIT,
Fastest, game files and PE DLLs are unchanged.

The log also shows four 1 MiB workers recovering from the protected 16-slot
stack pool, followed by failed 128 KiB Wine server threads. The old retry
accepted only exactly 1 MiB. It now accepts nonzero, page-aligned requests
through 1 MiB and lends a whole idle slot. The same padded backing is passed
to libnx: the stack is never undersized, TLS/reent space remains intact,
and live slots, failed-unmap quarantine and caller-owned stacks are unchanged.

If compiler scratch still cannot be allocated, the runtime now snapshots
general heap, GPU and stack state at that exact failure before returning NULL.
It does not invent a successful allocation or hide the error.

Validation includes ASan/UBSan on production code: all 256 supported sizes,
2,000 mixed 128 KiB/1 MiB stack lifetime cycles, 1,024 concurrent GPU allocation
cycles, close/rollback/quarantine faults and invalid inputs. ARM64 replay runs
the linked newlib/GPU allocators and stack wrapper from both release ELFs.
A synthetic fragmented heap uses the recorded capacity and GPU demand; the
new FEX allocation succeeds and GPU growth beyond 128 MiB remains possible.
This is not a reproduction of the complete hardware allocation history.
Switch boot, menu and gameplay still require hardware testing.

Close the title from HOME and install all of `switch/` from
`sleepingdogs-fex-memory-budget-fix.zip` last over the existing package.
Use the same forwarder and Launch Debug. Expected marker:
`[SD-MEMORY-BUDGET] build=v1 gpu_reserve_mib=128`.
Collect both fresh logs if it fails. The rollback ZIP restores thread-debug v1.
