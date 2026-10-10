/* Runs independently of registry persistence, balancing and guest log output. */
static void *f1_startup_monitor(void *unused)
{
    extern unsigned int wine_nx_file_reads, wine_nx_sd_reads, wine_nx_sd_hits;
    extern unsigned int wine_nx_syscalls;
    extern unsigned long long wine_nx_sd_read_ns;
    extern void wine_nx_f1_thread_snapshot(unsigned);
    extern void wine_nx_fex_fast_api_totals(unsigned out[2]);
    extern void wine_nx_fex_poll_totals(unsigned out[2]);
    extern void wine_nx_f1_apc_snapshot(unsigned long long out[5]);
    extern void wine_nx_f1_resource_snapshot(const char *);
    extern void wine_nx_f1_scratch_snapshot(void);
    extern void wine_nx_f1_vkmem_snapshot(void);
    extern void wine_nx_f1_gpu_heap_snapshot(void);
    extern void wine_nx_f1_native_heap_snapshot(void);
    extern void wine_nx_f1_native_stacks_snapshot(void);
    extern void wine_nx_f1_audio_snapshot(void);
    extern void wine_nx_page_store_snapshot(uint64_t out[8]);
    static struct f1_watch_row rows[F1_WATCH_THREADS];
    uint64_t start = 0;
    unsigned last = 0, first_noted = 0;
    (void)unused;
    for (;;) {
        svcSleepThread(1000000000LL);
        if (!__atomic_load_n(&fx_debug_live, __ATOMIC_ACQUIRE)) {
            if (start) return NULL;
            continue;
        }
        uint64_t now = armGetSystemTick();
        if (!start) start = now;
        unsigned seconds = armTicksToNs(now-start) / 1000000000ULL;
        unsigned presented = __atomic_load_n(&fx_first_present, __ATOMIC_ACQUIRE);
        if (presented && !first_noted) {
            first_noted = 1;
            wine_nx_f1_crash_note("first-present-success (Vulkan returned success/suboptimal)");
            log_line("[F1-RENDER] first present returned successfully; crash.log and runtime log remain active");
        }
        if (seconds-last < (presented ? 30u : 5u)) continue;
        last = seconds;
        uint64_t exited = __atomic_load_n(&f1_guest_exit_state,__ATOMIC_ACQUIRE);
        if (exited)
            log_line("[F1-STATE] guest-exited code=%08x; circuit loading stopped; remaining audio/presents may continue", (unsigned)exited);
        wine_nx_f1_resource_snapshot(exited ? "guest-exited" : presented ? "rendering" : "startup");
        wine_nx_f1_scratch_snapshot();
        wine_nx_f1_vkmem_snapshot();
        wine_nx_f1_gpu_heap_snapshot();
        wine_nx_f1_native_heap_snapshot();
        wine_nx_f1_native_stacks_snapshot();
        wine_nx_f1_audio_snapshot();
        uint64_t pages[8];
        wine_nx_page_store_snapshot(pages);
        log_line("[F1-PAGES] recovered=%llu bytes=%llu live=%llu pieces=%llu failed=%llu rollback_failed=%llu peak=%llu released=%llu",
            (unsigned long long)pages[0], (unsigned long long)pages[1],
            (unsigned long long)pages[2], (unsigned long long)pages[3],
            (unsigned long long)pages[4], (unsigned long long)pages[5],
            (unsigned long long)pages[6], (unsigned long long)pages[7]);
        /* Handoff stops syscall sampling, not persistent error capture. */
        if (!__atomic_load_n(&f1_startup_watch_enabled,__ATOMIC_ACQUIRE)) continue;
        unsigned overflow = 0;
        int count = f1_watch_snapshot(rows, F1_WATCH_THREADS, &overflow);
        now = armGetSystemTick(); /* no negative age if a call began during the copy */
        log_line("[F1-PROGRESS] t=%us reads=%u sd_reads=%u cache_hits=%u sd_ms=%llu syscalls=%u rows=%d overflow=%u",
            seconds, __atomic_load_n(&wine_nx_file_reads,__ATOMIC_RELAXED),
            __atomic_load_n(&wine_nx_sd_reads,__ATOMIC_RELAXED),
            __atomic_load_n(&wine_nx_sd_hits,__ATOMIC_RELAXED),
            __atomic_load_n(&wine_nx_sd_read_ns,__ATOMIC_RELAXED)/1000000,
            __atomic_load_n(&wine_nx_syscalls,__ATOMIC_RELAXED), count, overflow);
        for (int i = 0; i < count; ++i) {
            const struct f1_watch_row *r = rows+i;
            log_line("[F1-CALL] tid=%u %s %s age_ms=%llu status=%08x calls=%llu/%llu a0=%llx a1=%llx a2=%llx a3=%llx a4=%llx a5=%llx a6=%llx a7=%llx",
                r->tid, f1_watch_syscall_name(r->id), r->active?"entered":"returned",
                (unsigned long long)(r->begin?armTicksToNs(now-r->begin)/1000000:0), r->status,
                (unsigned long long)r->completed,(unsigned long long)r->calls,
                (unsigned long long)r->args[0],(unsigned long long)r->args[1],
                (unsigned long long)r->args[2],(unsigned long long)r->args[3],
                (unsigned long long)r->args[4],(unsigned long long)r->args[5],
                (unsigned long long)r->args[6],(unsigned long long)r->args[7]);
            if (r->file_serial)
                log_line("[F1-FILE] tid=%u %s %s handle=%llx bytes=%u age_ms=%llu status=%08x path=%s",
                    r->tid,r->file_kind==1?"open":"read",r->file_active?"entered":"returned",
                    (unsigned long long)r->file_handle,r->file_length,
                    (unsigned long long)(armTicksToNs(now-r->file_begin)/1000000),
                    r->file_status,r->path[0]?r->path:"<untracked>");
        }
        unsigned fast[2], poll[2];
        wine_nx_fex_fast_api_totals(fast); wine_nx_fex_poll_totals(poll);
        log_line("[F1-POLL] qpc=%u delay=%u fast_qpc=%u fast_delay=%u",poll[0],poll[1],fast[0],fast[1]);
        unsigned long long apcs[5];
        wine_nx_f1_apc_snapshot(apcs);
        log_line("[F1-APC] queued=%llu delivered=%llu rejected=%llu dispatch=%llu returned=%llu",
                 apcs[0],apcs[1],apcs[2],apcs[3],apcs[4]);
        pes13_fex_report_heap();
        /* Three bounded captures before any 3D handoff: 30, 45 and 60 seconds. */
        wine_nx_f1_thread_snapshot(seconds);
    }
}
