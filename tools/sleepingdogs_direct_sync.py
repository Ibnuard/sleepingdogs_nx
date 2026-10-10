"""Adapt direct sync to the verified FEXTendo v9 handlers; keep 720p and FEX intact."""
from pathlib import Path
import hashlib
import re
from port_common import ROOT, APPROVED
from f1_overlay import exact

BUILD = 'sleepingdogs-low-window-v10-direct-sync'
MARKER = 'sleepingdogs-fextendo-0.1.0-low-window-v10-direct-sync'
HORIZON = 'dlls/ntdll/unix/'
NATIVE = 'wine-nx-probe/source/'
COPIES = {HORIZON + n: 'src/low_window/' + n for n in
          ('sd_sync_state.h', 'sd_sync_queue.h', 'sd_sync_dispatch.h', 'sd_sync_client.h', 'sd_sync_legacy_wait.h')}
COPIES.update({NATIVE + n: 'src/low_window/' + n for n in ('sd_sync_config.h', 'sd_sync_report.h')})
MODIFIED = {HORIZON + n for n in ('horizon.c', 'horizon_private.h', 'server.c')} | {
    NATIVE + n for n in ('runtime.c', 'thread_profile.c', 'sd_perf_summary.h')}
FILES = MODIFIED | set(COPIES) | {HORIZON + 'sd_sync_router.h'}


