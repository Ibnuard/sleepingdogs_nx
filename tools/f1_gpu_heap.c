/* F1-only backing allocator for Nouveau. Early arena allocations and fallback
 * chunks use ordinary heap backing, never CPU virtual aliases. The pinned
 * Nouveau object's free import returns arena slices only after NvMap closes.
 *
 * This adapter is tied to the checked newlib malloc/free/memalign objects in
 * gpu_heap_binding.py. Newlib's memalign first mallocs bytes + alignment +
 * padding. Under pressure it can miss an already-aligned free chunk. Search
 * the actual free bins under the same recursive malloc lock after that fails.
 * Layout/rounding/splitting follow newlib's public-domain _mallocr.c allocator.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
#include <malloc.h>
#include <sys/reent.h>
#include <switch.h>
#include "f1_gpu_arena.h"

struct f1_chunk {
    size_t prev_size, size;
    struct f1_chunk *fd, *bk;
};
extern struct f1_chunk *__malloc_av_[258];
extern void __malloc_lock(struct _reent *);
extern void __malloc_unlock(struct _reent *);
extern void wine_nx_runtime_trace(const char *);
extern char *fake_heap_start, *fake_heap_end;
static Mutex f1_gpu_arena_lock;
static struct f1_gpu_arena f1_gpu_pool;
static unsigned f1_gpu_arena_ready, f1_gpu_arena_started;
static void f1_gpu_arena_snapshot(void);

/* Before Wine/FEX/scene allocations fragment the heap. The observed graphics
 * footprint reaches 571 MiB in DXVK alone. Keep up to 640 MiB contiguous for
 * real GPU backing, while smaller loader heaps use at most a third. No extra
 * process quota is assumed. Failure leaves the ordinary allocator available. */
void wine_nx_f1_gpu_heap_init(void)
{
    if(__atomic_exchange_n(&f1_gpu_arena_started,1,__ATOMIC_ACQ_REL))return;
    size_t capacity=(uintptr_t)fake_heap_end>(uintptr_t)fake_heap_start?
        (uintptr_t)fake_heap_end-(uintptr_t)fake_heap_start:0;
    size_t wanted=capacity>=1792u*1024u*1024u?F1_GPU_ARENA_BYTES:capacity/3;
    if(wanted>F1_GPU_ARENA_BYTES)wanted=F1_GPU_ARENA_BYTES;
    wanted&=~(size_t)(F1_GPU_UNIT-1);
    void *base=NULL;size_t reserved=wanted;
    int saved_errno=errno;
    while(reserved>=8u*1024u*1024u && !(base=memalign(F1_GPU_UNIT,reserved)))
        reserved=(reserved/2)&~(size_t)(F1_GPU_UNIT-1);
    if(base) {
        mutexLock(&f1_gpu_arena_lock);
        int ready=f1_gpu_arena_setup(&f1_gpu_pool,base,reserved);
        mutexUnlock(&f1_gpu_arena_lock);
        if(ready)__atomic_store_n(&f1_gpu_arena_ready,1,__ATOMIC_RELEASE);
        else {free(base);base=NULL;}
    }
    char line[192];
    snprintf(line,sizeof(line),"[F1-GPU-ARENA] init requested=%llu reserved=%llu unit=%u source=ordinary-heap",
        (unsigned long long)wanted,(unsigned long long)(base?reserved:0),F1_GPU_UNIT);
    wine_nx_runtime_trace(line);errno=saved_errno;
}

void wine_nx_f1_gpu_free(void *ptr)
{
    if(!ptr)return;
    int result=0;
    if(__atomic_load_n(&f1_gpu_arena_ready,__ATOMIC_ACQUIRE)) {
        mutexLock(&f1_gpu_arena_lock);
        result=f1_gpu_arena_put(&f1_gpu_pool,ptr);
        mutexUnlock(&f1_gpu_arena_lock);
    }
    if(!result)free(ptr);
    else if(result<0)wine_nx_runtime_trace("[F1-GPU-ARENA] invalid release ignored; active backing retained");
}

