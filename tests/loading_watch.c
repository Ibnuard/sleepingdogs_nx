/* Host fixtures for the real monitor, handoff and thread capture functions.
 * Horizon services are modeled. Every logging path asserts all targets run. */
#include <assert.h>
#include <pthread.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define F1_STARTUP_WATCH_IMPLEMENTATION
#include "f1_startup_watch.h"
#include "sd_loading_watch.h"
#include "fex_frame_metrics.h"

#define R_FAILED(x) ((x)!=0)
#define R_SUCCEEDED(x) ((x)==0)
#define NX_PROF_MAX_THREADS 3
#define NX_PROF_DEPTH 8
#define NX_PROF_TEB_CPU_AREA 0x1488
#define NX_PROF_CPU_CONTEXT 0
#define NX_PROF_I386_ESP 0xc4
#define NX_PROF_I386_EBP 0xb4
#define PES13_FEX_FRAME_RIP_OFFSET 0x20
#define PES13_FEX_FRAME_BLOCK_OFFSET 0x10
#define ThreadActivity_Paused 1
#define ThreadActivity_Runnable 0
#define FEX_PIPE_STAGES 5
#define FX_FAILED 5
typedef unsigned Result;
typedef struct { struct {uint64_t x;} pc, cpu_gprs[29]; uint64_t lr,sp,fp; } ThreadContext;
struct nx_prof_thread { unsigned handle,tid; char kind; uint64_t teb; };
struct pes13_fex_observed_tail { uint64_t size,rip; };
static struct nx_prof_thread registry[NX_PROF_MAX_THREADS] = {
    {1,4,'w',0x1100},{2,4,'s',0x1100},{3,8,'w',0x2200}
};
static pthread_mutex_t registry_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t profile_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t fx_handoff_lock=PTHREAD_MUTEX_INITIALIZER,fx_ui_lock=PTHREAD_MUTEX_INITIALIZER;
static struct {int screen,fatal;} fx_ui_view;
static int fx_debug_live,fx_first_present,fx_ui_created,fx_ui_stop,fx_ui_thread;
static uint64_t f1_guest_exit_state;
static unsigned sim_seconds,paused[4],pause_calls,resume_calls,read_calls,retry_done,mode;
static unsigned resource_calls,detail_calls,stack_lines,captures,pipe_lines,handoffs;
static unsigned last_detail,expiry_seen,freeze_seen,watch_survived;
static jmp_buf stop_monitor;
static struct fex_frame_hist fex_pipeline_stats[FEX_PIPE_STAGES];
static uint64_t fex_pipeline_timeouts[FEX_PIPE_STAGES],fex_pipeline_errors[FEX_PIPE_STAGES];
static uint64_t fex_pipeline_invalid,fex_frame_ok,fex_frame_errors,fex_frame_last;
unsigned int wine_nx_file_reads,wine_nx_sd_reads,wine_nx_sd_hits,wine_nx_syscalls;
unsigned long long wine_nx_sd_read_ns;
static void running(void) { assert(!paused[1]&&!paused[2]&&!paused[3]); }
static uint64_t armGetSystemTick(void) {return (uint64_t)sim_seconds*1000000000;}
static uint64_t armTicksToNs(uint64_t tick) {return tick;}
static void log_line(const char *fmt,...)
{
    running();
    if (!fx_debug_live) return;
    char line[2048];va_list ap;va_start(ap,fmt);vsnprintf(line,sizeof(line),fmt,ap);va_end(ap);
    if (!strncmp(line,"[SD-LOAD] v1 ",13)) {
        unsigned t,seen;unsigned long long presents,delta,age,errors;
        assert(sscanf(line,"[SD-LOAD] v1 t=%us presents=%llu delta=%llu present_seen=%u age_ms=%llu present_errors=%llu",
                      &t,&presents,&delta,&seen,&age,&errors)==6);
        assert(t<600);++detail_calls;last_detail=t;
        if(t>180&&presents==1800&&!delta&&seen&&age>60000)freeze_seen=1;
    }
    if (strstr(line,"detail window ended")) {assert(!f1_startup_watch_enabled);++expiry_seen;}
    if (!strncmp(line,"[FEX3-PIPE]",11)) ++pipe_lines;
    if (!strncmp(line,"[SD-THREAD] capture=",20)) ++captures;
    if (!strncmp(line,"[SD-STACK]",10)) ++stack_lines;
}
static void wine_nx_runtime_trace(const char *s) {log_line("%s",s);}
static void wine_nx_f1_crash_note(const char *s) {running();(void)s;}
static void fx_timestamp_start(void) {running();++handoffs;}
static int fixture_join(int thread,void *value) {running();(void)thread;assert(!value);return 0;}
static int fx_handoff(void);
static void svcSleepThread(uint64_t ns)
{
    running();
    if(ns==2000000) return;
    assert(ns==1000000000);
    if(++sim_seconds>625)longjmp(stop_monitor,1);
    if(sim_seconds==10){
        fx_ui_created=1;assert(fx_handoff());
        watch_survived=!!f1_startup_watch_enabled;
        fx_first_present=1;
    }
    if(sim_seconds>=10&&sim_seconds<=100){
        fex_frame_ok=1800;fex_frame_last=armGetSystemTick();
        fex_frame_add(&fex_pipeline_stats[1],50);
    }
    if(sim_seconds==20||sim_seconds==100){
        uint64_t args[8]={42};
        f1_watch_begin(4,1,args,armGetSystemTick());
    }
}
static int envIsSyscallHinted(unsigned id) {running();assert(id==0x32||id==0x33);return mode!=6;}
static uint64_t thread_ticks(unsigned handle) {running();return handle*1000+sim_seconds;}
static Result svcSetThreadActivity(unsigned handle,unsigned state)
{
    assert(handle>=1&&handle<=3);
    if(state==ThreadActivity_Paused){
        running();++pause_calls;
        if(mode==1&&handle==1)return 1;
        paused[handle]=1;return 0;
    }
    ++resume_calls;assert(paused[handle]);
    if(mode==3&&handle==2&&!retry_done){retry_done=1;return 1;}
    paused[handle]=0;return 0;
}
static Result svcGetThreadContext3(ThreadContext *ctx,unsigned handle)
{
    assert(paused[handle]);++read_calls;memset(ctx,0,sizeof(*ctx));
    ctx->pc.x=0x1000;ctx->lr=0x1020;
    return mode==2&&handle==3?1:0;
}
static unsigned walk_callers(const ThreadContext *ctx,uint64_t *out)
{(void)ctx;out[0]=0x1020;return 1;}
static void *write_alias(const void *p,uint64_t size) {assert(size==4);return (void *)p;}
static struct {void *(*write_alias)(const void *,uint64_t);} native_host={write_alias};
#define pes13_fex_native_host() (&native_host)
static int fex_stall_read(uint64_t address,void *dest,size_t length)
{(void)address;(void)dest;(void)length;return 0;}
void wine_nx_fex_fast_api_totals(unsigned out[2]) {running();memset(out,0,8);}
void wine_nx_fex_poll_totals(unsigned out[2]) {running();memset(out,0,8);}
void wine_nx_f1_apc_snapshot(unsigned long long out[5]) {running();memset(out,0,40);}
void wine_nx_page_store_snapshot(uint64_t out[8]) {running();memset(out,0,64);}
void wine_nx_f1_resource_snapshot(const char *reason) {(void)reason;running();++resource_calls;}
#define SNAPSHOT(name) void name(void){running();}
SNAPSHOT(wine_nx_f1_scratch_snapshot)
SNAPSHOT(wine_nx_f1_vkmem_snapshot)
SNAPSHOT(wine_nx_f1_gpu_heap_snapshot)
SNAPSHOT(wine_nx_f1_native_heap_snapshot)
SNAPSHOT(wine_nx_f1_native_stacks_snapshot)
SNAPSHOT(wine_nx_f1_audio_snapshot)
SNAPSHOT(pes13_fex_report_heap)
const char *f1_watch_syscall_name(unsigned id) {(void)id;return "fixture_wait";}

/* The test builder appends the unmodified compiled-source functions here. */
