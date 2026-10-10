/* SPDX-License-Identifier: LGPL-2.1-or-later */
static void sd_direct_sync_report(void)
{
    extern void wine_nx_sd_sync_snapshot(uint64_t out[8]);
    extern void wine_nx_sd_sync_calls(uint64_t out[3]);
    uint64_t q[8], c[3];
    wine_nx_sd_sync_snapshot(q);
    wine_nx_sd_sync_calls(c);
    log_line("[SD-DIRECT-SYNC] direct=%llu pipe=%llu direct_select=%llu queued=%llu sleeps=%llu targeted=%llu broad=%llu completed=%llu fallback_waits=%llu active=%llu peak=%llu; cumulative",
        (unsigned long long)c[0], (unsigned long long)c[1], (unsigned long long)c[2],
        (unsigned long long)q[4], (unsigned long long)q[0], (unsigned long long)q[1],
        (unsigned long long)q[2], (unsigned long long)q[3], (unsigned long long)q[5],
        (unsigned long long)q[6], (unsigned long long)q[7]);
}
