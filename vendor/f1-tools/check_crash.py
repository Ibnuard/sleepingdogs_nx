"""Test the real crash writer and handoff with injected native/SD failures.

Host mocks validate control flow and saved bytes, not Switch crash handling.
"""
from pathlib import Path
import argparse
import shutil
import subprocess
from check_startup import function

SWITCH = r'''
#include <stdint.h>
#include <stddef.h>
typedef uint32_t Result; typedef uint32_t u32; typedef uint32_t Handle;
typedef uint64_t u64; typedef int64_t s64;
typedef struct {uint64_t addr,size;uint32_t type,attr,perm,device_refcount,ipc_refcount,padding;} MemoryInfo;
#define Perm_R 1
Result svcQueryMemory(MemoryInfo *,u32 *,uintptr_t);
unsigned threadGetCurHandle(void);
typedef struct {unsigned session,object_id;} Service;
typedef struct {Service s;} FsFile;
typedef struct {Service s;} FsFileSystem;
typedef unsigned FsDirEntryType;
typedef union {uint64_t x;} CpuRegister;
typedef struct {uint32_t error_desc,pad[3];CpuRegister cpu_gprs[29],fp,lr,sp,pc;
 uint64_t padding,fpu_gprs[64];uint32_t pstate,afsr0,afsr1,esr;CpuRegister far;} ThreadExceptionDump;
#define R_SUCCEEDED(r) (!(r))
#define R_FAILED(r) ((r)!=0)
#define FsOpenMode_Write 2
#define FsWriteOption_None 0
#define FsWriteOption_Flush 1
#define BreakReason_NotificationOnlyFlag 0x80000000u
FsFileSystem *fsdevGetDeviceFileSystem(const char *);
Result fsFsGetEntryType(FsFileSystem *,const char *,FsDirEntryType *);
Result fsFsDeleteFile(FsFileSystem *,const char *);
Result fsFsRenameFile(FsFileSystem *,const char *,const char *);
Result fsFsCreateFile(FsFileSystem *,const char *,s64,unsigned);
Result fsFsOpenFile(FsFileSystem *,const char *,unsigned,FsFile *);
Result serviceClone(Service *,Service *);
void serviceClose(Service *);void fsFileClose(FsFile *);
Result fsFileWrite(FsFile *,s64,const void *,u64,unsigned);
uint64_t armGetSystemTick(void);
'''

