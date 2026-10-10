/* Production staging/apply functions, pinned Wine ABI, concurrent start gate. */
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include "ntstatus.h"
#define WIN32_NO_STATUS
#include "windef.h"
#include "winternl.h"
#include "horizon_threads.h"
#include "sd_thread_debug.h"

struct horizon_server_object {
    struct horizon_thread_state thread;
    struct sd_thread_debug sd_debug;
    struct horizon_server_object *thread_next;
};
static struct horizon_server_object objects[2], *horizon_server_threads;
static pthread_mutex_t horizon_server_objects_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t start_gate = PTHREAD_COND_INITIALIZER;
static TEB caller_teb;
static int closed;
#undef NtCurrentTeb
#define NtCurrentTeb() (&caller_teb)
#define HORIZON_SERVER_OBJECT_THREAD 1
static unsigned horizon_server_find_typed_object_locked(unsigned handle, int type,
                                                         struct horizon_server_object **object)
{
    assert(type == HORIZON_SERVER_OBJECT_THREAD);
    if (handle == 0x50) return STATUS_OBJECT_TYPE_MISMATCH;
    if (closed || (handle != 0x40 && handle != 0x44 && handle != 0x48)) return STATUS_INVALID_HANDLE;
    *object = &objects[handle == 0x44]; return 0;
}
static TEB32 *get_wow_teb(TEB *teb)
{
    return teb->WowTebOffset ? (TEB32 *)((char *)teb + teb->WowTebOffset) : NULL;
}
#include "sd_thread_debug.inc"

struct child_state {
    TEB teb;
    unsigned char guard1[32];
    TEB32 wow;
    unsigned char guard2[32];
    I386_CONTEXT context;
} child;

static I386_CONTEXT debug_context(unsigned iteration)
{
    I386_CONTEXT c;
    memset(&c, 0xa5, sizeof(c)); c.ContextFlags = CONTEXT_I386_DEBUG_REGISTERS;
    c.Dr0 = 0x4c0a8a; c.Dr1 = 0x5b2e92; c.Dr2 = 0x61ce88;
    c.Dr3 = 0x68d35a; c.Dr6 = iteration; c.Dr7 = 0x155;
    return c;
}

static void reset(void)
{
    memset(objects, 0, sizeof(objects)); memset(&caller_teb, 0, sizeof(caller_teb));
    caller_teb.ClientId.UniqueProcess = (HANDLE)12; caller_teb.ClientId.UniqueThread = (HANDLE)4;
    for (unsigned i = 0; i < 2; ++i) {
        horizon_thread_init(&objects[i].thread, 76 + i * 4, 12, 15, 0);
        objects[i].thread.suspend = 1;
    }
    objects[0].thread_next = &objects[1]; horizon_server_threads = objects; closed = 0;
    memset(&child, 0x5a, sizeof(child)); memset(&child.teb, 0, sizeof(child.teb));
    child.teb.ClientId.UniqueProcess = (HANDLE)12; child.teb.ClientId.UniqueThread = (HANDLE)76;
    child.teb.WowTebOffset = (char *)&child.wow - (char *)&child.teb;
}

static void apply_and_check(const I386_CONTEXT *incoming)
{
    I386_CONTEXT initial;
    TEB32 initial_wow = child.wow;
    /* Reproduce runtime initialization AFTER pending SetContext. */
    memset(&child.context, 0, sizeof(child.context)); child.context.ContextFlags = CONTEXT_I386_ALL;
    child.context.Eip = 0x7bc5e830; child.context.Esp = 0x745fff0;
    child.context.Eax = 0x549430; child.context.Ebx = 0x59ad0c30; initial = child.context;
    assert(sd_wow64_apply_start_debug(&child.teb, &child.context));
    assert(!sd_wow64_apply_start_debug(&child.teb, &child.context));
    assert(!memcmp(&incoming->Dr0, &child.context.Dr0, 24));
    memcpy(&initial.Dr0, &incoming->Dr0, 24); assert(!memcmp(&initial, &child.context, sizeof(initial)));
    memcpy((char *)&initial_wow + 0x1dc, &incoming->Dr0, 24);
    assert(!memcmp(&initial_wow, &child.wow, sizeof(initial_wow)));
    for (unsigned i = 0; i < 32; ++i) assert(child.guard1[i] == 0x5a && child.guard2[i] == 0x5a);
    assert(!objects[0].sd_debug.valid && !objects[1].sd_debug.valid);
}

static void *start_child(void *arg)
{
    pthread_mutex_lock(&horizon_server_objects_mutex);
    objects[0].thread.teb = (ULONG_PTR)&child.teb;
    while (!horizon_thread_may_start(&objects[0].thread))
        pthread_cond_wait(&start_gate, &horizon_server_objects_mutex);
    objects[0].thread.started = 1;
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    apply_and_check(arg);
    return NULL;
}

