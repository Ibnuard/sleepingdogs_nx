/* Diagnostic build only. One consumer on the existing startup monitor.
 * These reports read existing counters; the context sampler stays disabled.
 * Driver call wall times include waiting and are not GPU execution times. */
#ifndef F1_PERF_OBSERVER_H
#define F1_PERF_OBSERVER_H
static void f1_perf_observer(uint64_t now)
{
    extern void wine_nx_thread_report(void);
    extern unsigned int wine_nx_file_reads, wine_nx_sd_reads, wine_nx_sd_hits;
    extern unsigned int wine_nx_syscalls;
    extern unsigned long long wine_nx_sd_read_ns;
    extern void wine_nx_fex_fast_api_totals(unsigned out[2]);
    extern void wine_nx_fex_poll_totals(unsigned out[2]);
    static uint64_t last;
    static unsigned report;
    uint64_t elapsed = last && now >= last ? armTicksToNs(now-last) / 1000000 : 0;
    if (last && elapsed < 10000) return;
    uint64_t begin = armGetSystemTick();
    log_line("[F1-PERF] report=%u phase=%s tick=%llu window_ms=%llu sampler=off",
             report, last ? "sample" : "baseline", (unsigned long long)now,
             (unsigned long long)elapsed);
    last = now;
    /* The first thread report primes CPU tick baselines. The first SERVER
     * report includes startup; later SERVER reports cover successive windows. */
    wine_nx_thread_report();
    fex_pipeline_report();
    fex_warm_report();
    unsigned fast[2], poll[2];
    wine_nx_fex_fast_api_totals(fast);
    wine_nx_fex_poll_totals(poll);
    log_line("[F1-PERF-COUNTERS] reads=%u sd_reads=%u cache_hits=%u sd_ms=%llu syscalls=%u qpc=%u delay=%u fast_qpc=%u fast_delay=%u; cumulative",
             __atomic_load_n(&wine_nx_file_reads,__ATOMIC_RELAXED),
             __atomic_load_n(&wine_nx_sd_reads,__ATOMIC_RELAXED),
             __atomic_load_n(&wine_nx_sd_hits,__ATOMIC_RELAXED),
             __atomic_load_n(&wine_nx_sd_read_ns,__ATOMIC_RELAXED) / 1000000,
             __atomic_load_n(&wine_nx_syscalls,__ATOMIC_RELAXED),
             poll[0],poll[1],fast[0],fast[1]);
    log_line("[F1-PERF] report=%u observer_us=%llu; includes report I/O, excludes this final line",
             report++, (unsigned long long)(armTicksToNs(armGetSystemTick()-begin) / 1000));
}
#endif
