/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Passive, one-shot diagnostics. All shared fields use atomic accesses.
 * Rows belong to one thread lifetime, so recycled kernel handles do not merge.
 * Times from different threads overlap; they must never be added as frame cost.
 */
#ifndef SD_FRAME_DIAG_CORE_H
#define SD_FRAME_DIAG_CORE_H
#include <stdint.h>
#define SD_DIAG_THREADS 128
#define SD_DIAG_STAGES 7
#define SD_DIAG_LOAD(p) __atomic_load_n((p), __ATOMIC_RELAXED)
#define SD_DIAG_ADD(p,v) __atomic_add_fetch((p),(v),__ATOMIC_RELAXED)
struct sd_diag_stat {
    uint64_t calls, ticks, peak, timeouts, errors, direct, pipe;
};
struct sd_diag_row {
    unsigned handle;
    struct sd_diag_stat stages[SD_DIAG_STAGES];
    uint64_t frames, frame_ticks, frame_peak, cpu_frames, cpu_ticks;
    uint64_t over33, over50, over100;
};
struct sd_diag_data {
    uint64_t begin, end, capacity_drops;
    unsigned next;
    struct sd_diag_row rows[SD_DIAG_THREADS];
};
static void sd_diag_peak(uint64_t *target, uint64_t value)
{
    uint64_t old = SD_DIAG_LOAD(target);
    while (old < value && !__atomic_compare_exchange_n(target, &old, value, 1,
                                                       __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {}
}
static int sd_diag_inside(const struct sd_diag_data *data, uint64_t begin, uint64_t end)
{
    uint64_t first = __atomic_load_n(&data->begin, __ATOMIC_ACQUIRE);
    return first && begin >= first && end >= begin && end < SD_DIAG_LOAD(&data->end);
}
static struct sd_diag_row *sd_diag_register(struct sd_diag_data *data, unsigned handle)
{
    unsigned index = __atomic_fetch_add(&data->next, 1, __ATOMIC_RELAXED);
    if (index >= SD_DIAG_THREADS) {
        SD_DIAG_ADD(&data->capacity_drops, 1);
        return 0;
    }
    struct sd_diag_row *row = &data->rows[index];
    __atomic_store_n(&row->handle, handle, __ATOMIC_RELEASE);
    return row;
}
static void sd_diag_record(struct sd_diag_row *row, unsigned stage, uint64_t ticks,
                           unsigned timeout, unsigned error, unsigned route)
{
    if (!row || stage >= SD_DIAG_STAGES) return;
    struct sd_diag_stat *stat = &row->stages[stage];
    SD_DIAG_ADD(&stat->ticks, ticks);
    SD_DIAG_ADD(&stat->timeouts, !!timeout);
    SD_DIAG_ADD(&stat->errors, !!error);
    SD_DIAG_ADD(&stat->direct, route == 1);
    SD_DIAG_ADD(&stat->pipe, route == 2);
    sd_diag_peak(&stat->peak, ticks);
    SD_DIAG_ADD(&stat->calls, 1);
}
static void sd_diag_frame(struct sd_diag_row *row, uint64_t ticks, uint64_t cpu,
                          int cpu_valid, uint64_t us)
{
    if (!row) return;
    SD_DIAG_ADD(&row->frame_ticks, ticks);
    sd_diag_peak(&row->frame_peak, ticks);
    if (cpu_valid && cpu <= ticks) {
        SD_DIAG_ADD(&row->cpu_ticks, cpu);
        SD_DIAG_ADD(&row->cpu_frames, 1);
    }
    SD_DIAG_ADD(&row->over33, us > 33333);
    SD_DIAG_ADD(&row->over50, us > 50000);
    SD_DIAG_ADD(&row->over100, us > 100000);
    SD_DIAG_ADD(&row->frames, 1);
}
#endif
