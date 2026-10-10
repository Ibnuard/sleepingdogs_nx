# Sleeping Dogs FEXTendo v16: scoped Wine notifications

Experimental native FPS candidate, still 1280x720. No Switch FPS gain or stable
30 FPS is claimed. This build addresses avoidable Wine wakeups; it does not
establish that those wakeups are the dominant gameplay bottleneck.

## Evidence and response to the latest test

The supplied log has SHA256
`1de314d6e7b88288db0ebb5c9c580072ace6180484dee20f16c4446be3a674c5`.
Its diagnostic capture has 410 present intervals over 29.949336 seconds,
approximately 13.69 FPS. The ten windows after capture starts total 1,460 frames
over 102.562 seconds, approximately 14.24 FPS. Those windows include time inside
the capture, so the two results must not be added or treated as independent runs.

The v15 fullscreen correction is present and the later swapchain is 1280x720,
with `extra_scale=0`. The correction worked, but the user reports no perceptible
FPS improvement. The supplied session used Stable; the user also tested
Performance with the same outcome. Changing between those profiles is therefore
not presented as a new fix.

LSFG is OFF in the supplied session. The user tested LSFG separately and reports
that it did not help. This log cannot establish what happened in that separate
ON session. v16 retains the existing LSFG integration but targets native work.

The final direct-sync counter records 162,632 broad queued-waiter notifications.
The old counter does not identify their origins or CPU cost. Presenting-thread
CPU time is not total game CPU time. Wait durations overlap across threads, and
the DXVK HUD GPU percentage is a queue-idle-based estimate, not a hardware engine
counter. The screenshots and log do not prove a single dominant CPU/GPU cause.

## What changes

Only the Wine `horizon.c` and launcher/runtime compilation units are rebuilt.
The original FEX port, DXVK 3.1.1-sdbatch2, Mesa v14.1 driver/cache identity,
geometry correction and LSFG implementation remain the v15 inputs.

Three notifications use a narrower route:

- Adding a message to an I/O completion port.
- Closing the last handle of an I/O completion port, after the existing handle
  close notification has run.
- Rearming a waitable timer.

The direct queue only accepts events, mutexes, semaphores and threads. A wait
containing a timer, file, completion port or completion-wait object uses the
legacy path in its entirety, including mixed wait-all. Those legacy waiters still
receive both shared and privately routed notifications. v16 skips the unrelated
direct-queue list walk for the three cases above.

Global notifications for user APCs, resume and termination are unchanged. Named
pipe and registry notifications are also unchanged because they may directly
change event state. The same object mutex protects registration, notification,
state inspection and counters. No timeout, signal consumption, priority, clock,
affinity or object lifetime policy changes.

## Install and compare

1. Close FEXTendo completely from HOME. Merge the update ZIP's `switch` folder
   into the SD card root. It includes the new NRO and the existing v15 runtime
   dependencies. User preferences and game/save files are not included.
2. Keep 1280x720, the same clocks, route, camera and graphics/profile settings.
   Turn LSFG OFF when comparing native FPS. Choose either Stable or Performance,
   then use that same selection for both runs. Warm the route before measuring.
3. Confirm the runtime banner says `0.1.0-v16-sync-notify`, and the log contains
   `[SD-SYNC-V16] filter=1 active=1`. Save the log before launching again.
4. For an ON/OFF comparison using this same NRO, create
   `sdmc:/switch/sleepingdogs-fex/sync-notify-filter.txt` containing `0` and a
   newline. Fully close and relaunch. This restores the previous broad path for
   the three notifications. Delete that file or set it to `1` to reenable v16.
   Missing file defaults ON; it is effective only in existing sync mode 2.
5. The rollback ZIP restores the exact delivered v15 NRO and runtime metadata.
   The optional filter file has no effect on v15.

Periodic `[SD-SYNC-V16]` counters distinguish completion posts, timer rearms and
port closes. `queued_candidates_skipped` counts the sum of active queued waiters
excluded from those list walks. It is **not** a count of actual condvar signals
saved, milliseconds saved, or additional frames. The filter is an experimental
candidate even when that counter is large.

## Verification and limits

The build recipe first reproduces the v15 ELF byte-for-byte with its original
link inputs. The Switch linker embeds the output basename, so that basename is
also preserved. Only the two intended objects are then replaced. Inputs and
staged sources are hashed before and after compilation.

The host suite extracts the actual production post-completion, set-timer,
timer-update, direct-dispatch, select, queue and router functions. Object lookup,
thread services and clocks use a host fixture. AddressSanitizer and
UndefinedBehaviorSanitizer cover ON/OFF with both legacy notification routes,
completion data and error status, port close, timer deadlines, mixed wait-all,
mode fallback, and 12,000 completion notices interleaved with 3,000 event round
trips. Existing APC, termination, mutex, semaphore, handle-close and timeout cases
also run. A source audit limits `horizon.c` changes to the three calls and checks
the pipe, registry and direct queue implementations are unchanged.

ARM64 tests execute the compiled notification/dispatch guards and check inherited
runtime behavior, the Mesa cache identity, LSFG links and NRO-to-ELF payload.
These checks cannot simulate Switch scheduling, rendering speed or in-game
loading. The package reports keep `hardware_tested=false` and
`fps_gain_measured=false`. Hardware comparison is the next evidence needed.

Sources and recipes are bundled under `source/sync-notify-v16/` alongside the
existing v15 sources and component licenses. Shared SDK and baseline build files
are not modified.
