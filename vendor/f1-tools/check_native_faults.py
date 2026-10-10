"""Execute the generated native exception and window teardown paths with mocks.

The fault mock rejects VM/PE dispatch without a Wine TEB. This tests the routing
bug found during the 0.1.11 log investigation, not the cause of the device crash.
"""
from pathlib import Path
import argparse
import shutil
import subprocess
from check_startup import function
from check_crash import SWITCH

FAULTS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <setjmp.h>
#include "switch.h"
typedef uint64_t DWORD64; typedef uint32_t NTSTATUS; typedef uintptr_t ULONG_PTR;
typedef struct { uint32_t ExceptionCode; void *ExceptionAddress; unsigned NumberParameters; uintptr_t ExceptionInformation[3]; } EXCEPTION_RECORD;
typedef struct {uint64_t Pc,Sp;} CONTEXT;
#define STATUS_ACCESS_VIOLATION 0xc0000005u
#define STATUS_DATATYPE_MISALIGNMENT 0x80000002u
#define STATUS_BREAKPOINT 0x80000003u
#define STATUS_ILLEGAL_INSTRUCTION 0xc000001du
#define EXCEPTION_EXECUTE_FAULT 8
#define EXCEPTION_WRITE_FAULT 1
#define EXCEPTION_READ_FAULT 0
static jmp_buf stop;
static int has_teb,vm_calls,pe_calls,fatal_calls,restore_calls,vm_result,pe_handles;
static NTSTATUS fatal_status;
static ThreadExceptionDump *expected;
static void *NtCurrentTeb(void){return has_teb?(void*)1:NULL;}
static void pes13_fex_test_fault(void){}
static void pes13_fex_context_fault_barrier(void){}
static int horizon_redirect_user_shared_data(ThreadExceptionDump *c){return 0;}
static void horizon_resume_exception(ThreadExceptionDump *c){++restore_calls;longjmp(stop,1);}
static void horizon_restore_exception_context_x9(ThreadExceptionDump *c){assert(0);}
static int (*wine_nx_box64_callret_trap)(ULONG_PTR *);
static int (*wine_nx_box64_describe_native_pc)(ULONG_PTR,unsigned long long *,char *,size_t);
static int (*wine_nx_box64_handle_fault)(ULONG_PTR);
static void pes13_fex_fault_stage(unsigned s,uint64_t pc,uint64_t addr,unsigned status){}
static NTSTATUS virtual_handle_fault(EXCEPTION_RECORD *r,void *sp){assert(has_teb);++vm_calls;return vm_result;}
static void pes13_fex_dump_context(ThreadExceptionDump *c,CONTEXT *out){out->Pc=c->pc.x;out->Sp=c->sp.x;}
static int pes13_fex_dispatch_exception(EXCEPTION_RECORD *r,CONTEXT *c){assert(has_teb);++pe_calls;return pe_handles;}
static void pes13_fex_restore_context(CONTEXT *c){++restore_calls;longjmp(stop,1);}
void wine_nx_f1_crash_exception(const void *c,unsigned status){assert(c==expected);++fatal_calls;fatal_status=status;}
static void wine_nx_runtime_trace(const char *m){}
static void svcSleepThread(uint64_t ns){assert(fatal_calls==1);longjmp(stop,2);}
'''

FAULT_TEST = r'''
static void run_case(unsigned esr,int teb,int vm,int handled,unsigned expect_vm,unsigned expect_pe,unsigned expect_fatal){
 ThreadExceptionDump ctx={.esr=esr,.pc.x=0x12345678,.sp.x=0x22220000,.far.x=0xdeadbeef};
 expected=&ctx;has_teb=teb;vm_result=vm;pe_handles=handled;
 vm_calls=pe_calls=fatal_calls=restore_calls=0;
 if(!setjmp(stop))pes13_fex_wine_exception_handler(&ctx);
 assert(vm_calls==expect_vm&&pe_calls==expect_pe&&fatal_calls==expect_fatal);
 assert(restore_calls==!expect_fatal);
 if(expect_fatal)assert(fatal_status);
}
int main(void){
 /* Every no-TEB native AV previously entered the TEB-dependent VM path. */
 run_case(0x92000004,0,STATUS_ACCESS_VIOLATION,0,0,0,1);
 run_case(0x92000044,0,STATUS_ACCESS_VIOLATION,0,0,0,1);
 run_case(0x82000004,0,STATUS_ACCESS_VIOLATION,0,0,0,1);
 run_case(0x92000404,0,STATUS_ACCESS_VIOLATION,0,0,0,1);
 run_case(0xf2000000,0,0,0,0,0,1);
 run_case(0x02000000,0,0,0,0,0,1);
 /* Recoverable Wine VM faults and translated guest exceptions still resume. */
 run_case(0x92000004,1,0,0,1,0,0);
 run_case(0x92000044,1,0,0,1,0,0);
 run_case(0x92000004,1,STATUS_ACCESS_VIOLATION,1,1,1,0);
 run_case(0x92000004,1,STATUS_ACCESS_VIOLATION,0,1,1,1);
 run_case(0xf2000000,1,0,1,0,1,0);
 run_case(0x92000404,1,0,0,0,0,1);
 puts("PASS: actual exception route saves native faults without a TEB; Wine VM and guest recovery remain intact (11 cases)");
}
'''

DETACH = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <setjmp.h>
#include <stdio.h>
struct user_thread_info {void *rawinput;uintptr_t server_queue,idle_event;void *session_data,*mouse_tracking_info;};
static struct user_thread_info info={(void*)1,2,3,(void*)4,(void*)5};
static unsigned exiting_thread_id=92,step,fail_at,events;
static char last[128];static jmp_buf stop;
static unsigned GetCurrentThreadId(void){return 92;}
static struct user_thread_info *get_user_thread_info(void){return &info;}
static void advance(unsigned want){assert(++step==want);if(fail_at==step)longjmp(stop,1);}
static void destroy_thread_windows(void){advance(1);}
static void driver_detach(void){advance(2);}
static const struct {void (*pThreadDetach)(void);} driver={driver_detach},*user_driver=&driver;
static void fake_free(void *ptr){advance(ptr==(void*)1?3:ptr==(void*)4?7:8);}
static void cleanup_imm_thread(void){advance(4);}
static void NtClose(uintptr_t handle){advance(handle==2?5:6);}
void wine_nx_f1_crash_stage(const char *s,int r,unsigned long long a,unsigned long long b){assert(a==92&&!r&&!b);strcpy(last,s);++events;}
#define free fake_free
'''