MOCK = r'''
#include <assert.h>
#include <errno.h>
#include <setjmp.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "switch.h"
static char disk[32769],previous[32769];
/* Recovery is unarmed in the early-fatal suite. Armed routing is exercised
 * separately against f1_relaunch.c with an independent restart worker. */
void wine_nx_f1_relaunch_fatal(unsigned kind,unsigned code){(void)kind;(void)code;}
static unsigned exists,old_exists,clones,closes,writes,flushes,fail_clone,fail_write,fail_open,fail_create;
static unsigned real_calls,real_reason;static uintptr_t real_address,real_size;
static uint64_t ticks;static FsFileSystem sd;static jmp_buf escaped;
static uintptr_t readable_low;static size_t readable_size;static unsigned readable_perm=Perm_R;
static ssize_t write_answer=-99;static unsigned raw_write_calls;static s64 write_offsets[1024];
Result svcQueryMemory(MemoryInfo *info,u32 *page,uintptr_t p){
 *page=0;if(!readable_size||p<readable_low||p-readable_low>=readable_size)return 0xd401;
 *info=(MemoryInfo){.addr=readable_low,.size=readable_size,.perm=readable_perm};return 0;
}
unsigned threadGetCurHandle(void){return 0x55;}
void wine_nx_f1_native_heap_counters(uint64_t out[7]){for(unsigned i=0;i<7;i++)out[i]=i+1;}
ssize_t __real_write(int fd,const void *data,size_t n){(void)fd;(void)data;++raw_write_calls;errno=EIO;return write_answer==-99?(ssize_t)n:write_answer;}
FsFileSystem *fsdevGetDeviceFileSystem(const char *n){assert(!strcmp(n,"sdmc"));return &sd;}
Result fsFsGetEntryType(FsFileSystem *s,const char *p,FsDirEntryType *t){assert(s==&sd);*t=0;return strstr(p,"previous")?!old_exists:!exists;}
Result fsFsDeleteFile(FsFileSystem *s,const char *p){assert(s==&sd&&strstr(p,"crash-previous.log"));old_exists=0;return 0;}
Result fsFsRenameFile(FsFileSystem *s,const char *a,const char *b){assert(s==&sd&&strstr(a,"crash.log")&&strstr(b,"crash-previous.log"));memcpy(previous,disk,sizeof(disk));exists=0;old_exists=1;return 0;}
Result fsFsCreateFile(FsFileSystem *s,const char *p,s64 n,unsigned opt){assert(s==&sd&&strstr(p,"crash.log")&&n==32768&&!opt);if(fail_create)return 0x111;exists=1;memset(disk,0,sizeof(disk));return 0;}
Result fsFsOpenFile(FsFileSystem *s,const char *p,unsigned mode,FsFile *f){assert(s==&sd&&strstr(p,"crash.log")&&mode==2);if(fail_open)return 0x222;f->s=(Service){10,42};return 0;}
Result serviceClone(Service *s,Service *o){assert(s->session==10);++clones;if(clones==fail_clone)return 0x333;o->session=10+clones;o->object_id=s->object_id;return 0;}
void serviceClose(Service *s){assert(s->session);++closes;s->session=0;}
void fsFileClose(FsFile *f){serviceClose(&f->s);}
Result fsFileWrite(FsFile *f,s64 off,const void *p,u64 n,unsigned opt){assert(f->s.session==11||f->s.session==12);assert(off>=0&&off+n<=32768);assert(writes<1024);write_offsets[writes++]=off;if(fail_write)return 0x444;memcpy(disk+off,p,n);if(opt)++flushes;errno=EIO;return 0;}
uint64_t armGetSystemTick(void){return ++ticks;}
void __real_abort(void){++real_calls;longjmp(escaped,1);}
void __real_exit(int r){++real_calls;real_reason=r;longjmp(escaped,1);}
void __real__exit(int r){++real_calls;real_reason=r;longjmp(escaped,1);}
void __real_diagAbortWithResult(Result r){++real_calls;real_reason=r;longjmp(escaped,1);}
Result __real_svcBreak(u32 r,uintptr_t a,uintptr_t n){++real_calls;real_reason=r;real_address=a;real_size=n;return 0x567;}
'''

