/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <stdio.h>
#include "sd_low_window.h"
#include "sd_guest_arena.h"
#include "f1_native_stacks.h"

extern void wine_nx_runtime_trace(const char *);

/* Both the launcher and guest-test path call this before admitting any guest.
 * Each resource initializer owns its once-only state, so a launcher retry
 * cannot allocate a second arena or repeat the probes over an existing alias.
 * Run on the main thread after Debug has opened the current session's log.
 */
int sd_launch_memory_prepare(char *error, size_t error_size)
{
    char line[160];
    wine_nx_runtime_trace("[SD-INIT] v2 preparing memory before launch validation");
    wine_nx_f1_native_stacks_init();
    sd_low_window_init();
    if (!sd_low_window_ready()) {
        snprintf(error, error_size,
            "Low-window memory check failed. See [SD-LOWVA] in fex-runtime.log.");
        return 0;
    }
    sd_guest_arena_init();
    if (!sd_guest_arena_base()) {
        snprintf(error, error_size,
            "Cannot map the Sleeping Dogs data arena. See [SD-ALIAS] in fex-runtime.log.");
        return 0;
    }
    snprintf(line, sizeof(line), "[SD-INIT] v2 ready probe=1 arena=%zu", sd_guest_arena_size());
    wine_nx_runtime_trace(line);
    return 1;
}