_Static_assert(sizeof(size_t) == 8 && sizeof(struct f1_chunk) == 32,
               "Pinned AArch64 newlib chunk ABI required");

/* attempts, recovered, failed, recovered bytes, largest examined aligned range,
 * last request, last alignment, scanned free chunks. */
static uint64_t f1_gpu_heap_stats[8];
static uint64_t f1_gpu_scan_limits;

/* Same size classes as the hash-pinned newlib _malloc_r. Walking small bins
 * for a multi-MiB request can exhaust the scan budget before a usable large
 * chunk is visited (0.1.24 hardware: scanned=131073 on every attempt). */
static unsigned f1_gpu_bin_index(size_t size)
{
    if ((size >> 9) == 0) return (unsigned)(size >> 3);
    if ((size >> 9) <= 4) return 56 + (unsigned)(size >> 6);
    if ((size >> 9) <= 20) return 91 + (unsigned)(size >> 9);
    if ((size >> 9) <= 84) return 110 + (unsigned)(size >> 12);
    if ((size >> 9) <= 340) return 119 + (unsigned)(size >> 15);
    if ((size >> 9) <= 1364) return 124 + (unsigned)(size >> 18);
    return 126;
}

static size_t f1_gpu_fit(struct f1_chunk *chunk, size_t alignment, size_t *lead)
{
    const size_t size = chunk->size & ~(size_t)3;
    const uintptr_t user = (uintptr_t)chunk + 16;
    if (user > UINTPTR_MAX - (alignment - 1)) return 0;
    uintptr_t aligned = (user + alignment - 1) & ~(uintptr_t)(alignment - 1);
    size_t prefix = aligned - user;
    if (prefix && prefix < 32) {
        if (prefix > SIZE_MAX - alignment) return 0;
        prefix += alignment;
    }
    if (prefix > size) return 0;
    *lead = prefix;
    return size - prefix;
}

static void *f1_gpu_find_chunk(size_t alignment, size_t bytes, size_t *largest,
                               uint64_t *scanned)
{
    if (alignment < 32 || (alignment & (alignment - 1)) ||
        bytes > SIZE_MAX - 23) return NULL;
    size_t needed = (bytes + 23) & ~(size_t)15;
    if (needed < 32) needed = 32;
    struct _reent *reent = _REENT;
    struct f1_chunk *best = NULL;
    size_t best_size = SIZE_MAX, prefix = 0;
    __malloc_lock(reent);
    /* Bin 0 is the top/wilderness, handled separately below. Bin 1 is the
     * last split remainder; it uses the same doubly-linked sentinel ABI. */
    unsigned first_bin = f1_gpu_bin_index(needed);
    if (first_bin < 2) first_bin = 2;
    for (unsigned bin = 1; bin < 128; bin = bin == 1 ? first_bin : bin + 1) {
        struct f1_chunk *head = (void *)&__malloc_av_[bin * 2];
        for (struct f1_chunk *p = head->fd; p != head; p = p->fd) {
            /* Bound time in a heavily fragmented heap. Nothing is changed
             * until an owned, mutually linked free chunk has been selected. */
            if (++*scanned > 131072) {
                __atomic_add_fetch(&f1_gpu_scan_limits, 1, __ATOMIC_RELAXED);
                goto searched;
            }
            size_t lead = 0, fit = f1_gpu_fit(p, alignment, &lead);
            if (fit >= 16 && fit - 8 > *largest) *largest = fit - 8;
            size_t span = p->size & ~(size_t)3;
            if (fit >= needed && span < best_size) {
                best = p; best_size = span; prefix = lead;
                if (span == needed) goto searched;
            }
        }
    }
searched:;
    void *result = NULL;
    if (best) {
        if (best->fd->bk != best || best->bk->fd != best || (best->size & 2))
            goto unlock;
        /* Unlink just as malloc does; binmap bits are lazily cleared by
         * malloc. Keep the whole chunk temporarily in use for free_r. */
        best->fd->bk = best->bk;
        best->bk->fd = best->fd;
        struct f1_chunk *next = (void *)((char *)best + best_size);
        next->size |= 1;
        struct f1_chunk *aligned = (void *)((char *)best + prefix);
        size_t available = best_size - prefix;
        if (prefix) {
            aligned->size = available | 1;
            best->size = prefix | (best->size & 1);
            _free_r(reent, (char *)best + 16);
        }
        if (available - needed >= 32) {
            struct f1_chunk *tail = (void *)((char *)aligned + needed);
            tail->size = (available - needed) | 1;
            aligned->size = needed | (aligned->size & 1);
            _free_r(reent, (char *)tail + 16);
        }
        result = (char *)aligned + 16;
    } else {
        struct f1_chunk *top = __malloc_av_[2];
        size_t lead = 0, fit = f1_gpu_fit(top, alignment, &lead);
        /* Never exhaust the top: normal malloc needs its minimum chunk. */
        if (fit >= 40 && fit - 40 > *largest) *largest = fit - 40;
        if (fit >= needed && fit - needed >= 32) {
            size_t total = top->size & ~(size_t)3;
            struct f1_chunk *aligned = (void *)((char *)top + lead);
            struct f1_chunk *tail = (void *)((char *)aligned + needed);
            __malloc_av_[2] = tail;
            tail->size = (total - lead - needed) | 1;
            if (lead) {
                aligned->size = needed | 1;
                top->size = lead | (top->size & 1);
                _free_r(reent, (char *)top + 16);
            } else aligned->size = needed | (top->size & 1);
            result = (char *)aligned + 16;
        }
    }
unlock:
    __malloc_unlock(reent);
    return result;
}

