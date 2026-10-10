/* ISC: Copyright 2017-2018 libnx Authors.
 * See licenses/libnx-LICENSE.md.txt for the full license.
 * Derived from switchbrew/libnx nx/source/kernel/virtmem.c, SHA256
 * 78a92f70e33e064b6d30e73370a7e7cdf709654ecf2ae6b5cba3877fa9f5df23.
 * Same manager/regions/reservation list, with exhaustive recovery after a
 * random search misses. Linked instead of virtmem.o, never alongside it.
 */
#include <switch.h>
#include <stdint.h>
extern void *__libnx_alloc(size_t size);
extern void __libnx_free(void *p);
#define RANDOM_MAX_ATTEMPTS 0x200

typedef struct {
    uintptr_t start;
    uintptr_t end;
} MemRegion;

struct VirtmemReservation {
    VirtmemReservation *next;
    VirtmemReservation *prev;
    MemRegion region;
};

static Mutex g_VirtmemMutex;

static MemRegion g_AliasRegion;
static MemRegion g_HeapRegion;
static MemRegion g_AslrRegion;
static MemRegion g_StackRegion;

static VirtmemReservation *g_Reservations;

static bool g_IsLegacyKernel;
/* Updated only on the recovery path. No polling, allocation or log I/O. */
static u64 fx_vm_scans, fx_vm_recovered, fx_vm_failed, fx_vm_largest;
void pes13_virtmem_snapshot(u64 out[4]) {
    out[0] = __atomic_load_n(&fx_vm_scans, __ATOMIC_RELAXED);
    out[1] = __atomic_load_n(&fx_vm_recovered, __ATOMIC_RELAXED);
    out[2] = __atomic_load_n(&fx_vm_failed, __ATOMIC_RELAXED);
    out[3] = __atomic_load_n(&fx_vm_largest, __ATOMIC_RELAXED);
}

/* Caller holds the ORIGINAL libnx manager lock. Walk actual kernel blocks and
 * the same software reservations used by Wine, libnx threads and FEX. Never
 * accept a merely unmapped but reserved address. Monotonic block/interval
 * progress bounds the scan without a retry lottery or a second owner table. */
static void *_memregionFindSequential(MemRegion *r, size_t size, size_t guard) {
    uintptr_t cur = r->start, largest = 0;
    void *found = NULL;
    __atomic_fetch_add(&fx_vm_scans, 1, __ATOMIC_RELAXED);
    while (cur < r->end) {
        MemoryInfo info;
        u32 page;
        if (R_FAILED(svcQueryMemory(&info, &page, cur)) || !info.size ||
            info.addr > cur || info.size > UINTPTR_MAX - info.addr) break;
        uintptr_t end = info.addr + info.size;
        if (end > r->end) end = r->end;
        if (end <= cur) break;
        if (info.type != MemType_Unmapped) { cur = end; continue; }
        /* Find the earliest obstruction within this kernel-unmapped block. */
        uintptr_t free_end = end, skip_end = cur;
        const MemRegion *fixed[] = { &g_HeapRegion, &g_AliasRegion };
        for (unsigned i = 0; i < 2; ++i) {
            const MemRegion *b = fixed[i];
            if (b->start >= b->end || b->end <= cur || b->start >= end) continue;
            if (b->start <= cur) { if (b->end > skip_end) skip_end = b->end; }
            else if (b->start < free_end) free_end = b->start;
        }
        for (VirtmemReservation *rv = g_Reservations; rv; rv = rv->next) {
            const MemRegion *b = &rv->region;
            if (b->start >= b->end || b->end <= cur || b->start >= end) continue;
            if (b->start <= cur) { if (b->end > skip_end) skip_end = b->end; }
            else if (b->start < free_end) free_end = b->start;
        }
        if (skip_end > cur) { cur = skip_end < end ? skip_end : end; continue; }
        /* Round inward even if a caller's reservation is not page aligned. */
        if (cur > UINTPTR_MAX - 0xfff) break;
        uintptr_t lo = (cur + 0xfff) & ~(uintptr_t)0xfff;
        uintptr_t hi = free_end & ~(uintptr_t)0xfff;
        size_t span = hi > lo ? hi - lo : 0;
        size_t usable = guard <= span / 2 ? span - guard * 2 : 0;
        if (usable > largest) largest = usable;
        if (size <= usable) { found = (void *)(lo + guard); break; }
        cur = free_end;
    }
    __atomic_store_n(&fx_vm_largest, largest, __ATOMIC_RELAXED);
    __atomic_fetch_add(found ? &fx_vm_recovered : &fx_vm_failed, 1, __ATOMIC_RELAXED);
    return found;
}

