"""Index the proven F1 wake recipients; retain original wait handlers and control."""
from pathlib import Path
import re
VERSION = '0.1.34-index1'
BUILD = 'f1-fextendo-0.1.34-indexed-wake'
PARENT = 'f1-fextendo-0.1.33-targeted-wake'

def once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after, 1)

def apply(source):
    tools = Path(__file__).resolve().parent
    native = source/'wine-nx-probe/source'
    unix = source/'dlls/ntdll/unix'
    p = unix/'horizon.c'; text = p.read_text()
    old_adapter = Path(re.search(r'#include "([^"]*/fex_sync_horizon.h)"', text).group(1))
    adapter = old_adapter.read_text()
    adapter = once(adapter, '#include "pes13_perf27_wait.h"',
        f'#include "{old_adapter.with_name("pes13_perf27_wait.h")}"\n#include "f1_indexed_wait.h"')
    adapter = once(adapter, 'static struct pes27_router fex_sync_router;',
        'static struct pes27_router fex_sync_router;\n'
        'extern int wine_nx_f1_indexed_wake; /* startup only */\n'
        'static struct f1_wait_router f1_index_router;\n'
        'static void f1_wake_handles_changed_locked(void)\n{\n'
        '    if (wine_nx_f1_indexed_wake) f1_wait_handles_changed(&f1_index_router);\n}\n')
    adapter = once(adapter,
        '    if (wine_nx_fex_targeted_wake)\n        pes27_notify(&fex_sync_router, object, 1, fex_sync_resolve, fex_sync_wake);',
        '    if (wine_nx_fex_targeted_wake) {\n'
        '        if (wine_nx_f1_indexed_wake)\n'
        '            f1_wait_notify(&f1_index_router, object, fex_sync_resolve, fex_sync_wake);\n'
        '        else pes27_notify(&fex_sync_router, object, 1, fex_sync_resolve, fex_sync_wake);\n    }')
    adapter = once(adapter, '    pes27_register(&fex_sync_router, &waiter);',
        '    if (wine_nx_f1_indexed_wake) {\n'
        '        struct f1_waiter indexed = {.interest = interest, .condition = &private_cond};\n'
        '        f1_wait_register(&f1_index_router, &indexed, fex_sync_resolve);\n'
        '        condvarWaitTimeout(&private_cond.cond, &horizon_server_objects_mutex.normal, (u64)timeout * 100);\n'
        '        f1_wait_unregister(&f1_index_router, &indexed);\n'
        '        return;\n    }\n'
        '    pes27_register(&fex_sync_router, &waiter);')
    adapter = once(adapter, '    out[0] = wine_nx_fex_targeted_wake;',
        '    const struct pes27_router *stats = wine_nx_f1_indexed_wake ? &f1_index_router.stats : &fex_sync_router;\n'
        '    out[0] = wine_nx_fex_targeted_wake;')
    for field in ('notices','broad_notices','candidates','notified','filtered','sleeps'):
        adapter = once(adapter, 'fex_sync_router.'+field, 'stats->'+field)
    adapter += '''
void wine_nx_f1_wake_index_snapshot(uint64_t out[5])
{
    pthread_mutex_lock(&horizon_server_objects_mutex);
    out[0] = wine_nx_fex_targeted_wake && wine_nx_f1_indexed_wake;
    out[1] = f1_index_router.visited; out[2] = f1_index_router.resolved;
    out[3] = f1_index_router.rebuilds; out[4] = f1_index_router.active;
    pthread_mutex_unlock(&horizon_server_objects_mutex);
}
'''
    (unix/'f1_sync_horizon.h').write_text(adapter)
    (unix/'f1_indexed_wait.h').write_bytes((tools/'f1_indexed_wait.h').read_bytes())
    text = once(text, f'#include "{old_adapter}"', '#include "f1_sync_horizon.h"')
    text = once(text, '    *bucket = entry;\n}',
        '    *bucket = entry;\n    f1_wake_handles_changed_locked();\n}')
    text = once(text, '    *ptr = entry->hash_next;\n}',
        '    *ptr = entry->hash_next;\n    f1_wake_handles_changed_locked();\n}')
    p.write_text(text)
    p = native/'runtime.c'; text = p.read_text()
    text = once(text, '#define FX_APP_VERSION "0.1.33-wake2"', f'#define FX_APP_VERSION "{VERSION}"')
    text = once(text, f'"{PARENT}"', f'"{BUILD}"')
    text = once(text, 'int wine_nx_fex_targeted_wake = 0;',
        'int wine_nx_fex_targeted_wake = 0;\nint wine_nx_f1_indexed_wake = 0;')
    marker = '    wine_nx_fex_targeted_wake = wine_nx_config_file_bool(RUNTIME_DIR "/f1-targeted-wake.txt", 0);'
    text = once(text, marker, marker+'\n'
        '    wine_nx_f1_indexed_wake = wine_nx_config_file_bool(RUNTIME_DIR "/f1-indexed-wake.txt", 0);\n'
        '    log_line("[F1-WAKE-INDEX] startup enabled=%d; f1-indexed-wake.txt=1 enables, absent/0 restores 0.1.33 scan",\n'
        '             wine_nx_fex_targeted_wake && wine_nx_f1_indexed_wake);')
    marker = '    wine_nx_fex_sync_snapshot(now);'
    text = once(text, marker, marker+'''
    {
        extern void wine_nx_f1_wake_index_snapshot(uint64_t out[5]);
        static uint64_t previous_index[5];
        uint64_t index[5];
        wine_nx_f1_wake_index_snapshot(index);
        log_line("[F1-WAKE-INDEX] enabled=%llu visited=%llu resolved=%llu rebuilds=%llu active=%llu",
            (unsigned long long)index[0], (unsigned long long)(index[1]-previous_index[1]),
            (unsigned long long)(index[2]-previous_index[2]),
            (unsigned long long)(index[3]-previous_index[3]), (unsigned long long)index[4]);
        memcpy(previous_index,index,sizeof(index));
    }''')
    p.write_text(text)
    p = native/'f1_perf_observer.h'
    text = once(p.read_text(), '    fex_sync_report();', '    fex_sync_report();\n    fex_frame_report();')
    p.write_text(text)
    p = native/'f1_crash.c'; text = once(p.read_text(), PARENT, BUILD)
    text = once(text, '/ crash.log / 0.1.33-wake2', f'/ crash.log / {VERSION}'); p.write_text(text)
    return ['dlls/ntdll/unix/'+n for n in ('horizon.c','f1_sync_horizon.h','f1_indexed_wait.h')] + [
        'wine-nx-probe/source/'+n for n in ('runtime.c','f1_crash.c','f1_perf_observer.h')]
