/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Local NT named pipes for Wine-NX. Included by horizon.c, sharing its handle,
 * event, wait and completion-port objects. No filesystem or network transport.
 * Every endpoint, queue and reference is protected by objects_mutex. Queued
 * operations capture the issuer's IOSB width; completion can run on another
 * thread (including the server thread, which has no WoW64 context).
 */
#include "sd_named_pipe.h"
#include "winioctl.h"

struct sd_pipe_message {
    struct sd_pipe_message *next;
    ULONG size, offset;
    unsigned char data[];
};
struct sd_pipe_operation {
    struct sd_pipe_operation *next;
    struct horizon_server_object *file, *event;
    void *iosb, *buffer;
    ULONG size, tid;
    ULONG_PTR context;
    NTSTATUS status;
    int wow, synchronous, listen, completed, pending, suppress_port;
};
struct sd_pipe_endpoint {
    struct sd_pipe_endpoint *next, *peer;
    struct horizon_server_object *file;
    WCHAR *name;
    unsigned int name_len;
    ULONG type, read_mode, completion_mode, max_instances, sharing;
    ULONG in_quota, out_quota, state;
    int server, closed;
    struct sd_pipe_message *head, *tail;
    ULONG bytes, messages;
    struct sd_pipe_operation *operations, *last_operation;
};
static struct sd_pipe_endpoint *sd_pipe_servers;
static unsigned int sd_pipe_logs;

