/* SPDX-License-Identifier: LGPL-2.1-or-later. Called by the monitor only. */
void wine_nx_sd_diag_thread_map(void)
{
    static struct nx_prof_thread snapshot[NX_PROF_MAX_THREADS];
    char line[180];
    pthread_mutex_lock(&registry_mutex);
    memcpy(snapshot, registry, sizeof(snapshot));
    pthread_mutex_unlock(&registry_mutex);
    for (unsigned i = 0; i < NX_PROF_MAX_THREADS; ++i) {
        const struct nx_prof_thread *row = &snapshot[i];
        if (!row->handle) continue;
        snprintf(line, sizeof(line), "[SD-DIAG-MAP] handle=%u tid=%u kind=%c registered_core=%d fixed=%d",
                 row->handle, row->tid, row->kind, row->core, row->fixed);
        wine_nx_runtime_trace(line);
    }
}
