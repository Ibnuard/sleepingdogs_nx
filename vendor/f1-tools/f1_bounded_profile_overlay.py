"""Bounded location sampling after the event optimization failed to improve FPS."""
from pathlib import Path
VERSION='0.1.32-prof1'
BUILD='f1-fextendo-0.1.32-circuit-profile'
PARENT='f1-fextendo-0.1.31-direct-events'
def once(text,before,after):
    assert text.count(before)==1,before
    return text.replace(before,after,1)

def apply(source):
    native=source/'wine-nx-probe/source'
    p=native/'thread_profile.c';text=p.read_text()
    text=once(text,'#define NX_PROF_TARGETS      2','#define NX_PROF_TARGETS      4')
    text=once(text,'#define NX_PROF_PERIOD_NS    50000000','#define NX_PROF_PERIOD_NS    100000000')
    text=once(text,'static int profiling;','''static int profiling;
static Thread f1_profile_thread;
static uint64_t f1_profile_started, f1_profile_budget_ns;
static unsigned f1_profile_finished, f1_profile_abort;
static int f1_profile_enabled = 1;
#include "f1_bounded_profile.h"
extern int wine_nx_config_file_bool(const char *, int);
static unsigned f1_profile_guest_callers(uint64_t, uint32_t *);
''')
    text=once(text,'                /* Box64\'s guest-register and stack conventions do not apply. */\n                x86_count = 0;',
        '''                /* In native Wine/driver code use the last exported WOW64
                 * frame chain. In JIT code keep only the validated FEX block
                 * label; Box64's guest register conventions do not apply. */
                x86_count = translated ? 0 : f1_profile_guest_callers(target->teb,x86_callers);''')
    marker='        svcSleepThread( NX_PROF_PERIOD_NS );\n        pthread_mutex_lock( &profile_mutex );'
    text=once(text,marker,'''        svcSleepThread( NX_PROF_PERIOD_NS );
        if (f1_profile_budget_ns &&
            armTicksToNs(armGetSystemTick()-f1_profile_started) >= f1_profile_budget_ns) break;
        pthread_mutex_lock( &profile_mutex );''')
    text=once(text,'            if (R_FAILED(resumed)) ++fex_hot_resume_failures;',
        '            if (R_FAILED(resumed)) { ++fex_hot_resume_failures; f1_profile_abort=1; }')
    text=once(text,'            if (paused>fex_hot_peak_ticks) fex_hot_peak_ticks=paused;',
        '''            if (paused>fex_hot_peak_ticks) fex_hot_peak_ticks=paused;
            if (armTicksToNs(paused)>UINT64_C(5000000)) f1_profile_abort=2;''')
    text=once(text,'            else target->missed++;\n        }\n        pthread_mutex_unlock( &profile_mutex );',
        '            else target->missed++;\n            if (f1_profile_abort) break;\n        }\n        pthread_mutex_unlock( &profile_mutex );')
    marker='        pthread_mutex_unlock( &profile_mutex );\n    }\n}\n\nvoid wine_nx_profile_start'
    text=once(text,marker,'''        pthread_mutex_unlock( &profile_mutex );
        if (f1_profile_abort) break;
    }
    __atomic_store_n(&f1_profile_finished,1,__ATOMIC_RELEASE);
}

void wine_nx_profile_start''')
    text=once(text,'    static Thread thread;\n    MemoryInfo info;',
        '    Thread *thread = &f1_profile_thread;\n    MemoryInfo info;')
    start=text.index('void wine_nx_profile_start( void )')
    end=text.index('\nstatic int appendf(',start)
    section=text[start:end].replace('threadCreate( &thread,','threadCreate( thread,').replace(
        'threadStart( &thread )','threadStart( thread )').replace('threadClose( &thread )','threadClose( thread )')
    # 48 is higher priority than the game but remains below system services.
    section=section.replace('0x4000, 0x24,','0x4000, 48,')
    section=section.replace('the %u busiest threads','%u selected threads')
    section=section.replace('    rc = threadCreate(',
        '    f1_profile_started=armGetSystemTick();\n    rc = threadCreate(',1)
    section+='''
void wine_nx_f1_profile_window(uint64_t elapsed_us, uint64_t frames)
{
    static struct f1_profile_gate gate;
    static int configured;
    if (!configured) {
        f1_profile_enabled=!wine_nx_config_file_bool("sdmc:/switch/f1-fex/f1-no-sampler.txt",0);
        configured=1;
    }
    if (!f1_profile_enabled || !f1_profile_gate_window(&gate,elapsed_us,frames)) return;
    f1_profile_budget_ns=UINT64_C(60000000000);
    wine_nx_runtime_trace("[F1-PROFILE] trigger=two-slow-windows duration=60s period=100ms targets=main,dxvk-cs,two-busiest-workers; sampled residency includes waits");
    wine_nx_profile_start();
    if (!profiling) wine_nx_runtime_trace("[F1-PROFILE] start failed; no samples collected");
}

static void f1_profile_finish(void)
{
    if (!profiling || !__atomic_load_n(&f1_profile_finished,__ATOMIC_ACQUIRE)) return;
    threadWaitForExit(&f1_profile_thread);
    threadClose(&f1_profile_thread);
    profiling=0;
    char line[192];
    snprintf(line,sizeof(line),"[F1-PROFILE] complete abort=%u samples_stop_ns=%llu; sampler thread closed; use later F1-FRAME windows for FPS",f1_profile_abort,
        (unsigned long long)armTicksToNs(armGetSystemTick()-f1_profile_started));
    wine_nx_runtime_trace(line);
}
'''
    text=text[:start]+section+text[end:]
    # The report selects from rows only while both locks keep handles live.
    marker='    pthread_mutex_lock( &profile_mutex );\n    snprintf(line,sizeof(line),"[FEX3-HOT]'
    text=once(text,marker,'''    pthread_mutex_lock( &registry_mutex );
    pthread_mutex_lock( &profile_mutex );
    snprintf(line,sizeof(line),"[FEX3-HOT]''')
    start=text.index('    /* The next interval samples the threads busiest in this one. */')
    end=text.index('\n}\n',start)
    text=text[:start]+'''    /* Keep main and DXVK even while blocked, then two CPU-heavy workers.
     * Revalidate registry handles so a thread that exited after the CPU
     * snapshot cannot be selected after unregister cleared its old slot. */
    memset(targets,0,sizeof(targets));
    unsigned selected=0;
    if (!__atomic_load_n(&f1_profile_finished,__ATOMIC_ACQUIRE))
    for (unsigned pass=0;pass<3;pass++)
    for (i=0;i<count && selected<NX_PROF_TARGETS;i++) {
        if (rows[i].kind!='w') continue;
        unsigned slot;
        for(slot=0;slot<NX_PROF_MAX_THREADS;slot++)
            if(registry[slot].handle==rows[i].handle && registry[slot].tid==rows[i].tid &&
               registry[slot].kind=='w') break;
        if(slot==NX_PROF_MAX_THREADS) continue;
        if(pass==0 && rows[i].tid!=4) continue;
        if(pass==1 && strcmp(fex_dxvk_slots[slot].name,"dxvk-cs")) continue;
        if(pass==2 && rows[i].permille<NX_PROF_MIN_PERMILLE) continue;
        for(j=0;j<selected && targets[j].handle!=rows[i].handle;j++);
        if(j<selected) continue;
        struct nx_prof_target *target=&targets[selected++];
        target->handle=rows[i].handle; target->tid=rows[i].tid;
        target->kind=rows[i].kind; target->teb=rows[i].teb;
        snprintf(line,sizeof(line),"[F1-PROFILE-TARGET] slot=%u tid=%u name=%s cpu_permille=%u role=%s",
            selected-1,target->tid,fex_dxvk_slots[slot].name,rows[i].permille,
            pass==0?"main":pass==1?"dxvk-cs":"busy-worker");
        wine_nx_runtime_trace(line);
    }
    pthread_mutex_unlock( &profile_mutex );
    pthread_mutex_unlock( &registry_mutex );'''+text[end:]
    text=once(text,'    if (profiling) profile_report( rows, count );',
        '    if (profiling) { profile_report(rows,count); f1_profile_finish(); }')
    text+='''
static unsigned f1_profile_guest_callers(uint64_t teb, uint32_t *callers)
{
    struct f1_thread_sample saved = {0};
    f1_snapshot_guest(teb,&saved);
    for (unsigned i=0;i<saved.x86_count;i++) callers[i]=saved.x86[i];
    return saved.x86_count;
}
'''
    p.write_text(text)
    (native/'f1_bounded_profile.h').write_bytes(Path(__file__).with_name('f1_bounded_profile.h').read_bytes())
    p=native/'f1_frame_summary.h';text=p.read_text()
    marker='    last = now; frames = next_frames; errors = next_errors;'
    text=once(text,marker,'''    extern void wine_nx_f1_profile_window(uint64_t, uint64_t);
    if (last && elapsed_us) wine_nx_f1_profile_window(elapsed_us,count);
'''+marker)
    p.write_text(text)
    p=native/'f1_perf_observer.h';text=p.read_text()
    text=once(text,'sampler=off','sampler=bounded-diagnostic')
    text=text.replace('These reports read existing counters; the context sampler stays disabled.',
        'The separate bounded context sampler reports its trigger and completion.')
    p.write_text(text)
    p=native/'runtime.c';text=p.read_text()
    text=once(text,'#define FX_APP_VERSION "0.1.31-event1"',f'#define FX_APP_VERSION "{VERSION}"')
    text=once(text,f'"{PARENT}"',f'"{BUILD}"')
    text=once(text,'[FEX3-HOT] enabled=%d sample_period_ms=50 targets=2; sampled residency includes waits; diagnostic only',
        '[FEX3-HOT] startup_sampler=%d; circuit sampler auto-arms after two 3-25 FPS windows, 60s only; f1-no-sampler.txt=1 disables')
    p.write_text(text)
    p=native/'f1_crash.c';text=once(p.read_text(),PARENT,BUILD)
    text=once(text,'/ crash.log / 0.1.31-event1',f'/ crash.log / {VERSION}');p.write_text(text)
    return ['wine-nx-probe/source/'+n for n in ('runtime.c','f1_crash.c','thread_profile.c',
        'f1_bounded_profile.h','f1_frame_summary.h','f1_perf_observer.h')]
