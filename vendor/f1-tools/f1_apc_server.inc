/* Ordinary user APCs use Wine's existing queue_apc/select wire protocol.
 * Special/kernel APCs and reserve objects need additional semantics: reject
 * them explicitly instead of pretending their callback has been scheduled. */
static unsigned long long f1_apc_queued, f1_apc_delivered, f1_apc_rejected;
unsigned long long f1_apc_entered, f1_apc_returned;

void wine_nx_f1_apc_snapshot(unsigned long long out[5])
{
    out[0] = __atomic_load_n(&f1_apc_queued, __ATOMIC_RELAXED);
    out[1] = __atomic_load_n(&f1_apc_delivered, __ATOMIC_RELAXED);
    out[2] = __atomic_load_n(&f1_apc_rejected, __ATOMIC_RELAXED);
    out[3] = __atomic_load_n(&f1_apc_entered, __ATOMIC_RELAXED);
    out[4] = __atomic_load_n(&f1_apc_returned, __ATOMIC_RELAXED);
}

static int f1_server_queue_apc(struct horizon_server_connection *connection,
                             const unsigned char *message,
                             const unsigned char *data, unsigned int data_size)
{
    const struct queue_apc_request *request = (const void *)message;
    struct queue_apc_reply reply = {0};
    struct horizon_server_object *thread;
    union apc_call call;
    unsigned int status;

    /* Use the Wine types, so a changed protocol cannot silently truncate the
     * 64-bit function/context/IOSB values carried by WoW64. */
    if (data_size != sizeof(call)) status = STATUS_INVALID_PARAMETER;
    else {
        memcpy(&call, data, sizeof(call));
        if (call.type != APC_USER || request->reserve_handle) status = STATUS_NOT_IMPLEMENTED;
        else if (call.user.flags) status = STATUS_NOT_SUPPORTED;
        else if (!call.user.func) status = STATUS_INVALID_PARAMETER;
        else {
            pthread_mutex_lock(&horizon_server_objects_mutex);
            thread = horizon_server_get_thread_locked(request->handle, &status);
            if (thread) {
                if (thread->thread.terminated) status = STATUS_THREAD_IS_TERMINATING;
                else status = f1_apc_push(&thread->f1_apcs, &call.user);
                if (!status) {
                    __atomic_add_fetch(&f1_apc_queued, 1, __ATOMIC_RELAXED);
                    /* An alertable waiter need not be waiting on its own
                     * thread handle. Wake both shared and routed waiters. */
                    horizon_server_signal_changed_locked();
                }
            }
            pthread_mutex_unlock(&horizon_server_objects_mutex);
        }
    }
    if (status) __atomic_add_fetch(&f1_apc_rejected, 1, __ATOMIC_RELAXED);
    reply.__header.error = status;
    return horizon_server_write_reply(connection->reply_fd, &reply, sizeof(reply), NULL, 0);
}

/* Call after checking/consuming wait objects, like Wine server/thread.c.
 * A nonalertable wait, an invalid handle or an already signaled object must
 * not consume an ordinary user APC. NtTestAlert uses a zero-size select. */
static int f1_server_select_apc(struct horizon_server_connection *connection,
                              const struct horizon_select_request *request,
                              unsigned int wait_status, union apc_call *call)
{
    if (wait_status != STATUS_TIMEOUT || !(request->flags & SELECT_ALERTABLE) ||
        request->header.reply_size < sizeof(*call) || !connection->thread ||
        connection->thread->thread.terminated || connection->thread->thread.suspend)
        return 0;
    if (!f1_apc_pop(&connection->thread->f1_apcs, call)) return 0;
    __atomic_add_fetch(&f1_apc_delivered, 1, __ATOMIC_RELAXED);
    return 1;
}
