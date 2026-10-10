/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Executes the production pipe implementation; only Horizon's handle registry,
 * scheduler wake and TEB are replaced by a small host fixture. Wine headers and
 * the production IOCP queue are used directly. */
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ntstatus.h"
#define WIN32_NO_STATUS
#include "windef.h"
#include "winbase.h"
#include "winternl.h"
#include "winioctl.h"
/* unix_private.h's WoW64 IOSB and Horizon's protocol envelope. */
typedef struct { union { NTSTATUS Status; ULONG Pointer; }; ULONG Information; } IO_STATUS_BLOCK32;
struct horizon_server_request_header { int req; unsigned int request_size, reply_size; };
struct horizon_server_reply_header { unsigned int error, reply_size; };
#include "horizon_completion.h"
#ifndef NT_ERROR
#define NT_ERROR(status) (((ULONG)(status) >> 30) == 3)
#endif

#define HORIZON_SERVER_OBJECT_FILE 1
#define HORIZON_SERVER_OBJECT_EVENT 2
struct horizon_server_object {
    unsigned int refs;
    int type, signaled, manual_reset;
    ULONG file_access, file_options, file_completion_flags;
    struct sd_pipe_endpoint *sd_pipe;
    struct horizon_server_object *file_completion;
    unsigned long long file_completion_key;
    struct horizon_completion_queue completion;
};
struct horizon_server_handle_entry {
    unsigned int handle;
    struct horizon_server_object *object;
    struct horizon_server_handle_entry *next;
};
static struct horizon_server_handle_entry *handles;
static unsigned int next_handle = 0x100, object_count, passed;
static pthread_mutex_t horizon_server_objects_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t horizon_server_objects_cond = PTHREAD_COND_INITIALIZER;
static _Thread_local TEB test_teb;
static _Thread_local int wow;
#undef NtCurrentTeb
#define NtCurrentTeb() (&test_teb)
static int in_wow64_call(void) { return wow; }
static void horizon_trace(const char *s, ...) { (void)s; }
static void horizon_server_signal_changed_locked(void) { pthread_cond_broadcast(&horizon_server_objects_cond); }
static struct horizon_server_handle_entry *horizon_server_find_handle_locked(unsigned int h)
{
    struct horizon_server_handle_entry *e;
    for (e = handles; e && e->handle != h; e = e->next) {}
    return e;
}
static struct horizon_server_handle_entry *horizon_server_create_handle_locked(int type)
{
    struct horizon_server_handle_entry *e = calloc(1, sizeof(*e));
    assert(e);
    e->object = calloc(1, sizeof(*e->object)); assert(e->object);
    object_count++;
    e->object->refs = 1; e->object->type = type;
    e->handle = next_handle; next_handle += 4;
    e->next = handles; handles = e;
    return e;
}
static void sd_pipe_free_locked(struct horizon_server_object *);
static void horizon_server_free_object(struct horizon_server_object *o)
{
    sd_pipe_free_locked(o);
    horizon_completion_clear(&o->completion);
    if (o->file_completion && !--o->file_completion->refs) horizon_server_free_object(o->file_completion);
    object_count--;
    free(o);
}
static void horizon_server_post_completion_locked(struct horizon_server_object *port,
         unsigned long long key, unsigned long long value, unsigned int status, unsigned long long count)
{
    assert(horizon_completion_add(&port->completion, key, value, status, count));
    horizon_server_signal_changed_locked();
}
static long allocations_before_failure = -1;
static void *test_malloc(size_t size)
{
    if (!allocations_before_failure) return NULL;
    if (allocations_before_failure > 0) allocations_before_failure--;
    return malloc(size);
}
static void *test_calloc(size_t n, size_t size)
{
    if (!allocations_before_failure) return NULL;
    if (allocations_before_failure > 0) allocations_before_failure--;
    return calloc(n, size);
}
#define malloc test_malloc
#define calloc test_calloc
#include "sd_named_pipe.inc"
#undef malloc
#undef calloc

