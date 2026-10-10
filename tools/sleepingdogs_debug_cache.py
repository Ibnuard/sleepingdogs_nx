"""Synchronize the pinned Wine x86 TEB debug cache after successful context sets."""
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT


def apply(source):
    source = Path(source)
    # Refuse to silently use offsets from a different version of guest ntdll.
    guest = (source / 'dlls/ntdll/signal_i386.c').read_text()
    for marker in ('DWORD              dr0;           /* 1dc debug registers */',
                   'DWORD              dr7;           /* 1f0 */',
                   'context->Dr0 = x86_thread_data()->dr0;',
                   'context->Dr7 = x86_thread_data()->dr7;'):
        assert marker in guest, marker
    unix = source / 'dlls/ntdll/unix'
    (unix / 'sd_wow64_debug_cache.h').write_bytes((ROOT / 'src/sd_wow64_debug_cache.h').read_bytes())
    p = unix / 'signal_arm64.c'
    s = exact(p.read_text(), '#include "horizon_wow64.h"',
              '#include "horizon_wow64.h"\n#include "sd_wow64_debug_cache.h"')
    old = '''    return horizon_transfer_i386_context( cpu,
                                          get_cpu_area( IMAGE_FILE_MACHINE_I386 ),
                                          (I386_CONTEXT *)ctx, TRUE );'''
    new = '''    {
        I386_CONTEXT *saved = get_cpu_area( IMAGE_FILE_MACHINE_I386 );
        NTSTATUS status = horizon_transfer_i386_context(cpu, saved, (I386_CONTEXT *)ctx, TRUE);
        /* Guest RtlRaiseException advertises DEBUG_REGISTERS after copying its
         * TEB cache. Without this mirror it submits stale zeros and disarms FEX.
         * Partial contexts, failed transfers, and remote threads do not touch it.
         * An explicitly requested clear must still clear both copies. */
        if (!status && (((const I386_CONTEXT *)ctx)->ContextFlags &
                        (CONTEXT_I386_DEBUG_REGISTERS & ~CONTEXT_i386)))
        {
            TEB *teb = NtCurrentTeb();
            if (sd_wow64_sync_debug_cache(get_wow_teb(teb), saved))
            {
                static unsigned logged;
                if (__atomic_fetch_add(&logged, 1, __ATOMIC_RELAXED) < 8)
                    horizon_trace("[SD-TEB-DEBUG] sync tid=%lu dr0=%08x dr7=%08x\\n",
                                  (unsigned long)(ULONG_PTR)teb->ClientId.UniqueThread,
                                  saved->Dr0, saved->Dr7);
            }
        }
        return status;
    }'''
    p.write_text(exact(s, old, new))
    p = source / 'wine-nx-probe/source/runtime.c'
    marker = 'log_line("[SD-FEX] launch_mode=%s",fx_ui_view.debug?"debug":"gui");'
    p.write_text(exact(p.read_text(), marker, marker + '\n'
        '                        log_line("[SD-TEB-DEBUG] build=v1 exception debug cache sync");'))
