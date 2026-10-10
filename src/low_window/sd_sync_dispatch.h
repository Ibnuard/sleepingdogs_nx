/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Direct request dispatch and thread-reference cache adapted from Autorun
 * 17a558619724 / 0625c79c9dbb. No FEX translator or guest ABI change.
 */
static pthread_key_t sd_sync_thread_key;
static pthread_once_t sd_sync_thread_once = PTHREAD_ONCE_INIT;
static int sd_sync_thread_key_valid;
static __thread struct horizon_server_object *sd_sync_thread;

static void sd_sync_release_thread(void *ptr)
{
    struct horizon_server_object *thread = ptr;
    sd_sync_thread = NULL;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    if (!--thread->refs) horizon_server_free_object(thread);
    pthread_mutex_unlock(&horizon_server_objects_mutex);
}

static void sd_sync_init_thread_key(void)
{
    sd_sync_thread_key_valid = !pthread_key_create(&sd_sync_thread_key, sd_sync_release_thread);
}

static struct horizon_server_object *sd_sync_get_thread_locked(unsigned tid)
{
    struct horizon_server_object *thread = sd_sync_thread;
    if (thread && thread->thread.tid == tid) return thread->thread.terminated ? NULL : thread;
    if (thread) {
        if (pthread_setspecific(sd_sync_thread_key, NULL)) return NULL;
        sd_sync_thread = NULL;
        if (!--thread->refs) horizon_server_free_object(thread);
    }
    for (thread = horizon_server_threads; thread; thread = thread->thread_next)
        if (thread->thread.tid == tid && !thread->thread.terminated) break;
    if (!thread || pthread_setspecific(sd_sync_thread_key, thread)) return NULL;
    ++thread->refs;
    return sd_sync_thread = thread;
}

int horizon_server_sync_call(unsigned tid, const void *message, const void *data,
                             unsigned data_size, void *reply, void *reply_data)
{
    const struct horizon_server_request_header *request = message;
    struct horizon_server_connection connection = {0}, *previous;
    struct horizon_server_object *thread;
    int (*handler)(struct horizon_server_connection *, const unsigned char *) = NULL;
    int status;
    if (!horizon_fast_sync_enabled || !tid || !message || !reply) return 0;
    if (request->request_size != data_size || (data_size && !data) ||
        (request->reply_size && !reply_data)) return 0;
    switch (request->req) {
    case HORIZON_REQ_SELECT: break;
    case HORIZON_REQ_EVENT_OP: handler = horizon_server_handle_event_op; break;
    case HORIZON_REQ_QUERY_EVENT: handler = horizon_server_handle_query_event; break;
    case HORIZON_REQ_RELEASE_MUTEX: handler = horizon_server_handle_release_mutex; break;
    case HORIZON_REQ_QUERY_MUTEX: handler = horizon_server_handle_query_mutex; break;
    case HORIZON_REQ_RELEASE_SEMAPHORE: handler = horizon_server_handle_release_semaphore; break;
    case HORIZON_REQ_QUERY_SEMAPHORE: handler = horizon_server_handle_query_semaphore; break;
    default: return 0;
    }
    if (!sd_sync_thread) {
        pthread_once(&sd_sync_thread_once, sd_sync_init_thread_key);
        if (!sd_sync_thread_key_valid) return 0;
    }
    pthread_mutex_lock(&horizon_server_objects_mutex);
    thread = sd_sync_get_thread_locked(tid);
    /* Keep startup and suspended-thread requests on the proven server path. */
    if (!thread || !thread->thread.started || thread->thread.suspend) {
        pthread_mutex_unlock(&horizon_server_objects_mutex);
        return 0;
    }
    connection.tid = tid;
    connection.pid = thread->thread.pid;
    connection.thread = thread;
    connection.direct_reply = reply;
    connection.direct_data = reply_data;
    connection.direct_size = request->reply_size;
    previous = horizon_server_current;
    horizon_server_current = &connection;
    if (handler) status = handler(&connection, message);
    else status = horizon_server_handle_select(&connection, message, data, data_size);
    horizon_server_current = previous;
    if (status) {
        struct horizon_server_reply_header *header = reply;
        memset(reply, 0, HORIZON_SERVER_FIXED_MESSAGE_SIZE);
        header->error = HORIZON_STATUS_UNSUCCESSFUL;
    }
    return 1;
}