static void sd_pipe_log(const char *op, ULONG handle, NTSTATUS status, ULONG amount)
{
    if (sd_pipe_logs++ < 96)
        horizon_trace("[SD-PIPE] %s handle=%x status=%08x bytes=%u", op, handle, status, amount);
}
static void sd_pipe_changed(void)
{
    horizon_server_signal_changed_locked();
    /* Direct synchronous callers are not server select waiters. */
    pthread_cond_broadcast(&horizon_server_objects_cond);
}
static void sd_pipe_release(struct horizon_server_object *o)
{
    if (o && !--o->refs) horizon_server_free_object(o);
}
static struct sd_pipe_endpoint *sd_pipe_find(HANDLE h)
{
    struct horizon_server_handle_entry *e = horizon_server_find_handle_locked(HandleToULong(h));
    return e ? e->object->sd_pipe : NULL;
}
static WCHAR sd_pipe_lower(WCHAR c) { return c >= 'A' && c <= 'Z' ? c + ('a' - 'A') : c; }
static int sd_pipe_prefix(const WCHAR *s, unsigned int n, const char *prefix)
{
    unsigned int i;
    for (i = 0; prefix[i]; i++)
        if (i >= n || sd_pipe_lower(s[i]) != (unsigned char)prefix[i]) return 0;
    return i;
}
/* RtlDosPathNameToNtPathName normally supplies \\??\\pipe\\... . */
static int sd_pipe_name(OBJECT_ATTRIBUTES *attr, const WCHAR **name, unsigned int *length)
{
    const UNICODE_STRING *s;
    unsigned int n;
    int prefix;
    if (!attr || !(s = attr->ObjectName) || !s->Buffer || (s->Length & 1)) return 0;
    n = s->Length / sizeof(WCHAR);
    prefix = sd_pipe_prefix(s->Buffer, n, "\\??\\pipe\\");
    if (!prefix) prefix = sd_pipe_prefix(s->Buffer, n, "\\device\\namedpipe\\");
    if (!prefix) return 0;
    *name = s->Buffer + prefix;
    *length = n - prefix;
    return 1;
}
static int sd_pipe_same(const struct sd_pipe_endpoint *p, const WCHAR *name, unsigned int n)
{
    unsigned int i;
    if (p->name_len != n) return 0;
    for (i = 0; i < n; i++) if (p->name[i] != sd_pipe_lower(name[i])) return 0;
    return 1;
}
static ULONG sd_pipe_access(ULONG access)
{
    if (access & GENERIC_ALL) access |= FILE_ALL_ACCESS;
    if (access & GENERIC_READ) access |= FILE_GENERIC_READ;
    if (access & GENERIC_WRITE) access |= FILE_GENERIC_WRITE;
    return access & ~(GENERIC_ALL | GENERIC_READ | GENERIC_WRITE | GENERIC_EXECUTE);
}
static void sd_pipe_clear_messages(struct sd_pipe_endpoint *p)
{
    while (p->head) {
        struct sd_pipe_message *m = p->head;
        p->head = m->next;
        free(m);
    }
    p->tail = NULL;
    p->bytes = p->messages = 0;
}
static void sd_pipe_store_io(struct sd_pipe_operation *op, NTSTATUS status, ULONG size)
{
    if (op->wow) {
        IO_STATUS_BLOCK32 *io = op->iosb;
        io->Information = size;
        __atomic_store_n(&io->Status, status, __ATOMIC_RELEASE);
    } else {
        IO_STATUS_BLOCK *io = op->iosb;
        io->Information = size;
        __atomic_store_n(&io->Status, status, __ATOMIC_RELEASE);
    }
}
static void sd_pipe_finish(struct sd_pipe_operation *op, NTSTATUS status, ULONG size)
{
    struct horizon_server_object *file = op->file;
    sd_pipe_store_io(op, status, size);
    op->status = status;
    op->completed = 1;
    if (op->pending || !NT_ERROR(status)) {
        if (!(file->file_completion_flags & FILE_SKIP_SET_EVENT_ON_HANDLE)) file->signaled = 1;
        if (op->event) op->event->signaled = 1;
    }
    if (!op->synchronous && !op->suppress_port && op->context && file->file_completion &&
        (op->pending || !NT_ERROR(status)) &&
        horizon_completion_file_posts(op->pending, file->file_completion_flags))
        horizon_server_post_completion_locked(file->file_completion, file->file_completion_key,
                                               op->context, status, size);
    sd_pipe_changed();
    if (!op->synchronous) {
        sd_pipe_release(op->event);
        free(op);
        sd_pipe_release(file);
    }
}
static void sd_pipe_unlink_op(struct sd_pipe_endpoint *p, struct sd_pipe_operation **link)
{
    struct sd_pipe_operation *op = *link;
    *link = op->next;
    if (p->last_operation == op) {
        struct sd_pipe_operation *last = p->operations;
        while (last && last->next) last = last->next;
        p->last_operation = last;
    }
    op->next = NULL;
}
static ULONG sd_pipe_take(struct sd_pipe_endpoint *p, void *buffer, ULONG size, NTSTATUS *status)
{
    ULONG total = 0;
    *status = STATUS_SUCCESS;
    while (p->head) {
        struct sd_pipe_message *m = p->head;
        ULONG available = m->size - m->offset;
        ULONG count = min(available, size - total);
        if (count) memcpy((char *)buffer + total, m->data + m->offset, count);
        m->offset += count;
        p->bytes -= count;
        total += count;
        if (m->offset == m->size) {
            p->head = m->next;
            if (!p->head) p->tail = NULL;
            p->messages--;
            free(m);
        } else if (p->read_mode) *status = STATUS_BUFFER_OVERFLOW;
        if (p->read_mode || total == size) break;
    }
    return total;
}
static void sd_pipe_drain(struct sd_pipe_endpoint *p)
{
    struct sd_pipe_operation **link = &p->operations;
    while (*link) {
        struct sd_pipe_operation *op = *link;
        NTSTATUS status;
        ULONG count = 0;
        if (op->listen) { link = &op->next; continue; }
        if (p->head) count = sd_pipe_take(p, op->buffer, op->size, &status);
        else if (!p->peer) status = p->state == FILE_PIPE_DISCONNECTED_STATE ? STATUS_PIPE_DISCONNECTED : STATUS_PIPE_BROKEN;
        else break;
        sd_pipe_unlink_op(p, link);
        sd_pipe_finish(op, status, count);
    }
}
/* Called before the last handle reference is dropped, even with pending I/O. */
static void sd_pipe_close_locked(struct horizon_server_object *file)
{
    struct sd_pipe_endpoint *p = file->sd_pipe, *peer;
    struct sd_pipe_endpoint **link;
    if (!p || p->closed) return;
    p->closed = 1;
    if (p->server) {
        for (link = &sd_pipe_servers; *link && *link != p; link = &(*link)->next) {}
        if (*link) *link = p->next;
    }
    peer = p->peer;
    p->peer = NULL;
    if (peer) {
        peer->peer = NULL;
        peer->state = FILE_PIPE_CLOSING_STATE;
        sd_pipe_drain(peer);
    }
    while (p->operations) {
        struct sd_pipe_operation *op = p->operations;
        sd_pipe_unlink_op(p, &p->operations);
        sd_pipe_finish(op, STATUS_CANCELLED, 0);
    }
    sd_pipe_clear_messages(p);
    sd_pipe_changed();
}
static void sd_pipe_free_locked(struct horizon_server_object *file)
{
    struct sd_pipe_endpoint *p = file->sd_pipe;
    if (!p) return;
    /* The handle-close hook cancels requests before freeing the object. */
    sd_pipe_clear_messages(p);
    free(p->name);
    free(p);
    file->sd_pipe = NULL;
}

