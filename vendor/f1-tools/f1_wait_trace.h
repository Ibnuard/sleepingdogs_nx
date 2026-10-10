/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Opt-in select-handler observations. No changes to object state or results.
 * Timing samples include parking/preemption; they are not thread CPU time.
 * All counters are atomic for the independent, coarse report consumer.
 */
#ifndef F1_WAIT_TRACE_H
#define F1_WAIT_TRACE_H
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define F1_WAIT_ROWS 128
enum f1_wait_counter {
    FW_ENTER, FW_DONE, FW_READY, FW_PARKED, FW_SLEEPS, FW_TIMEOUT, FW_APC,
    FW_ERRORS, FW_SAMPLES, FW_LOCK_US, FW_PARK_US, FW_BODY_US, FW_COUNT
};
struct f1_wait_row { unsigned tid; uint64_t value[FW_COUNT]; };
struct f1_wait_probe {
    struct f1_wait_row *row;
    uint64_t started, locked, park_start, parked_ticks;
    unsigned sleeps, sampled;
};
extern int wine_nx_f1_wait_stats;
extern void wine_nx_runtime_trace(const char *);
static struct f1_wait_row f1_wait_rows[F1_WAIT_ROWS];
static uint64_t f1_wait_overflow;
static void f1_wait_add(struct f1_wait_row *row, unsigned field, uint64_t n)
{ __atomic_add_fetch(&row->value[field], n, __ATOMIC_RELAXED); }

static void f1_wait_begin(struct f1_wait_probe *p, unsigned tid)
{
    static __thread struct f1_wait_row *cached;
    static __thread unsigned sequence;
    p->row = NULL;
    if (!wine_nx_f1_wait_stats || !tid) return;
    if (!cached || __atomic_load_n(&cached->tid, __ATOMIC_RELAXED) != tid) {
        cached = NULL;
        for (unsigned i=0; i<F1_WAIT_ROWS; ++i) {
            unsigned found = __atomic_load_n(&f1_wait_rows[i].tid, __ATOMIC_RELAXED);
            if (found == tid || (!found && __atomic_compare_exchange_n(
                    &f1_wait_rows[i].tid, &found, tid, 0, __ATOMIC_RELAXED, __ATOMIC_RELAXED))) {
                cached = &f1_wait_rows[i]; break;
            }
        }
        if (!cached) { __atomic_add_fetch(&f1_wait_overflow,1,__ATOMIC_RELAXED); return; }
    }
    p->row = cached; p->sleeps = 0; p->parked_ticks = 0;
    p->sampled = !(++sequence & 63);
    p->started = p->sampled ? armGetSystemTick() : 0;
    f1_wait_add(p->row,FW_ENTER,1);
}
static void f1_wait_locked(struct f1_wait_probe *p)
{ if (p->row && p->sampled) p->locked = armGetSystemTick(); }
static void f1_wait_before_park(struct f1_wait_probe *p)
{
    if (!p->row) return;
    ++p->sleeps;
    if (p->sampled) p->park_start = armGetSystemTick();
}
static void f1_wait_after_park(struct f1_wait_probe *p)
{ if (p->row && p->sampled) p->parked_ticks += armGetSystemTick()-p->park_start; }
static void f1_wait_end(struct f1_wait_probe *p, unsigned status)
{
    if (!p->row) return;
    if (p->sampled) {
        uint64_t body = armGetSystemTick()-p->locked;
        f1_wait_add(p->row,FW_LOCK_US,armTicksToNs(p->locked-p->started)/1000);
        f1_wait_add(p->row,FW_PARK_US,armTicksToNs(p->parked_ticks)/1000);
        f1_wait_add(p->row,FW_BODY_US,armTicksToNs(body-p->parked_ticks)/1000);
        f1_wait_add(p->row,FW_SAMPLES,1);
    }
    if (p->sleeps) { f1_wait_add(p->row,FW_PARKED,1); f1_wait_add(p->row,FW_SLEEPS,p->sleeps); }
    else if (status < 0xc0) f1_wait_add(p->row,FW_READY,1); /* normal or abandoned */
    if (status == 0x102) f1_wait_add(p->row,FW_TIMEOUT,1);
    else if (status == 0xc0) f1_wait_add(p->row,FW_APC,1);
    else if (status & 0x80000000u) f1_wait_add(p->row,FW_ERRORS,1);
    f1_wait_add(p->row,FW_DONE,1);
}

/* Existing monitor only. A single consumer; per-field snapshots are not a
 * transaction. Long waits contribute timing in their completion window. */
void wine_nx_f1_wait_report(void)
{
    static uint64_t previous[F1_WAIT_ROWS][FW_COUNT], previous_overflow;
    if (!wine_nx_f1_wait_stats) return;
    char line[640];
    for (unsigned i=0; i<F1_WAIT_ROWS; ++i) {
        struct f1_wait_row *r = &f1_wait_rows[i];
        unsigned tid = __atomic_load_n(&r->tid,__ATOMIC_RELAXED);
        if (!tid) continue;
        uint64_t d[FW_COUNT], n[FW_COUNT];
        for (unsigned j=0; j<FW_COUNT; ++j) {
            n[j]=__atomic_load_n(&r->value[j],__ATOMIC_RELAXED);
            d[j]=n[j]-previous[i][j];previous[i][j]=n[j];
        }
        if (!d[FW_ENTER] && !d[FW_DONE]) continue;
        snprintf(line,sizeof(line),
            "[F1-WAIT] tid=%u entered=%llu done=%llu ready=%llu parked=%llu sleeps=%llu timeout=%llu apc=%llu errors=%llu samples=%llu lock_us=%llu park_us=%llu body_us=%llu",
            tid,(unsigned long long)d[FW_ENTER],(unsigned long long)d[FW_DONE],
            (unsigned long long)d[FW_READY],(unsigned long long)d[FW_PARKED],
            (unsigned long long)d[FW_SLEEPS],(unsigned long long)d[FW_TIMEOUT],
            (unsigned long long)d[FW_APC],(unsigned long long)d[FW_ERRORS],
            (unsigned long long)d[FW_SAMPLES],(unsigned long long)d[FW_LOCK_US],
            (unsigned long long)d[FW_PARK_US],(unsigned long long)d[FW_BODY_US]);
        wine_nx_runtime_trace(line);
    }
    uint64_t overflow=__atomic_load_n(&f1_wait_overflow,__ATOMIC_RELAXED);
    if (overflow != previous_overflow) {
        snprintf(line,sizeof(line),"[F1-WAIT] overflow=%llu",(unsigned long long)(overflow-previous_overflow));
        wine_nx_runtime_trace(line);previous_overflow=overflow;
    }
}
#endif
