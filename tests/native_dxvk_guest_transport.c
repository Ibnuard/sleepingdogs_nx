/* SPDX-License-Identifier: MIT
 * Real PE32 transport, with only Wine's endpoint discovery and native dispatch
 * modeled. Exercise first-use races, failed discovery, publication and errors.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
static HMODULE WINAPI test_module(LPCSTR name);
static FARPROC WINAPI test_proc(HMODULE module,LPCSTR name);
static void WINAPI test_enter(LPCRITICAL_SECTION lock);
static void WINAPI test_leave(LPCRITICAL_SECTION lock);
#define GetModuleHandleA test_module
#define GetProcAddress test_proc
#ifdef TEST_COUNT_LOCKS
#define EnterCriticalSection test_enter
#define LeaveCriticalSection test_leave
#endif
#include "com_guest.c"
#undef GetModuleHandleA
#undef GetProcAddress
#undef EnterCriticalSection
#undef LeaveCriticalSection
#include "com_methods.h"

#define THREADS 12u
#define RACE_CALLS 4096u
#define TIMED_CALLS 2000000u
#define HANDLE_VALUE UINT64_C(0x31415926abcddcba)
static LONG checks,queries,endpoint_calls,enters,leaves;
static LONG failure_mode,endpoint_status,packet_fault;
static HANDLE ready;
static int timing;
static volatile uint32_t checksum;
static void say(const char *s){DWORD n;WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),s,(DWORD)strlen(s),&n,NULL);}
static void number(uint64_t v){char s[32];unsigned n=0;do{s[n++]=(char)('0'+v%10);v/=10;}while(v);while(n){char c[2]={s[--n],0};say(c);}}
static void require(int good,const char *message){InterlockedIncrement(&checks);if(!good){say(message);say("\n");ExitProcess(1);}}
static void WINAPI test_enter(LPCRITICAL_SECTION lock){InterlockedIncrement(&enters);EnterCriticalSection(lock);}
static void WINAPI test_leave(LPCRITICAL_SECTION lock){InterlockedIncrement(&leaves);LeaveCriticalSection(lock);}
static LONG WINAPI native_call(uint64_t handle,unsigned index,void *request){
    struct sd_com_packet *p=request;
    if(timing){checksum+=p->args[0];p->fault=0;return 0;}
    require(handle==HANDLE_VALUE&&index==0,"incomplete or incorrect published endpoint handle");
    require(p->abi==SD_COM_ABI&&!p->reserved,"packet header altered");
    InterlockedIncrement(&endpoint_calls);
    p->ret=0x5a5a;p->aux=0x1234;p->fault=(uint32_t)packet_fault;
    return endpoint_status;
}
static LONG WINAPI query_memory(HANDLE process,const void *address,int kind,void *out,SIZE_T bytes,SIZE_T *written){
    require(process==(HANDLE)(intptr_t)-1&&address==module&&kind==1000&&bytes==8&&!written,"endpoint discovery arguments changed");
    InterlockedIncrement(&queries);
    /* Deliberately widen the torn-handle window; no caller may observe it. */
    uint32_t *words=out;words[0]=(uint32_t)HANDLE_VALUE;Sleep(2);words[1]=(uint32_t)(HANDLE_VALUE>>32);
    if(failure_mode==3)return (LONG)0xc0000001u;
    if(failure_mode==4){words[0]=words[1]=0;return 0;}
    return 0;
}
static HMODULE WINAPI test_module(LPCSTR name){require(!memcmp(name,"ntdll.dll",10),"wrong discovery module");return (HMODULE)(uintptr_t)0x10000;}
static FARPROC WINAPI test_proc(HMODULE value,LPCSTR name){
    require(value==(HMODULE)(uintptr_t)0x10000,"wrong module passed to discovery");
    if(!memcmp(name,"NtQueryVirtualMemory",21))return failure_mode==1?NULL:(FARPROC)query_memory;
    require(!memcmp(name,"__wine_unix_call",16),"unexpected discovery symbol");
    return failure_mode==2?NULL:(FARPROC)native_call;
}
static void fresh(void){
    /* Tests reset only with all workers joined; production never resets. */
    unix_call=NULL;unix_handle=0;queries=endpoint_calls=enters=leaves=0;
#ifdef TEST_FAST_ENDPOINT
    published_endpoint=NULL;
#endif
    failure_mode=endpoint_status=packet_fault=0;
}
static DWORD WINAPI worker(void *arg){
    UINT count=(UINT)(uintptr_t)arg;
    require(WaitForSingleObject(ready,10000)==WAIT_OBJECT_0,"start barrier timed out");
    for(UINT i=0;i<count;++i){
        struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_STATS};
        require(proxy_call(&p)==0&&p.ret==0x5a5a&&p.aux==0x1234,"concurrent transport changed output");
    }
    return 0;
}
static void race(void){
    fresh();ResetEvent(ready);HANDLE threads[THREADS];
    for(UINT i=0;i<THREADS;++i){threads[i]=CreateThread(NULL,0,worker,(void*)(uintptr_t)RACE_CALLS,0,NULL);require(threads[i]!=NULL,"create thread failed");}
    SetEvent(ready);
    require(WaitForMultipleObjects(THREADS,threads,TRUE,30000)==WAIT_OBJECT_0,"concurrent transport timed out");
    for(UINT i=0;i<THREADS;++i)CloseHandle(threads[i]);
    require(queries==1&&endpoint_calls==THREADS*RACE_CALLS,"endpoint initialized or dispatched wrong number of times");
    require(enters==leaves,"discovery lock leaked");
}
static void errors(void){
    for(LONG mode=1;mode<=4;++mode){
        fresh();failure_mode=mode;struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_STATS};
        LONG expected=mode<=2?(LONG)0xc0000139u:mode==3?(LONG)0xc0000001u:(LONG)0xc0000008u;
        require(proxy_call(&p)==expected&&!unix_call&&!endpoint_calls,"failed discovery published an endpoint or changed error");
        failure_mode=0;require(proxy_call(&p)==0&&endpoint_calls==1&&p.ret==0x5a5a,"failed discovery cannot be retried");
        require(enters==leaves,"failed discovery kept its lock");
    }
    packet_fault=E_INVALIDARG;struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_STATS};
    require(proxy_call(&p)==E_INVALIDARG&&p.aux==0x1234,"native packet failure lost");
    endpoint_status=(LONG)0xc0000005u;require(proxy_call(&p)==endpoint_status,"transport failure precedence lost");
    endpoint_status=packet_fault=0;
}
static uint32_t hot_path(void){
    fresh();struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_STATS};require(proxy_call(&p)==0,"warmup failed");
    enters=leaves=0;
    for(UINT i=0;i<10000;++i)require(proxy_call(&p)==0,"hot transport failed");
    require(queries==1&&endpoint_calls==10001&&enters==leaves,"hot transport repeated discovery or lost calls");
