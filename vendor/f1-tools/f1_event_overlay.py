"""Remove the pipe round trip for F1 SET/RESET using the unchanged event core."""
from pathlib import Path
VERSION='0.1.31-event1'
BUILD='f1-fextendo-0.1.31-direct-events'
PARENT='f1-fextendo-0.1.30-cpu-trace'

def once(text,before,after):
    assert text.count(before)==1,before
    return text.replace(before,after,1)

def apply(source):
    native=source/'wine-nx-probe/source'
    unix=source/'dlls/ntdll/unix'
    p=unix/'horizon.c';text=p.read_text()
    start=text.index('static int horizon_server_handle_event_op(')
    end=text.index('\nstatic int horizon_server_handle_query_event(',start)
    old=text[start:end]
    # Reuse the exact original locked transition and lookup in both paths.
    begin=old.index('    pthread_mutex_lock( &horizon_server_objects_mutex );')
    finish=old.index('    pthread_mutex_unlock( &horizon_server_objects_mutex );')
    finish+=len('    pthread_mutex_unlock( &horizon_server_objects_mutex );')
    body=old[begin:finish].replace('request->handle','handle').replace('request->op','op').replace('reply.state','*previous')
    helper=('static unsigned int f1_event_operation(unsigned int handle, int op, int *previous)\n{\n'
            '    struct horizon_server_object *object = NULL;\n    unsigned int status;\n'+body+
            '\n    return status;\n}\n\n#include "f1_event_direct.h"\n\n')
    replacement=old.replace('    struct horizon_server_object *object = NULL;\n','').replace('    unsigned int status;\n','')
    replacement=once(replacement,old[begin:finish],
                     '    reply.header.error = f1_event_operation(request->handle, request->op, &reply.state);')
    replacement=once(replacement,'    reply.header.error = status;\n','')
    text=text[:start]+helper+replacement+text[end:]
    p.write_text(text)
    (unix/'f1_event_direct.h').write_bytes(Path(__file__).with_name('f1_event_direct.h').read_bytes())
    p=unix/'sync.c';text=p.read_text()
    marker='static NTSTATUS inproc_set_event( HANDLE handle, LONG *prev_state )'
    text=once(text,marker,'#ifdef __SWITCH__\nextern int wine_nx_f1_direct_events;\n'
              'extern unsigned int horizon_f1_event_direct(unsigned int, int, int *);\n#endif\n\n'+marker)
    for func,op in [('set',1),('reset',2)]:
        marker=f'    if (do_fsync()) return fsync_{func}_event( handle, prev_state );'
        direct=(f'    if (wine_nx_f1_direct_events)\n    {{\n        int previous = 0;\n'
                f'        ret = horizon_f1_event_direct(wine_server_obj_handle(handle), {op}, &previous);\n'
                '        if (!ret && prev_state) *prev_state = previous;\n        return ret;\n    }\n')
        text=once(text,marker,'#ifdef __SWITCH__\n'+direct+'#endif\n\n'+marker)
    p.write_text(text)
    p=native/'runtime.c';text=p.read_text()
    text=once(text,'#define FX_APP_VERSION "0.1.30-cpu1"',f'#define FX_APP_VERSION "{VERSION}"')
    text=once(text,f'"{PARENT}"',f'"{BUILD}"')
    text=once(text,'int wine_nx_fex_targeted_wake = 0;',
              'int wine_nx_f1_direct_events = 1;\nint wine_nx_fex_targeted_wake = 0;')
    marker='    log_line( "[INIT] core balancing %s (no-balance.txt)", wine_nx_balance_enabled ? "on" : "off" );'
    text=once(text,marker,marker+'\n'
      '    wine_nx_f1_direct_events = !wine_nx_config_file_bool(RUNTIME_DIR "/f1-event-server.txt", 0);\n'
      '    log_line("[F1-EVENT] direct=%d; shared event object/lock/wakeup; SET/RESET only; f1-event-server.txt=1 restores pipe path", wine_nx_f1_direct_events);')
    p.write_text(text)
    p=native/'f1_perf_observer.h';text=p.read_text()
    marker='    unsigned fast[2], poll[2];'
    text=once(text,marker,
      '    extern void wine_nx_f1_event_snapshot(uint64_t out[6]);\n'
      '    uint64_t events[6];\n    wine_nx_f1_event_snapshot(events);\n'
      '    log_line("[F1-EVENT] set=%llu reset=%llu unchanged=%llu errors=%llu samples=%llu sampled_us=%llu; cumulative, one sample per 256 calls per thread",\n'
      '             (unsigned long long)events[0],(unsigned long long)events[1],\n'
      '             (unsigned long long)events[2],(unsigned long long)events[3],\n'
      '             (unsigned long long)events[4],(unsigned long long)events[5]);\n'+marker)
    p.write_text(text)
    p=native/'f1_crash.c'
    text=once(p.read_text(),PARENT,BUILD)
    text=once(text,'/ crash.log / 0.1.30-cpu1',f'/ crash.log / {VERSION}')
    p.write_text(text)
    return ['dlls/ntdll/unix/'+n for n in ('horizon.c','sync.c','f1_event_direct.h')]+[
      'wine-nx-probe/source/'+n for n in ('runtime.c','f1_crash.c','f1_perf_observer.h')]