NTSTATUS sd_pipe_create(HANDLE *handle, ULONG access, OBJECT_ATTRIBUTES *attr, IO_STATUS_BLOCK *io,
                       ULONG sharing, ULONG disposition, ULONG options, ULONG type, ULONG read_mode,
                       ULONG completion_mode, ULONG max_instances, ULONG in_quota, ULONG out_quota)
{
    const WCHAR *name;
    unsigned int n, i, instances = 0;
    struct sd_pipe_endpoint *p, *other;
    struct horizon_server_handle_entry *entry;
    NTSTATUS status = STATUS_SUCCESS;
    *handle = NULL;
    if (!io || !sd_pipe_name(attr, &name, &n) || !n || n > 256 || attr->RootDirectory)
        return STATUS_OBJECT_NAME_INVALID;
    if (type > 1 || read_mode > 1 || completion_mode > 1 || (read_mode && !type) ||
        !max_instances || !(sharing & (FILE_SHARE_READ | FILE_SHARE_WRITE)) ||
        (disposition != FILE_CREATE && disposition != FILE_OPEN_IF)) return STATUS_INVALID_PARAMETER;
    if (options & FILE_SYNCHRONOUS_IO_ALERT) return STATUS_NOT_SUPPORTED;
    p = calloc(1, sizeof(*p));
    if (!p) return STATUS_NO_MEMORY;
    p->name = malloc(n * sizeof(WCHAR));
    if (!p->name) { free(p); return STATUS_NO_MEMORY; }
    for (i = 0; i < n; i++) p->name[i] = sd_pipe_lower(name[i]);
    p->name_len = n;
    p->server = 1;
    p->state = FILE_PIPE_LISTENING_STATE;
    p->type = type; p->read_mode = read_mode; p->completion_mode = completion_mode;
    p->max_instances = max_instances; p->sharing = sharing;
    p->in_quota = in_quota ? in_quota : 65536;
    p->out_quota = out_quota ? out_quota : 65536;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    for (other = sd_pipe_servers; other; other = other->next) if (sd_pipe_same(other, name, n)) {
        instances++;
        if (disposition == FILE_CREATE) status = STATUS_OBJECT_NAME_COLLISION;
        else if (other->type != type || other->sharing != sharing || other->max_instances != max_instances)
            status = STATUS_ACCESS_DENIED;
    }
    if (!status && instances >= max_instances) status = STATUS_INSTANCE_NOT_AVAILABLE;
    if (!status && !(entry = horizon_server_create_handle_locked(HORIZON_SERVER_OBJECT_FILE)))
        status = STATUS_NO_MEMORY;
    if (!status) {
        p->file = entry->object;
        p->file->sd_pipe = p;
        p->file->file_access = sd_pipe_access(access);
        p->file->file_options = options;
        p->file->manual_reset = 1;
        p->file->signaled = 1;
        p->next = sd_pipe_servers; sd_pipe_servers = p;
        *handle = ULongToHandle(entry->handle);
        io->Information = instances ? FILE_OPENED : FILE_CREATED;
    } else { free(p->name); free(p); }
    io->Status = status;
    sd_pipe_log("create", HandleToULong(*handle), status, 0);
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return status;
}

