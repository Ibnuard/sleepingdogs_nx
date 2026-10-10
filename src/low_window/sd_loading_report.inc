/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Called by the independent debug monitor, never from a rendering thread.
 * These are completed host calls. Neither an unchanged count nor a long wait
 * proves a GPU fault; correlate with SD-CALL/SD-PC and resource observations. */
static void sd_loading_report(unsigned seconds)
{
    static uint64_t previous_presents;
    uint64_t presents = __atomic_load_n(&fex_frame_ok, __ATOMIC_RELAXED);
    uint64_t errors = __atomic_load_n(&fex_frame_errors, __ATOMIC_RELAXED);
    uint64_t last = __atomic_load_n(&fex_frame_last, __ATOMIC_RELAXED);
    uint64_t now = armGetSystemTick();
    log_line("[SD-LOAD] v1 t=%us presents=%llu delta=%llu present_seen=%u age_ms=%llu present_errors=%llu",
             seconds, (unsigned long long)presents,
             (unsigned long long)(presents - previous_presents), (unsigned)(last != 0),
             (unsigned long long)(last && now >= last ? armTicksToNs(now - last) / 1000000 : 0),
             (unsigned long long)errors);
    previous_presents = presents;
    fex_pipeline_report();
}
