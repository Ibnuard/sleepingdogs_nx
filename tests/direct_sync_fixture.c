/* Platform fixture for the actual FEXTendo direct-sync handlers. */
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include "horizon_threads.h"
#define TRUE 1
#define FALSE 0
#define TRACE(...) ((void)0)
#define STATUS_SUCCESS HORIZON_STATUS_SUCCESS
#define STATUS_NO_MEMORY HORIZON_STATUS_NO_MEMORY
#define STATUS_TIMEOUT HORIZON_STATUS_TIMEOUT
#define STATUS_USER_APC 0x000000c0u
#define SELECT_ALERTABLE 2
#define HORIZON_APC_CALL_SIZE 64
#define HORIZON_SERVER_WAIT_SLICE 200000LL
#define HORIZON_SERVER_POLL_INTERVAL 10000LL
typedef uint64_t u64;
typedef struct { long long QuadPart; } LARGE_INTEGER;
/* Host APC transport fixture; actual Wine protocol is compiled by the NRO build. */
struct user_apc { unsigned type, flags; unsigned long long func, args[3]; };
union apc_call { struct user_apc user; unsigned char bytes[HORIZON_APC_CALL_SIZE]; };
#include "f1_apc_queue.h"
struct horizon_server_object {
    int type, manual_reset, signaled;
    unsigned refs, count, max;
    struct horizon_mutex_state mutex;
    struct horizon_thread_state thread;
    struct horizon_server_object *thread_next;
    struct sd_sync_link *sd_waiters;
    struct f1_apc_queue f1_apcs;
    long long timer_when;
};
struct horizon_server_handle_entry { struct horizon_server_object *object; };
struct horizon_server_connection {
    int reply_fd;
    unsigned tid, pid;
    struct horizon_server_object *thread;
    void *direct_reply, *direct_data;
    size_t direct_size;
};
static struct horizon_server_object objects[16], threads[8];
static struct horizon_server_handle_entry handles[16];
static struct horizon_server_object *horizon_server_threads = threads;
static __thread struct horizon_server_connection *horizon_server_current;
static pthread_mutex_t horizon_server_objects_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t horizon_server_objects_cond = PTHREAD_COND_INITIALIZER;
static unsigned horizon_server_sleepers, freed_objects;
static unsigned long long f1_apc_delivered;
int wine_nx_fex_targeted_wake;
static __thread unsigned char pipe_reply[HORIZON_SERVER_FIXED_MESSAGE_SIZE];
static unsigned pipe_replies;
static unsigned int horizon_server_current_tid(void);
static void fex_sync_signal_object_locked(const void *object);
static long long clock_ticks(void) {
    struct timespec t; assert(!clock_gettime(CLOCK_REALTIME, &t));
    return (long long)t.tv_sec * 10000000 + t.tv_nsec / 100;
}
static void NtQueryPerformanceCounter(LARGE_INTEGER *n, void *f) { (void)f; n->QuadPart = clock_ticks(); }
static void NtQuerySystemTime(LARGE_INTEGER *n) { n->QuadPart = clock_ticks(); }
static unsigned condvarWaitTimeout(pthread_cond_t *c, pthread_mutex_t *m, u64 ns) {
    long long deadline = clock_ticks() + ns / 100;
    struct timespec t = { deadline / 10000000, deadline % 10000000 * 100 };
    int r = pthread_cond_timedwait(c, m, &t); assert(!r || r == ETIMEDOUT); return r;
}
static void horizon_server_update_timers_locked(void) {}
static void horizon_server_free_object(struct horizon_server_object *o) {
    assert(!o->refs && !o->sd_waiters); ++freed_objects;
}
static int horizon_server_write_reply(int fd, const void *r, size_t s, const void *d, size_t n) {
    (void)fd; (void)d; (void)n; assert(s <= sizeof(pipe_reply));
    memcpy(pipe_reply, r, s); __atomic_add_fetch(&pipe_replies, 1, __ATOMIC_RELAXED); return 0;
}
static struct horizon_server_handle_entry *horizon_server_find_handle_locked(unsigned h) {
    return h && h < 16 && handles[h].object ? handles + h : NULL;
}
static unsigned horizon_server_find_typed_object_locked(unsigned h, int type, struct horizon_server_object **out) {
    struct horizon_server_handle_entry *e = horizon_server_find_handle_locked(h);
    if (!e) return HORIZON_STATUS_INVALID_HANDLE;
    if (e->object->type != type) return HORIZON_STATUS_OBJECT_TYPE_MISMATCH;
    *out = e->object; return 0;
}
static unsigned horizon_server_wait_object_locked(unsigned h, int consume) {
    struct horizon_server_handle_entry *e;
    struct horizon_server_object *o;
    unsigned tid = horizon_server_current_tid();
    if (h == HORIZON_CURRENT_THREAD_HANDLE) return HORIZON_STATUS_TIMEOUT;
    if (!(e = horizon_server_find_handle_locked(h))) return HORIZON_STATUS_INVALID_HANDLE;
    o = e->object;
    if (o->type == HORIZON_SERVER_OBJECT_MUTEX) {
        if (!horizon_mutex_signaled(&o->mutex, tid)) return HORIZON_STATUS_TIMEOUT;
        return consume && horizon_mutex_acquire(&o->mutex, tid) ? HORIZON_STATUS_ABANDONED_WAIT_0 : 0;
    }
    if (o->type == HORIZON_SERVER_OBJECT_SEMAPHORE) {
        if (!o->count) return HORIZON_STATUS_TIMEOUT;
        if (consume) --o->count;
        return 0;
    }
    if (o->type == HORIZON_SERVER_OBJECT_THREAD) return o->thread.terminated ? 0 : HORIZON_STATUS_TIMEOUT;
    if (!o->signaled) return HORIZON_STATUS_TIMEOUT;
    if (consume && !o->manual_reset) o->signaled = 0;
    return 0;
}
