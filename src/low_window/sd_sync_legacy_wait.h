/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Wait routing only. The existing server owns object state and wait semantics.
 * All functions run with the server object mutex held, including registration
 * immediately before the atomic condvar wait/unlock. No allocation or I/O.
 */
#ifndef PES13_PERF27_WAIT_H
#define PES13_PERF27_WAIT_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define PES27_MAX_HANDLES 64
struct pes27_interest {
    unsigned int handles[PES27_MAX_HANDLES], count;
    int broad;
    const void *thread;
};
struct pes27_waiter {
    struct pes27_waiter *next;
    const struct pes27_interest *interest;
    void *condition;
};
struct pes27_router {
    struct pes27_waiter *head;
    uint64_t notices, broad_notices, candidates, notified, filtered, sleeps;
};
typedef const void *(*pes27_resolve_fn)(unsigned int, const void *);
typedef void (*pes27_wake_fn)(void *);

/* Parse the checked Horizon select wire layout. Invalid/unknown operations
 * conservatively keep broad wakeups; validation remains with select_status.
 * Handles are resolved when signaling, under the same mutex, so duplicate
 * handles match object identity and a closed handle is rechecked promptly.
 */
static inline void pes27_decode(struct pes27_interest *out, const void *data,
    unsigned int bytes, unsigned int size, unsigned int apc_bytes,
    int wait_op, int wait_all_op, int signal_wait_op, const void *thread)
{
    const unsigned char *p = data;
    int op;
    memset(out, 0, sizeof(*out)); out->broad = 1; out->thread = thread;
    if (!p || size < 4 || bytes < size) return;
    if (bytes - size >= apc_bytes) p += apc_bytes;
    memcpy(&op, p, sizeof(op));
    if (op == wait_op || op == wait_all_op) {
        unsigned int count = (size - 4) / 4;
        if (!count || count > PES27_MAX_HANDLES || (size - 4) % 4) return;
        memcpy(out->handles, p + 4, count * 4); out->count = count;
    } else if (op == signal_wait_op) {
        if (size < 12) return;
        memcpy(out->handles, p + 4, 4); out->count = 1;
    } else return;
    out->broad = 0;
}
static inline int pes27_interested(const struct pes27_interest *in,
                                  const void *changed, pes27_resolve_fn resolve)
{
    if (!changed || !in || in->broad) return 1;
    for (unsigned int i = 0; i < in->count; ++i) {
        const void *obj = resolve(in->handles[i], in->thread);
        if (!obj || obj == changed) return 1;
    }
    return 0;
}
static inline void pes27_register(struct pes27_router *r, struct pes27_waiter *w)
{
    w->next = r->head; r->head = w; ++r->sleeps;
}
static inline void pes27_unregister(struct pes27_router *r, struct pes27_waiter *w)
{
    struct pes27_waiter **p = &r->head;
    while (*p && *p != w) p = &(*p)->next;
    if (*p) *p = w->next;
    w->next = NULL;
}
static inline void pes27_notify(struct pes27_router *r, const void *changed,
    int targeted, pes27_resolve_fn resolve, pes27_wake_fn wake)
{
    ++r->notices;
    if (!changed) ++r->broad_notices;
    for (struct pes27_waiter *w = r->head; w; w = w->next) {
        ++r->candidates;
        if (!targeted || pes27_interested(w->interest, changed, resolve)) {
            ++r->notified;
            if (wake) wake(w->condition);
        } else ++r->filtered;
    }
}
#endif
