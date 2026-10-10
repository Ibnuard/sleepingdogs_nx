/* LGPL-2.1-or-later. Keep Wine's x86 exception cache and WoW64 state coherent. */
#ifndef SD_WOW64_DEBUG_CACHE_H
#define SD_WOW64_DEBUG_CACHE_H

/* This is the private layout in the pinned Wine dlls/ntdll/signal_i386.c.
 * RtlRaiseException reads these fields, not the WoW64 CPU area. Selectors and
 * exit_frame belong to other code and must never be overwritten here. */
struct sd_x86_thread_debug_cache
{
    DWORD fs, gs;
    DWORD dr0, dr1, dr2, dr3, dr6, dr7;
    ULONG exit_frame;
};
C_ASSERT(offsetof(TEB32, GdiTebBatch) + offsetof(struct sd_x86_thread_debug_cache, dr0) == 0x1dc);
C_ASSERT(offsetof(TEB32, GdiTebBatch) + offsetof(struct sd_x86_thread_debug_cache, dr7) == 0x1f0);
C_ASSERT(sizeof(struct sd_x86_thread_debug_cache) <= sizeof(((TEB32 *)0)->GdiTebBatch));

static int sd_wow64_sync_debug_cache(TEB32 *teb, const I386_CONTEXT *saved)
{
    struct sd_x86_thread_debug_cache *cache;
    int changed;
    if (!teb || !saved) return 0;
    cache = (struct sd_x86_thread_debug_cache *)&teb->GdiTebBatch;
    changed = cache->dr0 != saved->Dr0 || cache->dr1 != saved->Dr1 ||
              cache->dr2 != saved->Dr2 || cache->dr3 != saved->Dr3 ||
              cache->dr6 != saved->Dr6 || cache->dr7 != saved->Dr7;
    cache->dr0 = saved->Dr0; cache->dr1 = saved->Dr1;
    cache->dr2 = saved->Dr2; cache->dr3 = saved->Dr3;
    cache->dr6 = saved->Dr6; cache->dr7 = saved->Dr7;
    return changed;
}
#endif
