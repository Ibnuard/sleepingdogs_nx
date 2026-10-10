/* SPDX-License-Identifier: MIT
 * Reserve the usual four simultaneous compiler workspaces before scene assets
 * fragment the native heap. Same sizes/ABI as FEX; never recycle an owned slot.
 * Keep the four pairs dedicated even while temporarily idle: a later compiler
 * burst needs these workspaces after graphics has filled the ordinary heap.
 * Caller supplies HOST_LOCK, aligned_alloc/free and host_log. */
#ifndef F1_SCRATCH_H
#define F1_SCRATCH_H

#if defined(__SWITCH__) || defined(F1_SCRATCH_PAGES_TEST)
#include "scratch_pages/horizon_scratch_pages.h"
extern size_t wine_nx_release_idle_backing_pages(void);
extern void pes13_virtmem_snapshot(uint64_t out[4]);
static unsigned f1_scratch_pressure_calls;
static void *f1_scratch_recover(size_t size)
{
    /* The ordinary allocation already failed. Only completely idle Wine
     * arenas may be returned; live backing and the eight reserve owners stay
     * intact. Never hold the reserve mutex across Wine's mapping lock. */
    size_t trimmed = wine_nx_release_idle_backing_pages();
    void *ptr = trimmed ? aligned_alloc(PAGE_BYTES, size) : NULL;
    struct fx_sp_failure failure = {FX_SP_OK, 0};
    if (!ptr) ptr = fx_scratch_pages_take_report(size, &failure);
    unsigned attempt = __atomic_add_fetch(&f1_scratch_pressure_calls, 1, __ATOMIC_RELAXED);
    if (attempt <= 16 || !(attempt & (attempt - 1))) {
        static const char *const stages[] = {"ok", "size", "budget", "owners",
            "source-pages", "descriptors", "virtual-range", "reservation", "map", "permission"};
        char message[224];
        snprintf(message, sizeof(message),
            "[F1-SCRATCH-RECOVER] bytes=%zu idle_released=%zu recovered=%u stage=%s rc=%08x",
            size, trimmed, ptr != NULL, stages[failure.stage], (unsigned)failure.result);
        host_log(message);
    }
    return ptr;
}
#endif

#define F1_SCRATCH_SLOTS 8
static struct { void *ptr; size_t size; unsigned used; } f1_scratch_slots[F1_SCRATCH_SLOTS];
#ifdef __SWITCH__
static host_mutex f1_scratch_lock;
#else
static host_mutex f1_scratch_lock = PTHREAD_MUTEX_INITIALIZER;
#endif
static unsigned f1_scratch_initialized, f1_scratch_active, f1_scratch_peak;
static unsigned f1_scratch_fallbacks, f1_scratch_failures;
static size_t f1_scratch_released_bytes;
static unsigned f1_scratch_released_slots;

/* Retain this ABI for the Vulkan and native-thread retry wrappers. 0.1.24
 * reclaimed idle compiler workspaces for graphics, then failed both 8/16 MiB
 * compiler allocations at the scene transition. Idle here only describes
 * current ownership, not whether the engine needs the capacity again. DXVK
 * already retries smaller chunks; stacks have their separate protected pool. */
size_t wine_nx_f1_release_idle_scratch(size_t requested)
{
    (void)requested;
    return 0;
}

static void f1_scratch_init(void)
{
    unsigned count = 0;
    size_t bytes = 0;
    HOST_LOCK(&f1_scratch_lock);
    if (f1_scratch_initialized) { HOST_UNLOCK(&f1_scratch_lock); return; }
    f1_scratch_initialized = 1;
    for (unsigned i = 0; i < F1_SCRATCH_SLOTS; ++i) {
        size_t size = (i < 4 ? 8u : 16u) * 1024 * 1024;
        void *ptr = aligned_alloc(PAGE_BYTES, size);
        f1_scratch_slots[i].ptr = ptr;
        f1_scratch_slots[i].size = size;
        if (ptr) { bytes += size; ++count; }
    }
    HOST_UNLOCK(&f1_scratch_lock);
    char message[160];
    snprintf(message, sizeof(message), "[F1-SCRATCH] reserve slots=%u bytes=%zu; protected=1; live code unchanged", count, bytes);
    host_log(message);
}