int main(void)
{
    I386_CONTEXT input = debug_context(9), queried, expected;
    struct horizon_server_object untouched;
    reset(); untouched = objects[1]; queried = input; expected = input;
    memset(&expected.Dr0, 0, 24);
    assert(!sd_wow64_remote_debug_context((HANDLE)0x40, &queried, FALSE));
    assert(!memcmp(&queried, &expected, sizeof(queried)));
    assert(!objects[0].thread.teb && !objects[0].sd_debug.valid);
    assert(!sd_wow64_remote_debug_context((HANDLE)0x40, &input, TRUE));
    queried = expected;
    assert(!sd_wow64_remote_debug_context((HANDLE)0x48, &queried, FALSE));
    assert(!memcmp(&queried, &input, sizeof(queried)));
    assert(!memcmp(&objects[1], &untouched, sizeof(untouched)));
    assert(objects[0].thread.suspend == 1);
    objects[0].thread.teb = (ULONG_PTR)&child.teb; objects[0].thread.started = 1;
    apply_and_check(&input);
    puts("PASS pre-TEB staging, initial zeros, alias handles, debug-only writes, startup reset/cache, one-shot apply");

    for (unsigned flags = 0; flags < 64; ++flags) {
        reset(); input = debug_context(7); input.ContextFlags = CONTEXT_i386 | flags;
        NTSTATUS status = sd_wow64_remote_debug_context((HANDLE)0x40, &input, TRUE);
        assert(status == (flags == 16 ? 0 : STATUS_NOT_SUPPORTED));
        assert(objects[0].sd_debug.valid == (flags == 16));
    }
    for (unsigned which = 0; which < 9; ++which) for (unsigned set = 0; set < 2; ++set) {
        reset(); input = debug_context(9); expected = input;
        HANDLE handle = (HANDLE)0x40; NTSTATUS status = STATUS_NOT_SUPPORTED;
        if (which == 0) objects[0].thread.started = 1;
        if (which == 1) objects[0].thread.suspend = 0;
        if (which == 2) objects[0].thread.pid = 99;
        if (which == 3) { objects[0].thread.terminated = 1; status = STATUS_THREAD_IS_TERMINATING; }
        if (which == 4) { handle = (HANDLE)0x50; status = STATUS_OBJECT_TYPE_MISMATCH; }
        if (which == 5) { closed = 1; status = STATUS_INVALID_HANDLE; }
        if (which == 6) { handle = (HANDLE)0x100000040ull; status = STATUS_INVALID_HANDLE; }
        if (which == 7) { input.ContextFlags = 0x10; expected = input; }
        if (which == 8) { handle = NULL; status = STATUS_INVALID_HANDLE; }
        assert(sd_wow64_remote_debug_context(handle, &input, set) == status);
        assert(!memcmp(&input, &expected, sizeof(input)) && !objects[0].sd_debug.valid);
    }
    assert(sd_wow64_remote_debug_context((HANDLE)0x40, NULL, TRUE) == STATUS_INVALID_PARAMETER);
    puts("PASS all 64 groups; running, unsuspended, foreign-process, terminated, closed, bad-type/width/architecture/null rejected");

    reset(); input = debug_context(9);
    assert(!sd_wow64_remote_debug_context((HANDLE)0x40, &input, TRUE));
    memset(&input.Dr0, 0, 24);
    assert(!sd_wow64_remote_debug_context((HANDLE)0x40, &input, TRUE));
    assert(objects[0].sd_debug.valid);
    assert(!sd_wow64_apply_start_debug(&child.teb, &child.context)); /* not started */
    objects[0].thread.started = 1;
    assert(!sd_wow64_apply_start_debug(&child.teb, &child.context)); /* TEB not published */
    objects[0].thread.teb = (ULONG_PTR)&child.teb;
    assert(!sd_wow64_apply_start_debug(NULL, &child.context));
    assert(!sd_wow64_apply_start_debug(&child.teb, NULL));
    apply_and_check(&input);
    puts("PASS overwrite and explicit clear; invalid/early startup does not consume pending state");

    for (unsigned i = 0; i < 1000; ++i) {
        pthread_t thread; int count;
        reset(); input = debug_context(i);
        assert(!pthread_create(&thread, NULL, start_child, &input));
        assert(!sd_wow64_remote_debug_context((HANDLE)0x40, &input, TRUE));
        pthread_mutex_lock(&horizon_server_objects_mutex);
        assert(!horizon_thread_resume(&objects[0].thread, &count) && count == 1);
        pthread_cond_signal(&start_gate);
        pthread_mutex_unlock(&horizon_server_objects_mutex);
        assert(!pthread_join(thread, NULL));
    }
    puts("PASS 1000 concurrent child TEB publication / parent SetContext / resume / post-reset apply cycles");
    return 0;
}