#ifdef TEST_FAST_ENDPOINT
    require(enters==0,"hot transport still locks the proxy table");
    /* This draw/stats path has no proxy-table dependency after discovery. */
    EnterCriticalSection(&proxy_lock);SetEvent(ready);
    HANDLE t=CreateThread(NULL,0,worker,(void*)1,0,NULL);require(t!=NULL,"held-lock worker create failed");
    DWORD wait=WaitForSingleObject(t,5000);LeaveCriticalSection(&proxy_lock);
    require(wait==WAIT_OBJECT_0,"hot transport blocked behind an unrelated proxy-table owner");CloseHandle(t);
#else
    require(enters==10000,"v8 control did not reproduce per-call locking");
#endif
    return (uint32_t)enters;
}
void WINAPI start(void){
    InitializeCriticalSection(&proxy_lock);module=(HINSTANCE)(uintptr_t)0x20000;
#ifdef TEST_COUNT_LOCKS
    ready=CreateEventA(NULL,TRUE,FALSE,NULL);require(ready!=NULL,"barrier create failed");
    for(UINT i=0;i<8;++i)race();errors();uint32_t hot_locks=hot_path();CloseHandle(ready);
    say("{\"status\":\"PASS\",\"checks\":");number(checks);say(",\"race_threads\":12,\"race_rounds\":8,\"race_calls\":393216,\"hot_calls\":10000,\"hot_lock_pairs\":");number(hot_locks);say("}\n");
#else
    fresh();struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_STATS};require(proxy_call(&p)==0,"benchmark warmup failed");
    /* Invoke the actual generated DrawIndexed wrapper and stack packet. */
    struct proxy object={.vtbl=proxy_vtable(SD_COM_IF_ID3D11DeviceContext),.magic=PROXY_MAGIC,.token=0x10001,.interface_id=SD_COM_IF_ID3D11DeviceContext,.refs=1};
    ID3D11DeviceContext *context=(ID3D11DeviceContext*)&object;
    LARGE_INTEGER a,b,f;QueryPerformanceFrequency(&f);timing=1;QueryPerformanceCounter(&a);
    for(UINT i=0;i<TIMED_CALLS;++i)ID3D11DeviceContext_DrawIndexed(context,3,7,-2);
    QueryPerformanceCounter(&b);timing=0;require(checksum==TIMED_CALLS*3,"benchmark draw arguments/count changed");
    say("{\"status\":\"PASS\",\"calls\":");number(TIMED_CALLS);say(",\"ticks\":");number(b.QuadPart-a.QuadPart);say(",\"frequency\":");number(f.QuadPart);say("}\n");
#endif
    ExitProcess(0);
}
