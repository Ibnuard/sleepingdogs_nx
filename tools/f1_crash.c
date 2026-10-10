/* LGPL-2.1-or-later. Bounded, persistent F1 crash breadcrumbs.
 * The fatal path uses a preopened private IPC session: no malloc, stdio,
 * Wine calls or shared log mutex. Supplementary checked frame reads happen
 * only after the primary record has been flushed.
 * A kernel/GPU kill may bypass all handlers; completed checkpoints survive it. */
#include <switch.h>
#include <errno.h>
#include <stdint.h>
#include <stddef.h>
#include "f1_relaunch.h"

#define F1_CRASH_BYTES 32768
#define F1_EVENT_BASE 1024
#define F1_EVENT_BYTES 256
#define F1_EVENT_COUNT 64
#define F1_FATAL_BASE (F1_EVENT_BASE + F1_EVENT_COUNT * F1_EVENT_BYTES)
#define F1_FATAL_BYTES 4096

static FsFile f1_crash_owner, f1_crash_events, f1_crash_fatal;
static unsigned f1_crash_ready, f1_crash_busy, f1_crash_sequence, f1_crash_dropped;
static unsigned f1_crash_fatal_claimed;
static Result f1_crash_write_error;

struct f1_text { char *data; size_t used, capacity; };
static void f1_text_add(struct f1_text *b, const char *s)
{
    if (!s) s = "<null>";
    while (*s && b->used + 1 < b->capacity) b->data[b->used++] = *s++;
}
static void f1_text_number(struct f1_text *b, uint64_t n, unsigned base)
{
    static const char digits[] = "0123456789abcdef";
    char reversed[32]; unsigned count = 0;
    do { reversed[count++] = digits[n % base]; n /= base; } while (n);
    while (count && b->used + 1 < b->capacity) b->data[b->used++] = reversed[--count];
}
static void f1_text_value(struct f1_text *b, const char *key, uint64_t value)
{
    f1_text_add(b, key); f1_text_add(b, "0x"); f1_text_number(b, value, 16);
}
static void f1_text_finish(struct f1_text *b)
{
    while (b->used + 1 < b->capacity) b->data[b->used++] = ' ';
    b->data[b->used++] = '\n';
}

#include "f1_crash_detail.h"

/* A clone has its own kernel session, so fsFileWrite bypasses libnx's shared
 * filesystem session pool. Keep the original domain object alive until exit. */
unsigned wine_nx_f1_crash_init(int debug, int renderer, int profile)
{
    int saved_errno = errno;
    FsFileSystem *sd = fsdevGetDeviceFileSystem("sdmc");
    Result rc = 0;
    char blank[512];
    if (__atomic_load_n(&f1_crash_ready, __ATOMIC_ACQUIRE)) return 0;
    if (!sd) { errno = saved_errno; return 0xf001u; }
    /* Only our two diagnostic files are rotated; never game/save/config data. */
    FsDirEntryType type;
    if (R_SUCCEEDED(fsFsGetEntryType(sd, "/switch/f1-fex/crash.log", &type))) {
        if (R_SUCCEEDED(fsFsGetEntryType(sd, "/switch/f1-fex/crash-previous.log", &type))) {
            rc = fsFsDeleteFile(sd, "/switch/f1-fex/crash-previous.log");
            if (R_FAILED(rc)) goto done;
        }
        rc = fsFsRenameFile(sd, "/switch/f1-fex/crash.log", "/switch/f1-fex/crash-previous.log");
        if (R_FAILED(rc)) goto done;
    }
    rc = fsFsCreateFile(sd, "/switch/f1-fex/crash.log", F1_CRASH_BYTES, 0);
    if (R_FAILED(rc)) goto done;
    rc = fsFsOpenFile(sd, "/switch/f1-fex/crash.log", FsOpenMode_Write, &f1_crash_owner);
    if (R_FAILED(rc)) goto done;
    rc = serviceClone(&f1_crash_owner.s, &f1_crash_events.s);
    if (R_FAILED(rc)) goto close_owner;
    rc = serviceClone(&f1_crash_owner.s, &f1_crash_fatal.s);
    if (R_FAILED(rc)) goto close_events;
    for (unsigned i = 0; i < sizeof(blank); ++i) blank[i] = ' ';
    blank[sizeof(blank)-1] = '\n';
    for (unsigned at = 0; at < F1_CRASH_BYTES; at += sizeof(blank)) {
        rc = fsFileWrite(&f1_crash_events, at, blank, sizeof(blank), FsWriteOption_None);
        if (R_FAILED(rc)) goto close_fatal;
    }
    struct f1_text b = {blank, 0, sizeof(blank)};
    f1_text_add(&b, "FEXTendo F1 2013 / crash.log / 0.1.28\n");
    f1_text_add(&b, "build=f1-fextendo-0.1.28-memory-map renderer=");
    f1_text_add(&b, renderer == 1 ? "DXVK 2.7.1 Async" : "DXVK 3.1.1");
    static const char *profiles[] = {"Balanced", "Low latency", "Stable", "Quality"};
    f1_text_add(&b, " profile=");
    f1_text_add(&b, profile >= 0 && profile < 4 ? profiles[profile] : "unknown");
    f1_text_add(&b, debug ? " mode=debug\n" : " mode=gui\n");
    f1_text_value(&b, "native_anchor_wine_nx_f1_crash_init=", (uintptr_t)wine_nx_f1_crash_init);
    f1_text_value(&b, " launch_tick=", armGetSystemTick());
    f1_text_add(&b, "\nCheckpoints are not proof of a rendered frame. Blank fatal section means no fatal hook ran.\n");
    f1_text_finish(&b);
    rc = fsFileWrite(&f1_crash_events, 0, blank, sizeof(blank), FsWriteOption_Flush);
    if (R_FAILED(rc)) goto close_fatal;
    __atomic_store_n(&f1_crash_ready, 1, __ATOMIC_RELEASE);
    goto done;
close_fatal:
    serviceClose(&f1_crash_fatal.s);
close_events:
    serviceClose(&f1_crash_events.s);
close_owner:
    fsFileClose(&f1_crash_owner);
done:
    errno = saved_errno;
    return rc;
}

