/* LGPL-2.1-or-later.
 * A small, private reserve prevents late 1 MiB Wine native stacks from depending
 * on the largest remaining malloc hole. Blocks stay in normal Horizon heap
 * memory; libnx still creates, maps, starts and closes every thread.
 *
 * libnx 4.12.0 caller-supplied stacks include TLS/reent, unlike NULL stacks.
 * Keep its padding calculation and add the 48-byte entry record before page
 * rounding, leaving at least the requested 1 MiB usable native stack.
 */
#include "f1_native_stacks.h"
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/reent.h>

extern unsigned char __tls_start[], __tls_end[];
extern size_t __tls_align;
extern void *__libnx_aligned_alloc(size_t, size_t);
extern Result __real_threadCreate(Thread *, ThreadFunc, void *, void *, size_t, int, int);
extern Result __real_threadClose(Thread *);
extern void wine_nx_runtime_trace(const char *);

enum { F1_STACK_COUNT = 16, F1_STACK_BYTES = 1024 * 1024, F1_STACK_PAGE = 4096 };
enum f1_stack_state { F1_STACK_EMPTY, F1_STACK_IDLE, F1_STACK_CREATING,
                      F1_STACK_ACTIVE, F1_STACK_CLOSING, F1_STACK_QUARANTINED };
struct f1_native_stack {
    void *memory;
    Thread *owner;
    enum f1_stack_state state;
};
static struct f1_native_stack f1_native_stacks[F1_STACK_COUNT];
static Mutex f1_native_stack_mutex;
static unsigned f1_native_stack_initialized;
static size_t f1_native_stack_bytes;
static unsigned f1_native_stack_recovered, f1_native_stack_exhausted;

/* Called only while this slot is reserved for our operation. Source heap pages
 * must be writable and unborrowed before reuse. threadCreate ignores the Result
 * of rollback svcUnmapMemory; a failed rollback must never recycle that block.
 * Examine the complete allocation, including split MemoryInfo regions. */
static int f1_native_stack_is_unmapped(void *memory, size_t bytes)
{
    uintptr_t cursor = (uintptr_t)memory, end = cursor + bytes;
    if (!memory || end < cursor) return 0;
    while (cursor < end) {
        MemoryInfo info;
        u32 page_info;
        if (R_FAILED(svcQueryMemory(&info, &page_info, cursor)) || info.addr > cursor ||
            info.size > UINTPTR_MAX - info.addr || info.addr + info.size <= cursor ||
            (info.type & MemState_Type) != MemType_Heap || info.perm != Perm_Rw ||
            info.attr || info.ipc_refcount || info.device_refcount) return 0;
        cursor = info.addr + info.size;
    }
    return 1;
}

void wine_nx_f1_native_stacks_snapshot(void)
{
    int saved_errno = errno;
    unsigned reserved = 0, idle = 0, active = 0, quarantine = 0;
    mutexLock(&f1_native_stack_mutex);
    for (unsigned i = 0; i < F1_STACK_COUNT; ++i) {
        enum f1_stack_state state = f1_native_stacks[i].state;
        reserved += state != F1_STACK_EMPTY;
        idle += state == F1_STACK_IDLE;
        active += state == F1_STACK_ACTIVE || state == F1_STACK_CREATING || state == F1_STACK_CLOSING;
        quarantine += state == F1_STACK_QUARANTINED;
    }
    size_t bytes = f1_native_stack_bytes;
    unsigned recovered = f1_native_stack_recovered, exhausted = f1_native_stack_exhausted;
    mutexUnlock(&f1_native_stack_mutex);
    char message[256];
    snprintf(message, sizeof(message),
        "[F1-NATIVE-STACKS] reserved=%u idle=%u inuse=%u quarantine=%u bytes=%lu recoveries=%u exhausted=%u",
        reserved, idle, active, quarantine, (unsigned long)(bytes * reserved), recovered, exhausted);
    wine_nx_runtime_trace(message);
    errno = saved_errno;
}

