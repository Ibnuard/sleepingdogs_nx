/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Debug-only observations across the menu -> scene transition. */
#ifndef SD_LOADING_WATCH_H
#define SD_LOADING_WATCH_H

#define SD_LOADING_WATCH_SECONDS 600u
#define SD_LOADING_REPORT_SECONDS 15u
#define SD_LOADING_CAPTURE_SECONDS 30u

static inline int sd_loading_snapshot_due(unsigned seconds, unsigned *captures, unsigned *last)
{
    if (seconds < SD_LOADING_CAPTURE_SECONDS || seconds >= SD_LOADING_WATCH_SECONDS ||
        *captures >= SD_LOADING_WATCH_SECONDS / SD_LOADING_CAPTURE_SECONDS ||
        (*captures && (seconds < *last || seconds - *last < SD_LOADING_CAPTURE_SECONDS)))
        return 0;
    ++*captures;
    *last = seconds;
    return 1;
}

#endif