static void f1_crash_write_normal(unsigned offset, const char *record, size_t bytes)
{
    Result rc = fsFileWrite(&f1_crash_events, offset, record, bytes, FsWriteOption_Flush);
    if (R_FAILED(rc)) __atomic_store_n(&f1_crash_write_error, rc, __ATOMIC_RELAXED);
}

void wine_nx_f1_crash_note(const char *message)
{
    int saved_errno = errno;
    if (!__atomic_load_n(&f1_crash_ready, __ATOMIC_ACQUIRE)) return;
    if (__atomic_exchange_n(&f1_crash_busy, 1, __ATOMIC_ACQUIRE)) {
        __atomic_add_fetch(&f1_crash_dropped, 1, __ATOMIC_RELAXED); return;
    }
    char record[F1_EVENT_BYTES];
    struct f1_text b = {record, 0, sizeof(record)};
    unsigned serial = ++f1_crash_sequence;
    f1_text_add(&b, "event="); f1_text_number(&b, serial, 10);
    f1_text_value(&b, " tick=", armGetSystemTick());
    f1_text_add(&b, " "); f1_text_add(&b, message); f1_text_finish(&b);
    f1_crash_write_normal(F1_EVENT_BASE + ((serial-1) % F1_EVENT_COUNT)*F1_EVENT_BYTES, record, sizeof(record));
    __atomic_store_n(&f1_crash_busy, 0, __ATOMIC_RELEASE);
    errno = saved_errno;
}

void wine_nx_f1_crash_resource(uint64_t threads, unsigned query_rc, uint64_t used,
                             uint64_t arena_free, uint64_t arena, uint64_t capacity)
{
    int saved_errno = errno;
    if (!__atomic_load_n(&f1_crash_ready, __ATOMIC_ACQUIRE) ||
        __atomic_exchange_n(&f1_crash_busy, 1, __ATOMIC_ACQUIRE)) return;
    char record[512]; struct f1_text b = {record, 0, sizeof(record)};
    f1_text_value(&b, "RESOURCE tick=", armGetSystemTick());
    f1_text_value(&b, " free_threads=", threads); f1_text_value(&b, " query_rc=", query_rc);
    f1_text_value(&b, "\nheap_used=", used); f1_text_value(&b, " arena_free=", arena_free);
    f1_text_value(&b, " arena=", arena); f1_text_value(&b, " capacity=", capacity);
    f1_text_value(&b, " unclaimed=", capacity > arena ? capacity-arena : 0);
    f1_text_value(&b, "\nlast_write_rc=", __atomic_load_n(&f1_crash_write_error, __ATOMIC_RELAXED));
    f1_text_value(&b, " dropped_events=", __atomic_load_n(&f1_crash_dropped, __ATOMIC_RELAXED));
    f1_text_finish(&b); f1_crash_write_normal(512, record, sizeof(record));
    __atomic_store_n(&f1_crash_busy, 0, __ATOMIC_RELEASE); errno = saved_errno;
}

void wine_nx_f1_crash_stage(const char *stage, int result, unsigned long long a, unsigned long long b)
{
    char text[192]; struct f1_text out = {text, 0, sizeof(text)};
    f1_text_add(&out, stage); f1_text_value(&out, " result=", (uint32_t)result);
    f1_text_value(&out, " a=", a); f1_text_value(&out, " b=", b);
    text[out.used] = 0; wine_nx_f1_crash_note(text);
}

