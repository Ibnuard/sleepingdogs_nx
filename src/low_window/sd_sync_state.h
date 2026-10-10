/* SPDX-License-Identifier: LGPL-2.1-or-later
 * FEXTendo adaptation of Autorun 17a558619724 / 0625c79c9dbb.
 * Keep the local APC, startup and object handlers. All queue state is guarded
 * by horizon_server_objects_mutex. Modes: 0 pipe, 1 direct, 2 direct + queues.
 */
int horizon_fast_sync_enabled;
struct sd_sync_link {
    struct sd_sync_link *next, *prev;
    struct horizon_server_object *object;
    struct sd_sync_waiter *waiter;
};
struct sd_sync_waiter {
    struct sd_sync_waiter *next, **prev;
    struct horizon_server_connection *connection;
    const struct horizon_select_request *request;
    const unsigned char *data;
    unsigned data_size, count, status;
    int queued, notified, completed;
    pthread_cond_t condition;
    struct sd_sync_link links[64];
};
static struct sd_sync_waiter *sd_sync_waiters;
static uint64_t sd_sync_counts[8]; /* sleeps, targeted, broad, completed, queued, fallback, active, peak */
static void sd_sync_notify_locked(const void *object);

void wine_nx_sd_sync_snapshot(uint64_t out[8])
{
    pthread_mutex_lock(&horizon_server_objects_mutex);
    memcpy(out, sd_sync_counts, sizeof(sd_sync_counts));
    pthread_mutex_unlock(&horizon_server_objects_mutex);
}

static void horizon_server_sync_lock(const struct horizon_server_connection *connection)
{
    /* Direct dispatch already owns the same mutex. The original handlers
     * retain their unlock, including their atomic condvar wait/unlock. */
    if (!connection->direct_reply) pthread_mutex_lock(&horizon_server_objects_mutex);
}