static void *f1_scratch_alloc(size_t size)
{
    void *ptr = NULL;
    HOST_LOCK(&f1_scratch_lock);
    for (unsigned i = 0; i < F1_SCRATCH_SLOTS; ++i) {
        if (f1_scratch_slots[i].ptr && !f1_scratch_slots[i].used && f1_scratch_slots[i].size == size) {
            f1_scratch_slots[i].used = 1;
            if (++f1_scratch_active > f1_scratch_peak) f1_scratch_peak = f1_scratch_active;
            ptr = f1_scratch_slots[i].ptr;
            break;
        }
    }
    HOST_UNLOCK(&f1_scratch_lock);
    if (!ptr) {
        ptr = aligned_alloc(PAGE_BYTES, size);
        if (size >= 8u * 1024 * 1024) __atomic_add_fetch(&f1_scratch_fallbacks, 1, __ATOMIC_RELAXED);
#if defined(__SWITCH__) || defined(F1_SCRATCH_PAGES_TEST)
        if (!ptr) ptr = f1_scratch_recover(size);
#endif
        if (!ptr) __atomic_add_fetch(&f1_scratch_failures, 1, __ATOMIC_RELAXED);
    }
    return ptr;
}

static void f1_scratch_free(void *ptr)
{
    if (!ptr) return;
    HOST_LOCK(&f1_scratch_lock);
    for (unsigned i = 0; i < F1_SCRATCH_SLOTS; ++i) {
        if (f1_scratch_slots[i].ptr == ptr) {
            if (f1_scratch_slots[i].used) { f1_scratch_slots[i].used = 0; --f1_scratch_active; }
            HOST_UNLOCK(&f1_scratch_lock);
            return;
        }
    }
    HOST_UNLOCK(&f1_scratch_lock);
#if defined(__SWITCH__) || defined(F1_SCRATCH_PAGES_TEST)
    if (fx_scratch_pages_release(ptr)) return;
#endif
    free(ptr);
}

void wine_nx_f1_scratch_snapshot(void)
{
    char message[192];
    HOST_LOCK(&f1_scratch_lock);
    unsigned active = f1_scratch_active, peak = f1_scratch_peak;
    size_t idle_bytes = 0, live_bytes = 0, released_bytes = f1_scratch_released_bytes;
    unsigned released_slots = f1_scratch_released_slots;
    for (unsigned i = 0; i < F1_SCRATCH_SLOTS; ++i) {
        if (!f1_scratch_slots[i].ptr) continue;
        if (f1_scratch_slots[i].used) live_bytes += f1_scratch_slots[i].size;
        else idle_bytes += f1_scratch_slots[i].size;
    }
    HOST_UNLOCK(&f1_scratch_lock);
    snprintf(message, sizeof(message), "[F1-SCRATCH] active=%u peak=%u fallbacks=%u failures=%u",
        active, peak, __atomic_load_n(&f1_scratch_fallbacks, __ATOMIC_RELAXED),
        __atomic_load_n(&f1_scratch_failures, __ATOMIC_RELAXED));
    host_log(message);
    snprintf(message, sizeof(message),
        "[F1-SCRATCH-RESERVE] live=%zu idle=%zu released=%zu slots_released=%u",
        live_bytes, idle_bytes, released_bytes, released_slots);
    host_log(message);
#if defined(__SWITCH__) || defined(F1_SCRATCH_PAGES_TEST)
    uint64_t pages[15], vm[4];
    pes13_fex_scratch_pages_snapshot(pages);
    pes13_virtmem_snapshot(vm);
    snprintf(message, sizeof(message),
        "[F1-SCRATCH-PAGES] attempts=%llu recovered=%llu failed=%llu live=%llu peak=%llu owners=%llu pieces=%llu",
        (unsigned long long)pages[0], (unsigned long long)pages[1], (unsigned long long)pages[2],
        (unsigned long long)pages[3], (unsigned long long)pages[4], (unsigned long long)pages[5],
        (unsigned long long)pages[6]);
    host_log(message);
    snprintf(message, sizeof(message),
        "[F1-SCRATCH-PAGES] returned=%llu map_failed=%llu unmap_failed=%llu quarantined=%llu rc=%08x requested=%llu budget_refusals=%llu",
        (unsigned long long)pages[7], (unsigned long long)pages[8], (unsigned long long)pages[9],
        (unsigned long long)pages[10], (unsigned)pages[12], (unsigned long long)pages[13],
        (unsigned long long)pages[14]);
    host_log(message);
    snprintf(message, sizeof(message),
        "[F1-VIRTMEM] scans=%llu recovered=%llu failed=%llu largest=%llu",
        (unsigned long long)vm[0], (unsigned long long)vm[1],
        (unsigned long long)vm[2], (unsigned long long)vm[3]);
    host_log(message);
#endif
}
#endif
