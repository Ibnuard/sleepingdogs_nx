/* SPDX-License-Identifier: LGPL-2.1-or-later
 * No allocation, locks, thread suspension or log writes on the measured paths.
 * CPU ticks are queried once per Present, only inside the 30-second capture.
 */
#include "sd_frame_diag_core.h"
#include "f1_bounded_profile.h"
static int sd_frame_diag_enabled;
static struct sd_diag_data sd_frame_diag;
static __thread struct sd_diag_row *sd_frame_diag_row;
static __thread int sd_frame_diag_registered;

static struct sd_diag_row *sd_frame_diag_current(void)
{
    if (!sd_frame_diag_registered) {
        sd_frame_diag_row = sd_diag_register(&sd_frame_diag, threadGetCurHandle());
        sd_frame_diag_registered = 1;
    }
    return sd_frame_diag_row;
}

/* Exported to Wine's request completion path. stage 0/1/2=select/event/other;
 * Vulkan uses 3/4/5/6=acquire/submit/fence/semaphore. Reuse existing timestamps. */
void wine_nx_sd_diag_note(unsigned stage, uint64_t begin, uint64_t end,
                          unsigned timeout, unsigned error, unsigned route)
{
    if (!sd_diag_inside(&sd_frame_diag, begin, end)) return;
    sd_diag_record(sd_frame_diag_current(), stage, end-begin, timeout, error, route);
}

static void sd_frame_diag_present(uint64_t queue, uint64_t swapchain, uint64_t now, int valid)
{
    static __thread uint64_t previous_wall, previous_cpu, previous_queue, previous_swapchain;
    static __thread unsigned previous_valid;
    uint64_t cpu = 0;
    if (!valid || !sd_diag_inside(&sd_frame_diag, now, now)) {
        previous_wall = previous_valid = 0;
        return;
    }
    unsigned cpu_valid = R_SUCCEEDED(svcGetInfo(&cpu, InfoType_ThreadTickCount,
                                               threadGetCurHandle(), UINT64_MAX));
    if (previous_wall && sd_diag_inside(&sd_frame_diag, previous_wall, now) &&
        queue == previous_queue && swapchain == previous_swapchain) {
        unsigned good_cpu = cpu_valid && previous_valid && cpu >= previous_cpu;
        uint64_t delta_cpu = good_cpu ? cpu-previous_cpu : 0;
        sd_diag_frame(sd_frame_diag_current(), now-previous_wall, delta_cpu, good_cpu,
                      armTicksToNs(now-previous_wall)/1000);
    }
    previous_wall = now; previous_cpu = cpu; previous_valid = cpu_valid;
    previous_queue = queue; previous_swapchain = swapchain;
}

/* Monitor-thread only. Counter snapshots during capture are approximate;
 * final values contain completed calls wholly inside the capture interval. */
