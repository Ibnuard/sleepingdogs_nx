"""Reproduce the DXVK descriptor-thread failure and test native failure reporting."""
from pathlib import Path
import argparse
import hashlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_launcher import profile_config
from check_startup import function

NATIVE = r'''
#define _DEFAULT_SOURCE 1
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include <malloc.h>
typedef uint64_t u64;
typedef unsigned Result;
typedef void (*ThreadFunc)(void *);
typedef struct {unsigned marker;} Thread;
#define R_FAILED(r) ((r)!=0)
#define MAKERESULT(m,d) ((m)|((d)<<9))
#define Module_Libnx 345
#define LibnxError_OutOfMemory 2
#define InfoType_FreeThreadCount 24
#define CUR_PROCESS_HANDLE 0xffff8001u
static char trace[8192];
char *fake_heap_start=(char *)(uintptr_t)0x10000000, *fake_heap_end=(char *)(uintptr_t)0x80000000;
void wine_nx_f1_crash_resource(uint64_t t,unsigned r,uint64_t u,uint64_t f,uint64_t a,uint64_t c)
{(void)t;(void)r;(void)u;(void)f;(void)a;assert(c==0x70000000);}
size_t wine_nx_release_idle_backing_pages(void){return 0;}
size_t wine_nx_f1_release_idle_scratch(size_t size){(void)size;return 0;}
/* This suite runs before the exclusive reserve is initialized. Its active
 * fallback and close ownership are covered by check_native_stacks.py. */
Result wine_nx_f1_native_stack_retry(Result previous,Thread *t,ThreadFunc entry,void *arg,
                                   void *stack,size_t size,int priority,int core)
{(void)t;(void)entry;(void)arg;(void)stack;(void)size;(void)priority;(void)core;return previous;}
void wine_nx_f1_crash_stage(const char *s,unsigned r,uint64_t a,uint64_t b){(void)s;(void)r;(void)a;(void)b;}
int wine_nx_f1_relaunch_request(unsigned kind,unsigned code){(void)kind;(void)code;return 0;}
static Result native_result, query_result;
static int pthread_result, native_calls, pthread_calls;
static void *want_thread, *want_arg, *want_stack;
static ThreadFunc want_entry;
static void *(*want_pentry)(void *);
static const pthread_attr_t *want_attr;
static size_t want_size;
static int want_priority, want_core;
void wine_nx_runtime_trace(const char *message) {
    assert(strlen(trace)+strlen(message)+2<sizeof(trace));
    strcat(trace,message);strcat(trace,"\n");errno=EIO;
}
void wine_nx_f1_guest_memory_snapshot(uint64_t out[6]){for(int i=0;i<6;i++)out[i]=(uint64_t)(i+1)<<20;errno=EIO;}
unsigned long long wine_nx_sd_cache_bytes(void){errno=EIO;return 8ull<<20;}
void horizon_get_memory_info(unsigned long long *t,unsigned long long *u){*t=1280ull<<20;*u=1181ull<<20;errno=EIO;}
#define InfoType_TotalMemorySize 6
#define InfoType_UsedMemorySize 7
#define InfoType_SystemResourceSizeTotal 16
#define InfoType_SystemResourceSizeUsed 17
static Result svcGetInfo(u64 *out,int info,unsigned handle,u64 sub) {
    assert(handle==CUR_PROCESS_HANDLE&&sub==0);
    errno=ENOSPC;
    switch(info){
    case 6:*out=2048ull<<20;return 0;
    case 7:*out=1949ull<<20;return 0;
    case 16:return 0xf001; /* no dedicated system resource: kernel rejects */
    case 17:return 0xf001;
    }
    assert(info==24);
    if(!query_result)*out=9;
    return query_result;
}
Result __real_threadCreate(Thread *thread,ThreadFunc entry,void *arg,void *stack,size_t size,int priority,int core) {
    assert(thread==want_thread&&entry==want_entry&&arg==want_arg&&stack==want_stack);
    assert(size==want_size&&priority==want_priority&&core==want_core);
    ++native_calls;thread->marker=123;errno=EDOM;return native_result;
}
int __real_pthread_create(pthread_t *thread,const pthread_attr_t *attr,void *(*entry)(void *),void *arg) {
    assert(thread==want_thread&&attr==want_attr&&entry==want_pentry&&arg==want_arg);
    ++pthread_calls;*thread=456;errno=ERANGE;return pthread_result;
}
'''