static HANDLE new_handle(int type)
{
    return ULongToHandle(horizon_server_create_handle_locked(type)->handle);
}
static struct horizon_server_object *object(HANDLE h)
{
    struct horizon_server_handle_entry *e = horizon_server_find_handle_locked(HandleToULong(h));
    assert(e); return e->object;
}
static void close_handle(HANDLE h)
{
    struct horizon_server_handle_entry **link, *e, *other;
    struct horizon_server_object *o;
    int remaining = 0;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    for (link = &handles; *link && (*link)->handle != HandleToULong(h); link = &(*link)->next) {}
    assert(*link); e = *link; *link = e->next; o = e->object;
    for (other = handles; other; other = other->next) if (other->object == o) remaining = 1;
    if (!remaining && o->sd_pipe) sd_pipe_close_locked(o);
    if (!--o->refs) horizon_server_free_object(o);
    free(e);
    pthread_mutex_unlock(&horizon_server_objects_mutex);
}
static HANDLE duplicate(HANDLE h)
{
    struct horizon_server_handle_entry *e = calloc(1, sizeof(*e)); assert(e);
    e->handle = next_handle; next_handle += 4; e->object = object(h); e->object->refs++;
    e->next = handles; handles = e; return ULongToHandle(e->handle);
}
static void attributes(const char *path, WCHAR *buffer, UNICODE_STRING *name, OBJECT_ATTRIBUTES *attr)
{
    unsigned int i;
    for (i = 0; path[i]; i++) buffer[i] = (unsigned char)path[i];
    buffer[i] = 0; name->Buffer = buffer; name->Length = i * 2; name->MaximumLength = (i + 1) * 2;
    memset(attr, 0, sizeof(*attr)); attr->Length = sizeof(*attr); attr->ObjectName = name;
}
static NTSTATUS create_path(HANDLE *h, const char *path, ULONG type, ULONG read_mode, ULONG max, ULONG options, ULONG disposition)
{
    WCHAR buf[300]; UNICODE_STRING name; OBJECT_ATTRIBUTES attr; IO_STATUS_BLOCK io = {0};
    attributes(path, buf, &name, &attr);
    return sd_pipe_create(h, GENERIC_READ | GENERIC_WRITE, &attr, &io, 3, disposition, options,
                          type, read_mode, 0, max, 0, 0);
}
static HANDLE server(ULONG type, ULONG read_mode, ULONG options)
{
    HANDLE h;
    assert(!create_path(&h, "\\??\\pipe\\sd-test", type, read_mode, 255, options, FILE_OPEN_IF));
    return h;
}
static NTSTATUS open_path(HANDLE *h, const char *path, ULONG options)
{
    WCHAR buf[300]; UNICODE_STRING name; OBJECT_ATTRIBUTES attr; IO_STATUS_BLOCK io = {0}; NTSTATUS ret;
    attributes(path, buf, &name, &attr);
    assert(sd_pipe_open(h, GENERIC_READ | GENERIC_WRITE, &attr, &io, FILE_OPEN, options, &ret));
    return ret;
}
static HANDLE client(ULONG options)
{
    HANDLE h; assert(!open_path(&h, "\\Device\\NamedPipe\\SD-TEST", options)); return h;
}
static NTSTATUS control(HANDLE h, ULONG code, HANDLE event, IO_STATUS_BLOCK *io, void *data, ULONG size, ULONG_PTR ctx)
{
    NTSTATUS ret; assert(sd_pipe_control(h, event, NULL, (void *)ctx, io, code, data, size, &ret)); return ret;
}
static NTSTATUS rw(HANDLE h, HANDLE event, IO_STATUS_BLOCK *io, void *data, ULONG size, BOOL write, ULONG_PTR ctx)
{
    NTSTATUS ret; assert(sd_pipe_read_write(h, event, NULL, (void *)ctx, io, data, size, write, &ret)); return ret;
}
static void bind_port(HANDLE file, HANDLE port)
{
    object(file)->file_completion = object(port); object(port)->refs++;
    object(file)->file_completion_key = 0x44556677;
}
static void packet(HANDLE port, ULONG_PTR ctx, NTSTATUS status, ULONG bytes)
{
    struct horizon_completion_msg msg;
    assert(horizon_completion_take(&object(port)->completion, &msg));
    assert(msg.ckey == 0x44556677 && msg.cvalue == ctx && msg.status == (ULONG)status && msg.information == bytes);
}
static void clean(void) { assert(!handles && !sd_pipe_servers && !object_count); passed++; }

