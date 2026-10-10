/* Host execution of the production affinity/header glue with mocked Horizon SVCs. */
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
typedef uint32_t Handle, Result, u32;
typedef int32_t s32;
typedef uint64_t u64;
#define R_FAILED(x) ((x)!=0)
#define R_SUCCEEDED(x) ((x)==0)
#define CUR_THREAD_HANDLE 999
#define CUR_PROCESS_HANDLE 998
#define InfoType_CoreMask 1
#define InfoType_PriorityMask 2
#define NX_PROF_MAX_THREADS 8
#define NX_PROF_LINE 1000
static Handle current=1;
static u64 allowed=15, tick=100, priorities=UINT64_C(1)<<63;
static unsigned fail_set, fail_get, fail_info, sets, follows, last_follow;
static s32 cores[16], prios[16];
static u64 masks[16], ticks[16];
static Handle threadGetCurHandle(void) { return current; }
static u64 armGetSystemTick(void) { return tick; }
static u64 armTicksToNs(u64 t) { return t; }
static Result svcGetInfo(u64 *out,unsigned type,Handle h,u64 sub) {
    (void)h;(void)sub;
    if(fail_info)return 1;
    *out=type==InfoType_CoreMask?allowed:priorities;return 0;
}
static Result svcGetThreadCoreMask(s32 *core,u64 *mask,Handle h) {
    if(fail_get)return 1;
    if(h==CUR_THREAD_HANDLE)h=current;
    *core=cores[h];*mask=masks[h];return 0;
}
static Result svcSetThreadCoreMask(Handle h,s32 core,u64 mask) {
    ++sets;if(fail_set){--fail_set;return 1;}
    if(h==CUR_THREAD_HANDLE)h=current;
    assert(mask && !(mask&~allowed));cores[h]=core;masks[h]=mask;return 0;
}
static Result svcGetThreadPriority(s32 *p,Handle h) { *p=prios[h];return 0; }
static Result svcSetThreadPriority(Handle h,s32 p) { prios[h]=p;return 0; }
static uint64_t thread_ticks(Handle h) { return ticks[h]; }
static void wine_nx_runtime_trace(const char *s) { assert(s); }
static void follow_impl(void *teb,unsigned mask) { assert(teb);++follows;last_follow=mask; }
static void (*horizon_follow_thread_cores)(void *,unsigned)=follow_impl;
struct nx_prof_thread {
    Handle handle;unsigned tid;char kind;s32 core;int fixed;
    uint64_t teb,last_ticks,balance_ticks;
};
static struct nx_prof_thread registry[NX_PROF_MAX_THREADS];
static pthread_mutex_t registry_mutex=PTHREAD_MUTEX_INITIALIZER;
static __thread int affinity_fixed;
static int wine_nx_fex_auto_core3;
int wine_nx_balance_enabled=1,wine_nx_fex_balance_stable=1;
#include "thread_profile.h"
#include "fex_balance_stable.h"
#include "fex_worker_cores.h"
#include "fex_dxvk_core3.h"
static int appendf(char *line,int len,const char *format,...) {
    (void)line;(void)format;return len;
}
#include "shader_registry_glue.inc"

