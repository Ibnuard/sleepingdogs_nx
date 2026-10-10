"""Exercise the shipped quota helper and launch gate with deterministic PM failures."""
from pathlib import Path
import argparse
import shutil
import subprocess
from check_startup import function

PREAMBLE = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
typedef uint64_t u64;
typedef int64_t s64;
typedef uint32_t Result;
typedef uint32_t Handle;
#define R_FAILED(r) ((r)!=0)
#define R_SUCCEEDED(r) ((r)==0)
#define InfoType_FreeThreadCount 24
#define InfoType_ResourceLimit 9
#define INVALID_HANDLE 0u
#define LimitableResource_Threads 1
#define CUR_PROCESS_HANDLE 0xffff8001u
static unsigned limit,active;
static Result init_result, boost_result, self_result, app_result, query_results[3];
static int queries,inits,boosts,exits,selfs,apps,no_extra;
static unsigned svc_hints;
static Result handle_result,set_result,limit_results[2],used_results[2];
static int handle_queries,resource_closes,native_sets,limit_reads,used_reads,direct_noop,bad_used;
static u64 resource_handle;
static u64 application_pid=123;
static char trace[8192];
void wine_nx_runtime_trace(const char *s){
    assert(strlen(trace)+strlen(s)+2<sizeof(trace));strcat(trace,s);strcat(trace,"\n");errno=EIO;
}
static Result svcGetInfo(u64 *out,int type,unsigned process,u64 sub){
    if(type==InfoType_ResourceLimit){
        assert(process==INVALID_HANDLE&&!sub&&svc_hints==7&&application_pid==123);
        ++handle_queries;if(!handle_result)*out=resource_handle;return handle_result;
    }
    assert(type==24&&process==CUR_PROCESS_HANDLE&&!sub);
    Result rc=query_results[queries<3?queries:2];++queries;
    if(!rc)*out=limit-active;
    errno=ENOSYS;return rc;
}
static Result svcGetProcessId(u64 *out,unsigned process){
    assert(process==CUR_PROCESS_HANDLE);++selfs;if(!self_result)*out=123;return self_result;
}
static Result pmshellInitialize(void){++inits;return init_result;}
static void pmshellExit(void){assert(inits==exits+1);++exits;}
static Result pmshellGetApplicationProcessIdForShell(u64 *out){++apps;if(!app_result)*out=application_pid;return app_result;}
static Result pmshellBoostApplicationThreadResourceLimit(void){
    assert(application_pid==123&&selfs==1&&apps==1);++boosts;
    if(!boost_result&&!no_extra)limit=256;
    return boost_result;
}
static int envIsSyscallHinted(unsigned id){
    switch(id){case 0x30:return (svc_hints&1)!=0;case 0x31:return (svc_hints&2)!=0;
        case 0x7e:return (svc_hints&4)!=0;default:assert(0);return 0;}
}
static Result svcGetResourceLimitLimitValue(s64 *out,Handle h,int resource){
    assert(h==0x77&&resource==LimitableResource_Threads&&(svc_hints&1));
    Result rc=limit_results[limit_reads?1:0];++limit_reads;if(!rc)*out=limit;return rc;
}
static Result svcGetResourceLimitCurrentValue(s64 *out,Handle h,int resource){
    assert(h==0x77&&resource==LimitableResource_Threads&&(svc_hints&2));
    Result rc=used_results[used_reads?1:0];++used_reads;if(!rc)*out=bad_used?-1:(s64)active;return rc;
}
static Result svcSetResourceLimitLimitValue(Handle h,int resource,u64 value){
    assert(h==0x77&&resource==LimitableResource_Threads&&svc_hints==7&&application_pid==123);
    assert(value==256&&value>limit&&value>active&&handle_queries==1&&limit_reads==1&&used_reads==1);
    ++native_sets;if(!set_result&&!direct_noop)limit=value;return set_result;
}
static Result svcCloseHandle(Handle h){assert(h==0x77&&handle_queries==1&&!resource_closes);++resource_closes;return 0;}
static void reset(void){
    limit=96;active=4;init_result=boost_result=self_result=app_result=0;
    query_results[0]=query_results[1]=query_results[2]=0;queries=inits=boosts=exits=selfs=apps=no_extra=0;
    svc_hints=7;handle_result=set_result=limit_results[0]=limit_results[1]=used_results[0]=used_results[1]=0;
    handle_queries=resource_closes=native_sets=limit_reads=used_reads=direct_noop=bad_used=0;resource_handle=0x77;
    application_pid=123;trace[0]=0;errno=EDOM;
}
'''

HARNESS = r'''
static Result modeled_create_thread(void){if(active==limit)return (132u<<9)|1u;++active;return 0;}
static void check_budget(void){
    char error[192];
    reset();active=8;
    for(int i=0;i<44;i++){assert(!modeled_create_thread());assert(!modeled_create_thread());}
    assert(modeled_create_thread()==0x10801&&active==96);
    reset();
    assert(wine_nx_f1_prepare_threads(error,sizeof(error))&&errno==EDOM&&!error[0]);
    assert(limit==256&&boosts==1&&inits==1&&exits==1&&queries==2);
    assert(strstr(trace,"ready=1 before=92 before_rc=00000000 after=252 after_rc=00000000"));
    active=8;
    for(int i=0;i<64;i++){assert(!modeled_create_thread());assert(!modeled_create_thread());}
    assert(active==136&&limit-active==120);
    reset();limit=256;strcpy(error,"stale");
    assert(wine_nx_f1_prepare_threads(error,sizeof(error))&&!error[0]);
    assert(!inits&&!boosts&&!exits&&queries==1&&!handle_queries&&!native_sets);
    reset();application_pid=456;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error)));
    assert(strstr(error,"holding R")&&!boosts&&exits==1&&limit==96&&!handle_queries&&!native_sets);
    reset();init_result=0x1234;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error)));
    assert(strstr(error,"PM 00001234")&&!boosts&&!exits&&!selfs&&!apps);
    reset();self_result=0x4567;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&!boosts&&exits==1);
    reset();app_result=0x6789;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&!boosts&&exits==1);
    reset();boost_result=0xdead;
    assert(wine_nx_f1_prepare_threads(error,sizeof(error))&&boosts==1&&exits==1&&!error[0]);
    assert(strstr(trace,"boost_rc=0000dead")&&native_sets==1&&resource_closes==1&&limit==256);
    reset();no_extra=1;
    assert(wine_nx_f1_prepare_threads(error,sizeof(error))&&exits==1&&errno==EDOM&&!error[0]);
    assert(native_sets==1&&handle_queries==1&&resource_closes==1&&limit==256);
    assert(strstr(trace,"limit_before=96 used_before=4 limit_after=256 used_after=4 target_limit=256"));
    assert(strstr(trace,"ready=1 before=92 before_rc=00000000 after=252 after_rc=00000000"));
    active=8;
    for(int i=0;i<64;i++){assert(!modeled_create_thread());assert(!modeled_create_thread());}
    assert(active==136&&limit-active==120);
    for(unsigned hints=0;hints<7;hints++){
        reset();no_extra=1;svc_hints=hints;
        assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&errno==EDOM);
        assert(!handle_queries&&!native_sets&&!resource_closes&&exits==1);
        assert(strstr(error,"loader cannot raise"));
    }
    reset();no_extra=1;handle_result=0x9876;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&!native_sets&&!resource_closes);
    assert(strstr(trace,"handle_rc=00009876"));
    reset();no_extra=1;resource_handle=0;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&!native_sets&&!resource_closes);
    reset();no_extra=1;resource_handle=UINT64_MAX;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&!native_sets&&!resource_closes);
    reset();no_extra=1;limit_results[0]=0xabcd;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&!native_sets&&resource_closes==1);
    reset();no_extra=1;used_results[0]=0x4567;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&!native_sets&&resource_closes==1);
    reset();no_extra=1;bad_used=1;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&!native_sets&&resource_closes==1);
    reset();no_extra=1;set_result=0x1234;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&native_sets==1&&resource_closes==1&&limit==96);
    assert(strstr(trace,"set_rc=00001234")&&strstr(error,"Cannot prepare"));
    reset();no_extra=1;direct_noop=1;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&native_sets==1&&resource_closes==1&&limit==96);
    reset();no_extra=1;limit_results[1]=0x1234;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&native_sets==1&&resource_closes==1);
    reset();no_extra=1;used_results[1]=0x1234;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&native_sets==1&&resource_closes==1);
    reset();no_extra=1;query_results[2]=0x1234;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&native_sets==1&&resource_closes==1);
    reset();no_extra=1;limit=300;active=290;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&!native_sets&&resource_closes==1&&limit==300);
    reset();query_results[0]=query_results[1]=0xf601;
    assert(wine_nx_f1_prepare_threads(error,sizeof(error))&&boosts==1&&exits==1);
    assert(strstr(trace,"before_rc=0000f601")&&strstr(trace,"after_rc=0000f601"));
    reset();query_results[0]=query_results[1]=query_results[2]=0xf601;boost_result=0xabcd;
    assert(!wine_nx_f1_prepare_threads(error,sizeof(error))&&exits==1);
    assert(strstr(trace,"boost_rc=0000abcd"));
    reset();no_extra=direct_noop=1;char tiny[8];memset(tiny,'x',sizeof(tiny));
    assert(!wine_nx_f1_prepare_threads(tiny,sizeof(tiny))&&!tiny[7]);
    reset();no_extra=direct_noop=1;assert(!wine_nx_f1_prepare_threads(NULL,0));
    puts("PASS: modeled 96-thread failure reproduces 0x10801. Device PM no-op at 92 free reproduced; actual helper uses the caller's resource handle and mocked setter to raise 96 to 256, verifies 252 free and supports 64 guest/server pairs. No other resource or process is modified.");
    puts("PASS: existing capacity, PM success/failure, wrong PID, all missing SVC hints, handle/read/set/readback errors, no-op setter, invalid counts, no lowering of existing limits, handle cleanup, errno and bounded messages.");
}
'''

LAUNCH = r'''
typedef int pthread_attr_t;
typedef int pthread_t;
static pthread_t fx_ui_thread;
static int fx_ui_created,fx_ui_command,fx_boot_started,fx_ui_lock;
enum {FX_HOME,FX_SETTINGS,FX_LOADING,FX_FAILED};
static struct {int renderer,selected,screen,fatal,debug;const char *message;} fx_ui_view;
static unsigned wine_nx_f1_crash_init(int debug,int renderer,int profile)
{assert(debug==fx_ui_view.debug&&renderer==fx_ui_view.renderer&&profile==fx_ui_view.selected);return 0;}
static char fx_ui_message[192];
static const char *fx_renderer_ids[]={"dxvk-3.1.1","dxvk-2.7.1-async"};
static char fx_renderer_error_text[]="Missing renderer",fx_renderer_error_detail[]="Missing test DLL";
static int renderer_ok=1,preset_ok=1,joins,registered_exit;
#define RUNTIME_DIR "/test"
static void *fx_ui_main(void *arg){return arg;}
static void fx_exit_check(void){}
static void log_line(const char *fmt,...){char msg[384];va_list ap;va_start(ap,fmt);vsnprintf(msg,sizeof(msg),fmt,ap);va_end(ap);wine_nx_runtime_trace(msg);}
static void fx_native_error(const char *s){(void)s;assert(0);}
static int pthread_attr_init(pthread_attr_t *a){*a=1;return 0;}
static int pthread_attr_setstacksize(pthread_attr_t *a,size_t n){assert(*a==1&&n==256*1024);return 0;}
static int pthread_attr_destroy(pthread_attr_t *a){*a=0;return 0;}
static int pthread_create(pthread_t *t,const pthread_attr_t *a,void *(*entry)(void *),void *arg){
    assert(*a==1&&entry==fx_ui_main&&!arg);*t=1;fx_ui_command=1;return 0;
}
static int pthread_join(pthread_t t,void **ret){assert(t==1&&!ret);++joins;return 0;}
static int pthread_mutex_lock(int *m){assert(m==&fx_ui_lock);return 0;}
static int pthread_mutex_unlock(int *m){assert(m==&fx_ui_lock);return 0;}
static void svcSleepThread(long long ns){
    assert(ns==10000000&&fx_ui_view.screen==FX_FAILED&&fx_ui_view.message==fx_ui_message);
    fx_ui_command=-1; /* user leaves the recoverable launch error */
}
static int fx_apply_renderer(const char *root,int r){assert(!strcmp(root,RUNTIME_DIR)&&r==0);return renderer_ok;}
static int fx_apply_preset(const char *root,int p){assert(!strcmp(root,RUNTIME_DIR)&&p==0);return preset_ok;}
/* Graphics migration is exercised separately with real files. This fixture
 * isolates quota failure/recovery before Wine starts. */
