/* Bounded startup observations. No allocation, guest-memory reads or I/O on
 * the observed path. This records the latest boundary, not a call stack:
 * callbacks can unwind past a native dispatcher frame. LGPL-2.1-or-later. */
#ifndef F1_STARTUP_WATCH_H
#define F1_STARTUP_WATCH_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <pthread.h>
#ifdef __SWITCH__
#include <switch/arm/counter.h>
#endif

#define F1_WATCH_THREADS 128
#define F1_WATCH_PATH 192
struct f1_watch_row {
    uint32_t tid, id, active, status;
    uint64_t serial, begin, end, calls, completed, args[8];
    uint32_t file_active, file_status, file_kind, file_length;
    uint64_t file_handle, file_begin, file_end, file_serial;
    char path[F1_WATCH_PATH];
};
extern int f1_startup_watch_enabled;
uint64_t f1_watch_begin(uint32_t tid, uint32_t id, const uint64_t args[8], uint64_t now);
void f1_watch_end(uint32_t tid, uint64_t serial, uint32_t status, uint64_t now);
uint64_t f1_watch_file_begin(uint32_t tid, const char *path, uint64_t handle,
                            uint32_t length, uint64_t now);
void f1_watch_file_end(uint32_t tid, uint64_t serial, uint64_t handle,
                       uint32_t status, uint64_t now);
int f1_watch_snapshot(struct f1_watch_row *out, unsigned capacity, unsigned *overflow);
const char *f1_watch_syscall_name(unsigned id);

#ifdef F1_STARTUP_WATCH_IMPLEMENTATION
int f1_startup_watch_enabled;
static pthread_mutex_t f1_watch_mutex = PTHREAD_MUTEX_INITIALIZER;
static struct f1_watch_row f1_watch_rows[F1_WATCH_THREADS];
static unsigned f1_watch_overflow;
static uint64_t f1_watch_serial;
static struct { uint64_t handle; char path[F1_WATCH_PATH]; } f1_watch_files[256];
static unsigned f1_watch_next_file;

/* Called only with f1_watch_mutex. Never log or call a guest/native service
 * under this mutex; the reader copies the data then unlocks before logging. */
static struct f1_watch_row *f1_watch_row_for(uint32_t tid)
{
    unsigned i, empty = F1_WATCH_THREADS;
    if (!tid) return NULL;
    for (i = 0; i < F1_WATCH_THREADS; ++i) {
        if (f1_watch_rows[i].tid == tid) return &f1_watch_rows[i];
        if (!f1_watch_rows[i].tid && empty == F1_WATCH_THREADS) empty = i;
    }
    if (empty == F1_WATCH_THREADS) { ++f1_watch_overflow; return NULL; }
    f1_watch_rows[empty].tid = tid;
    return &f1_watch_rows[empty];
}

uint64_t f1_watch_begin(uint32_t tid, uint32_t id, const uint64_t args[8], uint64_t now)
{
    uint64_t serial = 0;
    if (!__atomic_load_n(&f1_startup_watch_enabled, __ATOMIC_RELAXED)) return 0;
    pthread_mutex_lock(&f1_watch_mutex);
    struct f1_watch_row *r = f1_watch_row_for(tid);
    if (r) {
        serial = r->serial = ++f1_watch_serial;
        r->id = id; r->active = 1; r->status = UINT32_MAX; r->begin = now; r->end = 0;
        ++r->calls; memcpy(r->args, args, sizeof(r->args));
    }
    pthread_mutex_unlock(&f1_watch_mutex);
    return serial;
}

void f1_watch_end(uint32_t tid, uint64_t serial, uint32_t status, uint64_t now)
{
    if (!serial) return;
    pthread_mutex_lock(&f1_watch_mutex);
    struct f1_watch_row *r = f1_watch_row_for(tid);
    if (r) {
        ++r->completed;
        /* A callback may have published a newer boundary. Do not overwrite it. */
        if (r->serial == serial) { r->active = 0; r->status = status; r->end = now; }
    }
    pthread_mutex_unlock(&f1_watch_mutex);
}

uint64_t f1_watch_file_begin(uint32_t tid, const char *path, uint64_t handle,
                            uint32_t length, uint64_t now)
{
    uint64_t serial = 0;
    if (!__atomic_load_n(&f1_startup_watch_enabled, __ATOMIC_RELAXED)) return 0;
    pthread_mutex_lock(&f1_watch_mutex);
    struct f1_watch_row *r = f1_watch_row_for(tid);
    if (r) {
        serial = r->file_serial = ++f1_watch_serial;
        r->file_active = 1; r->file_status = UINT32_MAX; r->file_kind = path ? 1 : 2;
        r->file_begin = now; r->file_end = 0;
        r->file_handle = handle; r->file_length = length; r->path[0] = 0;
        if (!path) {
            /* Most recent match wins if Wine has reused a handle. */
            for (unsigned n = 0; n < 256 && n < f1_watch_next_file; ++n) {
                unsigned j = (f1_watch_next_file - 1 - n) % 256;
                if (f1_watch_files[j].handle == handle) { path = f1_watch_files[j].path; break; }
            }
        }
        if (path) {
            size_t len = strnlen(path,F1_WATCH_PATH-1);
            memcpy(r->path,path,len); r->path[len] = 0;
        }
    }
    pthread_mutex_unlock(&f1_watch_mutex);
    return serial;
}

void f1_watch_file_end(uint32_t tid, uint64_t serial, uint64_t handle,
                       uint32_t status, uint64_t now)
{
    if (!serial) return;
    pthread_mutex_lock(&f1_watch_mutex);
    struct f1_watch_row *r = f1_watch_row_for(tid);
    if (r && r->file_serial == serial) {
        r->file_active = 0; r->file_status = status; r->file_end = now;
        r->file_handle = handle;
        if (r->file_kind == 1 && !status && handle) {
            unsigned j = f1_watch_next_file++ % 256;
            f1_watch_files[j].handle = handle;
            memcpy(f1_watch_files[j].path, r->path, F1_WATCH_PATH);
        }
    }
    pthread_mutex_unlock(&f1_watch_mutex);
}

int f1_watch_snapshot(struct f1_watch_row *out, unsigned capacity, unsigned *overflow)
{
    unsigned n = 0;
    if (pthread_mutex_trylock(&f1_watch_mutex)) return -1;
    for (unsigned i = 0; i < F1_WATCH_THREADS && n < capacity; ++i)
        if (f1_watch_rows[i].tid) out[n++] = f1_watch_rows[i];
    *overflow = f1_watch_overflow;
    pthread_mutex_unlock(&f1_watch_mutex);
    return (int)n;
}
#endif
#endif
