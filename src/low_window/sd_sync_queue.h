/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Per-object queues adapted from Autorun 0625c79c9dbb. Only event, mutex,
 * semaphore and thread waits join this queue. Other waits keep local polling.
 * Included after the original select-status implementation, under its lock.
 */
static void sd_sync_unqueue_locked(struct sd_sync_waiter *waiter)
{
    if (waiter->queued) {
        *waiter->prev = waiter->next;
        if (waiter->next) waiter->next->prev = waiter->prev;
        waiter->queued = 0;
        --sd_sync_counts[6];
    }
    while (waiter->count) {
        struct sd_sync_link *link = &waiter->links[--waiter->count];
        struct horizon_server_object *object = link->object;
        if (link->next == link) object->sd_waiters = NULL;
        else {
            link->prev->next = link->next;
            link->next->prev = link->prev;
            if (object->sd_waiters == link) object->sd_waiters = link->next;
        }
        if (!--object->refs) horizon_server_free_object(object);
    }
}

static int sd_sync_queue_locked(struct sd_sync_waiter *waiter)
{
    const unsigned char *data = waiter->data;
    const unsigned int *handles;
    unsigned size = waiter->request->size, count;
    int op;
    if (horizon_fast_sync_enabled != 2 || !waiter->connection->direct_reply) return 0;
    if (!data || size < sizeof(op)) return 0;
    if (waiter->data_size >= HORIZON_APC_RESULT_SIZE &&
        size <= waiter->data_size - HORIZON_APC_RESULT_SIZE) data += HORIZON_APC_RESULT_SIZE;
    else if (size > waiter->data_size) return 0;
    memcpy(&op, data, sizeof(op));
    if (op == HORIZON_SELECT_WAIT || op == HORIZON_SELECT_WAIT_ALL) {
        if (size < 8 || (size - 4) % 4) return 0;
        count = (size - 4) / 4;
        handles = (const void *)(data + 4);
    } else if (op == HORIZON_SELECT_SIGNAL_AND_WAIT) {
        if (size < 8) return 0;
        count = 1;
        handles = (const void *)(data + 4);
    } else return 0;
    if (count > 64) return 0;
    for (unsigned i = 0; i < count; ++i) {
        struct horizon_server_handle_entry *entry;
        struct horizon_server_object *object;
        struct sd_sync_link *link = &waiter->links[waiter->count];
        if (handles[i] == HORIZON_CURRENT_THREAD_HANDLE) object = waiter->connection->thread;
        else {
            entry = horizon_server_find_handle_locked(handles[i]);
            object = entry ? entry->object : NULL;
        }
        if (!object) goto unsupported;
        switch (object->type) {
        case HORIZON_SERVER_OBJECT_EVENT:
        case HORIZON_SERVER_OBJECT_MUTEX:
        case HORIZON_SERVER_OBJECT_SEMAPHORE:
        case HORIZON_SERVER_OBJECT_THREAD: break;
        default: goto unsupported;
        }
        link->object = object;
        link->waiter = waiter;
        if (object->sd_waiters) {
            link->next = object->sd_waiters;
            link->prev = object->sd_waiters->prev;
            link->prev->next = link;
            link->next->prev = link;
        } else object->sd_waiters = link->next = link->prev = link;
        ++object->refs;
        ++waiter->count;
    }
    waiter->next = sd_sync_waiters;
    waiter->prev = &sd_sync_waiters;
    if (waiter->next) waiter->next->prev = &waiter->next;
    sd_sync_waiters = waiter;
    waiter->queued = 1;
    ++sd_sync_counts[4];
    if (++sd_sync_counts[6] > sd_sync_counts[7]) sd_sync_counts[7] = sd_sync_counts[6];
    return 1;
unsupported:
    sd_sync_unqueue_locked(waiter);
    return 0;
}

static void sd_sync_wake_locked(struct sd_sync_waiter *waiter, int broad)
{
    if (waiter->notified) return;
    waiter->notified = 1;
    ++sd_sync_counts[broad ? 2 : 1];
    pthread_cond_signal(&waiter->condition);
}

static void sd_sync_notify_locked(const void *changed)
{
    const struct horizon_server_object *object = changed;
    struct sd_sync_link *link;
    if (!sd_sync_waiters) return;
    if (!object) {
        /* APCs, ResumeThread and termination retain the existing broad path.
         * Do not acquire signals on behalf of a possibly suspended thread. */
        for (struct sd_sync_waiter *w = sd_sync_waiters; w; w = w->next)
            sd_sync_wake_locked(w, 1);
        return;
    }
    if (!(link = object->sd_waiters)) return;
    do {
        struct sd_sync_waiter *w = link->waiter;
        struct horizon_server_connection *previous = horizon_server_current;
        if (w->completed) continue;
        if (w->connection->thread->thread.suspend || w->connection->thread->thread.terminated) {
            sd_sync_wake_locked(w, 0);
            continue;
        }
        /* The existing select implementation owns wait-any/all consumption,
         * mutex ownership and status values. Signal-and-wait has already
         * signaled before it queues, hence initial=0 here. */
        horizon_server_current = w->connection;
        w->status = horizon_server_select_status(w->request, w->data, w->data_size, 0);
        horizon_server_current = previous;
        if (w->status == HORIZON_STATUS_TIMEOUT) continue;
        w->completed = 1;
        ++sd_sync_counts[3];
        sd_sync_wake_locked(w, 0);
    } while ((link = link->next) != object->sd_waiters);
}

static void sd_sync_sleep_locked(struct sd_sync_waiter *waiter, long long timeout)
{
    /* Retain v9's 20ms safety recheck for local cooperative suspension and
     * cancellation. No new periodic polling is introduced. */
    if (timeout > HORIZON_SERVER_WAIT_SLICE) timeout = HORIZON_SERVER_WAIT_SLICE;
    if (timeout <= 0) return;
    waiter->notified = 0;
    ++sd_sync_counts[0];
    condvarWaitTimeout(&waiter->condition.cond, &horizon_server_objects_mutex.normal, (u64)timeout * 100);
}