BOOL sd_pipe_open(HANDLE *handle, ULONG access, OBJECT_ATTRIBUTES *attr, IO_STATUS_BLOCK *io,
                  ULONG disposition, ULONG options, NTSTATUS *result)
{
    const WCHAR *name;
    unsigned int n;
    struct sd_pipe_endpoint *p, *server = NULL;
    struct horizon_server_handle_entry *entry;
    NTSTATUS status = STATUS_OBJECT_NAME_NOT_FOUND;
    if (!sd_pipe_name(attr, &name, &n)) return FALSE;
    *handle = NULL;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    for (p = sd_pipe_servers; p; p = p->next) if (sd_pipe_same(p, name, n)) {
        status = STATUS_PIPE_NOT_AVAILABLE;
        if (!p->peer && p->state == FILE_PIPE_LISTENING_STATE) { server = p; break; }
    }
    access = sd_pipe_access(access);
    if (disposition != FILE_OPEN || attr->RootDirectory) status = STATUS_INVALID_PARAMETER;
    else if (options & FILE_SYNCHRONOUS_IO_ALERT) status = STATUS_NOT_SUPPORTED;
    else if (server) {
        if (((access & FILE_READ_DATA) && !(server->sharing & FILE_SHARE_READ)) ||
            ((access & FILE_WRITE_DATA) && !(server->sharing & FILE_SHARE_WRITE))) status = STATUS_ACCESS_DENIED;
        else if (!(p = calloc(1, sizeof(*p)))) status = STATUS_NO_MEMORY;
        else if (!(entry = horizon_server_create_handle_locked(HORIZON_SERVER_OBJECT_FILE))) {
            free(p); status = STATUS_NO_MEMORY;
        } else {
            p->file = entry->object; p->file->sd_pipe = p;
            p->file->file_access = access; p->file->file_options = options;
            p->file->manual_reset = 1; p->file->signaled = 1;
            p->type = server->type; p->max_instances = server->max_instances; p->sharing = server->sharing;
            p->in_quota = server->out_quota; p->out_quota = server->in_quota;
            p->peer = server; server->peer = p;
            p->state = server->state = FILE_PIPE_CONNECTED_STATE;
            *handle = ULongToHandle(entry->handle);
            status = STATUS_SUCCESS;
            /* Only one connect request is accepted for an instance. */
            if (server->operations && server->operations->listen) {
                struct sd_pipe_operation *op = server->operations;
                sd_pipe_unlink_op(server, &server->operations);
                sd_pipe_finish(op, STATUS_SUCCESS, 0);
            }
        }
    }
    io->Status = *result = status;
    io->Information = status ? 0 : FILE_OPENED;
    sd_pipe_log("open", HandleToULong(*handle), status, 0);
    sd_pipe_changed();
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return TRUE;
}

/* The caller holds the server mutex. APC completion and alertable synchronous
 * I/O are explicitly rejected until the existing APC bridge can support their
 * cancellation/lifetime contract. Event + IOCP overlapped I/O are supported. */
static struct sd_pipe_operation *sd_pipe_begin(struct sd_pipe_endpoint *p, HANDLE event,
                                               PIO_APC_ROUTINE apc, void *context,
                                               IO_STATUS_BLOCK *io, NTSTATUS *status)
{
    struct sd_pipe_operation *op;
    struct horizon_server_object *event_object = NULL;
    struct horizon_server_handle_entry *e;
    if (!io) { *status = STATUS_ACCESS_VIOLATION; return NULL; }
    if (apc || (p->file->file_options & FILE_SYNCHRONOUS_IO_ALERT)) {
        *status = STATUS_NOT_SUPPORTED; return NULL;
    }
    if ((ULONG_PTR)event & ~(ULONG_PTR)1) {
        e = horizon_server_find_handle_locked((ULONG_PTR)event & ~1u);
        if (!e) { *status = STATUS_INVALID_HANDLE; return NULL; }
        if (e->object->type != HORIZON_SERVER_OBJECT_EVENT) {
            *status = STATUS_OBJECT_TYPE_MISMATCH; return NULL;
        }
        event_object = e->object;
    }
    op = calloc(1, sizeof(*op));
    if (!op) { *status = STATUS_NO_MEMORY; return NULL; }
    op->synchronous = !!(p->file->file_options & FILE_SYNCHRONOUS_IO_NONALERT);
    op->wow = in_wow64_call() && !op->synchronous;
    op->iosb = op->wow ? io->Pointer : io;
    op->tid = HandleToULong(NtCurrentTeb()->ClientId.UniqueThread);
    op->context = (ULONG_PTR)context;
    op->suppress_port = !!((ULONG_PTR)event & 1);
    op->file = p->file; op->file->refs++; op->file->signaled = 0;
    op->event = event_object;
    if (event_object) { event_object->refs++; event_object->signaled = 0; }
    return op;
}
static NTSTATUS sd_pipe_result(struct sd_pipe_operation *op, NTSTATUS immediate)
{
    NTSTATUS status;
    (void)immediate; /* Only synchronous operations remain allocated here. */
    while (!op->completed) pthread_cond_wait(&horizon_server_objects_cond, &horizon_server_objects_mutex);
    status = op->status;
    sd_pipe_release(op->event);
    sd_pipe_release(op->file);
    free(op);
    return status;
}
static void sd_pipe_queue(struct sd_pipe_endpoint *p, struct sd_pipe_operation *op)
{
    op->pending = 1;
    sd_pipe_store_io(op, STATUS_PENDING, 0);
    if (p->last_operation) p->last_operation->next = op;
    else p->operations = op;
    p->last_operation = op;
}

