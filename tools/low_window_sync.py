"""Observe semaphore lifecycle and the first invalid waits; preserve NT results."""
import shutil
from port_common import ROOT
from f1_overlay import exact

INPUTS = ('tools/low_window_sync.py', 'src/low_window/sd_sync_watch.h',
          'src/low_window/sd_sync_watch.inc', 'src/low_window/sd_sync_bridge.inc')


def overlay(source):
    native = source / 'wine-nx-probe/source'
    for name in ('sd_sync_watch.h', 'sd_sync_watch.inc', 'sd_sync_bridge.inc'):
        shutil.copy2(ROOT / 'src/low_window' / name, native / name)
    path = source / 'dlls/ntdll/unix/signal_arm64.c'
    text = path.read_text()
    text = exact(text, '\nNTSTATUS wine_nx_do_syscall( ULONG_PTR *stack_args,',
                 '\n#include "../../../wine-nx-probe/source/sd_sync_bridge.inc"\n'
                 '\nNTSTATUS wine_nx_do_syscall( ULONG_PTR *stack_args,')
    text = exact(text, '    uint64_t watch_serial = 0;',
                 '    uint64_t sync_creation_before = sd_sync_create_serial;\n    uint64_t watch_serial = 0;')
    text = exact(text, '    if (watch_serial) f1_watch_end(watch_tid,watch_serial,result,armGetSystemTick());',
                 '    if (watch_serial) {\n'
                 '        sd_sync_after_syscall((void *)handler,x0,x3,x4,result,sync_creation_before);\n'
                 '        f1_watch_end(watch_tid,watch_serial,result,armGetSystemTick());\n    }')
    path.write_text(text)
    path = source / 'dlls/ntdll/unix/sync.c'
    text = path.read_text()
    text = exact(text, '#include "unix_private.h"',
                 '#include "unix_private.h"\n#include "../../../wine-nx-probe/source/sd_sync_watch.h"')
    # Only normal exits read *handle, which the original function already wrote.
    # Early validation failures are still observed by the dispatcher with h=0.
    for name, following in (('NtCreateSemaphore', 'NtOpenSemaphore'), ('NtOpenSemaphore', 'NtQuerySemaphore')):
        begin = text.index('NTSTATUS WINAPI ' + name + '(')
        end = text.index('NTSTATUS WINAPI ' + following + '(', begin)
        section = text[begin:end]
        section = exact(section, '    return ret;\n}',
                        '    wine_nx_sd_sync_created_handle((uintptr_t)*handle);\n    return ret;\n}')
        text = text[:begin] + section + text[end:]
    path.write_text(text)
    path = native / 'runtime.c'
    text = path.read_text()
    text = exact(text, '#include "sd_loading_watch.h"',
                 '#include "sd_loading_watch.h"\n#include "sd_sync_watch.h"')
    text = exact(text, 'sleepingdogs-fextendo-0.1.0-low-window-v3-load-watch',
                 'sleepingdogs-fextendo-0.1.0-low-window-v5-sync-startup-fix')
    text = exact(text, '        /* Bound detailed observations to ten minutes of a Debug launch. */',
                 '        wine_nx_sd_sync_report(); /* Drain outside all paused-thread captures. */\n'
                 '        /* Bound detailed observations to ten minutes of a Debug launch. */')
    text = exact(text, '[SD-WATCH] v2 debug detail=600s;',
                 '[SD-WATCH] v3 sync lifecycle + first-invalid object; debug detail=600s;')
    path.write_text(text)