static int f1_prepare_game_graphics(const char *root){assert(!strcmp(root,RUNTIME_DIR));return 1;}
static int test_atexit(void (*fn)(void)){assert(fn==fx_exit_check);++registered_exit;return 0;}
#define atexit test_atexit
FUNCTION
static void reset_launch(int debug){
    reset();memset(&fx_ui_view,0,sizeof(fx_ui_view));fx_ui_view.debug=debug;
    fx_ui_created=fx_ui_command=fx_boot_started=fx_ui_lock=joins=registered_exit=0;
    fx_ui_message[0]=0;renderer_ok=preset_ok=1;
}
static void check_launch(void){
    for(int debug=0;debug<2;debug++){
        reset_launch(debug);assert(fx_launcher_start()==1&&boosts==1&&registered_exit==1);
        assert(!joins&&fx_ui_created);
        reset_launch(debug);no_extra=1;
        assert(fx_launcher_start()==1&&native_sets==1&&registered_exit==1&&limit==256);
        reset_launch(debug);no_extra=direct_noop=1;
        assert(!fx_launcher_start()&&joins==1&&!fx_ui_created&&!registered_exit);
        assert(strstr(fx_ui_message,"Cannot prepare application thread quota")&&!strstr(trace,"[F1-RENDERER]"));
        assert(!strstr(trace,"launch requested"));
        reset_launch(debug);renderer_ok=0;
        assert(!fx_launcher_start()&&!inits&&!boosts&&joins==1);
        assert(strstr(fx_ui_message,"Missing renderer"));
        reset_launch(debug);preset_ok=0;
        assert(!fx_launcher_start()&&!inits&&!boosts&&joins==1);
        assert(strstr(fx_ui_message,"graphics profile"));
    }
    puts("PASS: generated GUI/Debug launch gate requests quota before Wine, preserves renderer errors, returns to launcher on quota failure and only registers guest startup on success.");
}
int main(void){check_budget();check_launch();}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    native = args.source / 'wine-nx-probe/source'
    helper = native / 'f1_thread_budget.c'
    assert helper.read_bytes() == Path(__file__).with_name('f1_thread_budget.c').read_bytes()
    runtime = (native / 'runtime.c').read_text()
    launch = function(runtime, 'static int fx_launcher_start(void)')
    args.output.mkdir(parents=True, exist_ok=True)
    file = args.output / 'thread-budget-check.c'
    file.write_text(PREAMBLE + helper.read_text().replace('#include <switch.h>', '') + HARNESS + LAUNCH.replace('FUNCTION', launch))
    cc = shutil.which('clang') or shutil.which('cc')
    subprocess.run([cc, '-std=c11', '-O1', '-g', '-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all', str(file), '-o', str(file.with_suffix(''))], check=True)
    subprocess.run([str(file.with_suffix(''))], check=True)


if __name__ == '__main__':
    main()
