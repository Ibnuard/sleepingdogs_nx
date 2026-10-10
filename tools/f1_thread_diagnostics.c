/* LGPL-2.1-or-later. Retry SDK-owned stack allocation after reclaiming only idle
 * memory. Stack size, mapping, scheduling and lifetime remain owned by libnx. */
#include <switch.h>
#include <pthread.h>
#include <malloc.h>
#include <errno.h>
#include <stdio.h>
#include <stdint.h>
#include "f1_relaunch.h"
#include "f1_native_stacks.h"

extern void wine_nx_runtime_trace(const char *message);
extern Result __real_threadCreate(Thread *, ThreadFunc, void *, void *, size_t, int, int);
extern int __real_pthread_create(pthread_t *, const pthread_attr_t *, void *(*)(void *), void *);
extern char *fake_heap_start, *fake_heap_end;
extern void wine_nx_f1_crash_resource(uint64_t, unsigned, uint64_t, uint64_t, uint64_t, uint64_t);
extern size_t wine_nx_release_idle_backing_pages(void);
extern size_t wine_nx_f1_release_idle_scratch(size_t);
extern void wine_nx_f1_crash_stage(const char *, unsigned, uint64_t, uint64_t);
extern void wine_nx_f1_guest_memory_snapshot(uint64_t out[6]);
extern unsigned long long wine_nx_sd_cache_bytes(void);
extern void horizon_get_memory_info(unsigned long long *total, unsigned long long *used);

void wine_nx_f1_resource_snapshot(const char *reason)
{
    int saved_errno = errno;
    u64 free_threads = 0;
    /* Query-only SVC, also safe when the caller is a native server thread with
     * no Wine TEB. Older kernels can reject this info type; retain the Result. */
    Result result = svcGetInfo(&free_threads, InfoType_FreeThreadCount, CUR_PROCESS_HANDLE, 0);
    struct mallinfo heap = mallinfo();
    uint64_t capacity = (uintptr_t)fake_heap_end >= (uintptr_t)fake_heap_start ?
        (uintptr_t)fake_heap_end - (uintptr_t)fake_heap_start : 0;
    uint64_t unclaimed = capacity > (unsigned)heap.arena ? capacity-(unsigned)heap.arena : 0;
    char message[384];
    snprintf(message, sizeof(message),
             "[F1-RESOURCE] reason=%s free_threads=%llu query_rc=%08x heap_used=%u arena_free=%u heap_arena=%u heap_capacity=%llu heap_unclaimed=%llu heap_available=%llu",
             reason, (unsigned long long)free_threads, (unsigned)result,
             (unsigned)heap.uordblks, (unsigned)heap.fordblks, (unsigned)heap.arena,
             (unsigned long long)capacity, (unsigned long long)unclaimed,
             (unsigned long long)(unclaimed+(unsigned)heap.fordblks));
    wine_nx_f1_crash_resource(free_threads,result,(unsigned)heap.uordblks,
                            (unsigned)heap.fordblks,(unsigned)heap.arena,capacity);
    wine_nx_runtime_trace(message);
    /* Process quota as the kernel accounts it, independent of newlib. The
     * system resource pair covers page tables/blocks for code and heap maps;
     * a kernel ResourceExhausted (0xce01) on mapping points there. */
    static const unsigned kinds[4] = {InfoType_TotalMemorySize, InfoType_UsedMemorySize,
                                      InfoType_SystemResourceSizeTotal, InfoType_SystemResourceSizeUsed};
    u64 budget[4] = {0};
    unsigned rcs[4];
    for (unsigned i = 0; i < 4; ++i)
        rcs[i] = svcGetInfo(&budget[i], kinds[i], CUR_PROCESS_HANDLE, 0);
    snprintf(message, sizeof(message),
             "[F1-MEMBUDGET] reason=%s total=%llu used=%llu free=%llu sysres_total=%llu sysres_used=%llu rc=%08x/%08x/%08x/%08x",
             reason, (unsigned long long)budget[0], (unsigned long long)budget[1],
             (unsigned long long)(budget[0] > budget[1] ? budget[0] - budget[1] : 0),
             (unsigned long long)budget[2], (unsigned long long)budget[3],
             rcs[0], rcs[1], rcs[2], rcs[3]);
    wine_nx_runtime_trace(message);
    /* Who holds the heap: Wine backing (guest + PE allocations, incl. FEX code
     * cache), section pages, page-pool arenas, SD cache, and the RAM the game
     * is told about. All reads are lock-free counters. */
    uint64_t guest[6] = {0};
    unsigned long long reported_total = 0, reported_used = 0;
    wine_nx_f1_guest_memory_snapshot(guest);
    horizon_get_memory_info(&reported_total, &reported_used);
    snprintf(message, sizeof(message),
             "[F1-MEMMAP] reason=%s wine_backing=%llu backing_peak=%llu pooled=%llu sections=%llu sections_peak=%llu page_arenas=%llu sd_cache=%llu reported_total=%llu reported_used=%llu",
             reason, (unsigned long long)guest[0], (unsigned long long)guest[1],
             (unsigned long long)guest[2], (unsigned long long)guest[3],
             (unsigned long long)guest[4], (unsigned long long)guest[5],
             wine_nx_sd_cache_bytes(), reported_total, reported_used);
    wine_nx_runtime_trace(message);
    errno = saved_errno;
}