static void reset(void) {
    memset(registry,0,sizeof(registry));memset(sd_shader_slots,0,sizeof(sd_shader_slots));
    memset(fex_dxvk_slots,0,sizeof(fex_dxvk_slots));
    memset(ticks,0,sizeof(ticks));
    allowed=15;fail_set=fail_get=fail_info=sets=follows=0;affinity_fixed=0;current=1;
    sd_shader_enabled=fex_dxvk_enabled=0;
    for(unsigned i=0;i<16;i++){cores[i]=0;masks[i]=1;prios[i]=59;}
    wine_nx_thread_register('w',4,(void*)0x1000);
}
int main(void) {
    reset();assert(!wine_nx_sd_shader_configure(0));
    wine_nx_fex_dxvk_name(4,"dxvk-shader-l");
    assert(!wine_nx_thread_pipeline_begin()&&!sets&&masks[1]==1);
    assert(wine_nx_sd_shader_configure(1));
    wine_nx_fex_dxvk_name(4,"dxvk-shader-l");
    assert(sd_shader_slots[0].mode==SD_SHADER_WORKER&&masks[1]==7&&cores[1]==-1&&prios[1]==59);
    unsigned before=sets;
    wine_nx_fex_dxvk_name(4,"dxvk-shader-h");
    assert(sets==before&&!wine_nx_thread_pipeline_begin());
    wine_nx_fex_dxvk_name(4,"other");
    assert(!sd_shader_slots[0].mode&&masks[1]==1&&prios[1]==59);
    unsigned token=wine_nx_thread_pipeline_begin();
    assert(token==1&&masks[1]==7&&sd_shader_slots[0].mode==SD_SHADER_PIPELINE);
    assert(!wine_nx_thread_pipeline_begin());wine_nx_thread_pipeline_end(0);
    assert(masks[1]==7);current=2;wine_nx_thread_pipeline_end(token);assert(masks[1]==7);
    current=1;wine_nx_thread_pipeline_end(token);assert(masks[1]==1);
    token=wine_nx_thread_pipeline_begin();wine_nx_fex_dxvk_name(4,"dxvk-shader-n");
    wine_nx_thread_pipeline_end(token);assert(masks[1]==7&&sd_shader_slots[0].mode==SD_SHADER_WORKER);
    assert(wine_nx_fex_dxvk_affinity(4,2));assert(registry[0].fixed&&masks[1]==2);
    wine_nx_fex_dxvk_name(4,"dxvk-shader-l");assert(!wine_nx_thread_pipeline_begin()&&masks[1]==2);
    /* An affinity accepted before the worker is named must also win. */
    reset();wine_nx_sd_shader_configure(1);
    assert(wine_nx_fex_dxvk_affinity(4,2)&&registry[0].fixed&&masks[1]==2);
    wine_nx_fex_dxvk_name(4,"dxvk-shader-l");assert(masks[1]==2&&!wine_nx_thread_pipeline_begin());
    reset();wine_nx_sd_shader_configure(1);affinity_fixed=1;wine_nx_thread_register('w',4,(void*)0x1000);
    wine_nx_fex_dxvk_name(4,"dxvk-shader");assert(masks[1]==1&&!wine_nx_thread_pipeline_begin());
    reset();wine_nx_sd_shader_configure(1);wine_nx_fex_dxvk_configure(1,0);
    wine_nx_fex_dxvk_name(4,"dxvk-cs");assert(masks[1]==8&&prios[1]==63);
    assert(!wine_nx_thread_pipeline_begin());
    wine_nx_fex_dxvk_name(4,"dxvk-shader-l");assert(masks[1]==7&&prios[1]==59&&!fex_dxvk_slots[0].active);
    wine_nx_fex_dxvk_name(4,"dxvk-cs");assert(masks[1]==8&&prios[1]==63&&!sd_shader_slots[0].mode);
    reset();wine_nx_sd_shader_configure(1);fail_get=1;assert(!wine_nx_thread_pipeline_begin());
    fail_get=0;fail_set=1;assert(!wine_nx_thread_pipeline_begin()&&!sd_shader_slots[0].mode);
    token=wine_nx_thread_pipeline_begin();fail_set=2;wine_nx_thread_pipeline_end(token);
    assert(sd_shader_slots[0].mode==SD_SHADER_RESTORE&&masks[1]==7);
    assert(!sd_shader_retry_locked(0));assert(sd_shader_retry_locked(0)&&masks[1]==1);
    token=wine_nx_thread_pipeline_begin();fail_set=1;assert(wine_nx_fex_dxvk_affinity(4,4));
    assert(sd_shader_slots[0].mode==SD_SHADER_RESTORE&&registry[0].fixed);
    wine_nx_thread_pipeline_end(token);assert(masks[1]==7);
    assert(sd_shader_retry_locked(0)&&masks[1]==4); /* guest request wins */
    reset();wine_nx_sd_shader_configure(1);token=wine_nx_thread_pipeline_begin();
    fail_set=1;wine_nx_fex_dxvk_name(4,"dxvk-cs");assert(sd_shader_slots[0].mode==SD_SHADER_RESTORE);
    assert(!fex_dxvk_slots[0].active);wine_nx_fex_dxvk_name(4,"other");assert(masks[1]==1);
    /* Production balancer must not pin a migratable worker or pending restore. */
    wine_nx_fex_dxvk_name(4,"dxvk-shader");
    wine_nx_thread_balance();tick+=2000000000; ticks[1]+=1900000000;
    before=sets;wine_nx_thread_balance();assert(sets==before&&masks[1]==7);
    sd_shader_slots[0].mode=SD_SHADER_RESTORE;fail_set=1;tick+=2000000000;ticks[1]+=1900000000;
    wine_nx_thread_balance();assert(sd_shader_slots[0].mode==SD_SHADER_RESTORE&&masks[1]==7);
    /* Registering a reused native handle discards stale scope/helper state. */
    affinity_fixed=0;wine_nx_thread_register('w',8,(void*)0x2000);assert(!sd_shader_slots[0].mode);
    reset();allowed=4;wine_nx_sd_shader_configure(1);assert(wine_nx_thread_pipeline_begin());assert(masks[1]==4);
    reset();allowed=8;assert(!wine_nx_sd_shader_configure(1)&&!wine_nx_thread_pipeline_begin());
    reset();fail_info=1;assert(!wine_nx_sd_shader_configure(1));
    puts("PASS: shader affinity off/on, worker renaming, scoped/nested restoration, guest affinity, core-3 coexistence, failure retries, balancer exclusion and handle reuse");
}
