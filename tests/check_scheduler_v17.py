"""Execute v17 production scheduler, pinning and explicit group paths on host fixtures."""
from pathlib import Path
import os
import json
import shutil
import subprocess
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'tools')]
from port_common import ROOT, sha, write_json
from prepare_scheduler_v17 import WORK, NATIVE, HORIZON, RUNTIME, LINUX_WORK
from sleepingdogs_direct_sync import function
from prepare_lsfg_native import replace

PIN_FIXTURE = r'''
typedef uint64_t ULONG_PTR;
typedef int32_t LONG;
static LONG next_core_index;
struct horizon_pipe { unsigned client_cores; } mock_pipe;
struct mock_thread_data { int request_fd; } mock_thread_data;
static struct mock_thread_data *ntdll_get_thread_data(void) { return &mock_thread_data; }
static struct horizon_pipe *horizon_pipe_from_fd(int fd) { (void)fd;return &mock_pipe; }
static ULONG_PTR horizon_get_system_affinity_mask(void) { return allowed; }
static LONG InterlockedIncrement(LONG *p) { return ++*p; }
#define WARN(...) ((void)0)
#define TRACE(...) ((void)0)
'''

GROUP_FIXTURE = r'''
typedef uintptr_t HANDLE;
typedef struct { uint64_t Mask; uint16_t Group, Reserved[3]; } GROUP_AFFINITY;
typedef struct { struct { HANDLE UniqueThread, UniqueProcess; } ClientId; } THREAD_BASIC_INFORMATION;
static unsigned server_status, server_calls, query_status, query_foreign;
static unsigned get_system_affinity_mask(void) { return (unsigned)allowed; }
static unsigned GetCurrentProcessId(void) { return 123; }
#define HandleToULong(h) ((unsigned)(h))
#define ThreadBasicInformation 0
#define STATUS_INVALID_PARAMETER 0xc000000du
#define STATUS_ACCESS_VIOLATION 0xc0000005u
#define SET_THREAD_INFO_AFFINITY 1
static unsigned NtQueryInformationThread(HANDLE h,int type,THREAD_BASIC_INFORMATION *out,unsigned n,void *ret) {
    (void)type;(void)n;(void)ret;if(query_status)return query_status;
    if(h==CUR_THREAD_HANDLE)h=current;
    out->ClientId.UniqueProcess=query_foreign?456:123;
    out->ClientId.UniqueThread=(unsigned)h*4;return 0;
}
static unsigned is_current_thread_handle(HANDLE h) { return h==CUR_THREAD_HANDLE||h==current; }
struct mock_request { unsigned handle;uint64_t affinity;unsigned mask; };
static unsigned wine_server_obj_handle(HANDLE h) { return (unsigned)h; }
static unsigned wine_server_call(struct mock_request *r) { assert(r->mask==1);++server_calls;return server_status; }
#define SERVER_START_REQ(name) { struct mock_request storage,*req=&storage;
#define SERVER_END_REQ }
'''

