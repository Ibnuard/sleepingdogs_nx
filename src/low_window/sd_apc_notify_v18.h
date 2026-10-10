/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Ordinary user APC enqueue changes only its target thread's APC queue.
 * Included after sd_sync_queue.h; every access holds objects_mutex. Queued
 * waiters retain their connection/thread references until they unlink.
 * Object consumption, APC delivery and deadlines stay in the select handler.
 */
int wine_nx_sd_apc_targeted_wake = 1; /* immutable after startup */
/* Accepted notices, target candidates, unrelated candidates, actual signals.
 * Candidate counts are not saved wakes or a CPU/frame-time estimate. */
static uint64_t sd_apc_notify_counts[4];

static void __attribute__((noinline)) sd_sync_signal_apc_locked(
    const struct horizon_server_object *target)
{
    ++sd_apc_notify_counts[0];
    if (!wine_nx_sd_apc_targeted_wake || horizon_fast_sync_enabled != 2 || !target) {
        horizon_server_signal_changed_locked();
        return;
    }
    for (struct sd_sync_waiter *w = sd_sync_waiters; w; w = w->next) {
        if (w->connection->thread != target) {
            ++sd_apc_notify_counts[2];
            continue;
        }
        ++sd_apc_notify_counts[1];
        /* Do not consume an object or restrict request flags here. A wake
         * only asks the unchanged select handler to recheck its predicates. */
        if (!w->notified) ++sd_apc_notify_counts[3];
        sd_sync_wake_locked(w, 0);
    }
    /* Legacy mixed-object waits and start gates retain the original broad
     * notification. The optional router also keeps its existing semantics. */
    if (wine_nx_fex_targeted_wake)
        pes27_notify(&fex_sync_router, NULL, 1, fex_sync_resolve, fex_sync_wake);
    if (horizon_server_sleepers)
        pthread_cond_broadcast(&horizon_server_objects_cond);
}

void wine_nx_sd_apc_notify_snapshot(uint64_t out[5])
{
    pthread_mutex_lock(&horizon_server_objects_mutex);
    out[0] = wine_nx_sd_apc_targeted_wake;
    memcpy(out + 1, sd_apc_notify_counts, sizeof(sd_apc_notify_counts));
    pthread_mutex_unlock(&horizon_server_objects_mutex);
}