NATIVE_MAIN = r'''
static void native_entry(void *arg){(void)arg;}
static void *pthread_entry(void *arg){return arg;}
int main(void) {
    Thread t={0};want_thread=&t;want_entry=native_entry;want_arg=(void *)0xabc;
    want_stack=(void *)0x123000;want_size=0x100000;want_priority=59;want_core=-2;
    unsigned results[]={0,0x559,0xce01,0xd401};
    for(unsigned i=0;i<4;i++){
        trace[0]=0;native_result=results[i];
        assert(__wrap_threadCreate(&t,native_entry,want_arg,want_stack,want_size,59,-2)==results[i]);
        assert(t.marker==123&&errno==EDOM&&native_calls==(int)i+1);
        if(i){assert(strstr(trace,"stage=libnx-create"));assert(strstr(trace,"free_threads=9 query_rc=00000000"));
            assert(strstr(trace,"[F1-MEMBUDGET] reason=libnx-create-failed total=2147483648 used=2043674624 free=103809024 sysres_total=0 sysres_used=0 rc=00000000/00000000/0000f001/0000f001"));
            assert(strstr(trace,"[F1-MEMMAP] reason=libnx-create-failed wine_backing=1048576 backing_peak=2097152 pooled=3145728 sections=4194304 sections_peak=5242880 page_arenas=6291456 sd_cache=8388608 reported_total=1342177280 reported_used=1238368256"));}
        else assert(!trace[0]);
    }
    pthread_t pt;pthread_attr_t attr;want_thread=&pt;want_attr=&attr;want_pentry=pthread_entry;
    int errors[]={0,ENOMEM,EAGAIN,EINVAL,EPERM};
    for(unsigned i=0;i<5;i++){
        trace[0]=0;pthread_result=errors[i];
        assert(__wrap_pthread_create(&pt,&attr,pthread_entry,want_arg)==errors[i]);
        assert(pt==456&&errno==ERANGE&&pthread_calls==(int)i+1);
        if(i)assert(strstr(trace,"stage=pthread-create"));else assert(!trace[0]);
    }
    trace[0]=0;errno=EDOM;query_result=0xf601;
    wine_nx_f1_thread_failure("wine-stack",0xc0000017u,1048576,4096,12);
    assert(errno==EDOM);
    assert(strstr(trace,"stage=wine-stack status=c0000017 reserve=1048576 commit=4096 errno=12"));
    assert(strstr(trace,"query_rc=0000f601"));
    assert(strstr(trace,"[F1-MEMBUDGET] reason=wine-stack "));
    assert(strstr(trace,"[F1-MEMMAP] reason=wine-stack "));
    puts("PASS: actual native wrappers preserve arguments, ownership, Results and errno; creation failures survive disabled Wine trace; unsupported resource query is reported; kernel memory budget, system resource Results and the memory map are logged.");
}
'''