DETACH_TEST = r'''
#undef free
int main(void){
 thread_detach();assert(step==8&&events==16&&!exiting_thread_id);
 const char *names[]={"windows","driver","rawinput","imm","queue","idle","session","tracking"};
 for(fail_at=1;fail_at<=8;fail_at++){
  step=events=0;exiting_thread_id=92;
  if(!setjmp(stop))thread_detach();
  char want[128];snprintf(want,sizeof(want),"thread-detach-%s-enter",names[fail_at-1]);
  assert(!strcmp(last,want)&&events==2*fail_at-1&&exiting_thread_id==92);
 }
 puts("PASS: actual teardown preserves all eight cleanup calls and records the interrupted boundary");
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'switch.h').write_text(SWITCH)
    fault=function((a.source/'dlls/ntdll/unix/horizon.c').read_text(), 'void pes13_fex_wine_exception_handler(')
    detach=function((a.source/'dlls/win32u/sysparams.c').read_text(), 'static void thread_detach(')
    for name,code in (('native-fault',FAULTS+fault+FAULT_TEST),('thread-detach',DETACH+detach+DETACH_TEST)):
        c=a.output/(name+'.c');exe=a.output/name;c.write_text(code)
        subprocess.run([shutil.which('cc'),'-std=gnu11','-D__aarch64__','-O1','-g',
                        '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(a.output),str(c),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

if __name__=='__main__':main()
