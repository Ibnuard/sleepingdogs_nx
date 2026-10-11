/* SPDX-License-Identifier: MIT
 * Real PE32 COM wrappers on Windows, with a modeled Unix/native endpoint.
 * Token values in the sampler descriptor are test inputs, not DXVK descriptors.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
static void *WINAPI test_heap_alloc(HANDLE heap,DWORD flags,SIZE_T bytes);
static unsigned lookup_visits,remove_visits;
static int count_visits;
#define HeapAlloc test_heap_alloc
#include "com_guest.c"
#undef HeapAlloc
#include "com_methods.h"

#define LIVE_COUNT 16000u
#define LOOKUP_COUNT 32768u
#define THREAD_COUNT 4u
static LONG checks,fail_allocation;
static LONG references[4][65536];
static ID3D11Device *device;
static ID3D11DeviceContext *context;
static ID3D11SamplerState *objects[LIVE_COUNT],*concurrent[THREAD_COUNT];
static HANDLE concurrent_ready;
static LONG arrivals;
static const uint32_t device_token=0x1fffd,context_token=0x1fffe;
static void say(const char *s){DWORD n;WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),s,(DWORD)strlen(s),&n,NULL);}
static void number(uint64_t v){char s[32];unsigned n=0;do{s[n++]=(char)('0'+v%10);v/=10;}while(v);while(n){char c[2]={s[--n],0};say(c);}}
static void require(int good,const char *message){InterlockedIncrement(&checks);if(!good){say(message);say("\n");ExitProcess(1);}}
static void *WINAPI test_heap_alloc(HANDLE heap,DWORD flags,SIZE_T bytes){if(InterlockedExchange(&fail_allocation,0))return NULL;return HeapAlloc(heap,flags,bytes);}
static LONG *native_refs(uint32_t token){require((token>>16)<4&&(token&65535),"invalid modeled token");return &references[token>>16][token&65535];}
static void give(uint32_t address,uint32_t token){if(address){*(uint32_t*)(uintptr_t)address=token;if(token)InterlockedIncrement(native_refs(token));}}
static LONG WINAPI native_call(uint64_t handle,unsigned index,void *request){
    (void)handle;(void)index;struct sd_com_packet *p=request;p->ret=p->fault=p->aux=0;
    if(!p->interface_id&&p->method==SD_COM_CREATE_DEVICE){give(p->args[7],device_token);give(p->args[9],context_token);}
    else if(p->method==0)give(p->args[1],p->object);
    else if(p->method==1)InterlockedIncrement(native_refs(p->object));
    else if(p->method==2)require(InterlockedDecrement(native_refs(p->object))>=0,"native reference underflow");
    else if(p->interface_id==SD_COM_IF_ID3D11Device&&p->method==SD_COM_M_ID3D11Device_CreateSamplerState){
        const D3D11_SAMPLER_DESC *desc=(const void*)(uintptr_t)p->args[0];give(p->args[1],desc->MaxAnisotropy);
    } else require(0,"unexpected modeled endpoint call");
    return 0;
}
static HRESULT get_sampler(uint32_t token,ID3D11SamplerState **out){D3D11_SAMPLER_DESC desc={0};desc.MaxAnisotropy=token;return ID3D11Device_CreateSamplerState(device,&desc,out);}
static uint32_t token_at(UINT index){return 0x10000u+index+1;}
static void check_lists(UINT expected){
    UINT count=0;
    for(struct proxy *p=proxies;p;p=p->next){
        require(p->magic==PROXY_MAGIC&&p->refs>0,"invalid live proxy");
#ifdef TEST_HASH_LOOKUP
        require(p->previous&&*p->previous==p,"global proxy backlink broken");
        require(p->hash_previous&&*p->hash_previous==p,"bucket backlink broken");
#endif
        require(++count<=expected,"proxy list has cycle or excess entry");
    }
    require(count==expected,"wrong live proxy count");
#ifdef TEST_HASH_LOOKUP
    UINT bucket_count=0;
    for(UINT i=0;i<PROXY_BUCKET_COUNT;++i)for(struct proxy *p=proxy_buckets[i];p;p=p->hash_next){
        require(proxy_bucket(p->token,p->interface_id)==i,"proxy in wrong bucket");
        require(++bucket_count<=expected,"bucket cycle or excess entry");
    }
    require(bucket_count==expected,"bucket membership differs from live list");
#endif
}
static DWORD WINAPI worker(void *argument){
    UINT id=(UINT)(uintptr_t)argument;
    require(SUCCEEDED(get_sampler(0x30042,&concurrent[id]))&&concurrent[id],"concurrent create failed");
    if(InterlockedIncrement(&arrivals)==THREAD_COUNT)SetEvent(concurrent_ready);
    require(WaitForSingleObject(concurrent_ready,30000)==WAIT_OBJECT_0,"concurrent barrier timed out");
    for(UINT i=0;i<THREAD_COUNT;++i)require(concurrent[i]==concurrent[id],"concurrent wrap broke identity");
    /* Keep the common object live through the barrier; then use stable anchors. */
    ID3D11SamplerState_Release(concurrent[id]);
    for(UINT n=0;n<2048;++n){
        UINT i=(n*97+id*701)%LIVE_COUNT;ID3D11SamplerState *again=NULL;
        require(SUCCEEDED(get_sampler(token_at(i),&again))&&again==objects[i],"concurrent repeated identity failed");
        ID3D11SamplerState_Release(again);
    }
    return 0;
}
void WINAPI start(void){
    InitializeCriticalSection(&proxy_lock);unix_call=native_call;unix_handle=1;
    require(sizeof(void*)==4,"test must execute PE32");
    require(SUCCEEDED(SdCreateDevice(NULL,D3D_DRIVER_TYPE_HARDWARE,NULL,0,NULL,0,7,&device,NULL,&context)),"device setup failed");
    for(UINT i=0;i<LIVE_COUNT;++i)require(SUCCEEDED(get_sampler(token_at(i),&objects[i]))&&objects[i],"population failed");
    check_lists(LIVE_COUNT+2);
    for(UINT i=0;i<128;++i){
        IUnknown *a=NULL,*b=NULL;ID3D11SamplerState *same=NULL;
        require(SUCCEEDED(ID3D11SamplerState_QueryInterface(objects[i],&IID_IUnknown,(void**)&a)),"IUnknown alias failed");
        require(SUCCEEDED(ID3D11SamplerState_QueryInterface(objects[i],&IID_IUnknown,(void**)&b))&&a==b,"alias identity failed");
        require((void*)a!=(void*)objects[i],"different interface kinds incorrectly merged");
        require(SUCCEEDED(IUnknown_QueryInterface(a,&IID_ID3D11SamplerState,(void**)&same))&&same==objects[i],"alias roundtrip failed");
        ID3D11SamplerState_Release(same);IUnknown_Release(a);IUnknown_Release(b);
    }
    ID3D11SamplerState *generation=NULL,*again=NULL;
    require(SUCCEEDED(get_sampler(0x20008,&generation))&&generation!=objects[7],"different token generations merged");
    require(SUCCEEDED(get_sampler(0x20008,&again))&&again==generation,"generation identity failed");
    ID3D11SamplerState_Release(again);ID3D11SamplerState_Release(generation);
    require(SUCCEEDED(get_sampler(0,&again))&&!again,"null token did not stay null");
    fail_allocation=1;again=(void*)1;
    require(get_sampler(0x20009,&again)==E_OUTOFMEMORY&&!again,"allocation failure incorrectly published proxy");
    require(!references[2][9],"allocation failure leaked native reference");
    require(SUCCEEDED(get_sampler(0x20009,&again))&&again,"failed allocation poisoned later lookup");
    ID3D11SamplerState_Release(again);check_lists(LIVE_COUNT+2);
    concurrent_ready=CreateEventA(NULL,TRUE,FALSE,NULL);require(concurrent_ready!=NULL,"event create failed");
    HANDLE threads[THREAD_COUNT];
    for(UINT i=0;i<THREAD_COUNT;++i){threads[i]=CreateThread(NULL,0,worker,(void*)(uintptr_t)i,0,NULL);require(threads[i]!=NULL,"thread create failed");}
    require(WaitForMultipleObjects(THREAD_COUNT,threads,TRUE,60000)==WAIT_OBJECT_0,"threads timed out");
    for(UINT i=0;i<THREAD_COUNT;++i)CloseHandle(threads[i]);CloseHandle(concurrent_ready);
    check_lists(LIVE_COUNT+2);
    LARGE_INTEGER begin,end,frequency;QueryPerformanceFrequency(&frequency);lookup_visits=remove_visits=0;count_visits=1;
    QueryPerformanceCounter(&begin);
    for(UINT n=0;n<LOOKUP_COUNT;++n){
        UINT i=(n*4051u)%LIVE_COUNT;
        require(SUCCEEDED(get_sampler(token_at(i),&again))&&again==objects[i],"timed identity failed");
        ID3D11SamplerState_Release(again);
    }
    QueryPerformanceCounter(&end);count_visits=0;
    uint64_t ticks=(uint64_t)(end.QuadPart-begin.QuadPart);
    /* Release in a permutation, removing bucket/list heads and middle entries. */
    count_visits=1;
    for(UINT n=0;n<LIVE_COUNT;++n){UINT i=(n*4051u)%LIVE_COUNT;ID3D11SamplerState_Release(objects[i]);}
    count_visits=0;check_lists(2);
    ID3D11DeviceContext_Release(context);ID3D11Device_Release(device);require(!proxies,"guest proxies remain");check_lists(0);
    for(UINT g=0;g<4;++g)for(UINT i=0;i<65536;++i)require(!references[g][i],"native references remain");
    say("{\"status\":\"PASS\",\"checks\":");number(checks);say(",\"live_proxies\":");number(LIVE_COUNT);
    say(",\"timed_lookups\":");number(LOOKUP_COUNT);say(",\"ticks\":");number(ticks);say(",\"frequency\":");number(frequency.QuadPart);
    say(",\"lookup_visits\":");number(lookup_visits);say(",\"removal_visits\":");number(remove_visits);say("}\n");ExitProcess(0);
}