BOOL sd_pipe_read_write(HANDLE handle, HANDLE event, PIO_APC_ROUTINE apc, void *context,
                        IO_STATUS_BLOCK *io, void *buffer, ULONG size, BOOL write, NTSTATUS *result)
{
    struct sd_pipe_endpoint *p;
    struct sd_pipe_operation *op;
    struct sd_pipe_message *m = NULL;
    NTSTATUS status = STATUS_SUCCESS;
    ULONG count = 0;
    int synchronous;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    if (!(p = sd_pipe_find(handle))) { pthread_mutex_unlock(&horizon_server_objects_mutex); return FALSE; }
    if (!(p->file->file_access & (write ? FILE_WRITE_DATA : FILE_READ_DATA))) status = STATUS_ACCESS_DENIED;
    else if (size && !buffer) status = STATUS_ACCESS_VIOLATION;
    else if (p->state == FILE_PIPE_DISCONNECTED_STATE) status = STATUS_PIPE_DISCONNECTED;
    else if (p->state == FILE_PIPE_LISTENING_STATE) status = STATUS_PIPE_LISTENING;
    else if (write && !p->peer) status = STATUS_PIPE_BROKEN;
    if (!status && write && (size || p->type)) {
        if (size > ~0u - p->peer->bytes || !(m = malloc(sizeof(*m) + (size_t)size))) status = STATUS_NO_MEMORY;
        else { m->next = NULL; m->size = size; m->offset = 0; if (size) memcpy(m->data, buffer, size); }
    }
    if (status || !(op = sd_pipe_begin(p, event, apc, context, io, &status))) goto done;
    synchronous = op->synchronous;
    op->buffer = buffer; op->size = size;
    if (write) {
        if (m) {
            if (p->peer->tail) p->peer->tail->next = m; else p->peer->head = m;
            p->peer->tail = m; p->peer->bytes += size; p->peer->messages++; m = NULL;
            sd_pipe_drain(p->peer);
        }
        count = size;
    } else if (!size && !p->read_mode) {
        count = 0;
    } else if (p->head) count = sd_pipe_take(p, buffer, size, &status);
    else if (!p->peer) status = STATUS_PIPE_BROKEN;
    else if (p->completion_mode) status = STATUS_PIPE_EMPTY;
    else {
        sd_pipe_queue(p, op);
        *result = synchronous ? sd_pipe_result(op, STATUS_PENDING) : STATUS_PENDING;
        pthread_mutex_unlock(&horizon_server_objects_mutex);
        return TRUE;
    }
    sd_pipe_finish(op, status, count);
    if (synchronous) status = sd_pipe_result(op, status);
done:
    free(m);
    *result = status;
    sd_pipe_log(write ? "write" : "read", HandleToULong(handle), status, count);
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return TRUE;
}