void wine_nx_f1_native_stacks_init(void)
{
    int saved_errno = errno;
    mutexLock(&f1_native_stack_mutex);
    if (f1_native_stack_initialized) {
        mutexUnlock(&f1_native_stack_mutex);
        errno = saved_errno;
        return;
    }
    f1_native_stack_initialized = 1; /* initialization in progress */
    mutexUnlock(&f1_native_stack_mutex);

    size_t tls = ((uintptr_t)__tls_end - (uintptr_t)__tls_start + 15u) & ~(size_t)15u;
    size_t reent = (sizeof(struct _reent) + 15u) & ~(size_t)15u;
    size_t alignment = __tls_align > 2u * sizeof(void *) ? __tls_align : 2u * sizeof(void *);
    /* These are bounded by the linked binary. Refuse malformed/unsupported TLS
     * metadata instead of reserving a wrapped or unexpectedly huge allocation. */
    size_t bytes = 0;
    if (alignment && !(alignment & (alignment - 1u)) && alignment <= F1_STACK_PAGE &&
        tls <= F1_STACK_BYTES && reent <= F1_STACK_BYTES) {
        size_t needed = (tls + reent + alignment - 1u) & ~(alignment - 1u);
        bytes = (F1_STACK_BYTES + needed + 6u * sizeof(void *) + F1_STACK_PAGE - 1u) &
                ~(size_t)(F1_STACK_PAGE - 1u);
    }
    mutexLock(&f1_native_stack_mutex);
    f1_native_stack_bytes = bytes;
    mutexUnlock(&f1_native_stack_mutex);
    if (bytes) for (unsigned i = 0; i < F1_STACK_COUNT; ++i) {
        void *memory = __libnx_aligned_alloc(F1_STACK_PAGE, bytes);
        if (!memory) break; /* partial reserve remains useful; no retry storm */
        int reusable = f1_native_stack_is_unmapped(memory, bytes);
        mutexLock(&f1_native_stack_mutex);
        f1_native_stacks[i].memory = memory;
        f1_native_stacks[i].state = reusable ? F1_STACK_IDLE : F1_STACK_QUARANTINED;
        mutexUnlock(&f1_native_stack_mutex);
    }
    mutexLock(&f1_native_stack_mutex);
    f1_native_stack_initialized = 2;
    mutexUnlock(&f1_native_stack_mutex);
    wine_nx_f1_native_stacks_snapshot();
    errno = saved_errno;
}

Result wine_nx_f1_native_stack_retry(Result previous, Thread *thread, ThreadFunc entry,
                                   void *arg, void *stack, size_t size, int priority, int core)
{
    int saved_errno = errno;
    if (previous != MAKERESULT(Module_Libnx, LibnxError_OutOfMemory) ||
        stack || size != F1_STACK_BYTES) return previous;
    struct f1_native_stack *slot = NULL;
    mutexLock(&f1_native_stack_mutex);
    if (f1_native_stack_initialized == 2) {
        for (unsigned i = 0; i < F1_STACK_COUNT; ++i) {
            if (f1_native_stacks[i].state == F1_STACK_IDLE) {
                slot = &f1_native_stacks[i];
                slot->state = F1_STACK_CREATING;
                slot->owner = thread;
                break;
            }
        }
        if (!slot) ++f1_native_stack_exhausted;
    }
    mutexUnlock(&f1_native_stack_mutex);
    if (!slot) { errno = saved_errno; return previous; }

    errno = saved_errno;
    Result result = __real_threadCreate(thread, entry, arg, slot->memory,
                                       f1_native_stack_bytes, priority, core);
    saved_errno = errno;
    int reusable = R_FAILED(result) && f1_native_stack_is_unmapped(slot->memory, f1_native_stack_bytes);
    mutexLock(&f1_native_stack_mutex);
    if (R_SUCCEEDED(result)) {
        slot->state = F1_STACK_ACTIVE;
        ++f1_native_stack_recovered;
    } else {
        slot->owner = NULL;
        slot->state = reusable ? F1_STACK_IDLE : F1_STACK_QUARANTINED;
    }
    mutexUnlock(&f1_native_stack_mutex);
    char message[192];
    snprintf(message, sizeof(message),
        "[F1-NATIVE-STACK-RECOVER] requested=%lu backing=%lu result=%08x reusable=%u",
        (unsigned long)size, (unsigned long)f1_native_stack_bytes, (unsigned)result, (unsigned)reusable);
    wine_nx_runtime_trace(message);
    errno = saved_errno;
    return result;
}

Result __wrap_threadClose(Thread *thread)
{
    int saved_errno = errno;
    struct f1_native_stack *slot = NULL;
    mutexLock(&f1_native_stack_mutex);
    for (unsigned i = 0; i < F1_STACK_COUNT; ++i) {
        struct f1_native_stack *candidate = &f1_native_stacks[i];
        if (candidate->state == F1_STACK_ACTIVE && candidate->owner == thread &&
            thread->stack_mem == candidate->memory && !thread->owns_stack_mem) {
            slot = candidate;
            slot->state = F1_STACK_CLOSING;
            break;
        }
    }
    mutexUnlock(&f1_native_stack_mutex);
    errno = saved_errno;
    Result result = __real_threadClose(thread);
    saved_errno = errno;
    if (slot) {
        int reusable = R_SUCCEEDED(result) &&
            f1_native_stack_is_unmapped(slot->memory, f1_native_stack_bytes);
        mutexLock(&f1_native_stack_mutex);
        slot->owner = NULL;
        slot->state = reusable ? F1_STACK_IDLE : F1_STACK_QUARANTINED;
        mutexUnlock(&f1_native_stack_mutex);
        if (!reusable) {
            char message[160];
            snprintf(message, sizeof(message), "[F1-NATIVE-STACK-QUARANTINE] close_result=%08x bytes=%lu",
                     (unsigned)result, (unsigned long)f1_native_stack_bytes);
            wine_nx_runtime_trace(message);
        }
    }
    errno = saved_errno;
    return result;
}
