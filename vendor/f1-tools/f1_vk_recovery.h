/* LGPL-2.1-or-later. Ordinary driver retries after releasing idle Wine arenas.
 * The scratch-release ABI is retained, but the F1 policy now protects all FEX
 * compiler reserves. GPU memory always comes from the driver. */
#ifndef F1_VK_RECOVERY_H
#define F1_VK_RECOVERY_H
extern size_t wine_nx_release_idle_backing_pages(void);
extern size_t wine_nx_f1_release_idle_scratch(size_t requested);
extern void wine_nx_f1_resource_snapshot(const char *reason);
/* Failed driver calls, recovered calls, Wine bytes returned, reserve bytes
 * returned, last request bytes, last result. Atomic independent diagnostics. */
static uint64_t f1_vk_pressure[6];
void wine_nx_f1_vkmem_snapshot(void)
{
    uint64_t values[6];
    for (unsigned i = 0; i < 6; ++i)
        values[i] = __atomic_load_n(&f1_vk_pressure[i], __ATOMIC_RELAXED);
    nx_vk_trace("[F1-VKMEM-STATS] oom=%llu recovered=%llu wine_returned=%llu scratch_returned=%llu last_bytes=%llu last_result=%d",
        (unsigned long long)values[0], (unsigned long long)values[1],
        (unsigned long long)values[2], (unsigned long long)values[3],
        (unsigned long long)values[4], (int)(int32_t)values[5]);
}
static VkResult f1_vk_allocate_recover(PFN_vkAllocateMemory allocate, VkDevice device,
                                      const VkMemoryAllocateInfo *info, VkDeviceMemory *out)
{
    static unsigned reports;
    VkResult result = allocate(device, info, NULL, out);
    if (result == VK_ERROR_OUT_OF_HOST_MEMORY || result == VK_ERROR_OUT_OF_DEVICE_MEMORY) {
        size_t released = wine_nx_release_idle_backing_pages();
        if (released) result = allocate(device, info, NULL, out);
        size_t scratch = 0;
        if ((result == VK_ERROR_OUT_OF_HOST_MEMORY || result == VK_ERROR_OUT_OF_DEVICE_MEMORY) &&
            info->allocationSize <= SIZE_MAX) {
            scratch = wine_nx_f1_release_idle_scratch((size_t)info->allocationSize);
            if (scratch) result = allocate(device, info, NULL, out);
        }
        unsigned ticket = __atomic_fetch_add(&reports, 1, __ATOMIC_RELAXED);
        /* Keep a late small-resource failure visible after earlier large pool
         * attempts, without writing a line on every repeated OOM. */
        if (ticket < 16 || !(ticket & (ticket - 1)) || scratch) {
            nx_vk_trace("[F1-VKMEM] bytes=%llu type=%u idle_released=%llu scratch_released=%llu retries=%u result=%d failures=%u",
                (unsigned long long)info->allocationSize, info->memoryTypeIndex,
                (unsigned long long)released, (unsigned long long)scratch,
                (released != 0) + (scratch != 0), result, ticket + 1);
            if (result && info->allocationSize <= 4u*1024u*1024u)
                wine_nx_f1_resource_snapshot("vulkan-allocation-failed");
        }
        __atomic_add_fetch(&f1_vk_pressure[0], 1, __ATOMIC_RELAXED);
        if (!result) __atomic_add_fetch(&f1_vk_pressure[1], 1, __ATOMIC_RELAXED);
        __atomic_add_fetch(&f1_vk_pressure[2], released, __ATOMIC_RELAXED);
        __atomic_add_fetch(&f1_vk_pressure[3], scratch, __ATOMIC_RELAXED);
        __atomic_store_n(&f1_vk_pressure[4], info->allocationSize, __ATOMIC_RELAXED);
        __atomic_store_n(&f1_vk_pressure[5], (uint64_t)(int64_t)result, __ATOMIC_RELAXED);
    }
    return result;
}
#endif