BOOL sd_pipe_control(HANDLE handle, HANDLE event, PIO_APC_ROUTINE apc, void *context,
                     IO_STATUS_BLOCK *io, ULONG code, void *buffer, ULONG size, NTSTATUS *result)
{
    struct sd_pipe_endpoint *p, *peer;
    struct sd_pipe_operation *op;
    NTSTATUS status = STATUS_SUCCESS;
    ULONG count = 0;
    int synchronous;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    if (!(p = sd_pipe_find(handle))) { pthread_mutex_unlock(&horizon_server_objects_mutex); return FALSE; }
    if (code != FSCTL_PIPE_LISTEN && code != FSCTL_PIPE_DISCONNECT && code != FSCTL_PIPE_PEEK) {
        status = STATUS_NOT_SUPPORTED; goto done;
    }
    if (code == FSCTL_PIPE_LISTEN) {
        if (!p->server) status = STATUS_ILLEGAL_FUNCTION;
        else if (p->state == FILE_PIPE_CONNECTED_STATE) status = STATUS_PIPE_CONNECTED;
        else if (p->state == FILE_PIPE_CLOSING_STATE) status = STATUS_PIPE_CLOSING;
        else if (p->operations) status = STATUS_INVALID_PARAMETER;
        else if (p->completion_mode) status = STATUS_PIPE_LISTENING;
        if (status) goto done;
    } else if (code == FSCTL_PIPE_DISCONNECT) {
        if (!p->server) { status = STATUS_ILLEGAL_FUNCTION; goto done; }
    } else if (size < 16 || !buffer) { status = STATUS_BUFFER_TOO_SMALL; goto done; }
    if (!(op = sd_pipe_begin(p, event, apc, context, io, &status))) goto done;
    synchronous = op->synchronous;
    if (code == FSCTL_PIPE_LISTEN) {
        p->state = FILE_PIPE_LISTENING_STATE;
        op->listen = 1;
        sd_pipe_queue(p, op);
        *result = synchronous ? sd_pipe_result(op, STATUS_PENDING) : STATUS_PENDING;
        sd_pipe_log("listen", HandleToULong(handle), *result, 0);
        pthread_mutex_unlock(&horizon_server_objects_mutex);
        return TRUE;
    }
    if (code == FSCTL_PIPE_DISCONNECT) {
        peer = p->peer; p->peer = NULL; p->state = FILE_PIPE_DISCONNECTED_STATE;
        sd_pipe_clear_messages(p);
        if (peer) {
            peer->peer = NULL; peer->state = FILE_PIPE_DISCONNECTED_STATE;
            sd_pipe_clear_messages(peer); sd_pipe_drain(peer);
        }
        while (p->operations) {
            struct sd_pipe_operation *pending = p->operations;
            sd_pipe_unlink_op(p, &p->operations);
            sd_pipe_finish(pending, STATUS_PIPE_DISCONNECTED, 0);
        }
    } else {
        ULONG *header = buffer;
        struct sd_pipe_message *m;
        header[0] = p->state; header[1] = p->bytes; header[2] = p->type ? p->messages : 0;
        header[3] = p->type && p->head ? p->head->size - p->head->offset : 0;
        for (m = p->head; m && count < size - 16; m = m->next) {
            ULONG n = min(m->size - m->offset, size - 16 - count);
            if (n) memcpy((char *)buffer + 16 + count, m->data + m->offset, n);
            count += n;
            if (p->type) break;
        }
        if (count < (p->type ? header[3] : p->bytes)) status = STATUS_BUFFER_OVERFLOW;
        count += 16;
    }
    sd_pipe_finish(op, status, count);
    if (synchronous) status = sd_pipe_result(op, status);
done:
    *result = status;
    sd_pipe_log("control", HandleToULong(handle), status, code);
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return TRUE;
}

