/* SPDX-License-Identifier: LGPL-2.1-or-later. Explicit, per-launch diagnostics. */
#pragma once

static int sd_production_debug;
int wine_nx_sd_diagnostics_active(void) {
    return __atomic_load_n(&sd_production_debug, __ATOMIC_ACQUIRE);
}
static void sd_production_select_debug(int debug) {
    __atomic_store_n(&sd_production_debug, !!debug, __ATOMIC_RELEASE);
}
