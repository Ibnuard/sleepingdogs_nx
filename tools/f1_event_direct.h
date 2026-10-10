/* LGPL-2.1-or-later. In-process SET/RESET, using the server's object state.
 * The generated f1_event_operation() above is the original event handler's
 * locked state transition. It is shared with the pipe handler. No handle
 * cache, private event state, alternate wait loop, or ownership is introduced. */
#ifndef F1_EVENT_DIRECT_H
#define F1_EVENT_DIRECT_H
extern int wine_nx_f1_direct_events;
static uint64_t f1_event_counters[6]; /* set, reset, unchanged, errors, samples, sampled_us */

unsigned int horizon_f1_event_direct(unsigned int handle, int op, int *previous)
{
    static __thread unsigned sample_sequence;
    int prior = 0;
    unsigned int status;
    /* Pulse keeps the existing server path. */
    if (op != HORIZON_SET_EVENT && op != HORIZON_RESET_EVENT)
        return HORIZON_STATUS_NOT_IMPLEMENTED;
    const int sampled = !(++sample_sequence & 255);
    uint64_t begin = sampled ? armGetSystemTick() : 0;
    status = f1_event_operation(handle, op, &prior);
    if (!status && previous) *previous = prior;
    __atomic_add_fetch(&f1_event_counters[op == HORIZON_SET_EVENT ? 0 : 1],1,__ATOMIC_RELAXED);
    if (status) __atomic_add_fetch(&f1_event_counters[3],1,__ATOMIC_RELAXED);
    else if (!!prior == (op == HORIZON_SET_EVENT))
        __atomic_add_fetch(&f1_event_counters[2],1,__ATOMIC_RELAXED);
    if (sampled) {
        uint64_t elapsed = armTicksToNs(armGetSystemTick()-begin)/1000;
        __atomic_add_fetch(&f1_event_counters[4],1,__ATOMIC_RELAXED);
        __atomic_add_fetch(&f1_event_counters[5],elapsed,__ATOMIC_RELAXED);
    }
    return status;
}

void wine_nx_f1_event_snapshot(uint64_t out[6])
{
    for (unsigned i=0;i<6;i++) out[i]=__atomic_load_n(&f1_event_counters[i],__ATOMIC_RELAXED);
}
#endif
