# Suspended thread debug context

Input: `SS/08/fex-runtime.log` and `SS/08/crash.log`. The TEB cache v1 build
is active; debug registers arm on the main thread only. The last created guest
thread is tid 76, entry `0x549430`. Its native fault is PC zero, LR
`0xd41bc1a0`, inside the FEX dispatcher allocation. This identifies the native
failure boundary, not a complete guest stack trace.

The original game's CreateThread hook at `0xb74630` forces CREATE_SUSPENDED,
calls its context helper at `0xb74550` on the returned handle, then resumes
unless the caller requested suspension. That helper gets/sets only
CONTEXT_I386_DEBUG_REGISTERS. The previous native implementation returned
STATUS_NOT_IMPLEMENTED for every non-pseudo thread handle. FEX debug state is
per-thread, so setting the main thread's registers does not arm this worker.

The original worker's `0x5494f2` path calls DR1 target `0x5b2e92` with
ECX `0xe081`; the crash also contains this value. Without an execution
breakpoint, the target returns nonzero and the original worker erases its
stack before returning. With debug delivery, the original VEH handles the
exception and the worker reaches `0x54951c` with the stack intact. Instruction
replays validate this path; hardware boot is still unconfirmed.

The native repair stages six requested debug registers in the thread object,
under the same mutex used by the start gate, including when the child has not
yet published its TEB. It accepts only debug-only contexts for suspended,
never-started threads in the calling process. Running, terminated and invalid
targets fail without a context write. No suspend count is consumed. After
runtime initialization clears and seeds the CPU area, the child consumes the
pending values once and updates the Wine x86 TEB cache before entering WoW64.
Explicit clearing is honored. Registers are not implicitly inherited.

Validation: ASan/UBSan with real Wine ABI and 1000 concurrent start cycles;
actual ARM64 native context functions/handle lookup/startup; original x86
CreateThread hook, worker target, worker branch and VEH. CPU emulation uses
controlled OS boundaries and does not reproduce the Switch scheduler/GPU.
The package preserves previous PE DLLs, memory policy, named pipes and Fastest.

Install all of `switch/` from `sleepingdogs-fex-thread-debug-fix.zip` last over
the existing base package after closing the title from HOME. Use the existing
forwarder and Launch Debug. Expected markers are `[SD-THREAD-DEBUG] build=v1`
and `apply tid=...`, followed by per-thread FEX `[SD-DB] arm` lines.
If it still fails, collect both fresh logs from the same run.