static void sd_frame_diag_report(uint64_t now, int final)
{
    static const char *const stages[] = {"wine_select", "wine_event", "wine_other",
                                         "vk_acquire", "vk_submit", "vk_fence", "vk_semaphore"};
    extern void wine_nx_sd_diag_thread_map(void);
    uint64_t begin = SD_DIAG_LOAD(&sd_frame_diag.begin), end = SD_DIAG_LOAD(&sd_frame_diag.end);
    unsigned count = SD_DIAG_LOAD(&sd_frame_diag.next);
    if (count > SD_DIAG_THREADS) count = SD_DIAG_THREADS;
    wine_nx_sd_diag_thread_map();
    log_line("[SD-DIAG] phase=%s elapsed_ms=%llu rows=%u capacity_drops=%llu; cumulative, completed calls, overlapping wall times, not GPU execution",
        final ? "complete" : "sample", (unsigned long long)(armTicksToNs((now < end ? now : end)-begin)/1000000),
        count, (unsigned long long)SD_DIAG_LOAD(&sd_frame_diag.capacity_drops));
    for (unsigned i = 0; i < count; ++i) {
        const struct sd_diag_row *row = &sd_frame_diag.rows[i];
        unsigned handle = __atomic_load_n(&row->handle, __ATOMIC_ACQUIRE);
        if (!handle) continue;
        for (unsigned j = 0; j < SD_DIAG_STAGES; ++j) {
            const struct sd_diag_stat *s = &row->stages[j];
            uint64_t calls = SD_DIAG_LOAD(&s->calls);
            if (!calls) continue;
            uint64_t us = armTicksToNs(SD_DIAG_LOAD(&s->ticks))/1000;
            log_line("[SD-DIAG-WAIT] row=%u handle=%u stage=%s n=%llu total_us=%llu avg_us=%llu peak_us=%llu timeouts=%llu errors=%llu direct=%llu pipe=%llu",
                i, handle, stages[j], (unsigned long long)calls, (unsigned long long)us,
                (unsigned long long)(us/calls), (unsigned long long)(armTicksToNs(SD_DIAG_LOAD(&s->peak))/1000),
                (unsigned long long)SD_DIAG_LOAD(&s->timeouts), (unsigned long long)SD_DIAG_LOAD(&s->errors),
                (unsigned long long)SD_DIAG_LOAD(&s->direct), (unsigned long long)SD_DIAG_LOAD(&s->pipe));
        }
        uint64_t frames = SD_DIAG_LOAD(&row->frames);
        if (frames) log_line("[SD-DIAG-FRAME] row=%u handle=%u n=%llu gap_total_us=%llu gap_peak_us=%llu cpu_valid_n=%llu thread_cpu_total_us=%llu over33=%llu over50=%llu over100=%llu; presenting thread only",
            i, handle, (unsigned long long)frames,
            (unsigned long long)(armTicksToNs(SD_DIAG_LOAD(&row->frame_ticks))/1000),
            (unsigned long long)(armTicksToNs(SD_DIAG_LOAD(&row->frame_peak))/1000),
            (unsigned long long)SD_DIAG_LOAD(&row->cpu_frames),
            (unsigned long long)(armTicksToNs(SD_DIAG_LOAD(&row->cpu_ticks))/1000),
            (unsigned long long)SD_DIAG_LOAD(&row->over33), (unsigned long long)SD_DIAG_LOAD(&row->over50),
            (unsigned long long)SD_DIAG_LOAD(&row->over100));
    }
}

static void sd_frame_diag_monitor(uint64_t now, uint64_t frames)
{
    static struct f1_profile_gate gate;
    static uint64_t last, previous_frames, last_report;
    static unsigned done;
    if (!__atomic_load_n(&sd_frame_diag_enabled, __ATOMIC_ACQUIRE) || done) return;
    uint64_t begin = SD_DIAG_LOAD(&sd_frame_diag.begin);
    if (begin) {
        int final = now >= SD_DIAG_LOAD(&sd_frame_diag.end);
        if (final || armTicksToNs(now-last_report) >= UINT64_C(10000000000)) {
            sd_frame_diag_report(now, final);
            last_report = now;
            if (final) done = 1;
        }
        return;
    }
    if (!last) { last = now; previous_frames = frames; return; }
    uint64_t elapsed_us = armTicksToNs(now-last)/1000;
    if (elapsed_us < 10000000) return;
    uint64_t delta = frames >= previous_frames ? frames-previous_frames : 0;
    last = now; previous_frames = frames;
    if (!f1_profile_gate_window(&gate, elapsed_us, delta)) return;
    __atomic_store_n(&sd_frame_diag.end, now+armNsToTicks(UINT64_C(30000000000)), __ATOMIC_RELAXED);
    __atomic_store_n(&sd_frame_diag.begin, now, __ATOMIC_RELEASE);
    last_report = now;
    log_line("[SD-DIAG] phase=start tick=%llu duration_ms=30000; two consecutive 3-25 FPS windows, workload heuristic, sampler=off",
             (unsigned long long)now);
}