static void test_connect(void)
{
    HANDLE s = server(1, 1, 0), e = new_handle(HORIZON_SERVER_OBJECT_EVENT), port = new_handle(3), c;
    IO_STATUS_BLOCK io = {0}, again = {0}; bind_port(s, port);
    assert(control(s, FSCTL_PIPE_LISTEN, e, &io, NULL, 0, 10) == STATUS_PENDING);
    assert(io.Status == STATUS_PENDING && !object(e)->signaled && !object(s)->signaled);
    c = client(0); assert(io.Status == STATUS_SUCCESS && object(e)->signaled && object(s)->signaled);
    packet(port, 10, STATUS_SUCCESS, 0);
    assert(control(s, FSCTL_PIPE_LISTEN, NULL, &again, NULL, 0, 11) == STATUS_PIPE_CONNECTED);
    assert(!object(port)->completion.depth);
    close_handle(c); close_handle(s); close_handle(e); close_handle(port); clean();
}
static void test_messages(void)
{
    HANDLE s = server(1, 1, 0), c = client(0); IO_STATUS_BLOCK io = {0}; char out[20] = {0};
    unsigned char peek[32] = {0};
    assert(!rw(c, NULL, &io, "abcdef", 6, TRUE, 0));
    assert(!rw(c, NULL, &io, "XYZ", 3, TRUE, 0));
    assert(control(s, FSCTL_PIPE_PEEK, NULL, &io, peek, 18, 0) == STATUS_BUFFER_OVERFLOW);
    assert(((ULONG *)peek)[1] == 9 && ((ULONG *)peek)[2] == 2 && ((ULONG *)peek)[3] == 6);
    assert(!memcmp(peek + 16, "ab", 2));
    assert(rw(s, NULL, &io, out, 2, FALSE, 0) == STATUS_BUFFER_OVERFLOW && io.Information == 2);
    assert(!rw(s, NULL, &io, out, sizeof(out), FALSE, 0) && io.Information == 4 && !memcmp(out, "cdef", 4));
    assert(!rw(s, NULL, &io, out, sizeof(out), FALSE, 0) && io.Information == 3 && !memcmp(out, "XYZ", 3));
    assert(!rw(c, NULL, &io, NULL, 0, TRUE, 0));
    assert(!rw(s, NULL, &io, out, 8, FALSE, 0) && !io.Information);
    close_handle(c); close_handle(s); clean();
}
static void test_byte_stream(void)
{
    HANDLE s = server(1, 1, 0), c = client(0); IO_STATUS_BLOCK io = {0}; char data[16]; NTSTATUS ret;
    FILE_PIPE_INFORMATION info = {FILE_PIPE_BYTE_STREAM_MODE, 0};
    assert(sd_pipe_set(s, &io, &info, sizeof(info), FilePipeInformation, &ret) && !ret);
    assert(!rw(c, NULL, &io, "hello", 5, TRUE, 0)); assert(!rw(c, NULL, &io, "world", 5, TRUE, 0));
    assert(!rw(s, NULL, &io, data, 16, FALSE, 0) && io.Information == 10 && !memcmp(data, "helloworld", 10));
    close_handle(c); close_handle(s); clean();
}
static void test_wow_pending(void)
{
    HANDLE s = server(1, 1, 0), c = client(0), e = new_handle(2), port = new_handle(3);
    struct { ULONG before; IO_STATUS_BLOCK32 io; ULONG after; } target = {0x11223344, {0}, 0xaabbccdd};
    IO_STATUS_BLOCK bridge = {0}, write_io = {0}; char data[20] = {0};
    bind_port(s, port); bridge.Pointer = &target.io; wow = 1;
    assert(rw(s, e, &bridge, data, sizeof(data), FALSE, 12) == STATUS_PENDING);
    wow = 0; /* A native writer completes an x86 issuer's request. */
    assert(!rw(c, NULL, &write_io, "across threads", 14, TRUE, 0));
    assert(target.io.Status == STATUS_SUCCESS && target.io.Information == 14 && !memcmp(data, "across threads", 14));
    assert(target.before == 0x11223344 && target.after == 0xaabbccdd && bridge.Pointer == &target.io);
    packet(port, 12, STATUS_SUCCESS, 14); assert(object(e)->signaled);
    close_handle(c); close_handle(s); close_handle(e); close_handle(port); clean();
}
static void test_cancel_close(void)
{
    HANDLE s = server(1, 1, 0), c = client(0), duplicate_s = duplicate(s), port = new_handle(3);
    IO_STATUS_BLOCK io1 = {0}, io2 = {0}, cancelled; char a[8], b[8]; NTSTATUS ret;
    bind_port(s, port); test_teb.ClientId.UniqueThread = ULongToHandle(4);
    assert(rw(s, NULL, &io1, a, 8, FALSE, 21) == STATUS_PENDING);
    test_teb.ClientId.UniqueThread = ULongToHandle(8);
    assert(rw(s, NULL, &io2, b, 8, FALSE, 22) == STATUS_PENDING);
    assert(sd_pipe_cancel(s, NULL, &cancelled, TRUE, &ret) && !ret);
    assert(io1.Status == STATUS_PENDING && io2.Status == STATUS_CANCELLED); packet(port, 22, STATUS_CANCELLED, 0);
    close_handle(s); assert(io1.Status == STATUS_PENDING); /* duplicate retains connection */
    close_handle(duplicate_s); assert(io1.Status == STATUS_CANCELLED); packet(port, 21, STATUS_CANCELLED, 0);
    assert(rw(c, NULL, &io2, a, 8, FALSE, 0) == STATUS_PIPE_BROKEN);
    close_handle(c); close_handle(port); clean();
}
static void test_disconnect_reconnect(void)
{
    HANDLE s = server(1, 1, 0), c = client(0), c2; IO_STATUS_BLOCK r = {0}, io = {0}; char data[8];
    assert(rw(c, NULL, &r, data, 8, FALSE, 0) == STATUS_PENDING);
    assert(!control(s, FSCTL_PIPE_DISCONNECT, NULL, &io, NULL, 0, 0));
    assert(r.Status == STATUS_PIPE_DISCONNECTED);
    assert(open_path(&c2, "\\??\\pipe\\sd-test", 0) == STATUS_PIPE_NOT_AVAILABLE);
    assert(control(s, FSCTL_PIPE_LISTEN, NULL, &io, NULL, 0, 0) == STATUS_PENDING);
    c2 = client(0); assert(!io.Status);
    assert(rw(c, NULL, &r, "stale", 5, TRUE, 0) == STATUS_PIPE_DISCONNECTED);
    assert(!rw(c2, NULL, &r, "new", 3, TRUE, 0));
    assert(!rw(s, NULL, &io, data, sizeof(data), FALSE, 0) && !memcmp(data, "new", 3));
    close_handle(c); close_handle(c2); close_handle(s); clean();
}
static void test_completion_rules(void)
{
    HANDLE s = server(0, 0, 0), c = client(0), port = new_handle(3), e = new_handle(2);
    IO_STATUS_BLOCK io = {0}; char data[8]; ULONG peek[4]; bind_port(s, port);
    object(s)->file_completion_flags = FILE_SKIP_COMPLETION_PORT_ON_SUCCESS | FILE_SKIP_SET_EVENT_ON_HANDLE;
    assert(!rw(s, e, &io, "x", 1, TRUE, 31)); assert(!object(port)->completion.depth && object(e)->signaled);
    assert(rw(s, e, &io, data, 8, FALSE, 32) == STATUS_PENDING);
    assert(!rw(c, NULL, &(IO_STATUS_BLOCK){0}, "y", 1, TRUE, 0)); packet(port, 32, STATUS_SUCCESS, 1);
    assert(!object(s)->signaled);
    object(s)->file_completion_flags = 0;
    assert(!rw(s, ULongToHandle(HandleToULong(e) | 1), &io, "z", 1, TRUE, 33));
    assert(!object(port)->completion.depth);
    assert(!control(s, FSCTL_PIPE_PEEK, NULL, &io, peek, sizeof(peek), 0)); assert(!object(port)->completion.depth);
    close_handle(c); close_handle(s); close_handle(port); close_handle(e); clean();
}
static void test_instances_info(void)
{
    HANDLE a, b, c, d, unused; IO_STATUS_BLOCK io = {0}; NTSTATUS ret; FILE_PIPE_LOCAL_INFORMATION info;
    assert(!create_path(&a, "\\??\\pipe\\sd-test", 1, 1, 2, 0, FILE_OPEN_IF));
    assert(!create_path(&b, "\\??\\pipe\\SD-TEST", 1, 1, 2, 0, FILE_OPEN_IF));
    assert(create_path(&unused, "\\??\\pipe\\sd-test", 1, 1, 2, 0, FILE_OPEN_IF) == STATUS_INSTANCE_NOT_AVAILABLE);
    c = client(0); d = client(0);
    assert(open_path(&unused, "\\??\\pipe\\sd-test", 0) == STATUS_PIPE_NOT_AVAILABLE);
    assert(sd_pipe_query(a, &io, &info, sizeof(info), FilePipeLocalInformation, &ret) && !ret);
    assert(info.CurrentInstances == 2 && info.NamedPipeType == 1 && info.NamedPipeConfiguration == FILE_PIPE_FULL_DUPLEX);
    assert(!rw(c, NULL, &io, "c", 1, TRUE, 0)); assert(!rw(d, NULL, &io, "d", 1, TRUE, 0));
    { char data; assert(!rw(a, NULL, &io, &data, 1, FALSE, 0) && data == 'd');
      assert(!rw(b, NULL, &io, &data, 1, FALSE, 0) && data == 'c'); }
    close_handle(a); close_handle(b); close_handle(c); close_handle(d); clean();
}
struct sync_args { HANDLE h; char data[8]; IO_STATUS_BLOCK io; NTSTATUS status; };
static void *sync_reader(void *p)
{
    struct sync_args *a = p; test_teb.ClientId.UniqueThread = ULongToHandle(44);
    a->status = rw(a->h, NULL, &a->io, a->data, 8, FALSE, 0); return NULL;
}
static void test_sync(void)
{
    HANDLE s = server(0, 0, FILE_SYNCHRONOUS_IO_NONALERT), c = client(0); pthread_t t;
    struct sync_args a = {.h = s}; IO_STATUS_BLOCK io = {0};
    assert(!pthread_create(&t, NULL, sync_reader, &a));
    assert(!rw(c, NULL, &io, "wake", 4, TRUE, 0));
    assert(!pthread_join(t, NULL)); assert(!a.status && a.io.Information == 4 && !memcmp(a.data, "wake", 4));
    close_handle(s); close_handle(c); clean();
}
static void test_failures(void)
{
    HANDLE s = server(0, 0, 0), c = client(0), h; IO_STATUS_BLOCK io = {0}; char data[8]; NTSTATUS ret;
    assert(create_path(&h, "\\??\\pipe\\sd-test", 0, 0, 255, 0, FILE_CREATE) == STATUS_OBJECT_NAME_COLLISION);
    assert(create_path(&h, "\\??\\pipe\\invalid", 0, 1, 1, 0, FILE_OPEN_IF) == STATUS_INVALID_PARAMETER);
    for (long fail = 0; fail < 2; fail++) {
        allocations_before_failure = fail; assert(rw(c, NULL, &io, "fail", 4, TRUE, 0) == STATUS_NO_MEMORY);
        allocations_before_failure = -1; assert(!sd_pipe_find(s)->bytes);
    }
    assert(rw(s, ULongToHandle(0xdead), &io, data, 8, FALSE, 0) == STATUS_INVALID_HANDLE);
    assert(sd_pipe_read_write(s, NULL, (PIO_APC_ROUTINE)1, NULL, &io, data, 8, FALSE, &ret) && ret == STATUS_NOT_SUPPORTED);
    assert(!sd_pipe_read_write(ULongToHandle(0xdead), NULL, NULL, NULL, &io, data, 8, FALSE, &ret));
    assert(sd_pipe_cancel(s, &io, &(IO_STATUS_BLOCK){0}, FALSE, &ret) && ret == STATUS_NOT_FOUND);
    close_handle(s); close_handle(c); clean();
}
static void test_stress(void)
{
    for (unsigned int i = 0; i < 500; i++) {
        HANDLE s = server(1, 1, 0), c; IO_STATUS_BLOCK io = {0}, read_io = {0}; char data[8];
        assert(control(s, FSCTL_PIPE_LISTEN, NULL, &io, NULL, 0, 0) == STATUS_PENDING); c = client(0);
        assert(rw(s, NULL, &read_io, data, sizeof(data), FALSE, 0) == STATUS_PENDING);
        if (i & 1) { assert(!rw(c, NULL, &io, "ok", 2, TRUE, 0)); assert(read_io.Information == 2); }
        close_handle(c); assert(read_io.Status == ((i & 1) ? STATUS_SUCCESS : STATUS_PIPE_BROKEN));
        close_handle(s);
    }
    clean();
}
struct exchange_args { HANDLE h; int server; };
static void *exchange(void *arg)
{
    struct exchange_args *a = arg;
    test_teb.ClientId.UniqueThread = ULongToHandle(a->server ? 100 : 104);
    for (ULONG sequence = 0; sequence < 200; sequence++) {
        IO_STATUS_BLOCK io = {0}; ULONG received = ~0u;
        if (!a->server) assert(!rw(a->h, NULL, &io, &sequence, sizeof(sequence), TRUE, 0));
        assert(!rw(a->h, NULL, &io, &received, sizeof(received), FALSE, 0));
        assert(io.Information == sizeof(received) && received == sequence);
        if (a->server) assert(!rw(a->h, NULL, &io, &sequence, sizeof(sequence), TRUE, 0));
    }
    return NULL;
}
static void test_duplex_threads(void)
{
    HANDLE s = server(1, 1, FILE_SYNCHRONOUS_IO_NONALERT), c = client(FILE_SYNCHRONOUS_IO_NONALERT);
    struct exchange_args args[2] = {{s, 1}, {c, 0}}; pthread_t threads[2];
    assert(!pthread_create(&threads[0], NULL, exchange, &args[0]));
    assert(!pthread_create(&threads[1], NULL, exchange, &args[1]));
    assert(!pthread_join(threads[0], NULL)); assert(!pthread_join(threads[1], NULL));
    close_handle(c); close_handle(s); clean();
}
static void test_wow_connect_cancel_and_native_completion(void)
{
    HANDLE s = server(1, 1, 0), c, e = new_handle(2), port = new_handle(3);
    IO_STATUS_BLOCK32 io32 = {0}; IO_STATUS_BLOCK bridge = {0}, native_io = {0}, cancelled = {0};
    char data[8]; NTSTATUS ret; bind_port(s, port);
    bridge.Pointer = &io32; wow = 1;
    assert(control(s, FSCTL_PIPE_LISTEN, e, &bridge, NULL, 0, 77) == STATUS_PENDING);
    wow = 0; c = client(0); assert(!io32.Status); packet(port, 77, STATUS_SUCCESS, 0);
    assert(rw(s, NULL, &native_io, data, sizeof(data), FALSE, 78) == STATUS_PENDING);
    wow = 1; io32.Status = 0;
    assert(!rw(c, NULL, &bridge, "hi", 2, TRUE, 0));
    assert(native_io.Status == STATUS_SUCCESS && native_io.Information == 2); packet(port, 78, STATUS_SUCCESS, 2);
    assert(rw(s, e, &bridge, data, sizeof(data), FALSE, 79) == STATUS_PENDING);
    assert(sd_pipe_cancel(s, (IO_STATUS_BLOCK *)&io32, &cancelled, FALSE, &ret) && !ret);
    assert(io32.Status == STATUS_CANCELLED); packet(port, 79, STATUS_CANCELLED, 0);
    wow = 0; close_handle(s); close_handle(c); close_handle(e); close_handle(port); clean();
}
int main(void)
{
    test_teb.ClientId.UniqueThread = ULongToHandle(4);
    test_connect(); test_messages(); test_byte_stream(); test_wow_pending(); test_cancel_close();
    test_disconnect_reconnect(); test_completion_rules(); test_instances_info(); test_sync(); test_failures(); test_stress();
    test_duplex_threads(); test_wow_connect_cancel_and_native_completion();
    printf("{\"passed_groups\":%u,\"stress_connections\":500,\"duplex_thread_roundtrips\":200,\"objects_remaining\":%u}\n", passed, object_count);
    return 0;
}
