/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Replaces only initialization of the audited direct data arena. The existing
 * page protection, zero-on-recommit, and rollback logic runs on the low alias.
 * The high source becomes inaccessible while mapped and is never freed while
 * the kernel owns it. One physical allocation, two virtual ranges.
 */
static void *sd_arena_backing;
void sd_guest_arena_init(void)
{
    void *backing=NULL;
    const uintptr_t low=SD_LOW_ARENA_BASE;
    const size_t size=SD_GUEST_ARENA_BYTES;
    Handle process=envGetOwnProcessHandle();
    MemoryInfo info; u32 page;
    Result rc=0,unmap_rc=0;
    int saved_errno=errno,mapped=0;
    char message[256];
    if (__atomic_exchange_n(&sd_arena_started,1,__ATOMIC_ACQ_REL)) return;
    if (!sd_low_window_ready() || size>UINT64_C(0x7ffe0000)-low) goto done;
    backing=memalign(65536,size);
    if (!backing) goto done;
    if ((uintptr_t)backing<SD_NATIVE_BASE || (uintptr_t)backing>=SD_HOST_LIMIT ||
        size>SD_HOST_LIMIT-(uintptr_t)backing) goto failed;
    virtmemLock();
    rc=svcQueryMemory(&info,&page,low);
    if (R_FAILED(rc) || info.type!=MemType_Unmapped || info.addr>low ||
        info.size>UINT64_MAX-info.addr || info.addr+info.size<low+size) {
        if (R_SUCCEEDED(rc)) rc=0xffffffff;
        virtmemUnlock(); goto failed;
    }
    rc=svcMapProcessCodeMemory(process,low,(u64)backing,size);
    mapped=R_SUCCEEDED(rc);
    if (mapped) rc=svcSetProcessMemoryPermission(process,low,size,Perm_Rw);
    /* AliasCodeData supports the same data-only permission transitions as the
     * old ordinary-heap arena. No RX permission is ever requested here. */
    if (R_SUCCEEDED(rc)) rc=svcSetMemoryPermission((void *)low,size,Perm_None);
    if (R_FAILED(rc) && mapped)
        unmap_rc=svcUnmapProcessCodeMemory(process,low,(u64)backing,size);
    virtmemUnlock();
    if (R_FAILED(rc)) goto failed;
    sd_arena_backing=backing;
    sd_arena_base=(void *)low;
    memset(sd_arena_pages,4,sizeof(sd_arena_pages));
    goto done;
failed:
    if (R_FAILED(unmap_rc)) {
        sd_arena_backing=backing; /* intentionally retained; launch is disabled */
        wine_nx_runtime_trace("[SD-ALIAS] cleanup failed; high backing retained; game disabled");
    } else free(backing);
done:
    snprintf(message,sizeof(message),"[SD-ALIAS] v1 requested=%zu reserved=%zu low=%p high=%p rc=%08x unmap=%08x physical_copies=1",
        size,sd_guest_arena_size(),sd_arena_base,sd_arena_backing,rc,unmap_rc);
    wine_nx_runtime_trace(message);
    errno=saved_errno;
}