static void f1_crash_terminal_record(const char *kind, const char *reason, uint64_t code,
                                   uint64_t address, uint64_t size, uintptr_t caller,
                                   const ThreadExceptionDump *ctx, uintptr_t fp)
{
    if (!__atomic_load_n(&f1_crash_ready, __ATOMIC_ACQUIRE) ||
        __atomic_exchange_n(&f1_crash_fatal_claimed, 1, __ATOMIC_ACQ_REL)) return;
    int saved_errno = errno;
    char record[F1_FATAL_BYTES]; struct f1_text b = {record, 0, sizeof(record)};
    f1_text_add(&b, kind); f1_text_add(&b, " reason="); f1_text_add(&b, reason);
    f1_text_value(&b, " code=", code); f1_text_value(&b, " caller=", caller);
    f1_text_value(&b, "\naddress=", address); f1_text_value(&b, " size=", size);
    f1_text_value(&b, " tick=", armGetSystemTick());
    if (ctx) {
        f1_text_value(&b, "\nerror_desc=", ctx->error_desc); f1_text_value(&b, " esr=", ctx->esr);
        f1_text_value(&b, " pstate=", ctx->pstate); f1_text_value(&b, " far=", ctx->far.x);
        f1_text_value(&b, "\npc=", ctx->pc.x); f1_text_value(&b, " lr=", ctx->lr.x);
        f1_text_value(&b, " sp=", ctx->sp.x); f1_text_value(&b, " fp=", ctx->fp.x);
        for (unsigned i = 0; i < 29; ++i) {
            f1_text_add(&b, (i % 4) ? " x" : "\nx"); f1_text_number(&b, i, 10);
            f1_text_value(&b, "=", ctx->cpu_gprs[i].x);
        }
    }
    f1_text_add(&b, "\nEnd of terminal record. Native addresses use the matching build ELF.\n");
    f1_text_finish(&b);
    /* Separate session and reserved region: safe even if interrupted inside
     * the ordinary checkpoint writer. Never acquire its lock here. */
    fsFileWrite(&f1_crash_fatal, F1_FATAL_BASE, record, sizeof(record), FsWriteOption_Flush);
    f1_crash_native_detail(fp);
    errno = saved_errno;
}

static void f1_crash_fatal_record(const char *reason, uint64_t code, uint64_t address,
                                uint64_t size, uintptr_t caller, const ThreadExceptionDump *ctx, uintptr_t fp)
{
    f1_crash_terminal_record("FATAL",reason,code,address,size,caller,ctx,fp);
}

void wine_nx_f1_crash_exception(const void *dump, unsigned status)
{
    const ThreadExceptionDump *ctx = dump;
    f1_crash_fatal_record("unhandled-native-exception", status, ctx->far.x, 0, ctx->pc.x, ctx, ctx->fp.x);
    wine_nx_f1_relaunch_fatal(F1_RETURN_EXCEPTION, status);
}

extern void __real_abort(void) __attribute__((noreturn));
void __wrap_abort(void)
{
    f1_crash_fatal_record("abort", 0, 0, 0, (uintptr_t)__builtin_return_address(0), NULL, (uintptr_t)__builtin_frame_address(0));
    wine_nx_f1_relaunch_fatal(F1_RETURN_ABORT, 0);
    __real_abort();
}
extern void __real_diagAbortWithResult(Result) __attribute__((noreturn));
void __wrap_diagAbortWithResult(Result rc)
{
    f1_crash_fatal_record("diagAbortWithResult", rc, 0, 0, (uintptr_t)__builtin_return_address(0), NULL, (uintptr_t)__builtin_frame_address(0));
    wine_nx_f1_relaunch_fatal(F1_RETURN_ABORT, rc);
    __real_diagAbortWithResult(rc);
}
extern Result __real_svcBreak(u32, uintptr_t, uintptr_t);
Result __wrap_svcBreak(u32 reason, uintptr_t address, uintptr_t size)
{
    if (!(reason & BreakReason_NotificationOnlyFlag)) {
        f1_crash_fatal_record("svcBreak", reason, address, size, (uintptr_t)__builtin_return_address(0), NULL, (uintptr_t)__builtin_frame_address(0));
        wine_nx_f1_relaunch_fatal(F1_RETURN_ABORT, reason);
    }
    return __real_svcBreak(reason, address, size);
}

/* exit/_exit may terminate before an exception/abort hook. Record the caller
 * separately from fatal faults: an exit status of zero can be intentional. */
extern void __real_exit(int) __attribute__((noreturn));
void __wrap_exit(int status)
{
    f1_crash_terminal_record("EXIT","native-exit",(unsigned)status,0,0,
                            (uintptr_t)__builtin_return_address(0),NULL,(uintptr_t)__builtin_frame_address(0));
    wine_nx_f1_relaunch_fatal(F1_RETURN_NATIVE_EXIT, (unsigned)status);
    __real_exit(status);
}
extern void __real__exit(int) __attribute__((noreturn));
void __wrap__exit(int status)
{
    f1_crash_terminal_record("EXIT","native-_exit",(unsigned)status,0,0,
                            (uintptr_t)__builtin_return_address(0),NULL,(uintptr_t)__builtin_frame_address(0));
    wine_nx_f1_relaunch_fatal(F1_RETURN_NATIVE_EXIT, (unsigned)status);
    __real__exit(status);
}
