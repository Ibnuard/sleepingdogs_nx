"""Apply production Wine counter policy to an already generated v3 runtime.

The native compact monitor bypassed sd_perf_summary while the inherited
performance-counters.txt still enabled per-request clock/atomic accounting.
Keep the generic preference for the Wine renderer, and require a separate
explicit native opt-in which also restores its report consumer.
"""


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"runtime v4 anchor count {text.count(before)}: {before[:100]}")
    return text.replace(before, after, 1)


COUNTER_POLICY = r'''
/* A legacy performance-counters.txt shipped with earlier updates. Native
 * gameplay must not collect those counters without a report consumer. */
static int sd_perf_counter_policy(int native, int guest_tests,
                                  int generic_requested, int native_requested)
{
    return native ? (!guest_tests && native_requested) : generic_requested;
}
'''


def runtime_overlay(text):
    """Accept fully generated v3 source; retain LSFG, scheduling and checks."""
    text = replace_once(text, '#include "sd_perf_summary.h"',
                        '#include "sd_perf_summary.h"\n' + COUNTER_POLICY)
    text = replace_once(text,
        '        if(__atomic_load_n(&sd_com_enabled,__ATOMIC_ACQUIRE)){sd_com_progress_report();continue;} /* native compact monitor; no bulk observer */',
        '''        if(__atomic_load_n(&sd_com_enabled,__ATOMIC_ACQUIRE)) {
            sd_com_progress_report();
            /* Only the explicit native opt-in restores this report consumer.
             * Ordinary native launch keeps its small progress monitor. */
            if (sd_perf_counters) sd_perf_summary(now,0);
            continue;
        }''')
    before = '''    sd_perf_counters = wine_nx_config_file_bool(RUNTIME_DIR "/performance-counters.txt", 0);
    log_line("[SD-PERF] v1 requested=%d active=%d interval_ms=10000; normal Launch only; existing thread/driver/wait/compiler/IO counters",
             sd_perf_counters, sd_perf_counters && !fx_ui_view.debug);'''
    after = '''    const int sd_perf_generic_requested = wine_nx_config_file_bool(RUNTIME_DIR "/performance-counters.txt", 0);
    const int sd_perf_native_requested = sd_com_enabled &&
        wine_nx_config_file_bool(RUNTIME_DIR "/native-performance-counters.txt", 0);
    sd_perf_counters = sd_perf_counter_policy(sd_com_enabled, guest_tests,
        sd_perf_generic_requested, sd_perf_native_requested);
    log_line("[SD-PERF] v4 generic_requested=%d native_requested=%d active=%d interval_ms=10000; native counters require explicit native-performance-counters.txt opt-in",
             sd_perf_generic_requested, sd_perf_native_requested,
             sd_perf_counters && (sd_com_enabled || !fx_ui_view.debug));'''
    text = replace_once(text, before, after)
    text = replace_once(text,
        '        log_line("[SD-NDX-LOG] async queue=512 batch=32; native progress=5s; bulk observer disabled; missing tail possible after forced restart");',
        '        log_line("[SD-NDX-LOG] async queue=512 batch=32; native progress=5s; bulk observer default OFF, native-performance-counters.txt opt-in; missing tail possible after forced restart");')
    # Frame diagnostics observe the Wine Vulkan present counters. Native
    # DXVK bypasses both that producer and the trigger/report path. An old
    # frame-diagnostics.txt=1 must not silently enable unused server timing.
    # Native opt-in reports use the summary above; Debug/profile.txt remain
    # independent requests for their existing diagnostic paths.
    text = replace_once(text,
        '    __atomic_store_n(&sd_frame_diag_enabled, !guest_tests && sd_sync_load_mode(RUNTIME_DIR "/frame-diagnostics.txt") == 1, __ATOMIC_RELEASE);',
        '''    const int sd_frame_diag_requested = sd_sync_load_mode(RUNTIME_DIR "/frame-diagnostics.txt") == 1;
    __atomic_store_n(&sd_frame_diag_enabled, !sd_com_enabled && !guest_tests && sd_frame_diag_requested, __ATOMIC_RELEASE);''')
    text = replace_once(text,
        '    log_line("[SD-DIAG] v1 enabled=%d capture_ms=30000 trigger=two-slow-windows sampler=off; timing only, 720p unchanged", sd_frame_diag_enabled);',
        '    log_line("[SD-DIAG] v4 requested=%d enabled=%d route=%s; Wine frame diagnostics unavailable on native route, native-performance-counters.txt enables summary", sd_frame_diag_requested, sd_frame_diag_enabled, sd_com_enabled ? "native" : "Wine");')
    return text