CASES = r'''
static unsigned cases;
#define CASE() (++cases)
static void base(void) {
    reset(); wine_nx_sd_auto_affinity=1;wine_nx_balance_enabled=1;
    memset(sd_scheduler_counts,0,sizeof(sd_scheduler_counts));
    memset(sd_scheduler_pin_counts,0,sizeof(sd_scheduler_pin_counts));
    server_status=server_calls=query_status=query_foreign=0;
    mock_pipe.client_cores=0x55;next_core_index=0;
}
static void add(unsigned h, unsigned tid, char kind) {
    current=h;wine_nx_thread_register(kind,tid,(void *)(uintptr_t)(h*0x1000));current=1;
}
int main(void) {
    base();wine_nx_thread_balance();assert(masks[1]==7&&cores[1]==0&&follows==1&&last_follow==7);CASE();
    unsigned oldsets=sets,oldfollow=follows;
    tick+=2000000000;wine_nx_thread_balance();assert(sets==oldsets&&follows==oldfollow+1&&last_follow==7);CASE();
    /* Registry path also captures the main thread, which begins with any mask. */
    base();masks[1]=15;cores[1]=-1;sd_scheduler_update(15);
    assert(masks[1]==7&&cores[1]==0&&follows==1);CASE();
    base();cores[1]=2;masks[1]=4;sd_scheduler_update(15);assert(masks[1]==7&&cores[1]==2);CASE();
    base();registry[0].core=1;cores[1]=-1;masks[1]=15;sd_scheduler_update(15);
    assert(masks[1]==7&&cores[1]==1);CASE();
    base();allowed=5;cores[1]=1;sd_scheduler_update(5);assert(masks[1]==5&&cores[1]==0);CASE();
    base();allowed=4;sd_scheduler_update(4);assert(masks[1]==4&&cores[1]==2);CASE();
    base();allowed=8;sd_scheduler_update(8);assert(!sets&&!follows&&masks[1]==1);CASE();
    base();allowed=0;sd_scheduler_update(0);assert(!sets&&!follows);CASE();
    base();fail_info=1;wine_nx_thread_balance();assert(!sets&&!follows&&sd_scheduler_counts[4]==1);CASE();
    base();fail_get=1;sd_scheduler_update(15);assert(!sets&&!follows&&masks[1]==1&&sd_scheduler_counts[2]==1);CASE();
    base();fail_set=1;sd_scheduler_update(15);
    assert(sets==1&&!follows&&masks[1]==1&&sd_scheduler_counts[3]==1);CASE();
    base();wine_nx_balance_enabled=0;wine_nx_thread_balance();assert(!sets&&!follows);CASE();
    base();registry[0].fixed=1;sd_scheduler_update(15);assert(!sets&&!follows&&masks[1]==1);CASE();
    base();fex_dxvk_slots[0].active=1;masks[1]=8;cores[1]=3;
    sd_scheduler_update(15);assert(!sets&&!follows&&masks[1]==8);CASE();
    base();add(2,8,'s');sd_scheduler_update(15);assert(sets==1&&masks[2]==1);CASE();
    base();wine_nx_sd_shader_configure(1);wine_nx_fex_dxvk_name(4,"dxvk-shader-l");oldsets=sets;
    sd_scheduler_update(15);assert(sets==oldsets&&sd_shader_slots[0].mode==SD_SHADER_WORKER);CASE();
    /* Pending restores get their retry before fixed/helper eligibility filtering. */
    base();registry[0].fixed=1;sd_shader_slots[0]=(struct sd_shader_slot){SD_SHADER_RESTORE,1,2};
    sd_scheduler_update(15);assert(masks[1]==2&&!sd_shader_slots[0].mode&&registry[0].fixed&&sets==1);CASE();
    base();sd_shader_slots[0]=(struct sd_shader_slot){SD_SHADER_RESTORE,1,2};fail_set=1;
    sd_scheduler_update(15);assert(masks[1]==1&&sd_shader_slots[0].mode==SD_SHADER_RESTORE&&sets==1);CASE();
    /* A shader scope saves and restores the broad ordinary mask. */
    base();sd_scheduler_update(15);wine_nx_sd_shader_configure(1);
    unsigned token=wine_nx_thread_pipeline_begin();assert(token);
    wine_nx_thread_pipeline_end(token);assert(masks[1]==7&&cores[1]==0&&!sd_shader_slots[0].mode);CASE();
    /* OFF executes the production v16 balancer, including its single-core path. */
    base();wine_nx_sd_auto_affinity=0;masks[1]=7;
    wine_nx_thread_balance();tick+=2000000000;ticks[1]+=1900000000;wine_nx_thread_balance();
    assert(masks[1]&&!(masks[1]&(masks[1]-1)));CASE();
    /* Production automatic thread startup: round-robin preferred, broad allowed. */
    base();horizon_pin_current_thread(0);assert(masks[1]==7&&cores[1]==0&&mock_pipe.client_cores==7&&!registry[0].fixed);CASE();
    horizon_pin_current_thread(0);assert(cores[1]==1&&masks[1]==7);CASE();
    horizon_pin_current_thread(0);assert(cores[1]==2&&masks[1]==7);CASE();
    base();wine_nx_fex_auto_core3=1;horizon_pin_current_thread(0);assert(masks[1]==7);CASE();
    base();wine_nx_sd_auto_affinity=0;horizon_pin_current_thread(0);
    assert(masks[1]==1&&mock_pipe.client_cores==1);CASE();
    base();wine_nx_sd_auto_affinity=0;wine_nx_fex_auto_core3=1;next_core_index=3;
    horizon_pin_current_thread(0);assert(masks[1]==8&&cores[1]==3);CASE();
    base();fail_info=1;horizon_pin_current_thread(0);assert(!sets&&mock_pipe.client_cores==0x55);CASE();
    base();allowed=8;horizon_pin_current_thread(0);assert(!sets&&mock_pipe.client_cores==0x55);CASE();
    base();fail_set=1;horizon_pin_current_thread(0);assert(masks[1]==1&&mock_pipe.client_cores==0x55);CASE();
    for(unsigned mode=0;mode<2;++mode)for(unsigned mask=1;mask<16;++mask) {
        base();wine_nx_sd_auto_affinity=mode;horizon_pin_current_thread(mask);
        assert(masks[1]==mask&&registry[0].fixed&&mock_pipe.client_cores==mask);CASE();
    }
    /* Accepted group affinity uses the real Wine case + real helper/restoration. */
    for(unsigned mode=0;mode<2;++mode)for(unsigned shader=0;shader<2;++shader)
    for(unsigned remote=0;remote<2;++remote)for(unsigned mi=0;mi<3;++mi) {
        const unsigned request_masks[]={2,7,8};unsigned m=request_masks[mi];
        base();add(2,8,'w');wine_nx_sd_auto_affinity=mode;wine_nx_sd_shader_configure(shader);
        GROUP_AFFINITY g={.Mask=m};unsigned h=remote?2:1;
        assert(!set_group(h,&g,sizeof(g))&&server_calls==1);
        if(mode||!remote)assert(masks[h]==m&&registry[remote].fixed);
        else assert(masks[h]==1&&!registry[1].fixed); /* exact old remote group behavior */
        if(mode){sd_scheduler_update(15);assert(masks[h]==m);}CASE();
    }
    for(unsigned shader=0;shader<2;++shader)for(unsigned remote=0;remote<2;++remote) {
        base();add(2,8,'w');wine_nx_sd_shader_configure(shader);fail_set=1;
        GROUP_AFFINITY g={.Mask=2};unsigned h=remote?2:1;
        assert(!set_group(h,&g,sizeof(g))&&registry[remote].fixed&&masks[h]==1&&!follows);
        assert(sd_shader_slots[remote].mode==SD_SHADER_RESTORE);
        sd_scheduler_update(15);assert(masks[h]==2&&!sd_shader_slots[remote].mode);CASE();
    }
    base();add(2,8,'w');GROUP_AFFINITY g={.Mask=2};server_status=5;
    assert(set_group(2,&g,sizeof(g))==5&&!sets&&!registry[1].fixed);CASE();
    base();add(2,8,'w');query_status=3;assert(!set_group(2,&g,sizeof(g))&&!sets&&!registry[1].fixed);CASE();
    base();add(2,8,'w');query_foreign=1;assert(!set_group(2,&g,sizeof(g))&&!sets&&!registry[1].fixed);CASE();
    for(unsigned invalid=0;invalid<5;++invalid) {
        base();GROUP_AFFINITY bad={.Mask=2};unsigned length=sizeof(bad);
        if(invalid==0)bad.Mask=0;if(invalid==1)bad.Mask=16;if(invalid==2)bad.Group=1;
        if(invalid==3)bad.Reserved[0]=1;if(invalid==4)--length;
        assert(set_group(1,&bad,length)==STATUS_INVALID_PARAMETER&&!server_calls&&!sets);CASE();
    }
    base();assert(set_group(1,NULL,sizeof(g))==STATUS_ACCESS_VIOLATION&&!sets);CASE();
    sd_scheduler_report();
    printf("PASS %u production scheduler/startup/group-affinity cases\n",cases);
}
'''