BOOL sd_pipe_query(HANDLE handle, IO_STATUS_BLOCK *io, void *buffer, ULONG size, ULONG info, NTSTATUS *result)
{
    struct sd_pipe_endpoint *p;
    NTSTATUS status = STATUS_SUCCESS;
    ULONG written = 0;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    if (!(p = sd_pipe_find(handle))) { pthread_mutex_unlock(&horizon_server_objects_mutex); return FALSE; }
#define SD_PIPE_INFO(type) type *out = buffer; if (size < sizeof(*out)) { status = STATUS_INFO_LENGTH_MISMATCH; break; } memset(out, 0, sizeof(*out)); written = sizeof(*out)
    switch (info) {
    case FilePipeInformation: {
        SD_PIPE_INFO(FILE_PIPE_INFORMATION);
        out->ReadMode = p->read_mode; out->CompletionMode = p->completion_mode; break;
    }
    case FilePipeLocalInformation: {
        struct sd_pipe_endpoint *other, *server = p->server ? p : p->peer;
        SD_PIPE_INFO(FILE_PIPE_LOCAL_INFORMATION);
        out->NamedPipeType = p->type; out->MaximumInstances = p->max_instances;
        out->NamedPipeConfiguration = p->sharing == 3 ? FILE_PIPE_FULL_DUPLEX :
                                     (p->sharing & FILE_SHARE_READ ? FILE_PIPE_OUTBOUND : FILE_PIPE_INBOUND);
        out->CurrentInstances = 1;
        if (server) { out->CurrentInstances = 0; for (other = sd_pipe_servers; other; other = other->next)
            if (sd_pipe_same(other, server->name, server->name_len)) out->CurrentInstances++; }
        out->InboundQuota = p->in_quota; out->OutboundQuota = p->out_quota;
        out->ReadDataAvailable = p->bytes;
        out->WriteQuotaAvailable = p->peer && p->peer->bytes < p->out_quota ? p->out_quota - p->peer->bytes : 0;
        out->NamedPipeState = p->state; out->NamedPipeEnd = p->server ? FILE_PIPE_SERVER_END : FILE_PIPE_CLIENT_END; break;
    }
    case FileStandardInformation: {
        SD_PIPE_INFO(FILE_STANDARD_INFORMATION); out->NumberOfLinks = 1; out->AllocationSize.QuadPart = p->in_quota + p->out_quota;
        out->EndOfFile.QuadPart = p->bytes; break;
    }
    case FileAccessInformation: { SD_PIPE_INFO(FILE_ACCESS_INFORMATION); out->AccessFlags = p->file->file_access; break; }
    case FileModeInformation: { SD_PIPE_INFO(FILE_MODE_INFORMATION); out->Mode = p->file->file_options; break; }
    default: status = STATUS_INVALID_INFO_CLASS; break;
    }
#undef SD_PIPE_INFO
    io->Status = *result = status; io->Information = written;
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return TRUE;
}
BOOL sd_pipe_set(HANDLE handle, IO_STATUS_BLOCK *io, void *buffer, ULONG size, ULONG info, NTSTATUS *result)
{
    struct sd_pipe_endpoint *p;
    FILE_PIPE_INFORMATION *in = buffer;
    NTSTATUS status = STATUS_SUCCESS;
    if (info != FilePipeInformation) return FALSE; /* existing IOCP binding stays authoritative */
    pthread_mutex_lock(&horizon_server_objects_mutex);
    if (!(p = sd_pipe_find(handle))) { pthread_mutex_unlock(&horizon_server_objects_mutex); return FALSE; }
    if (size < sizeof(*in)) status = STATUS_INFO_LENGTH_MISMATCH;
    else if (in->ReadMode > 1 || in->CompletionMode > 1 || (in->ReadMode && !p->type)) status = STATUS_INVALID_PARAMETER;
    else { p->read_mode = in->ReadMode; p->completion_mode = in->CompletionMode; }
    io->Status = *result = status; io->Information = 0;
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return TRUE;
}
BOOL sd_pipe_volume(HANDLE handle, IO_STATUS_BLOCK *io, void *buffer, ULONG size, ULONG info, NTSTATUS *result)
{
    FILE_FS_DEVICE_INFORMATION *out = buffer;
    NTSTATUS status = STATUS_SUCCESS;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    if (!sd_pipe_find(handle)) { pthread_mutex_unlock(&horizon_server_objects_mutex); return FALSE; }
    if (info != FileFsDeviceInformation) status = STATUS_INVALID_INFO_CLASS;
    else if (size < sizeof(*out)) status = STATUS_INFO_LENGTH_MISMATCH;
    else { out->DeviceType = FILE_DEVICE_NAMED_PIPE; out->Characteristics = 0; }
    io->Status = *result = status; io->Information = status ? 0 : sizeof(*out);
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return TRUE;
}
BOOL sd_pipe_cancel(HANDLE handle, IO_STATUS_BLOCK *match, IO_STATUS_BLOCK *io, BOOL only_thread, NTSTATUS *result)
{
    struct sd_pipe_endpoint *p;
    struct sd_pipe_operation **link;
    ULONG tid = HandleToULong(NtCurrentTeb()->ClientId.UniqueThread), count = 0;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    if (!(p = sd_pipe_find(handle))) { pthread_mutex_unlock(&horizon_server_objects_mutex); return FALSE; }
    link = &p->operations;
    while (*link) {
        struct sd_pipe_operation *op = *link;
        if ((!only_thread || op->tid == tid) && (!match || op->iosb == match)) {
            sd_pipe_unlink_op(p, link); sd_pipe_finish(op, STATUS_CANCELLED, 0); count++;
        } else link = &op->next;
    }
    io->Status = *result = (!only_thread && !count) ? STATUS_NOT_FOUND : STATUS_SUCCESS;
    io->Information = 0;
    sd_pipe_log("cancel", HandleToULong(handle), *result, count);
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return TRUE;
}