void *wine_nx_f1_gpu_memalign(size_t alignment, size_t bytes)
{
    if (!alignment || (alignment & (alignment - 1))) { errno = EINVAL; return NULL; }
    if (alignment > SIZE_MAX - 64 || bytes > SIZE_MAX - alignment - 64) {
        errno = ENOMEM; return NULL;
    }
    const int saved_errno = errno;
    if(__atomic_load_n(&f1_gpu_arena_ready,__ATOMIC_ACQUIRE)) {
        mutexLock(&f1_gpu_arena_lock);
        void *pooled=f1_gpu_arena_take(&f1_gpu_pool,alignment,bytes);
        mutexUnlock(&f1_gpu_arena_lock);
        if(pooled)return pooled;
    }
    void *p = memalign(alignment, bytes);
    if (p || alignment < 4096 || !bytes || (alignment & (alignment - 1)))
        return p;
    size_t largest = 0; uint64_t scanned = 0;
    p = f1_gpu_find_chunk(alignment, bytes, &largest, &scanned);
    uint64_t ticket = __atomic_add_fetch(&f1_gpu_heap_stats[0], 1, __ATOMIC_RELAXED);
    __atomic_add_fetch(&f1_gpu_heap_stats[p ? 1 : 2], 1, __ATOMIC_RELAXED);
    if (p) {
        __atomic_add_fetch(&f1_gpu_heap_stats[3], bytes, __ATOMIC_RELAXED);
        errno = saved_errno;
    }
    __atomic_store_n(&f1_gpu_heap_stats[4], largest, __ATOMIC_RELAXED);
    __atomic_store_n(&f1_gpu_heap_stats[5], bytes, __ATOMIC_RELAXED);
    __atomic_store_n(&f1_gpu_heap_stats[6], alignment, __ATOMIC_RELAXED);
    __atomic_store_n(&f1_gpu_heap_stats[7], scanned, __ATOMIC_RELAXED);
    if (ticket <= 16 || !(ticket & (ticket - 1))) {
        char line[240];
        snprintf(line, sizeof(line),
            "[F1-GPU-HEAP] bytes=%llu align=%llu recovered=%u largest_examined=%llu scanned=%llu attempt=%llu",
            (unsigned long long)bytes, (unsigned long long)alignment, p != NULL,
            (unsigned long long)largest, (unsigned long long)scanned,
            (unsigned long long)ticket);
        wine_nx_runtime_trace(line);
        if(!p && (ticket==1 || !(ticket & (ticket-1))))f1_gpu_arena_snapshot();
    }
    return p;
}

