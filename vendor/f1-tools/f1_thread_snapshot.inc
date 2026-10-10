/* Startup-only sampling, independent of the presentation counter. No logging,
 * allocation or blocking mutex acquisition while a target is paused. */
struct f1_thread_sample {
    struct fex_stall_capture native;
    uint64_t cpu_ticks;
    uint32_t eip, esp, ebp, x86[8];
    unsigned x86_count;
    char kind;
};

static void f1_snapshot_guest(uint64_t teb, struct f1_thread_sample *out)
{
    uint64_t area = 0;
    if (!teb || teb > UINT64_MAX-NX_PROF_TEB_CPU_AREA ||
        !fex_stall_read(teb+NX_PROF_TEB_CPU_AREA, &area, sizeof(area)) ||
        !area || area > UINT64_MAX-0x100) return;
    uint64_t context = area+NX_PROF_CPU_CONTEXT;
    /* WOW64_CONTEXT offsets, checked against winnt.h by the host test. This
     * is the last exported guest context; it is not an exact live guest PC. */
    if (!fex_stall_read(context+0xb8, &out->eip, 4) ||
        !fex_stall_read(context+NX_PROF_I386_ESP, &out->esp, 4) ||
        !fex_stall_read(context+NX_PROF_I386_EBP, &out->ebp, 4)) return;
    uint32_t frame = out->ebp;
    for (unsigned i = 0; i < 8; ++i) {
        uint32_t words[2];
        if (frame < out->esp || (uint64_t)frame-out->esp > 16*1024*1024 ||
            !fex_stall_read(frame, words, sizeof(words))) break;
        out->x86[out->x86_count++] = words[1];
        if (words[0] <= frame) break;
        frame = words[0];
    }
}

static int f1_snapshot_due(unsigned seconds, unsigned *captures, unsigned *last)
{
    if (seconds < 30 || *captures >= 3 || (*captures && seconds-*last < 15)) return 0;
    ++*captures; *last = seconds;
    return 1;
}

void wine_nx_f1_thread_snapshot(unsigned seconds)
{
    static unsigned captures, last;
    static struct f1_thread_sample samples[NX_PROF_MAX_THREADS*2];
    struct nx_prof_thread live[NX_PROF_MAX_THREADS];
    unsigned n = 0;
    char line[1024];
    if (!f1_snapshot_due(seconds, &captures, &last)) return;
    if (!envIsSyscallHinted(0x32) || !envIsSyscallHinted(0x33)) {
        wine_nx_runtime_trace("[F1-THREAD] pause/context SVC unavailable; use F1-CALL observations");
        return;
    }
    memset(samples, 0, sizeof(samples));
    for (unsigned round = 0; round < 2; ++round) {
        /* Try, never wait for a possibly stalled registry owner. profile_mutex
         * keeps registered native handles alive until all targets are resumed. */
        if (pthread_mutex_trylock(&registry_mutex)) {
            wine_nx_runtime_trace("[F1-THREAD] registry busy; snapshot skipped"); return;
        }
        if (pthread_mutex_trylock(&profile_mutex)) {
            pthread_mutex_unlock(&registry_mutex);
            wine_nx_runtime_trace("[F1-THREAD] profiler busy; snapshot skipped"); return;
        }
        memcpy(live, registry, sizeof(live));
        pthread_mutex_unlock(&registry_mutex);
        for (unsigned i = 0; i < NX_PROF_MAX_THREADS; ++i) {
            if (!live[i].handle) continue;
            struct f1_thread_sample *s = &samples[n++];
            struct fex_stall_capture *out = &s->native;
            ThreadContext ctx;
            s->kind = live[i].kind;
            s->cpu_ticks = thread_ticks(live[i].handle);
            out->tid = live[i].tid; out->round = round;
            out->pause = svcSetThreadActivity(live[i].handle, ThreadActivity_Paused);
            if (R_FAILED(out->pause)) continue;
            out->read = svcGetThreadContext3(&ctx, live[i].handle);
            if (R_SUCCEEDED(out->read)) {
                out->pc = ctx.pc.x; out->lr = ctx.lr;
                out->state = ctx.cpu_gprs[28].x;
                out->caller_count = walk_callers(&ctx, out->callers);
                void *alias = pes13_fex_native_host()->write_alias((void *)(uintptr_t)out->pc, 4);
                out->is_jit = alias && alias != (void *)(uintptr_t)out->pc;
                if (out->is_jit && out->state <= UINT64_MAX-PES13_FEX_FRAME_RIP_OFFSET) {
                    uint32_t offset;
                    struct pes13_fex_observed_tail tail;
                    out->state_valid = fex_stall_read(out->state+PES13_FEX_FRAME_BLOCK_OFFSET,&out->block,8) &&
                        fex_stall_read(out->state+PES13_FEX_FRAME_RIP_OFFSET,&out->last_rip,8);
                    if (out->state_valid && fex_stall_read(out->block,&offset,4) &&
                        offset < 16*1024*1024 && out->block <= UINT64_MAX-offset &&
                        fex_stall_read(out->block+offset,&tail,sizeof(tail)) &&
                        tail.size <= 16*1024*1024 && tail.size >= offset+sizeof(tail) &&
                        out->pc >= out->block && out->pc-out->block < tail.size) out->guest_block = tail.rip;
                }
                /* Server rows can reference a client TEB. Only inspect the
                 * guest context while its owning Wine thread is paused. */
                if (live[i].kind == 'w') f1_snapshot_guest(live[i].teb, s);
            }
            out->resume = svcSetThreadActivity(live[i].handle, ThreadActivity_Runnable);
            if (R_FAILED(out->resume)) out->resume = svcSetThreadActivity(live[i].handle, ThreadActivity_Runnable);
        }
        pthread_mutex_unlock(&profile_mutex);
        if (!round) svcSleepThread(2000000);
    }
    snprintf(line,sizeof(line),"[F1-THREAD] capture=%u t=%us samples=%u observer=%llx; saved guest context/block labels, not exact live PCs",
        captures,seconds,n,(unsigned long long)(uintptr_t)&wine_nx_f1_thread_snapshot);
    wine_nx_runtime_trace(line);
    for (unsigned i = 0; i < n; ++i) {
        const struct f1_thread_sample *s = samples+i;
        const struct fex_stall_capture *r = &s->native;
        snprintf(line,sizeof(line),"[F1-PC] tid=%u%c round=%u pause=%x read=%x resume=%x cpu_ticks=%llu pc=%llx lr=%llx jit=%u block=%llx rip=%llx saved_eip=%x esp=%x ebp=%x",
            r->tid,s->kind,r->round,r->pause,r->read,r->resume,(unsigned long long)s->cpu_ticks,
            (unsigned long long)r->pc,(unsigned long long)r->lr,r->is_jit,
            (unsigned long long)r->guest_block,(unsigned long long)r->last_rip,s->eip,s->esp,s->ebp);
        wine_nx_runtime_trace(line);
        int len = snprintf(line,sizeof(line),"[F1-STACK] tid=%u%c round=%u native=",r->tid,s->kind,r->round);
        for (unsigned j = 0; j < r->caller_count; ++j)
            len += snprintf(line+len,sizeof(line)-len," %llx",(unsigned long long)r->callers[j]);
        len += snprintf(line+len,sizeof(line)-len," guest=");
        for (unsigned j = 0; j < s->x86_count; ++j)
            len += snprintf(line+len,sizeof(line)-len," %x",s->x86[j]);
        wine_nx_runtime_trace(line);
    }
}
