/* SPDX-License-Identifier: LGPL-2.1-or-later
 * F1 notification index. Caller holds the existing server object mutex for
 * every operation, including registration immediately before atomic sleep.
 * Object state, wait consumption, timeouts and APCs stay in the old server.
 * Keys are opaque identities, never dereferenced or retained as references.
 */
#ifndef F1_INDEXED_WAIT_H
#define F1_INDEXED_WAIT_H

#define F1_WAIT_BUCKETS 256u
struct f1_waiter;
struct f1_wait_link {
    struct f1_wait_link *next, **pprev;
    struct f1_waiter *waiter;
    const void *key;
};
struct f1_waiter {
    struct f1_waiter *next, **pprev;
    const struct pes27_interest *interest;
    void *condition;
    unsigned links_used;
    struct f1_wait_link links[PES27_MAX_HANDLES];
};
struct f1_wait_router {
    struct f1_waiter *head;
    struct f1_wait_link *buckets[F1_WAIT_BUCKETS], *broad;
    struct pes27_router stats; /* same logical counters as the legacy scan */
    uint64_t active, visited, resolved, rebuilds;
    int dirty;
};

static inline unsigned f1_wait_bucket(const void *key)
{
    uintptr_t n = (uintptr_t)key >> 4;
    n ^= n >> 9; n ^= n >> 17;
    return (unsigned)n & (F1_WAIT_BUCKETS - 1);
}
static inline void f1_wait_link(struct f1_wait_router *r, struct f1_waiter *w,
                                const void *key)
{
    struct f1_wait_link *link = &w->links[w->links_used++];
    struct f1_wait_link **head = key ? &r->buckets[f1_wait_bucket(key)] : &r->broad;
    link->key = key; link->waiter = w;
    link->next = *head; link->pprev = head;
    if (*head) (*head)->pprev = &link->next;
    *head = link;
}
static inline void f1_wait_unlink(struct f1_waiter *w)
{
    for (unsigned i = 0; i < w->links_used; ++i) {
        struct f1_wait_link *link = &w->links[i];
        *link->pprev = link->next;
        if (link->next) link->next->pprev = link->pprev;
    }
    w->links_used = 0;
}
static inline void f1_wait_index(struct f1_wait_router *r, struct f1_waiter *w,
                                pes27_resolve_fn resolve)
{
    const struct pes27_interest *in = w->interest;
    w->links_used = 0;
    if (!in || in->broad) { f1_wait_link(r, w, NULL); return; }
    for (unsigned i = 0; i < in->count; ++i) {
        const void *key = resolve(in->handles[i], in->thread);
        ++r->resolved;
        if (!key) {
            /* One unresolved dependency makes the entire interest broad,
             * matching pes27_interested, including closed handles. */
            f1_wait_unlink(w); f1_wait_link(r, w, NULL); return;
        }
        unsigned j;
        for (j = 0; j < w->links_used; ++j) if (w->links[j].key == key) break;
        if (j == w->links_used) f1_wait_link(r, w, key);
    }
}
static inline void f1_wait_handles_changed(struct f1_wait_router *r)
{
    /* Called on BOTH handle insertion and removal under the same lock.
     * No stale identity may filter a notification after close/reuse/alias. */
    r->dirty = 1;
}
static inline void f1_wait_refresh(struct f1_wait_router *r, pes27_resolve_fn resolve)
{
    if (!r->dirty) return;
    memset(r->buckets, 0, sizeof(r->buckets)); r->broad = NULL;
    for (struct f1_waiter *w = r->head; w; w = w->next) f1_wait_index(r, w, resolve);
    r->dirty = 0; ++r->rebuilds;
}
static inline void f1_wait_register(struct f1_wait_router *r, struct f1_waiter *w,
                                   pes27_resolve_fn resolve)
{
    f1_wait_refresh(r, resolve);
    w->next = r->head; w->pprev = &r->head;
    if (r->head) r->head->pprev = &w->next;
    r->head = w;
    f1_wait_index(r, w, resolve);
    ++r->active; ++r->stats.sleeps;
}
static inline void f1_wait_unregister(struct f1_wait_router *r, struct f1_waiter *w)
{
    f1_wait_unlink(w);
    *w->pprev = w->next;
    if (w->next) w->next->pprev = w->pprev;
    w->next = NULL; w->pprev = NULL; --r->active;
}
static inline void f1_wait_notify(struct f1_wait_router *r, const void *changed,
                                 pes27_resolve_fn resolve, pes27_wake_fn wake)
{
    uint64_t n = 0;
    f1_wait_refresh(r, resolve);
    ++r->stats.notices; r->stats.candidates += r->active;
    if (!changed) {
        ++r->stats.broad_notices;
        for (struct f1_waiter *w = r->head; w; w = w->next) {
            ++r->visited; ++n; if (wake) wake(w->condition);
        }
    } else {
        for (struct f1_wait_link *link = r->buckets[f1_wait_bucket(changed)];
             link; link = link->next) {
            ++r->visited;
            if (link->key != changed) continue;
            ++n; if (wake) wake(link->waiter->condition);
        }
        for (struct f1_wait_link *link = r->broad; link; link = link->next) {
            ++r->visited; ++n; if (wake) wake(link->waiter->condition);
        }
    }
    r->stats.notified += n; r->stats.filtered += r->active - n;
}
#endif