def main():
    test = WORK/'host-tests'
    test.mkdir(exist_ok=True)
    src = (NATIVE/RUNTIME/'thread_profile.c').read_text()
    horizon = (NATIVE/HORIZON/'horizon.c').read_text()
    thread = (NATIVE/HORIZON/'thread.c').read_text()
    fixture = (ROOT/'tests/shader_affinity.c').read_text().split('int main(void) {')[0]
    fixture = replace(fixture, 'static int wine_nx_fex_auto_core3;',
                      'int wine_nx_sd_auto_affinity;\n#include "sd_auto_affinity_v17.h"\nstatic int wine_nx_fex_auto_core3;')
    # Reset policy-specific flags as well as inherited fixture state.
    fixture = replace(fixture, 'sd_shader_enabled=fex_dxvk_enabled=0;',
                      'sd_shader_enabled=fex_dxvk_enabled=0;wine_nx_fex_auto_core3=0;')
    glue = '\n'.join(function(src,n) for n in
        ('wine_nx_thread_register','wine_nx_thread_affinity_fixed'))
    policy = src[src.index('/* The OS may schedule ordinary runnable Wine threads'):src.index('void wine_nx_thread_report( void )')]
    glue += '\n'+policy+'\n'+function(src,'wine_nx_thread_balance')
    (test/'shader_registry_glue.inc').write_text(glue, newline='\n')
    fixture += '\n'+PIN_FIXTURE+'\n'
    fixture += '\n'.join(function(horizon,n) for n in
        ('lowest_set_core','nth_core_mask','count_mask_bits','horizon_pin_current_thread'))
    fixture += '\n'+GROUP_FIXTURE+'\n'+function(thread,'fex_dxvk_explicit_affinity')
    group = function(thread,'NtSetInformationThread').split('case ThreadGroupInformation:',1)[1].split('case ThreadNameInformation:',1)[0]
    fixture += '\nstatic unsigned set_group(HANDLE handle,const void *data,unsigned length) {\n unsigned status;\n'+group+'\n}\n'
    fixture += CASES
    (test/'scheduler.c').write_text(fixture, newline='\n')
    for name in ('thread_profile.h','fex_dxvk_core3.h','sd_shader_affinity.h','sd_auto_affinity_v17.h'):
        shutil.copy2(NATIVE/RUNTIME/name, test/name)
    approved = ROOT.parent/'pes13-nx/local/production-input-fix/approved/source/src/runtime'
    for name in ('fex_balance_stable.h','fex_worker_cores.h'):
        shutil.copy2(approved/name,test/name)
    # Existing host fixture can require supporting policy includes.
    for name in ('fex_dxvk_core3_policy.h',):
        if (NATIVE/RUNTIME/name).exists():shutil.copy2(NATIVE/RUNTIME/name,test/name)
    linux_test = LINUX_WORK+'/host-tests'
    compiler = ['gcc','-std=gnu11','-D__SWITCH__','-g','-O1','-fsanitize=address,undefined',
                '-fno-omit-frame-pointer','-pthread','-I'+linux_test,
                linux_test+'/scheduler.c','-o',linux_test+'/scheduler']
    prefix = ['wsl','-d','Ubuntu','-u','blekjek','--'] if os.name=='nt' else []
    subprocess.run(prefix+compiler,check=True)
    result = subprocess.run(prefix+[linux_test+'/scheduler'],capture_output=True,text=True)
    if result.returncode:
        print(result.stdout + result.stderr, flush=True)
        result.check_returncode()
    print(result.stdout.strip(),flush=True)
    write_json(ROOT/'reports/scheduler-v17-host-check.json',dict(passed=True,status='PASS',
        output=result.stdout.strip(),sanitizers=['ASan','UBSan'],
        source_files=json.loads((WORK/'prepared.json').read_text())['files'],
        tests_check=sha(Path(__file__)),
        production_files={n:sha(NATIVE/n) for n in
          (HORIZON+'horizon.c',HORIZON+'thread.c',RUNTIME+'thread_profile.c',RUNTIME+'sd_shader_affinity.h')},
        fixture_sha256=sha(test/'scheduler.c'),hardware_tested=False,fps_gain_measured=False))

if __name__=='__main__':main()