TEST = r'''
static void reset(void){
 f1_crash_ready=f1_crash_busy=f1_crash_sequence=f1_crash_dropped=f1_crash_fatal_claimed=0;
 f1_crash_write_error=0;clones=closes=writes=flushes=fail_clone=fail_write=fail_open=fail_create=real_calls=0;
 f1_native_text_busy=f1_native_text_size=0;readable_low=readable_size=0;readable_perm=Perm_R;
}
int main(void){
 reset();errno=EDOM;assert(wine_nx_f1_crash_init(1,1,2)==0&&errno==EDOM);
 assert(strstr(disk,"DXVK 2.7.1 Async profile=Stable mode=debug"));
 assert(clones==2&&flushes==1);
 for(unsigned i=0;i<70;i++)wine_nx_f1_crash_note("checkpoint");
 assert(f1_crash_sequence==70&&strstr(disk,"event=70 "));
 assert(!strstr(disk,"event=1 "));assert(errno==EDOM);
 wine_nx_f1_crash_resource(214,0,630000000,2900000,633000000,1900000000);
 assert(strstr(disk,"RESOURCE")&&strstr(disk,"capacity=")&&strstr(disk,"unclaimed="));
 /* Busy checkpoint writer must not block an exception. Fatal IPC is separate. */
 f1_crash_busy=1;unsigned old_writes=writes;
 wine_nx_f1_crash_note("dropped");assert(writes==old_writes&&f1_crash_dropped==1);
 ThreadExceptionDump ctx={.error_desc=0x301,.esr=0x92000004,.pc.x=0x12345678,.sp.x=0x11223344,.far.x=0xdeadbeef,.cpu_gprs[28].x=0x2800};
 wine_nx_f1_crash_exception(&ctx,0xc0000005);
 assert(writes==old_writes+2&&strstr(disk+F1_FATAL_BASE,"unhandled-native-exception"));
 assert(write_offsets[old_writes]==F1_FATAL_BASE&&write_offsets[old_writes+1]==F1_NATIVE_BASE);
 assert(strstr(disk+F1_NATIVE_BASE,"rust_attempts=0x1"));
 assert(strstr(disk+F1_FATAL_BASE,"pc=0x12345678")&&strstr(disk+F1_FATAL_BASE,"x28=0x2800"));
 wine_nx_f1_crash_exception(&ctx,1);assert(writes==old_writes+2);
 /* Notification breaks and every native result/argument pass through. */
 assert(__wrap_svcBreak(0x80000003u,0x123,0x456)==0x567&&writes==old_writes+2);
 assert(real_reason==0x80000003u&&real_address==0x123&&real_size==0x456);
 f1_crash_fatal_claimed=0;
 assert(__wrap_svcBreak(1,0x99,8)==0x567&&strstr(disk+F1_FATAL_BASE,"reason=svcBreak"));
 f1_crash_fatal_claimed=0;
 if(!setjmp(escaped))__wrap_diagAbortWithResult(0x10801);
 assert(real_reason==0x10801&&strstr(disk+F1_FATAL_BASE,"code=0x10801"));
 f1_crash_fatal_claimed=0;
 if(!setjmp(escaped))__wrap_abort();
 assert(strstr(disk+F1_FATAL_BASE,"reason=abort"));
 f1_crash_fatal_claimed=0;
 if(!setjmp(escaped))__wrap_exit(7);
 assert(real_reason==7&&strstr(disk+F1_FATAL_BASE,"EXIT reason=native-exit code=0x7"));
 f1_crash_fatal_claimed=0;
 if(!setjmp(escaped))__wrap__exit(0);
 assert(real_reason==0&&strstr(disk+F1_FATAL_BASE,"EXIT reason=native-_exit code=0x0"));
 /* Current-thread frames only: checked mapping, alignment, bounds and cycles. */
 _Alignas(16) uintptr_t frames[8]={(uintptr_t)&frames[2],0x1114,(uintptr_t)&frames[4],0x2224,0,0x3334,0,0};
 readable_low=(uintptr_t)frames;readable_size=sizeof(frames);
 f1_crash_native_detail((uintptr_t)frames);
 assert(strstr(disk+F1_NATIVE_BASE,"return_pc_0=0x1114")&&strstr(disk+F1_NATIVE_BASE,"return_pc_2=0x3334"));
 frames[2]=(uintptr_t)frames;f1_crash_native_detail((uintptr_t)frames);
 assert(!strstr(disk+F1_NATIVE_BASE,"return_pc_2="));
 readable_perm=0;f1_crash_native_detail((uintptr_t)frames);assert(!strstr(disk+F1_NATIVE_BASE,"return_pc_0="));
 readable_perm=Perm_R;f1_crash_native_detail((uintptr_t)frames+1);assert(!strstr(disk+F1_NATIVE_BASE,"return_pc_0="));
 frames[0]=(uintptr_t)frames+sizeof(frames);f1_crash_native_detail((uintptr_t)frames);assert(!strstr(disk+F1_NATIVE_BASE,"return_pc_1="));
 /* Native stderr survives failed output; results/errno and unrelated fd unchanged. */
 char text[600];memset(text,'x',sizeof(text));memcpy(text+580,"allocation failed",17);
 readable_low=(uintptr_t)text;readable_size=sizeof(text);write_answer=-1;
 assert(__wrap_write(2,text,sizeof(text))==-1&&errno==EIO&&f1_native_text_size==512);
 f1_crash_native_detail(0);assert(strstr(disk+F1_NATIVE_BASE,"allocation failed"));
 unsigned before_size=f1_native_text_size;write_answer=3;
 assert(__wrap_write(9,text,12)==3&&f1_native_text_size==before_size);
 assert(__wrap_write(2,(void *)1,10)==3&&f1_native_text_size==before_size);
 f1_native_text_busy=1;f1_crash_native_detail(0);assert(strstr(disk+F1_NATIVE_BASE,"native_text_busy=1"));f1_native_text_busy=0;
 f1_crash_busy=0;errno=EDOM;
 wine_nx_crash_rust_allocation(3,524301,64,262177,0x123456);
 assert(strstr(disk+F1_RUST_BASE,"RUST_ALLOCATION_FAILED kind=0x3 bytes=0x8000d")&&errno==EDOM);
 /* The next launch preserves the prior record; errors leave capture disabled. */
 reset();assert(wine_nx_f1_crash_init(0,0,2)==0);
 assert(strstr(previous+F1_FATAL_BASE,"EXIT reason=native-_exit"));
 assert(strstr(disk,"DXVK 3.1.1 profile=Stable mode=gui"));
 for(unsigned i=1;i<=2;i++){reset();fail_clone=i;assert(wine_nx_f1_crash_init(1,0,0)==0x333);assert(!f1_crash_ready&&closes==i);}
 reset();fail_open=1;assert(wine_nx_f1_crash_init(1,0,0)==0x222&&!f1_crash_ready&&!closes);
 reset();fail_write=1;assert(wine_nx_f1_crash_init(1,0,0)==0x444&&!f1_crash_ready&&closes==3);
 reset();fail_create=1;assert(wine_nx_f1_crash_init(1,0,0)==0x111&&!f1_crash_ready&&!closes);
 reset();assert(!wine_nx_f1_crash_init(1,0,2));fail_write=1;
 wine_nx_f1_crash_note("failed-write");assert(!f1_crash_busy&&f1_crash_write_error==0x444);
 puts("PASS: real crash writer saves profile/checkpoints/registers, uses independent fatal IPC, bounds the ring, rotates prior capture, preserves native abort/break behavior and handles SD/session failures.");
 puts("PASS: primary record flushed before checked frames; unreadable/cyclic/out-of-range chains stop; native text and Rust allocation details bounded; write results and errno preserved.");
}
'''