Result __wrap_threadCreate(Thread *thread, ThreadFunc entry, void *arg, void *stack,
                           size_t size, int priority, int core)
{
    Result result = __real_threadCreate(thread, entry, arg, stack, size, priority, core);
    int saved_errno = errno;
    /* libnx 4.12.0 returns this before creating a thread when its aligned
     * stack allocation fails. Supplied stacks, mapping errors and thread quota
     * failures have different recovery/ownership rules and are not retried.
     * At most three ordinary SDK calls; never spin or borrow an active buffer. */
    if (!stack && result == MAKERESULT(Module_Libnx, LibnxError_OutOfMemory)) {
        size_t idle = wine_nx_release_idle_backing_pages(), scratch = 0;
        unsigned retries = 0;
        if (idle) {
            errno = saved_errno;
            result = __real_threadCreate(thread, entry, arg, stack, size, priority, core);
            saved_errno = errno; ++retries;
        }
        if (result == MAKERESULT(Module_Libnx, LibnxError_OutOfMemory)) {
            scratch = wine_nx_f1_release_idle_scratch(size);
            if (scratch) {
                errno = saved_errno;
                result = __real_threadCreate(thread, entry, arg, stack, size, priority, core);
                saved_errno = errno; ++retries;
            }
        }
        char message[256];
        snprintf(message, sizeof(message),
            "[F1-THREAD-RECOVER] bytes=%lu idle_released=%lu scratch_released=%lu retries=%u result=%08x",
            (unsigned long)size, (unsigned long)idle, (unsigned long)scratch, retries, (unsigned)result);
        wine_nx_runtime_trace(message);
        wine_nx_f1_crash_stage("thread-stack-retry", result, size, idle + scratch);
    }
    /* Graphics can consume every reclaimable FEX reserve. The exclusive native
     * stack pool survives that pressure and never changes the usable stack size. */
    errno = saved_errno;
    result = wine_nx_f1_native_stack_retry(result, thread, entry, arg, stack, size, priority, core);
    saved_errno = errno;
    if (R_FAILED(result)) {
        char message[240];
        snprintf(message, sizeof(message),
                 "[F1-THREAD] stage=libnx-create rc=%08x stack=%p bytes=%lu priority=%d core=%d",
                 (unsigned)result, stack, (unsigned long)size, priority, core);
        wine_nx_runtime_trace(message);
        wine_nx_f1_resource_snapshot("libnx-create-failed");
    }
    errno = saved_errno;
    return result;
}

int __wrap_pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                          void *(*entry)(void *), void *arg)
{
    int result = __real_pthread_create(thread, attr, entry, arg);
    int saved_errno = errno;
    if (result) {
        char message[192];
        snprintf(message, sizeof(message), "[F1-THREAD] stage=pthread-create errno=%d entry=%p",
                 result, (void *)(uintptr_t)entry);
        wine_nx_runtime_trace(message);
        wine_nx_f1_resource_snapshot("pthread-create-failed");
    }
    errno = saved_errno;
    return result;
}

void wine_nx_f1_thread_failure(const char *stage, unsigned status, unsigned long reserve,
                              unsigned long commit, int error)
{
    int saved_errno = errno;
    char message[240];
    snprintf(message, sizeof(message),
             "[F1-THREAD] stage=%s status=%08x reserve=%lu commit=%lu errno=%d",
             stage, status, reserve, commit, error);
    wine_nx_runtime_trace(message);
    wine_nx_f1_resource_snapshot(stage);
    errno = saved_errno;
}

void wine_nx_f1_game_thread_result(unsigned status, uintptr_t start)
{
    /* This F1 executable's CRT worker entry is pinned by the build receipt.
     * Hardware failed to start it at the circuit transition and kept rendering
     * the loading screen indefinitely. Report this specific resource failure;
     * an unrelated optional library thread or any successful retry is ignored. */
    if (status != 0xc0000017u || start != 0x00cae1b0u) return;
    int saved_errno = errno;
    wine_nx_f1_crash_stage("game-worker-no-memory", status, start, 0);
    wine_nx_runtime_trace("[F1-THREAD] F1 worker could not start after memory recovery; returning to launcher");
    wine_nx_f1_relaunch_request(F1_RETURN_RESOURCE, status);
    errno = saved_errno;
}
