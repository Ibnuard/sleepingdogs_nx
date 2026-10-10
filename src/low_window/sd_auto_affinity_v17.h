/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Automatic placement only. Guest-requested affinity and helper policies
 * remain authoritative. This mode never adds core 3, even when granted.
 */
#ifndef SD_AUTO_AFFINITY_V17_H
#define SD_AUTO_AFFINITY_V17_H
#include <stdint.h>
extern int wine_nx_sd_auto_affinity;
void wine_nx_sd_scheduler_pin_result(int failed);

static inline uint64_t sd_auto_allowed_mask(uint64_t process_mask)
{
    return process_mask & UINT64_C(7);
}

static inline int sd_auto_preferred(uint64_t mask, int current, int registered)
{
    if (current >= 0 && current < 3 && (mask & (UINT64_C(1) << current))) return current;
    if (registered >= 0 && registered < 3 && (mask & (UINT64_C(1) << registered))) return registered;
    return mask ? __builtin_ctzll(mask) : -1;
}
#endif
