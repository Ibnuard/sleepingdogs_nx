"""Support debug-only Get/SetThreadContext on new suspended WoW64 threads."""
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT


def apply(source):
    source = Path(source); unix = source / 'dlls/ntdll/unix'
    for name in ('sd_thread_debug.h', 'sd_thread_debug.inc'):
        (unix / name).write_bytes((ROOT / 'src' / name).read_bytes())
    p = unix / 'horizon.c'; s = p.read_text()
    s = exact(s, '#include "horizon_threads.h"',
              '#include "horizon_threads.h"\n#include "sd_thread_debug.h"')
    s = exact(s, '    struct horizon_thread_state thread;',
              '    struct horizon_thread_state thread;\n    struct sd_thread_debug sd_debug;')
    s = exact(s, '/* Identity of the client served by the calling server thread (mutex owner). */',
              '#include "sd_thread_debug.inc"\n\n'
              '/* Identity of the client served by the calling server thread (mutex owner). */')
    p.write_text(s)
    p = unix / 'signal_arm64.c'; s = p.read_text()
    s = exact(s, '#include "sd_wow64_debug_cache.h"',
              '#include "sd_wow64_debug_cache.h"\n#include "sd_thread_debug.h"')
    s = exact(s, '''    /* Remote threads require suspension and a synchronized emulator snapshot. */
    if (handle != GetCurrentThread()) return STATUS_NOT_IMPLEMENTED;''',
              '''    if (handle != GetCurrentThread())
        return sd_wow64_remote_debug_context(handle, (I386_CONTEXT *)ctx, TRUE);''')
    s = exact(s, '    if (handle != GetCurrentThread()) return STATUS_NOT_IMPLEMENTED;',
              '''    if (handle != GetCurrentThread())
        return sd_wow64_remote_debug_context(handle, ctx, FALSE);''')
    p.write_text(s)
    p = source / 'wine-nx-probe/source/runtime.c'; s = p.read_text()
    s = exact(s, '#include "horizon_private.h"',
              '#include "horizon_private.h"\n#include "sd_thread_debug.h"')
    marker = '    memcpy( ctx->ExtendedRegisters, &fx, sizeof(fx) );'
    s = exact(s, marker, marker + '''
    if (sd_wow64_apply_start_debug(teb, ctx))
    {
        static unsigned logged;
        if (__atomic_fetch_add(&logged, 1, __ATOMIC_RELAXED) < 16)
            log_line("[SD-THREAD-DEBUG] apply tid=%lu dr0=%08lx dr1=%08lx dr7=%08lx",
                     (unsigned long)(ULONG_PTR)teb->ClientId.UniqueThread,
                     (unsigned long)ctx->Dr0, (unsigned long)ctx->Dr1, (unsigned long)ctx->Dr7);
    }''')
    marker = 'log_line("[SD-TEB-DEBUG] build=v1 exception debug cache sync");'
    s = exact(s, marker, marker + '\n'
              '                        log_line("[SD-THREAD-DEBUG] build=v1 suspended thread debug context");')
    p.write_text(s)