def function_span(source, name):
    pattern = r'^(?:static )?[^\n;{}]+\b' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{'
    match = re.search(pattern, source, re.M)
    assert match, name
    # Production functions end on an unindented brace; nested blocks do not.
    end = source.index('\n}', match.end()) + 2
    return match.start(), end


def function(source, name):
    a, b = function_span(source, name)
    return source[a:b]


def change_function(source, name, transform):
    a, b = function_span(source, name)
    return source[:a] + transform(source[a:b]) + source[b:]


def apply(source: Path):
    for target, origin in COPIES.items():
        (source / target).parent.mkdir(parents=True, exist_ok=True)
        (source / target).write_bytes((ROOT / origin).read_bytes())
    router_path = APPROVED / 'source/src/runtime/fex_sync_horizon.h'
    assert hashlib.sha256(router_path.read_bytes()).hexdigest() == '095eac48321fe21902889b0123a9d3bd57c40b398e5190712a84a32c33acea19'
    assert hashlib.sha256((ROOT/'src/low_window/sd_sync_legacy_wait.h').read_bytes()).hexdigest() == '5cab9b5129fd48b80088d8d1f16ae041e40af69dd371ebf58c3fb6b048920b1c'
    router = router_path.read_text()
    router = exact(router, '#include "pes13_perf27_wait.h"', '#include "sd_sync_legacy_wait.h"')
    router = exact(router, 'static void fex_sync_signal_object_locked(const void *object)\n{',
                   'static void fex_sync_signal_object_locked(const void *object)\n{\n    sd_sync_notify_locked(object);')
    (source / HORIZON / 'sd_sync_router.h').write_text(router, newline='\n')
    path = source / HORIZON / 'horizon.c'
    s = path.read_text()
    s = exact(s, '    unsigned int completion_wait_handle;\n};',
              '    unsigned int completion_wait_handle;\n    void *direct_reply, *direct_data;\n    size_t direct_size;\n};')
    s = exact(s, '    struct horizon_memfile *mapping_memfile; /* mapping: a section with no file, kept by file_fd */\n};',
              '    struct horizon_memfile *mapping_memfile; /* mapping: a section with no file, kept by file_fd */\n'
              '    struct sd_sync_link *sd_waiters; /* native-only, append to preserve existing field offsets */\n};')
    old = '#include "/mnt/d/Dev/Switch/SwitchHub/pes13-nx/local/production-input-fix/approved/source/src/runtime/fex_sync_horizon.h"'
    s = exact(s, old, '#include "sd_sync_state.h"\n#include "sd_sync_router.h"')
    reply = '''static int horizon_server_sync_reply(struct horizon_server_connection *connection,
                                      const void *reply, size_t reply_size,
                                      const void *data, size_t data_size)
{
    if (!connection->direct_reply)
        return horizon_server_write_reply(connection->reply_fd, reply, reply_size, data, data_size);
    if (reply_size > HORIZON_SERVER_FIXED_MESSAGE_SIZE || data_size > connection->direct_size ||
        (data_size && (!data || !connection->direct_data))) return -1;
    memset(connection->direct_reply, 0, HORIZON_SERVER_FIXED_MESSAGE_SIZE);
    memcpy(connection->direct_reply, reply, reply_size);
    if (data_size) memcpy(connection->direct_data, data, data_size);
    return 0;
}

'''
    a, _ = function_span(s, 'horizon_server_write_status')
    s = s[:a] + reply + s[a:]
    # Closing a referenced object must wake queued waiters before its last
    # handle disappears; the queue itself keeps the allocation alive.
    s = change_function(s, 'horizon_server_close_object_handle', lambda f: exact(f,
        '        horizon_server_unlink_handle_locked( entry );',
        '        horizon_server_unlink_handle_locked( entry );\n        sd_sync_notify_locked(object);'))
    # A retried signal-and-wait carries only the wait handle. Preserve v9's
    # legacy path; allow the shortened retry only for an active direct call.
    s = change_function(s, 'horizon_server_select_signal_and_wait', lambda f: exact(exact(f,
        '    if (size < sizeof(*op)) return HORIZON_STATUS_INVALID_PARAMETER;',
        '    if (size < sizeof(*op) && (!horizon_server_current || !horizon_server_current->direct_reply ||\n'
        '        size < offsetof(struct horizon_select_signal_and_wait_op, signal)))\n'
        '        return HORIZON_STATUS_INVALID_PARAMETER;'),
        'status = initial ? horizon_server_signal_object_locked( op->signal ) : HORIZON_STATUS_SUCCESS;',
        'status = initial && size >= sizeof(*op) ? horizon_server_signal_object_locked( op->signal ) : HORIZON_STATUS_SUCCESS;'))
    _, b = function_span(s, 'horizon_server_select_status')
    s = s[:b] + '\n\n#include "sd_sync_queue.h"' + s[b:]
    def handler(f):
        f = exact(f, 'pthread_mutex_lock( &horizon_server_objects_mutex );', 'horizon_server_sync_lock( connection );')
        return exact(f, 'horizon_server_write_reply( connection->reply_fd,', 'horizon_server_sync_reply( connection,')
    for name in ('event_op', 'query_event', 'release_mutex', 'query_mutex', 'release_semaphore', 'query_semaphore'):
        s = change_function(s, 'horizon_server_handle_' + name, handler)
    def select(f):
        f = handler(f)
        f = exact(f, '    int polls;\n',
            '    int polls, queued = -1;\n'
            '    struct sd_sync_waiter waiter = { .connection = connection, .request = request,\n'
            '        .data = data, .data_size = data_size, .condition = PTHREAD_COND_INITIALIZER };\n')
        f = exact(f, '        horizon_server_update_timers_locked();',
            '        if (waiter.completed) { reply.header.error = waiter.status; break; }\n'
            '        horizon_server_update_timers_locked();')
        f = exact(f, '        fex_sync_select_sleep_locked( timeout, &interest );',
            '        if (connection->direct_reply && horizon_fast_sync_enabled == 2 && queued < 0)\n'
            '            queued = sd_sync_queue_locked(&waiter);\n'
            '        if (queued > 0) sd_sync_sleep_locked(&waiter, timeout);\n'
            '        else {\n'
            '            if (connection->direct_reply && horizon_fast_sync_enabled == 2) ++sd_sync_counts[5];\n'
            '            fex_sync_select_sleep_locked(timeout, &interest);\n'
            '        }')
        return exact(f, '    pthread_mutex_unlock( &horizon_server_objects_mutex );',
            '    sd_sync_unqueue_locked(&waiter);\n    pthread_mutex_unlock( &horizon_server_objects_mutex );')
    s = change_function(s, 'horizon_server_handle_select', select)
    _, b = function_span(s, 'horizon_server_handle_select')
    s = s[:b] + '\n\n#include "sd_sync_dispatch.h"' + s[b:]
    path.write_text(s, newline='\n')
    path = source / HORIZON / 'horizon_private.h'
    s = exact(path.read_text(), 'extern int horizon_server_connect(void);',
        'extern int horizon_server_connect(void);\n'
        'extern int horizon_fast_sync_enabled, horizon_server_profile_enabled;\n'
        'extern int horizon_server_sync_call(unsigned tid, const void *request, const void *data,\n'
        '                                    unsigned size, void *reply, void *reply_data);')
    path.write_text(s, newline='\n')
    path = source / HORIZON / 'server.c'
    s = exact(path.read_text(), 'unsigned int wine_nx_server_request_count = REQ_NB_REQUESTS;',
        'int horizon_server_profile_enabled;\n'
        'static uint64_t sd_sync_calls[3];\n'
        'void wine_nx_sd_sync_calls(uint64_t out[3])\n{\n'
        '    for (unsigned i = 0; i < 3; ++i) out[i] = __atomic_load_n(&sd_sync_calls[i], __ATOMIC_RELAXED);\n}\n'
        '#include "sd_sync_client.h"\n'
        'unsigned int wine_nx_server_request_count = REQ_NB_REQUESTS;')
    s = exact(s, '    u64 start = armGetSystemTick();',
        '    int direct = 0;\n    u64 start = horizon_server_profile_enabled ? armGetSystemTick() : 0;')
    s = change_function(s, 'server_call_unlocked', lambda f: exact(exact(exact(exact(f,
        '    if (!(ret = send_request( req )))',
        '#ifdef __SWITCH__\n    if ((direct = horizon_sync_call(req))) ret = req->u.reply.reply_header.error;\n'
        '    else\n#endif\n    if (!(ret = send_request( req )))'),
        '    if (code < REQ_NB_REQUESTS)', '    if (horizon_server_profile_enabled && code < REQ_NB_REQUESTS)'),
        '        wine_nx_server_names[code] = req->name;',
        '        __atomic_store_n(&wine_nx_server_names[code], req->name, __ATOMIC_RELAXED);\n'
        '        __atomic_add_fetch(&sd_sync_calls[direct ? 0 : 1], 1, __ATOMIC_RELAXED);\n'
        '        if (direct && code == REQ_select) __atomic_add_fetch(&sd_sync_calls[2], 1, __ATOMIC_RELAXED);'),
        '    TRACE_(client)("%s start\\n", req->name); \\', '    TRACE_(client)("%s start\\n", req->name);'))
    path.write_text(s, newline='\n')
    path = source / NATIVE / 'thread_profile.c'
    s = exact(path.read_text(),
        'const char *name = &wine_nx_server_names && wine_nx_server_names[top[i]] ? wine_nx_server_names[top[i]] : "?";',
        'const char *name = &wine_nx_server_names ? __atomic_load_n(&wine_nx_server_names[top[i]], __ATOMIC_RELAXED) : NULL;\n'
        '        if (!name) name = "?";')
    path.write_text(s, newline='\n')
    path = source / NATIVE / 'runtime.c'
    s = exact(path.read_text(), 'sleepingdogs-fextendo-0.1.0-low-window-v9-shader-optimizations', MARKER)
    s = exact(s, '#define FX_APP_VERSION "0.1.0-v9"', '#define FX_APP_VERSION "0.1.0-v10"')
    s = exact(s, '#include "sd_perf_summary.h"',
        '#include "sd_sync_config.h"\n#include "sd_sync_report.h"\n#include "sd_perf_summary.h"')
    s = exact(s, '    runtime_profile = wine_nx_config_file_bool(RUNTIME_DIR "/profile.txt", 0);',
        '    runtime_profile = wine_nx_config_file_bool(RUNTIME_DIR "/profile.txt", 0);\n'
        '    extern int horizon_fast_sync_enabled, horizon_server_profile_enabled;\n'
        '    horizon_fast_sync_enabled = guest_tests ? 0 : sd_sync_load_mode(RUNTIME_DIR "/sync-mode.txt");\n'
        '    horizon_server_profile_enabled = sd_perf_counters || runtime_profile || fx_ui_view.debug;\n'
        '    log_line("[SD-SYNC-MODE] v1 mode=%d profile=%d; 0=server 1=direct 2=direct-queued; original startup/APC handlers",\n'
        '             horizon_fast_sync_enabled, horizon_server_profile_enabled);')
    path.write_text(s, newline='\n')
    path = source / NATIVE / 'sd_perf_summary.h'
    s = exact(path.read_text(), '    sd_shader_cache_report();',
              '    sd_shader_cache_report();\n    sd_direct_sync_report();')
    path.write_text(s, newline='\n')
