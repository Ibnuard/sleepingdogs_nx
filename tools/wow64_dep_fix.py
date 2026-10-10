"""Wire Wine's accepted execute policy to FEX's existing optional notification."""
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT


def apply(source):
    folder = Path(source) / 'dlls/wow64'
    (folder / 'sd_wow64_dep.inc').write_bytes((ROOT / 'src/sd_wow64_dep.inc').read_bytes())
    p = folder / 'wow64_private.h'
    s = exact(p.read_text(encoding='utf-8'),
        'extern void     (WINAPI *pBTCpuNotifyMemoryDirty)( void *, SIZE_T );',
        'extern void     (WINAPI *pBTCpuNotifyMemoryDirty)( void *, SIZE_T );\n'
        'extern void     (WINAPI *pBTCpuNotifyProcessExecuteFlagsChange)( ULONG );\n'
        'extern void sd_wow64_sync_execute_flags(void);')
    p.write_text(s, encoding='utf-8', newline='\n')
    p = folder / 'syscall.c'
    s = exact(p.read_text(encoding='utf-8'),
        'void     (WINAPI *pBTCpuNotifyMemoryDirty)( void *, SIZE_T ) = NULL;',
        'void     (WINAPI *pBTCpuNotifyMemoryDirty)( void *, SIZE_T ) = NULL;\n'
        'void     (WINAPI *pBTCpuNotifyProcessExecuteFlagsChange)( ULONG ) = NULL;')
    s = exact(s, '    GET_PTR( BTCpuNotifyMemoryDirty );',
        '    GET_PTR( BTCpuNotifyMemoryDirty );\n    GET_PTR( BTCpuNotifyProcessExecuteFlagsChange );')
    s = exact(s, '    pBTCpuProcessInit();',
        '    pBTCpuProcessInit();\n    sd_wow64_sync_execute_flags();')
    p.write_text(s, encoding='utf-8', newline='\n')
    p = folder / 'process.c'
    s = exact(p.read_text(encoding='utf-8'), 'WINE_DEFAULT_DEBUG_CHANNEL(wow);',
        'WINE_DEFAULT_DEBUG_CHANNEL(wow);\n\n#include "sd_wow64_dep.inc"')
    s = exact(s, '    case ProcessExecuteFlags:   /* ULONG */\n', '')
    anchor = '    case ProcessAccessToken: /* PROCESS_ACCESS_TOKEN */'
    s = exact(s, anchor, '    case ProcessExecuteFlags:   /* ULONG */\n'
        '        return sd_wow64_set_execute_flags(handle, ptr, len);\n\n' + anchor)
    p.write_text(s, encoding='utf-8', newline='\n')