uintptr_t __attribute__((weak)) __libnx_virtmem_rng(void) {
    return (uintptr_t)randomGet64();
}

static Result _memregionInitWithInfo(MemRegion* r, InfoType id0_addr, InfoType id0_sz) {
    u64 base;
    Result rc = svcGetInfo(&base, id0_addr, CUR_PROCESS_HANDLE, 0);

    if (R_SUCCEEDED(rc)) {
        u64 size;
        rc = svcGetInfo(&size, id0_sz, CUR_PROCESS_HANDLE, 0);

        if (R_SUCCEEDED(rc)) {
            r->start = base;
            r->end   = base + size;
        }
    }

    return rc;
}

static void _memregionInitHardcoded(MemRegion* r, uintptr_t start, uintptr_t end) {
    r->start = start;
    r->end   = end;
}

NX_INLINE bool _memregionIsInside(MemRegion* r, uintptr_t start, uintptr_t end) {
    return start >= r->start && end <= r->end;
}

NX_INLINE bool _memregionOverlaps(MemRegion* r, uintptr_t start, uintptr_t end) {
    return start < r->end && r->start < end;
}

NX_INLINE bool _memregionIsMapped(uintptr_t start, uintptr_t end, uintptr_t guard, uintptr_t* out_end) {
    // Adjust start/end by the desired guard size.
    start -= guard;
    end += guard;

    // Query memory properties.
    MemoryInfo meminfo;
    u32 pageinfo;
    Result rc = svcQueryMemory(&meminfo, &pageinfo, start);
    if (R_FAILED(rc))
        diagAbortWithResult(MAKERESULT(Module_Libnx, LibnxError_BadQueryMemory));

    // Return true if there's anything mapped.
    uintptr_t memend = meminfo.addr + meminfo.size;
    if (meminfo.type != MemType_Unmapped || end > memend) {
        if (out_end) *out_end = memend + guard;
        return true;
    }

    return false;
}

NX_INLINE bool _memregionIsReserved(uintptr_t start, uintptr_t end, uintptr_t guard, uintptr_t* out_end) {
    // Adjust start/end by the desired guard size.
    start -= guard;
    end += guard;

    // Go through each reservation and check if any of them overlap the desired address range.
    for (VirtmemReservation *rv = g_Reservations; rv; rv = rv->next) {
        if (_memregionOverlaps(&rv->region, start, end)) {
            if (out_end) *out_end = rv->region.end + guard;
            return true;
        }
    }

    return false;
}

static void* _memregionFindRandom(MemRegion* r, size_t size, size_t guard_size) {
    // Page align the sizes.
    if (!size || size > SIZE_MAX - 0xfff || guard_size > SIZE_MAX - 0xfff || r->end <= r->start)
        return NULL;
    size = (size + 0xFFF) &~ 0xFFF;
    guard_size = (guard_size + 0xFFF) &~ 0xFFF;

    // Ensure the requested size isn't greater than the memory region itself...
    uintptr_t region_size = r->end - r->start;
    if (size > region_size || guard_size > (region_size - size) / 2)
        return NULL;

    // Main allocation loop.
    uintptr_t aslr_max_page_offset = (region_size - size) >> 12;
    for (unsigned i = 0; i < RANDOM_MAX_ATTEMPTS; i ++) {
        // Calculate a random memory range outside reserved areas.
        uintptr_t cur_addr;
        {
            uintptr_t page_offset = __libnx_virtmem_rng() % (aslr_max_page_offset + 1);
            cur_addr = (uintptr_t)r->start + (page_offset << 12);
            if (cur_addr - r->start < guard_size || r->end - cur_addr - size < guard_size)
                continue;

            // Avoid mapping within the alias region.
            if (_memregionOverlaps(&g_AliasRegion, cur_addr, cur_addr + size))
                continue;

            // Avoid mapping within the heap region.
            if (_memregionOverlaps(&g_HeapRegion, cur_addr, cur_addr + size))
                continue;

        }

        // Check that there isn't anything mapped at the desired memory range.
        if (_memregionIsMapped(cur_addr, cur_addr + size, guard_size, NULL))
            continue;

        // Check that the desired memory range doesn't overlap any reservations.
        if (_memregionIsReserved(cur_addr, cur_addr + size, guard_size, NULL))
            continue;

        // We found a suitable address!
        return (void*)cur_addr;
    }

    return _memregionFindSequential(r, size, guard_size);
}

