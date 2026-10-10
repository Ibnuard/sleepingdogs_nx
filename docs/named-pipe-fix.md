# Sleeping Dogs: local named-pipe compatibility

The Switch log from 7 October 2026 (`0ce58e3f795e39cf5a2c98cbc15d92ec5f128f77f554a1ecc4e5e9f2d6bbfb7c`)
shows seven FEX execution-breakpoint deliveries and a successful 1,000 MiB arena
allocation. The previous corrupt-stack exception is gone. The game now reaches
WinMain and calls `exit(1)` from `0x007dd270` (return address `0x007dd275`), before
the first graphics presentation.

Reading the original executable identifies the branch as failure of
`SteamAPI_Init()`, called at `0x009788ca`. Its log strings are
`Initializing SteamSDK....`, `API: Initializing....`, `failed`, and `Exiting...`.
The provided `steam_api.dll` delegates initialization to `pandora_api.dll`; the
log shows both that DLL and `pandoraclient.dll` loaded successfully. The latter
opens `\\.\pipe\pandora_master_pipe`. The old Horizon implementation has no
named-pipe creation request handler or named-pipe open implementation.

This is a concrete missing compatibility feature on the failed initialization
path. **The old log does not show the precise failing pipe syscall**, and fixing
the feature does not establish that the entire initialization will succeed.
The new `[SD-PIPE]` trace provides that evidence on the next device run.
The late query for `mscoree.dll` occurs during exit and is not treated as evidence
that the game needs a new .NET installation.

## Implementation

`src/sd_named_pipe.inc` provides local byte/message pipes inside the existing
Horizon handle registry. File objects keep the existing completion-port binding,
duplicate-handle ownership, event objects and waiter notification. It supports
multiple instances, duplex traffic, overlapped connect/read/write, event and
IOCP completion, peek, partial message reads, pipe mode/local information,
disconnect/reconnect and cancellation. Synchronous non-alertable calls wait on
the existing condition variable, releasing the object mutex.

Pending requests retain file/event references and the issuer's IOSB layout.
Completion writes information before publishing status with release semantics.
An x86 request remains an 8-byte IOSB when completed by a native thread. Closing
the last duplicate cancels pending requests; closing a peer drains buffered
data and completes remaining reads with a broken-pipe status. Reconnecting a
server does not reconnect an old client handle. Non-pipe calls retain the old
implementation.

No game EXE/DLL is patched, and no initializer is forced to return success.
The FEX DLL remains the previously tested execution-breakpoint build. Fastest,
the direct data arena, WoW64 self-context correction and renderer files remain.

The current transport does not support remote pipes, impersonation,
`FSCTL_PIPE_WAIT/TRANSCEIVE`, APC callbacks or alertable synchronous pipe I/O.
Those operations return errors instead of reporting false success. Buffered
writes allocate on demand; this implementation does not yet model Windows'
quota-based pending writes. Forced issuer-thread termination is not a new
cancellation trigger; applications must cancel/close outstanding I/O.

The implementation follows the pinned Wine `server/async.c` notification rules
and the [Microsoft overlapped pipe I/O contract](https://learn.microsoft.com/en-us/windows/win32/ipc/synchronous-and-overlapped-input-and-output).

## Validation and reproduction

Run in WSL:

```
python3 tests/check_named_pipe.py
python3 tools/build_named_pipe.py --work /home/blekjek/sleepingdogs-pipe-v1
```

The host harness includes the production pipe source and pinned Wine types and
completion queue. ASan/UBSan check connect, partial/zero-length messages, byte
streams, WoW64/native completions in both directions, duplicate close, per-thread
cancellation, reconnect isolation, IOCP notification flags, multiple instances,
allocation failure and threaded synchronous traffic. It also runs 500 connection
cycles and 200 duplex round trips. The host handle registry/TEB/scheduler are
fixtures, so this is not a full Horizon system test.

`tests/check_game_pipe_calls.py` executes the original x86 DLL functions at RVAs
`0x33f0` and `0x21770` in Unicorn. Only imported Win32 APIs and CRT memory routines
are modeled. Four cases verify the actual pipe path, flags and failure/success
returns. This does not emulate all of SteamAPI_Init or change original files.

`dist/sleepingdogs-fex-named-pipe-fix.zip` is a cumulative update over the existing
Sleeping Dogs runtime. Close the app from HOME, overwrite its `switch/` folder
on SD and select Launch Debug. The existing Sleeping Dogs 32-bit NSP is unchanged.
Look for `[SD-PIPE] local named pipes v1`, then `create`, `listen` and `open`.
If startup still fails, collect the new `fex-runtime.log` and `crash.log`.
Switch boot and gameplay remain unconfirmed until that device test.