Result wine_nx_f1_gpu_nvmap_create(NvMap *map, void *addr, u32 size, u32 align,
                                  NvKind kind, bool cached)
{
    Result rc = nvMapCreate(map, addr, size, align, kind, cached);
    if (R_FAILED(rc)) {
        static unsigned failures;
        unsigned ticket = __atomic_add_fetch(&failures, 1, __ATOMIC_RELAXED);
        if (ticket <= 16 || !(ticket & (ticket - 1))) {
            char line[192];
            snprintf(line, sizeof(line),
                "[F1-GPU-NVMAP] bytes=%u align=%u cached=%u rc=%08x failure=%u arena=%u",
                size, align, cached, (unsigned)rc, ticket,
                __atomic_load_n(&f1_gpu_arena_ready,__ATOMIC_ACQUIRE) &&
                (uintptr_t)addr>=f1_gpu_pool.base &&
                (uintptr_t)addr-f1_gpu_pool.base<(size_t)f1_gpu_pool.units*F1_GPU_UNIT);
            wine_nx_runtime_trace(line);
        }
    }
    return rc;
}

static void f1_gpu_arena_snapshot(void)
{
    char line[256];
    mutexLock(&f1_gpu_arena_lock);
    uint64_t capacity=(uint64_t)f1_gpu_pool.units*F1_GPU_UNIT;
    uint64_t used=(uint64_t)f1_gpu_pool.used*F1_GPU_UNIT;
    uint64_t peak=(uint64_t)f1_gpu_pool.peak*F1_GPU_UNIT;
    uint64_t largest=f1_gpu_arena_largest(&f1_gpu_pool);
    uint64_t takes=f1_gpu_pool.takes, misses=f1_gpu_pool.misses, returned=f1_gpu_pool.returned;
    uint64_t live=f1_gpu_pool.live, invalid=f1_gpu_pool.bad_frees;
    mutexUnlock(&f1_gpu_arena_lock);
    snprintf(line,sizeof(line),"[F1-GPU-ARENA] capacity=%llu used=%llu free=%llu largest=%llu peak=%llu live=%llu takes=%llu misses=%llu returned=%llu invalid=%llu",
        (unsigned long long)capacity,(unsigned long long)used,(unsigned long long)(capacity-used),
        (unsigned long long)largest,(unsigned long long)peak,(unsigned long long)live,
        (unsigned long long)takes,(unsigned long long)misses,(unsigned long long)returned,(unsigned long long)invalid);
    wine_nx_runtime_trace(line);
}

void wine_nx_f1_gpu_heap_snapshot(void)
{
    uint64_t v[8]; char line[256];
    f1_gpu_arena_snapshot();
    for (unsigned i = 0; i < 8; ++i)
        v[i] = __atomic_load_n(&f1_gpu_heap_stats[i], __ATOMIC_RELAXED);
    snprintf(line, sizeof(line),
        "[F1-GPU-HEAP-STATS] attempts=%llu recovered=%llu failed=%llu bytes=%llu largest_examined=%llu last_bytes=%llu last_align=%llu scanned=%llu",
        (unsigned long long)v[0], (unsigned long long)v[1], (unsigned long long)v[2],
        (unsigned long long)v[3], (unsigned long long)v[4], (unsigned long long)v[5],
        (unsigned long long)v[6], (unsigned long long)v[7]);
    wine_nx_runtime_trace(line);
    snprintf(line, sizeof(line), "[F1-GPU-SCAN] size_bins=1 limit_hits=%llu",
        (unsigned long long)__atomic_load_n(&f1_gpu_scan_limits, __ATOMIC_RELAXED));
    wine_nx_runtime_trace(line);
}