CPP = r'''
#include <cassert>
#include <memory>
#include <system_error>
#include <iostream>
namespace test {
static int attempts;
struct Thread {
    Thread()=default;
    template<class F> Thread(F) {
        ++attempts;
        throw std::system_error(std::make_error_code(std::errc::resource_unavailable_try_again));
    }
};
}
namespace dxvk {
template<class T> using Rc=std::shared_ptr<T>;
namespace sync {struct Fence {};}
struct DxvkDevice {
    bool heap,buffer;
    bool canUseDescriptorHeap() const {return heap;}
    bool canUseDescriptorBuffer() const {return buffer;}
    int vkd() const {return 0;}
};
struct DxvkDescriptorCopyWorker {
    Rc<DxvkDevice> m_device;int m_vkd;
    std::unique_ptr<sync::Fence> m_appendFence,m_consumeFence;
    int m_writeBufferDescriptorsFn;test::Thread m_thread;
    int getWriteBufferDescriptorFn(){return 0;}
    void runWorker(){}
    DxvkDescriptorCopyWorker(const Rc<DxvkDevice>&);
};
/* Only replace the OS thread primitive for fault injection. The constructor,
 * feature guard and member initialization are from the pinned DXVK source. */
CTOR
}
int main(int argc,char **argv) {
    assert(argc==3);
    auto device=std::make_shared<dxvk::DxvkDevice>();
    device->heap=false;device->buffer=true;
    bool failed=false;
    try{dxvk::DxvkDescriptorCopyWorker old(device);}catch(const std::system_error& e){
        failed=e.code()==std::errc::resource_unavailable_try_again;
    }
    assert(failed&&test::attempts==1);
    device->heap=std::string(argv[1])!="False";device->buffer=std::string(argv[2])!="False";
    dxvk::DxvkDescriptorCopyWorker fixed(device);
    assert(!device->heap&&!device->buffer&&test::attempts==1);
    std::cout<<"PASS: DXVK 3.1.1 original descriptor-buffer constructor reproduces EAGAIN; shipped legacy settings require no descriptor-copy thread.\n";
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    native = args.source / 'wine-nx-probe/source/f1_thread_diagnostics.c'
    assert native.read_bytes() == (ROOT / 'tools/f1_thread_diagnostics.c').read_bytes()
    code = native.read_text().replace('#include <switch.h>', '')
    (out/'switch.h').write_text('/* SDK types are supplied by this fault-injection fixture. */\n')
    cfile = out / 'native-thread-check.c'
    cfile.write_text(NATIVE + code + NATIVE_MAIN)
    cc = shutil.which('clang') or shutil.which('cc')
    subprocess.run([cc, '-std=c11', '-O1', '-g', '-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all', '-I'+str(out), '-I'+str(ROOT/'tools'), str(cfile), '-pthread', '-o', str(cfile.with_suffix(''))], check=True)
    subprocess.run([str(cfile.with_suffix(''))], check=True)

    upstream = ROOT / 'debug/0.1.7-thread-startup/dxvk_descriptor_worker.cpp'
    assert hashlib.sha256(upstream.read_bytes()).hexdigest() == '7ee98be13f569c59ff8ae126633d3610f511b6eebcf67fb5a5f38a8134c284c2'
    ctor = function(upstream.read_text(), 'DxvkDescriptorCopyWorker::DxvkDescriptorCopyWorker(')
    assert ctor.count('std::thread(') == 1
    cppfile = out / 'descriptor-check.cpp'
    cppfile.write_text(CPP.replace('CTOR', ctor.replace('std::thread(', 'test::Thread(')))
    cxx = shutil.which('g++') or shutil.which('clang++')
    exe = cppfile.with_suffix('')
    subprocess.run([cxx, '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all', str(cppfile), '-o', str(exe)], check=True)
    for renderer in (False, True):
        for profile in ('balanced', 'low-latency', 'stable', 'quality'):
            config = dict(line.split(' = ') for line in profile_config(profile, renderer).splitlines()
                          if line and not line.startswith('#'))
            subprocess.run([str(exe), config['dxvk.enableDescriptorHeap'], config['dxvk.enableDescriptorBuffer']], check=True)

    # Failure messages must be in the *generated* paths, not just a spare helper.
    thread = (args.source / 'dlls/ntdll/unix/thread.c').read_text()
    wrapper = function(thread, 'NTSTATUS WINAPI NtCreateThreadEx(')
    assert 'f1_create_thread_original(' in wrapper and 'wine_nx_f1_thread_failure(' in wrapper
    for stage in ('wine-teb', 'wine-stack'):
        assert f'wine_nx_f1_thread_failure("{stage}"' in thread
    horizon = (args.source / 'dlls/ntdll/unix/horizon.c').read_text()
    assert 'wine_nx_f1_thread_failure("wine-server-pthread"' in horizon
    print('PASS: generated NtCreateThreadEx, TEB/stack and server failure paths are connected.')


if __name__ == '__main__':
    main()