HANDOFF = r'''
#include <assert.h>
#include <stdio.h>
#include <pthread.h>
static pthread_mutex_t fx_handoff_lock=PTHREAD_MUTEX_INITIALIZER,fx_ui_lock=PTHREAD_MUTEX_INITIALIZER;
static struct {int screen,fatal;} fx_ui_view;
static int fx_ui_created,fx_ui_stop,fx_debug_live=1,f1_startup_watch_enabled=1;
static pthread_t fx_ui_thread;static FILE *fx_debug_file;
#define FX_FAILED 99
static unsigned stages;
static void wine_nx_f1_crash_note(const char *s){(void)s;++stages;}
static void fx_timestamp_start(void){}
static void log_line(const char *s){assert(fx_debug_live);assert(fprintf(fx_debug_file,"%s\n",s)>0);}
static void *ui(void *p){return p;}
'''
HANDOFF_TEST = r'''
int main(void){
 fx_debug_file=tmpfile();assert(fx_debug_file);fx_ui_created=1;
 assert(!pthread_create(&fx_ui_thread,NULL,ui,NULL));assert(fx_handoff());
 assert(!fx_ui_created&&fx_ui_stop&&!f1_startup_watch_enabled&&fx_debug_live&&stages==1);
 log_line("AFTER-HANDOFF-ERROR");assert(fx_handoff()&&stages==1);
 fx_ui_view.fatal=1;assert(!fx_handoff());
 rewind(fx_debug_file);char saved[256]={0};assert(fread(saved,1,255,fx_debug_file));
 assert(strstr(saved,"AFTER-HANDOFF-ERROR"));fclose(fx_debug_file);
 puts("PASS: actual handoff joins the UI and stops syscall sampling while keeping post-handoff logging open; repeated/failed handoffs preserve state.");
}
'''

