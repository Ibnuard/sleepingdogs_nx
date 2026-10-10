"""Optional first-fault diagnostic overlay; exception behavior is unchanged."""
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT


def apply(source):
    source = Path(source)
    unix = source / 'dlls/ntdll/unix'
    native = source / 'wine-nx-probe/source'
    for name, directory in (('sd_fault_trace.inc', unix), ('sd_fault_io.inc', native),
                            ('sd_fault_wine_log.h', native)):
        (directory / name).write_bytes((ROOT / 'src' / name).read_bytes())
    p = unix / 'signal_arm64.c'
    s = exact(p.read_text(), 'NTSTATUS call_user_exception_dispatcher(EXCEPTION_RECORD *rec, CONTEXT *context)',
              '#include "sd_fault_trace.inc"\n\nNTSTATUS call_user_exception_dispatcher(EXCEPTION_RECORD *rec, CONTEXT *context)')
    s = exact(s, '    unsigned int trace = pes13_fex_begin_guest_dispatch();',
              '    unsigned int trace = pes13_fex_begin_guest_dispatch();\n    sd_guest_fault_trace(rec, context);')
    p.write_text(s)
    p = native / 'f1_crash.c'
    p.write_text(p.read_text() + '\n#include "sd_fault_io.inc"\n')
    p = native / 'runtime.c'
    s = exact(p.read_text(), 'static void fx_wine_debug_line(void *context, const char *line)',
              '#include "sd_fault_wine_log.h"\n\nstatic void fx_wine_debug_line(void *context, const char *line)')
    s = exact(s, '    log_line("[WINE] %s", line);',
              '    if (sd_fault_wine_line(line)) log_line("[WINE] %s", line);')
    s = exact(s, 'memset(options, 0, 5 * sizeof(*options));', 'memset(options, 0, 6 * sizeof(*options));')
    s = exact(s, '        options[3].flags = errors | (1 << __WINE_DBCL_WARN);\n        options[4].flags = errors;',
              '        options[3].flags = errors | (1 << __WINE_DBCL_WARN) | (1 << __WINE_DBCL_TRACE);\n'
              '        strcpy(options[4].name, "wow");\n'
              '        options[4].flags = errors | (1 << __WINE_DBCL_WARN) | (1 << __WINE_DBCL_TRACE);\n'
              '        options[5].flags = errors;')
    marker = 'log_line("[SD-FEX] launch_mode=%s",fx_ui_view.debug?"debug":"gui");'
    s = exact(s, marker, marker + '\n'
              '                        log_line("[SD-FIRSTFAULT] build=v3 first 4 faults; skip debug/thread-name; code bytes; first snapshot also in crash.log");')
    p.write_text(s)
