/* SPDX-License-Identifier: LGPL-2.1-or-later
 * One consumer on the startup monitor. Reuse counters already collected by
 * v7 and kernel thread ticks; do not add sampling or rendering-thread work.
 * The existing Debug report owns the shared report baselines in Debug mode.
 */
#ifndef SD_PERF_SUMMARY_H
#define SD_PERF_SUMMARY_H
static int sd_perf_counters;

static void sd_perf_summary(uint64_t now, int debug)
{
    extern void wine_nx_thread_report(void);
    extern unsigned int wine_nx_file_reads, wine_nx_sd_reads, wine_nx_sd_hits;
    extern unsigned int wine_nx_syscalls;
    extern unsigned long long wine_nx_sd_read_ns;
    extern void wine_nx_fex_fast_api_totals(unsigned out[2]);
    extern void wine_nx_fex_poll_totals(unsigned out[2]);
    static uint64_t last, previous_sd_ns;
    static unsigned report, previous[8];
    if (!sd_perf_counters || debug) return;
    int sample = last && now >= last;
    uint64_t elapsed_us = sample ? armTicksToNs(now-last) / 1000 : 0;
    if (sample && elapsed_us < 10000000) return;
    uint64_t begin = armGetSystemTick();
    unsigned current[8], fast[2], poll[2], delta[8];
    wine_nx_fex_fast_api_totals(fast);
    wine_nx_fex_poll_totals(poll);
    current[0] = __atomic_load_n(&wine_nx_file_reads, __ATOMIC_RELAXED);
    current[1] = __atomic_load_n(&wine_nx_sd_reads, __ATOMIC_RELAXED);
    current[2] = __atomic_load_n(&wine_nx_sd_hits, __ATOMIC_RELAXED);
    current[3] = __atomic_load_n(&wine_nx_syscalls, __ATOMIC_RELAXED);
    current[4] = poll[0]; current[5] = poll[1];
    current[6] = fast[0]; current[7] = fast[1];
    uint64_t sd_ns = __atomic_load_n(&wine_nx_sd_read_ns, __ATOMIC_RELAXED);
    for (unsigned i = 0; i < 8; ++i) {
        delta[i] = sample ? current[i] - previous[i] : 0;
        previous[i] = current[i];
    }
    uint64_t delta_sd_ns = sample ? sd_ns-previous_sd_ns : 0;
    previous_sd_ns = sd_ns;
    last = now;
    log_line("[SD-PERF] report=%u phase=%s tick=%llu window_ms=%llu observation=existing-counters",
             report, sample ? "sample" : "baseline", (unsigned long long)now,
             (unsigned long long)(elapsed_us / 1000));
    /* Baseline reports from these helpers may include startup. The first
     * thread report primes tick baselines. Interpret only later windows.
     * Driver/server wall times can overlap and are not GPU execution times. */
    wine_nx_thread_report();
    fex_pipeline_report();
    fex_warm_report();
    fex_sync_report();
    log_line("[SD-PERF-IO] reads=%u sd_reads=%u cache_hits=%u sd_ms=%llu syscalls=%u qpc=%u delay=%u fast_qpc=%u fast_delay=%u; interval",
             delta[0], delta[1], delta[2], (unsigned long long)(delta_sd_ns / 1000000),
             delta[3], delta[4], delta[5], delta[6], delta[7]);
    log_line("[SD-PERF] report=%u observer_us=%llu; includes report I/O, excludes this final line",
             report++, (unsigned long long)(armTicksToNs(armGetSystemTick()-begin) / 1000));
}
#endif
