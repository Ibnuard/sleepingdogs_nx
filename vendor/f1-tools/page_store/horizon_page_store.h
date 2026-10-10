/* Page-aligned Wine backing storage, with a fragmented-heap fallback.
 * The caller maps each piece into one contiguous guest address range. No
 * additional resident arena, page copying on access, or guest ABI changes.
 */
#ifndef PES13_HORIZON_PAGE_STORE_H
#define PES13_HORIZON_PAGE_STORE_H
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define HORIZON_STORE_PAGE ((size_t)4096)
#define HORIZON_STORE_CHUNK ((size_t)1024 * 1024)
#define HORIZON_STORE_MAX_PIECES 4096u
struct horizon_store_piece {
    struct horizon_store_piece *next;
    void *data;
    size_t size;
};
struct horizon_page_store {
    void *data; /* Original fast path; NULL when pieces provide storage. */
    size_t size;
    struct horizon_store_piece *pieces;
    unsigned poisoned; /* An OS rollback failed: retain pages and reservations. */
};
typedef void *(*horizon_store_alloc_fn)(size_t);
typedef void (*horizon_store_free_fn)(void *, size_t);
typedef int (*horizon_store_op)(void *, void *, size_t, void *);

/* Relaxed, independent counters. The observer never takes allocator locks. */
static uint64_t horizon_store_stats[8];
enum { HS_RECOVERED, HS_RECOVERED_BYTES, HS_LIVE_BYTES, HS_PIECES,
       HS_FAILED, HS_ROLLBACK_FAILED, HS_PEAK_BYTES, HS_RELEASED };
static inline void horizon_store_add(unsigned id, uint64_t n) {
    __atomic_fetch_add(&horizon_store_stats[id], n, __ATOMIC_RELAXED);
}
static inline void horizon_store_peak(uint64_t n) {
    uint64_t prev = __atomic_load_n(&horizon_store_stats[HS_PEAK_BYTES], __ATOMIC_RELAXED);
    while (prev < n && !__atomic_compare_exchange_n(&horizon_store_stats[HS_PEAK_BYTES],
           &prev, n, 0, __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {}
}
static inline void horizon_store_dispose(struct horizon_page_store *s, horizon_store_free_fn release) {
    struct horizon_store_piece *p = s->pieces;
    if (s->poisoned) return;
    if (s->data) release(s->data, s->size);
    while (p) {
        struct horizon_store_piece *next = p->next;
        release(p->data, p->size);
        free(p);
        p = next;
    }
    memset(s, 0, sizeof(*s));
}
static inline int horizon_store_alloc(struct horizon_page_store *s, size_t size,
                                      horizon_store_alloc_fn allocate, horizon_store_free_fn release) {
    struct horizon_store_piece **tail;
    size_t left = size, ceiling = HORIZON_STORE_CHUNK;
    unsigned count = 0;
    int saved_errno = errno;
    memset(s, 0, sizeof(*s));
    if (!size || size % HORIZON_STORE_PAGE) { errno = EINVAL; return -1; }
    s->size = size;
    if ((s->data = allocate(size))) {
        memset(s->data, 0, size);
        return 0;
    }
    tail = &s->pieces;
    while (left && count < HORIZON_STORE_MAX_PIECES) {
        size_t n = left < ceiling ? left : ceiling;
        struct horizon_store_piece *p = calloc(1, sizeof(*p));
        if (!p) break;
        while (!(p->data = allocate(n))) {
            if (n == HORIZON_STORE_PAGE) break;
            n = ((n / 2) / HORIZON_STORE_PAGE) * HORIZON_STORE_PAGE;
            if (!n) n = HORIZON_STORE_PAGE;
            ceiling = n;
        }
        if (!p->data) { free(p); break; }
        p->size = n;
        memset(p->data, 0, n);
        *tail = p; tail = &p->next;
        left -= n; ++count;
    }
    if (left) {
        horizon_store_dispose(s, release);
        horizon_store_add(HS_FAILED, 1);
        errno = ENOMEM;
        return -1;
    }
    horizon_store_add(HS_RECOVERED, 1);
    horizon_store_add(HS_RECOVERED_BYTES, size);
    horizon_store_add(HS_PIECES, count);
    horizon_store_peak(__atomic_add_fetch(&horizon_store_stats[HS_LIVE_BYTES], size, __ATOMIC_RELAXED));
    errno = saved_errno;
    return 0;
}
static inline void horizon_store_free(struct horizon_page_store *s, horizon_store_free_fn release) {
    if (s->poisoned) return;
    if (s->pieces) {
        unsigned count = 0;
        for (struct horizon_store_piece *p = s->pieces; p; p = p->next) ++count;
        __atomic_fetch_sub(&horizon_store_stats[HS_LIVE_BYTES], s->size, __ATOMIC_RELAXED);
        __atomic_fetch_sub(&horizon_store_stats[HS_PIECES], count, __ATOMIC_RELAXED);
        horizon_store_add(HS_RELEASED, 1);
    }
    horizon_store_dispose(s, release);
}
static inline void *horizon_store_at(const struct horizon_page_store *s, size_t offset, size_t *available) {
    struct horizon_store_piece *p;
    if (offset >= s->size) { *available = 0; return NULL; }
    if (s->data) { *available = s->size - offset; return (char *)s->data + offset; }
    for (p = s->pieces; p && offset >= p->size; p = p->next) offset -= p->size;
    if (!p) { *available = 0; return NULL; }
    *available = p->size - offset;
    return (char *)p->data + offset;
}
/* A failed operation must leave its current piece untouched. Undo already
 * completed pieces. If the OS rejects an undo, preserve their storage rather
 * than freeing pages that may still be mapped. */
static inline int horizon_store_range(struct horizon_page_store *s, void *dst, size_t offset,
                                     size_t size, horizon_store_op apply,
                                     horizon_store_op undo, void *context) {
    size_t done = 0, n;
    int error;
    if (s->poisoned || offset > s->size || size > s->size - offset || !size ||
        (offset | size | (uintptr_t)dst) % HORIZON_STORE_PAGE) { errno = EINVAL; return -1; }
    while (done < size) {
        void *src = horizon_store_at(s, offset + done, &n);
        if (n > size - done) n = size - done;
        if (!src || apply((char *)dst + done, src, n, context)) break;
        done += n;
    }
    if (done == size) return 0;
    error = errno;
    if (undo) for (size_t back = 0; back < done; back += n) {
        void *src = horizon_store_at(s, offset + back, &n);
        if (n > done - back) n = done - back;
        if (undo((char *)dst + back, src, n, context)) {
            s->poisoned = 1;
            horizon_store_add(HS_ROLLBACK_FAILED, 1);
        }
    }
    errno = error;
    return -1;
}
#endif