void virtmemSetup(void) {
    Result rc;

    // Retrieve memory region information for the reserved alias region.
    rc = _memregionInitWithInfo(&g_AliasRegion, InfoType_AliasRegionAddress, InfoType_AliasRegionSize);
    if (R_FAILED(rc)) {
        // Wat.
        diagAbortWithResult(MAKERESULT(Module_Libnx, LibnxError_WeirdKernel));
    }

    // Account for the alias region extra size.
    u64 alias_extra_size;
    rc = svcGetInfo(&alias_extra_size, InfoType_AliasRegionExtraSize, CUR_PROCESS_HANDLE, 0);
    if (R_SUCCEEDED(rc)) {
        g_AliasRegion.end -= alias_extra_size;
    }

    // Retrieve memory region information for the reserved heap region.
    rc = _memregionInitWithInfo(&g_HeapRegion, InfoType_HeapRegionAddress, InfoType_HeapRegionSize);
    if (R_FAILED(rc)) {
        // Wat.
        diagAbortWithResult(MAKERESULT(Module_Libnx, LibnxError_BadGetInfo_Heap));
    }

    // Retrieve memory region information for the aslr/stack regions if available [2.0.0+]
    rc = _memregionInitWithInfo(&g_AslrRegion, InfoType_AslrRegionAddress, InfoType_AslrRegionSize);
    if (R_SUCCEEDED(rc)) {
        rc = _memregionInitWithInfo(&g_StackRegion, InfoType_StackRegionAddress, InfoType_StackRegionSize);
        if (R_FAILED(rc))
            diagAbortWithResult(MAKERESULT(Module_Libnx, LibnxError_BadGetInfo_Stack));
    }
    else {
        // [1.0.0] doesn't expose aslr/stack region information so we have to do this dirty hack to detect it.
        // Forgive me.
        g_IsLegacyKernel = true;
        rc = svcUnmapMemory((void*)0xFFFFFFFFFFFFE000UL, (void*)0xFFFFFE000UL, 0x1000);
        if (R_VALUE(rc) == KERNELRESULT(InvalidMemoryState)) {
            // Invalid src-address error means that a valid 36-bit address was rejected.
            // Thus we are 32-bit.
            _memregionInitHardcoded(&g_AslrRegion, 0x200000ull, 0x100000000ull);
            _memregionInitHardcoded(&g_StackRegion, 0x200000ull, 0x40000000ull);
        }
        else if (R_VALUE(rc) == KERNELRESULT(InvalidMemoryRange)) {
            // Invalid dst-address error means our 36-bit src-address was valid.
            // Thus we are 36-bit.
            _memregionInitHardcoded(&g_AslrRegion, 0x8000000ull, 0x1000000000ull);
            _memregionInitHardcoded(&g_StackRegion, 0x8000000ull, 0x80000000ull);
        }
        else {
            // Wat.
            diagAbortWithResult(MAKERESULT(Module_Libnx, LibnxError_WeirdKernel));
        }
    }
}

void virtmemLock(void) {
    mutexLock(&g_VirtmemMutex);
}

void virtmemUnlock(void) {
    mutexUnlock(&g_VirtmemMutex);
}

void* virtmemFindAslr(size_t size, size_t guard_size) {
    if (!mutexIsLockedByCurrentThread(&g_VirtmemMutex)) return NULL;
    return _memregionFindRandom(&g_AslrRegion, size, guard_size);
}

void* virtmemFindStack(size_t size, size_t guard_size) {
    if (!mutexIsLockedByCurrentThread(&g_VirtmemMutex)) return NULL;
    return _memregionFindRandom(&g_StackRegion, size, guard_size);
}

void* virtmemFindCodeMemory(size_t size, size_t guard_size) {
    if (!mutexIsLockedByCurrentThread(&g_VirtmemMutex)) return NULL;
    // [1.0.0] requires CodeMemory to be mapped within the stack region.
    return _memregionFindRandom(g_IsLegacyKernel ? &g_StackRegion : &g_AslrRegion, size, guard_size);
}

VirtmemReservation* virtmemAddReservation(void* mem, size_t size) {
    if (!mutexIsLockedByCurrentThread(&g_VirtmemMutex)) return NULL;
    VirtmemReservation* rv = (VirtmemReservation*)__libnx_alloc(sizeof(VirtmemReservation));
    if (rv) {
        rv->region.start = (uintptr_t)mem;
        rv->region.end   = rv->region.start + size;
        rv->next         = g_Reservations;
        rv->prev         = NULL;
        g_Reservations   = rv;
        if (rv->next)
            rv->next->prev = rv;
    }
    return rv;
}

void virtmemRemoveReservation(VirtmemReservation* rv) {
    if (!mutexIsLockedByCurrentThread(&g_VirtmemMutex)) return;
    if (rv->next)
        rv->next->prev = rv->prev;
    if (rv->prev)
        rv->prev->next = rv->next;
    else
        g_Reservations = rv->next;
    __libnx_free(rv);
}
