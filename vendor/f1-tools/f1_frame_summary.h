/* One observer on the existing monitor thread; no new work in Present. */
#ifndef F1_FRAME_SUMMARY_H
#define F1_FRAME_SUMMARY_H
static void f1_frame_summary(uint64_t now) {
    static uint64_t last, frames, errors, total_us, lock_us, driver_us;
    uint64_t elapsed_us = last ? armTicksToNs(now - last) / 1000 : 0;
    if (last && elapsed_us < 10000000) return;
    uint64_t next_frames = __atomic_load_n(&fex_frame_ok, __ATOMIC_RELAXED);
    uint64_t next_errors = __atomic_load_n(&fex_frame_errors, __ATOMIC_RELAXED);
    uint64_t next_total = __atomic_load_n(&fex_frame_stats[1].sum_us, __ATOMIC_RELAXED);
    uint64_t next_lock = __atomic_load_n(&fex_frame_stats[2].sum_us, __ATOMIC_RELAXED);
    uint64_t next_driver = __atomic_load_n(&fex_frame_stats[3].sum_us, __ATOMIC_RELAXED);
    uint64_t count = next_frames - frames;
    if (last && elapsed_us) {
        log_line("[F1-FRAME] window_ms=%llu frames=%llu fps_x100=%llu present_avg_us=%llu lock_avg_us=%llu driver_avg_us=%llu errors=%llu",
            (unsigned long long)(elapsed_us / 1000), (unsigned long long)count,
            (unsigned long long)(count * 100000000ULL / elapsed_us),
            (unsigned long long)(count ? (next_total - total_us) / count : 0),
            (unsigned long long)(count ? (next_lock - lock_us) / count : 0),
            (unsigned long long)(count ? (next_driver - driver_us) / count : 0),
            (unsigned long long)(next_errors - errors));
    }
    last = now; frames = next_frames; errors = next_errors;
    total_us = next_total; lock_us = next_lock; driver_us = next_driver;
}
#endif