VK = r'''
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
typedef int VkResult;typedef uint64_t VkDevice,VkSwapchainKHR,VkSemaphore,VkFence,VkQueue;
typedef struct {int unused;} VkAllocationCallbacks,VkSubmitInfo,VkSubmitInfo2;
typedef struct {struct {uint32_t width,height;} imageExtent;int imageFormat;} VkSwapchainCreateInfoKHR;
typedef struct {uint64_t timeout;VkSwapchainKHR swapchain;} VkAcquireNextImageInfoKHR;
typedef struct {uint32_t swapchainCount,waitSemaphoreCount;} VkPresentInfoKHR;
static unsigned notes,calls;static int answer;
static VkSwapchainCreateInfoKHR ci={{1280,720},44};static VkSwapchainKHR out;
static VkAcquireNextImageInfoKHR ai={55,22};static uint32_t index;
static VkPresentInfoKHR pi={1,3};static VkSubmitInfo si;static VkSubmitInfo2 si2;
static void wine_nx_f1_crash_stage(const char *s,int r,unsigned long long a,unsigned long long b)
{assert(s);(void)r;(void)a;(void)b;++notes;}
static VkResult f1_impl_win32u_vkCreateSwapchainKHR(VkDevice d,const VkSwapchainCreateInfoKHR *c,const VkAllocationCallbacks *a,VkSwapchainKHR *o)
{assert(d==11&&c==&ci&&!a&&o==&out);*o=123;++calls;return answer;}
static VkResult f1_impl_win32u_vkAcquireNextImageKHR(VkDevice d,VkSwapchainKHR s,uint64_t t,VkSemaphore sem,VkFence f,uint32_t *o)
{assert(d==11&&s==22&&t==55&&sem==66&&f==77&&o==&index);*o=2;++calls;return answer;}
static VkResult f1_impl_win32u_vkAcquireNextImage2KHR(VkDevice d,const VkAcquireNextImageInfoKHR *i,uint32_t *o)
{assert(d==11&&i==&ai&&o==&index);*o=3;++calls;return answer;}
static VkResult f1_impl_win32u_vkQueuePresentKHR(VkQueue q,const VkPresentInfoKHR *i)
{assert(q==33&&i==&pi);++calls;return answer;}
static VkResult f1_impl_win32u_vkQueueSubmit(VkQueue q,uint32_t n,const VkSubmitInfo *s,VkFence f)
{assert(q==33&&n==1&&s==&si&&f==77);++calls;return answer;}
static VkResult f1_impl_win32u_vkQueueSubmit2(VkQueue q,uint32_t n,const VkSubmitInfo2 *s,VkFence f)
{assert(q==33&&n==1&&s==&si2&&f==77);++calls;return answer;}
static VkResult f1_impl_win32u_vkQueueSubmit2KHR(VkQueue q,uint32_t n,const VkSubmitInfo2 *s,VkFence f)
{return f1_impl_win32u_vkQueueSubmit2(q,n,s,f);}
'''
VK_TEST = r'''
int main(void){
 int results[]={0,1000001003,-1,-4,-1000001004};
 for(unsigned i=0;i<200;i++){
  answer=results[i%5];
  assert(win32u_vkCreateSwapchainKHR(11,&ci,0,&out)==answer&&out==123);
  assert(win32u_vkAcquireNextImageKHR(11,22,55,66,77,&index)==answer&&index==2);
  assert(win32u_vkAcquireNextImage2KHR(11,&ai,&index)==answer&&index==3);
  assert(win32u_vkQueuePresentKHR(33,&pi)==answer);
  assert(win32u_vkQueueSubmit(33,1,&si,77)==answer);
  assert(win32u_vkQueueSubmit2(33,1,&si2,77)==answer);
  assert(win32u_vkQueueSubmit2KHR(33,1,&si2,77)==answer);
 }
 assert(calls==1400&&notes<=7*(6+8));
 puts("PASS: actual Vulkan wrappers preserve arguments, outputs, success/suboptimal/errors and bound writes across 1400 calls including submit2.");
}
'''

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    native=args.source/'wine-nx-probe/source'
    (args.output/'switch.h').write_text('#pragma once\n'+SWITCH)
    shutil.copy2(native/'f1_crash_detail.h',args.output/'f1_crash_detail.h')
    shutil.copy2(native/'f1_relaunch.h',args.output/'f1_relaunch.h')
    crash=(native/'f1_crash.c').read_text().replace('#include <switch.h>','')
    runtime=(native/'runtime.c').read_text()
    vulkan=(args.source/'dlls/win32u/vulkan.c').read_text()
    vk=VK
    for name in ('vkCreateSwapchainKHR','vkAcquireNextImageKHR','vkAcquireNextImage2KHR',
                 'vkQueuePresentKHR','vkQueueSubmit','vkQueueSubmit2','vkQueueSubmit2KHR'):
        vk+=function(vulkan,'static VkResult win32u_'+name+'(')
    cc=shutil.which('clang') or shutil.which('cc')
    for name,code in [('crash',MOCK+crash+TEST),('handoff','#include <string.h>\n'+HANDOFF+function(runtime,'static int fx_handoff(')+HANDOFF_TEST),('vulkan',vk+VK_TEST)]:
        path=args.output/(name+'.c');path.write_text(code);exe=path.with_suffix('')
        subprocess.run([cc,'-std=c11','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',
                        '-I',str(args.output),str(path),'-pthread','-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

if __name__=='__main__':main()
