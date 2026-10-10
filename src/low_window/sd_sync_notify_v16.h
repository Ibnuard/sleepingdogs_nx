/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Included after horizon_server_signal_changed_locked, under the same lock.
 * Only completion-port queue/close and timer rearm changes may use this path.
 * sd_sync_queue_locked rejects ALL waits containing any of those objects.
 * APC, resume, termination, registry and named-pipe notifications stay broad:
 * they may change an event or the state of a queued thread.
 */
int wine_nx_sd_sync_notify_filter = 1; /* immutable after startup */
enum sd_sync_legacy_reason {
    SD_SYNC_COMPLETION_POST,
    SD_SYNC_TIMER_REARM,
    SD_SYNC_COMPLETION_CLOSE
};
/* Calls by reason, then sum of queued candidates excluded from the list walk.
 * The latter is NOT a count of actual condvar signals or a timing estimate. */
static uint64_t sd_sync_legacy_counts[4];

static void sd_sync_signal_legacy_locked(enum sd_sync_legacy_reason reason)
{
    ++sd_sync_legacy_counts[reason];
    if (!wine_nx_sd_sync_notify_filter || horizon_fast_sync_enabled != 2) {
        horizon_server_signal_changed_locked();
        return;
    }
    sd_sync_legacy_counts[3] += sd_sync_counts[6];
    /* Preserve both legacy wait routes, including mixed-object wait-all and
     * shared start gates. There is no new queue, timeout or object mutation. */
    if (wine_nx_fex_targeted_wake)
        pes27_notify(&fex_sync_router, NULL, 1, fex_sync_resolve, fex_sync_wake);
    if (horizon_server_sleepers)
        pthread_cond_broadcast(&horizon_server_objects_cond);
}

void wine_nx_sd_sync_notify_snapshot(uint64_t out[5])
{
    pthread_mutex_lock(&horizon_server_objects_mutex);
    out[0] = wine_nx_sd_sync_notify_filter;
    memcpy(out + 1, sd_sync_legacy_counts, sizeof(sd_sync_legacy_counts));
    pthread_mutex_unlock(&horizon_server_objects_mutex);
}
