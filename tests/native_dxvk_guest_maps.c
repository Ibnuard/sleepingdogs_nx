/* SPDX-License-Identifier: MIT
 * Execute the real PE32 Map wrappers on Windows with a modeled native endpoint.
 * Native BindMap deliberately mirrors full-range initialization before exposure.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
static void *WINAPI test_heap_alloc(HANDLE heap,DWORD flags,SIZE_T bytes);
static BOOL WINAPI test_heap_free(HANDLE heap,DWORD flags,void *memory);
static void *WINAPI test_virtual_alloc(void *address,SIZE_T bytes,DWORD type,DWORD protect);
static BOOL WINAPI test_virtual_free(void *address,SIZE_T bytes,DWORD type);
#define HeapAlloc test_heap_alloc
#define HeapFree test_heap_free
#define VirtualAlloc test_virtual_alloc
#define VirtualFree test_virtual_free
#include "com_guest.c"
#undef HeapAlloc
#undef HeapFree
#undef VirtualAlloc
#undef VirtualFree
#include "com_methods.h"

#define RESOURCE_COUNT 16u
#define THREAD_COUNT 4u
#define BENCH_FRAMES 32u
struct modeled_resource {uint32_t token,bytes,id,mode;unsigned char *data,*guest;LONG refs;};
static struct modeled_resource resources[RESOURCE_COUNT];
static ID3D11Resource *objects[RESOURCE_COUNT];
static ID3D11DeviceContext *context;
static LONG context_refs,checks,heap_calls,heap_live,virtual_calls,virtual_live,virtual_frees;
static LONG fail_heap,fail_virtual,fail_bind,fail_map,fail_map_oom,oom_as_fault,abort_calls,map_requests;
static uint32_t next_id=1;
static CRITICAL_SECTION native_lock;
static HANDLE ready_event;
static LONG ready_count;
static void *thread_memory[THREAD_COUNT];
static void say(const char *s){DWORD n;WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),s,(DWORD)strlen(s),&n,NULL);}
static void number(uint64_t v){char s[32];unsigned n=0;do{s[n++]=(char)('0'+v%10);v/=10;}while(v);while(n){char c[2]={s[--n],0};say(c);}}
static void require(int good,const char *message){InterlockedIncrement(&checks);if(!good){say(message);say("\n");ExitProcess(1);}}
static int consume_failure(LONG *counter){for(;;){LONG value=InterlockedCompareExchange(counter,0,0);if(!value)return 0;if(InterlockedCompareExchange(counter,value-1,value)==value)return 1;}}
static void *WINAPI test_heap_alloc(HANDLE heap,DWORD flags,SIZE_T bytes){
    InterlockedIncrement(&heap_calls);if(consume_failure(&fail_heap))return NULL;
    void *result=HeapAlloc(heap,flags,bytes);if(result)InterlockedIncrement(&heap_live);return result;
}
static BOOL WINAPI test_heap_free(HANDLE heap,DWORD flags,void *memory){BOOL result=HeapFree(heap,flags,memory);if(result&&memory)InterlockedDecrement(&heap_live);return result;}
static void *WINAPI test_virtual_alloc(void *address,SIZE_T bytes,DWORD type,DWORD protect){
    InterlockedIncrement(&virtual_calls);if(consume_failure(&fail_virtual))return NULL;
    void *result=VirtualAlloc(address,bytes,type,protect);if(result)InterlockedIncrement(&virtual_live);return result;
}
static BOOL WINAPI test_virtual_free(void *address,SIZE_T bytes,DWORD type){
    BOOL result=VirtualFree(address,bytes,type);if(result){InterlockedIncrement(&virtual_frees);InterlockedDecrement(&virtual_live);}return result;
}
static struct modeled_resource *resource_for(uint32_t token){
    require(token>=0x10002&&token<0x10002+RESOURCE_COUNT,"invalid modeled resource token");return &resources[token-0x10002];
}
static struct modeled_resource *map_for(uint32_t id){for(UINT i=0;i<RESOURCE_COUNT;++i)if(resources[i].id==id)return &resources[i];require(0,"unknown modeled map");return NULL;}
static void close_map(struct modeled_resource *r){require(r->id&&r->refs>1&&context_refs>1,"invalid map ownership");r->id=0;r->guest=NULL;--r->refs;--context_refs;}
static LONG WINAPI native_call(uint64_t handle,unsigned index,void *request){
    (void)handle;(void)index;struct sd_com_packet *p=request;p->ret=p->fault=p->aux=0;EnterCriticalSection(&native_lock);
    if(p->interface_id&&p->method==1){if(p->object==0x10001)++context_refs;else ++resource_for(p->object)->refs;}
    else if(p->interface_id&&p->method==2){LONG refs=p->object==0x10001?--context_refs:--resource_for(p->object)->refs;require(refs>=0,"native reference underflow");}
    else if(p->interface_id==SD_COM_IF_ID3D11DeviceContext&&p->method==SD_COM_M_ID3D11DeviceContext_Map){
        struct modeled_resource *r=resource_for(p->args[0]);D3D11_MAPPED_SUBRESOURCE *out=(void*)(uintptr_t)p->args[4];
        ++map_requests;
        if(consume_failure(&fail_map_oom)){p->ret=E_OUTOFMEMORY;if(oom_as_fault)p->fault=E_OUTOFMEMORY;}
        else if(consume_failure(&fail_map))p->ret=DXGI_ERROR_WAS_STILL_DRAWING;
        else if(r->id)p->ret=p->fault=E_INVALIDARG;
        else{r->id=next_id++;r->mode=p->args[2];r->guest=NULL;++r->refs;++context_refs;out->RowPitch=r->bytes;out->DepthPitch=r->bytes;p->aux=r->id;p->high[0]=r->bytes;}
    } else if(!p->interface_id&&p->method==SD_COM_BIND_MAP){
        struct modeled_resource *r=map_for(p->args[0]);require(p->args[2]==r->bytes&&!r->guest,"invalid modeled bind");
        unsigned char *memory=(void*)(uintptr_t)p->args[1];MEMORY_BASIC_INFORMATION info;
        require(VirtualQuery(memory,&info,sizeof(info))&&info.State==MEM_COMMIT&&info.Protect==PAGE_READWRITE&&
                (uintptr_t)memory+r->bytes<=(uintptr_t)info.BaseAddress+info.RegionSize,"modeled writable range rejected");
        if(consume_failure(&fail_bind))p->ret=p->fault=E_POINTER;
        else{r->guest=memory;
            if(r->mode!=D3D11_MAP_WRITE_DISCARD)memcpy(memory,r->data,r->bytes);
#ifdef TEST_ZERO_DISCARD
            else memset(memory,0,r->bytes); /* Pinned v8.1 native policy. */
#endif
        }
    } else if(!p->interface_id&&p->method==SD_COM_ABORT_MAP){close_map(map_for(p->args[0]));++abort_calls;}
    else if(p->interface_id==SD_COM_IF_ID3D11DeviceContext&&p->method==SD_COM_M_ID3D11DeviceContext_Unmap){
        struct modeled_resource *r=resource_for(p->args[0]);require(r->id&&r->guest,"Unmap without bound shadow");
        if(r->mode!=D3D11_MAP_READ)memcpy(r->data,r->guest,r->bytes);p->aux=r->id;close_map(r);
    } else require(0,"unexpected modeled endpoint operation");
    LeaveCriticalSection(&native_lock);return 0;
}
static void create_resource(UINT i,uint32_t bytes){
    struct modeled_resource *r=&resources[i];require(!objects[i]&&!r->data,"resource already exists");r->bytes=bytes;r->token=0x10002+i;r->refs=1;
    r->data=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,bytes);require(r->data!=NULL,"modeled backing allocation failed");
    objects[i]=proxy_wrap(r->token,SD_COM_IF_ID3D11Resource);require(objects[i]!=NULL,"resource proxy failed");
}
static void destroy_resource(UINT i){struct modeled_resource *r=&resources[i];require(!r->id,"destroying active mapping");ID3D11Resource_Release(objects[i]);objects[i]=NULL;require(!r->refs,"resource refs remain");HeapFree(GetProcessHeap(),0,r->data);memset(r,0,sizeof(*r));}
static HRESULT map_resource(UINT i,D3D11_MAP type,D3D11_MAPPED_SUBRESOURCE *out){return ID3D11DeviceContext_Map(context,objects[i],0,type,0,out);}
static void unmap_resource(UINT i){ID3D11DeviceContext_Unmap(context,objects[i],0);require(resources[i].refs==1,"Unmap retained resource references");}
static void check_cache(void){
#ifdef TEST_SHADOW_CACHE
    UINT count=0,bytes=0;
    EnterCriticalSection(&proxy_lock);
    for(struct mapped_shadow *s=idle_shadows;s;s=s->next){
        require(!s->id&&!s->context&&!s->resource&&s->memory&&s->bytes,"cached entry retains active ownership");++count;bytes+=s->bytes;
        for(struct mapped_shadow *a=shadows;a;a=a->next)require(a->memory!=s->memory,"active mapping is cached");
        require(count<=SHADOW_CACHE_ENTRIES,"cache entry cap exceeded");
    }
    require(count==idle_shadow_count&&bytes==idle_shadow_bytes&&bytes<=SHADOW_CACHE_BYTES,"cache accounting mismatch");
    LeaveCriticalSection(&proxy_lock);
#endif
}
static void drain_cache(void){
#ifdef TEST_SHADOW_CACHE
    shadow_cache_clear();require(!idle_shadows&&!idle_shadow_bytes&&!idle_shadow_count,"cache drain incomplete");
#endif
    require(!shadows&&!virtual_live,"inactive memory remains after drain");
}
static void mode_tests(void){
    create_resource(0,4096);static unsigned char previous[4096];
    for(UINT type=D3D11_MAP_READ;type<=D3D11_MAP_WRITE_NO_OVERWRITE;++type){
        for(UINT i=0;i<4096;++i)resources[0].data[i]=previous[i]=(unsigned char)(i*13+type);
        D3D11_MAPPED_SUBRESOURCE out={0};require(SUCCEEDED(map_resource(0,(D3D11_MAP)type,&out)),"Map mode failed");
        if(type!=D3D11_MAP_WRITE_DISCARD)
            for(UINT i=0;i<4096;++i)require(((unsigned char*)out.pData)[i]==previous[i],"preserving Map changed bytes");
        memset(out.pData,0x6b,4096);unmap_resource(0);
        for(UINT i=0;i<4096;++i)require(resources[0].data[i]==(type==D3D11_MAP_READ?previous[i]:0x6b),"Unmap copy direction incorrect");
        check_cache();
    }
    D3D11_MAPPED_SUBRESOURCE a,b;require(SUCCEEDED(map_resource(0,D3D11_MAP_WRITE_DISCARD,&a)),"first reuse Map failed");
    memset(a.pData,0xcc,4096);unmap_resource(0);LONG before=virtual_calls;
    require(SUCCEEDED(map_resource(0,D3D11_MAP_WRITE_DISCARD,&b)),"repeated Map failed");
#ifdef TEST_SHADOW_CACHE
    require(a.pData==b.pData&&virtual_calls==before,"exact-size shadow was not reused");
#endif
    /* DISCARD has no initial-content guarantee. Initialize only a middle
     * range, then check exactly the data the application has written. */
    memset((unsigned char*)b.pData+137,0x57,61);
    unmap_resource(0);
    for(UINT i=137;i<198;++i)require(resources[0].data[i]==0x57,"partial DISCARD write was lost");
    destroy_resource(0);drain_cache();
}
static void overlap_tests(void){
    for(UINT i=0;i<3;++i)create_resource(i,4096);D3D11_MAPPED_SUBRESOURCE a,b,c;
    require(SUCCEEDED(map_resource(0,D3D11_MAP_WRITE_DISCARD,&a))&&SUCCEEDED(map_resource(1,D3D11_MAP_WRITE_DISCARD,&b))&&a.pData!=b.pData,"overlapping maps alias");
    memset(b.pData,0x5a,4096);unmap_resource(0);
    require(SUCCEEDED(map_resource(2,D3D11_MAP_WRITE_DISCARD,&c))&&c.pData!=b.pData,"active shadow reused");
#ifdef TEST_SHADOW_CACHE
    require(c.pData==a.pData,"inactive exact-size shadow not reused");
#endif
    for(UINT i=0;i<4096;++i)require(((unsigned char*)b.pData)[i]==0x5a,"overlapping mapping was overwritten");
    check_cache();unmap_resource(1);unmap_resource(2);
    for(UINT i=0;i<3;++i)destroy_resource(i);drain_cache();
}
static DWORD WINAPI worker(void *arg){
    UINT i=(UINT)(uintptr_t)arg;D3D11_MAPPED_SUBRESOURCE out;
    require(SUCCEEDED(map_resource(i,D3D11_MAP_WRITE_DISCARD,&out)),"thread Map failed");thread_memory[i]=out.pData;
    if(InterlockedIncrement(&ready_count)==THREAD_COUNT)SetEvent(ready_event);
    require(WaitForSingleObject(ready_event,30000)==WAIT_OBJECT_0,"thread barrier timed out");
    for(UINT j=0;j<THREAD_COUNT;++j)if(j!=i)require(thread_memory[j]!=out.pData,"concurrent active shadows alias");
    memset(out.pData,(int)i+1,resources[i].bytes);unmap_resource(i);
    for(UINT n=0;n<32;++n){require(SUCCEEDED(map_resource(i,D3D11_MAP_WRITE_DISCARD,&out)),"thread repeated Map failed");
#if !defined(TEST_SHADOW_CACHE) || defined(TEST_ZERO_DISCARD)
        require(!((unsigned char*)out.pData)[0]&&!((unsigned char*)out.pData)[resources[i].bytes-1],"thread shadow not reinitialized");
#endif
        memset(out.pData,(int)i+1,resources[i].bytes);unmap_resource(i);
        require(resources[i].data[0]==i+1&&resources[i].data[resources[i].bytes-1]==i+1,"concurrent discard write lost data");}
    return 0;
}
static void concurrency_tests(void){
    HANDLE threads[THREAD_COUNT];ready_event=CreateEventA(NULL,TRUE,FALSE,NULL);require(ready_event!=NULL,"event allocation failed");
    for(UINT i=0;i<THREAD_COUNT;++i){create_resource(i,65536);threads[i]=CreateThread(NULL,0,worker,(void*)(uintptr_t)i,0,NULL);require(threads[i]!=NULL,"thread create failed");}
    require(WaitForMultipleObjects(THREAD_COUNT,threads,TRUE,60000)==WAIT_OBJECT_0,"concurrent maps timed out");
    for(UINT i=0;i<THREAD_COUNT;++i){CloseHandle(threads[i]);for(UINT j=0;j<resources[i].bytes;++j)require(resources[i].data[j]==i+1,"concurrent copy contents differ");destroy_resource(i);}
    CloseHandle(ready_event);check_cache();drain_cache();
}
static void capacity_tests(void){
    D3D11_MAPPED_SUBRESOURCE out[5];
    for(UINT i=0;i<3;++i){create_resource(i,8*1024*1024);require(SUCCEEDED(map_resource(i,D3D11_MAP_WRITE_DISCARD,&out[i])),"large active Map failed");}
    require(out[0].pData!=out[1].pData&&out[0].pData!=out[2].pData&&out[1].pData!=out[2].pData,"large active maps alias");
    for(UINT i=0;i<3;++i){unmap_resource(i);check_cache();destroy_resource(i);}
#ifdef TEST_SHADOW_CACHE
    require(idle_shadow_bytes==SHADOW_CACHE_BYTES&&idle_shadow_count==2&&virtual_live==2,"byte cap did not evict excess idle entry");
#endif
    create_resource(0,17*1024*1024);LONG before=virtual_live;require(SUCCEEDED(map_resource(0,D3D11_MAP_WRITE_DISCARD,&out[0])),"oversized Map failed");
    unmap_resource(0);require(virtual_live==before,"oversized shadow retained");destroy_resource(0);check_cache();drain_cache();
    for(UINT i=0;i<5;++i){create_resource(i,4096*(i+1));require(SUCCEEDED(map_resource(i,D3D11_MAP_WRITE_DISCARD,&out[i])),"entry-cap Map failed");unmap_resource(i);check_cache();destroy_resource(i);}
#ifdef TEST_SHADOW_CACHE
    require(idle_shadow_count==SHADOW_CACHE_ENTRIES&&virtual_live==4,"entry cap did not evict excess idle entry");
#endif
    drain_cache();
}
static void failure_tests(void){
    D3D11_MAPPED_SUBRESOURCE out;create_resource(0,4096);create_resource(1,8192);
    require(SUCCEEDED(map_resource(0,D3D11_MAP_WRITE_DISCARD,&out)),"failure-test warmup failed");unmap_resource(0);
    LONG before=virtual_calls;fail_virtual=1;HRESULT result=map_resource(1,D3D11_MAP_WRITE_DISCARD,&out);
#ifdef TEST_SHADOW_CACHE
    require(SUCCEEDED(result)&&virtual_calls==before+2&&idle_shadow_count==0,"VirtualAlloc failure did not evict and retry once");unmap_resource(1);
#else
    require(result==E_OUTOFMEMORY&&!out.pData,"v7 VirtualAlloc failure not reported");
#endif
    fail_virtual=0;drain_cache();before=abort_calls;fail_virtual=2;
    require(map_resource(0,D3D11_MAP_WRITE_DISCARD,&out)==E_OUTOFMEMORY&&!out.pData&&!out.RowPitch&&!out.DepthPitch,"persistent allocation failure did not clear output");
    require(abort_calls==before+1&&!resources[0].id&&resources[0].refs==1,"persistent allocation failure did not abort native map");fail_virtual=0;drain_cache();
    fail_heap=1;result=map_resource(0,D3D11_MAP_WRITE_DISCARD,&out);
#ifdef TEST_SHADOW_CACHE
    require(SUCCEEDED(result),"HeapAlloc failure was not retried");unmap_resource(0);
#else
    require(result==E_OUTOFMEMORY&&!out.pData,"v7 HeapAlloc failure not reported");
#endif
    fail_heap=0;drain_cache();fail_heap=2;before=abort_calls;
    require(map_resource(0,D3D11_MAP_WRITE_DISCARD,&out)==E_OUTOFMEMORY&&!out.pData&&abort_calls==before+1,"persistent metadata failure not aborted");fail_heap=0;drain_cache();
    require(SUCCEEDED(map_resource(0,D3D11_MAP_WRITE_DISCARD,&out)),"bind-failure warmup failed");unmap_resource(0);
    fail_bind=1;before=abort_calls;
    require(map_resource(0,D3D11_MAP_READ,&out)==E_POINTER&&!out.pData&&!out.RowPitch&&!out.DepthPitch&&abort_calls==before+1,"failed BindMap not aborted cleanly");
    require(!virtual_live&&!shadows&&resources[0].refs==1,"failed BindMap cached or leaked memory");check_cache();
    before=virtual_calls;fail_map=1;
    require(map_resource(0,D3D11_MAP_READ,&out)==DXGI_ERROR_WAS_STILL_DRAWING&&!out.pData&&virtual_calls==before,"native Map failure allocated shadow");
    require(map_resource(0,D3D11_MAP_READ,NULL)==E_POINTER,"null Map output accepted");
    create_resource(2,12288);D3D11_MAPPED_SUBRESOURCE active;
    require(SUCCEEDED(map_resource(2,D3D11_MAP_WRITE_DISCARD,&active)),"active OOM-test Map failed");memset(active.pData,0x7d,12288);
    require(SUCCEEDED(map_resource(0,D3D11_MAP_WRITE_DISCARD,&out)),"native OOM cache warmup failed");unmap_resource(0);
    fail_map=1;before=map_requests;LONG before_virtual=virtual_calls;
    require(map_resource(1,D3D11_MAP_READ,&out)==DXGI_ERROR_WAS_STILL_DRAWING&&map_requests==before+1&&virtual_calls==before_virtual,"other failed native Map status was retried");
#ifdef TEST_SHADOW_CACHE
    require(idle_shadow_count==1,"other failed native Map status drained idle cache");
#endif
    fail_map_oom=1;before=map_requests;LONG before_abort=abort_calls;result=map_resource(1,D3D11_MAP_READ,&out);
#ifdef TEST_SHADOW_CACHE
    require(SUCCEEDED(result)&&map_requests==before+2&&idle_shadow_count==0,"native Map HRESULT OOM did not drain idle cache and retry once");unmap_resource(1);
#else
    require(result==E_OUTOFMEMORY&&!out.pData&&map_requests==before+1,"v7 native Map OOM handling changed");
#endif
    require(abort_calls==before_abort,"failed native Map incorrectly aborted absent map");fail_map_oom=0;
    require(SUCCEEDED(map_resource(0,D3D11_MAP_WRITE_DISCARD,&out)),"persistent native OOM warmup failed");unmap_resource(0);
    fail_map_oom=2;oom_as_fault=1;before=map_requests;
    require(map_resource(1,D3D11_MAP_READ,&out)==E_OUTOFMEMORY&&!out.pData&&!out.RowPitch&&!out.DepthPitch,"persistent native Map OOM not returned");
#ifdef TEST_SHADOW_CACHE
    require(map_requests==before+2&&!idle_shadows,"persistent native Map OOM retry was not bounded");
#else
    require(map_requests==before+1,"v7 native Map fault OOM retried");
#endif
    fail_map_oom=0;oom_as_fault=0;require(abort_calls==before_abort,"native OOM retry aborted absent map");
    fail_map_oom=1;before=map_requests;
    require(map_resource(1,D3D11_MAP_READ,&out)==E_OUTOFMEMORY&&map_requests==before+1,"native Map OOM retried without any idle memory to reclaim");fail_map_oom=0;
    for(UINT i=0;i<12288;++i)require(((unsigned char*)active.pData)[i]==0x7d,"native OOM cache drain changed active mapping");
    unmap_resource(2);destroy_resource(2);
    destroy_resource(0);destroy_resource(1);drain_cache();
}
void WINAPI start(void){
    InitializeCriticalSection(&proxy_lock);InitializeCriticalSection(&native_lock);unix_call=native_call;unix_handle=1;context_refs=1;
    require(sizeof(void*)==4,"test requires PE32");context=proxy_wrap(0x10001,SD_COM_IF_ID3D11DeviceContext);require(context!=NULL,"context proxy failed");
    mode_tests();overlap_tests();concurrency_tests();capacity_tests();failure_tests();
    create_resource(0,4*1024*1024);create_resource(1,5*1024*1024);
    LONG begin_virtual=virtual_calls,begin_heap=heap_calls;LARGE_INTEGER begin,end,frequency;QueryPerformanceFrequency(&frequency);QueryPerformanceCounter(&begin);
    for(UINT frame=0;frame<BENCH_FRAMES;++frame){
        D3D11_MAPPED_SUBRESOURCE a,b;require(SUCCEEDED(map_resource(0,D3D11_MAP_WRITE_DISCARD,&a))&&SUCCEEDED(map_resource(1,D3D11_MAP_WRITE_DISCARD,&b)),"4+5 MiB workload Map failed");
        require(a.pData!=b.pData,"4+5 MiB active mappings alias");memset(a.pData,0x31,64);memset(b.pData,0x42,64);unmap_resource(0);unmap_resource(1);
    }
    QueryPerformanceCounter(&end);LONG benchmark_virtual=virtual_calls-begin_virtual,benchmark_heap=heap_calls-begin_heap;check_cache();
#ifdef TEST_SHADOW_CACHE
    require(benchmark_virtual==2&&benchmark_heap==2&&idle_shadow_bytes==9*1024*1024,"representative workload did not reuse exact allocations");
#else
    require(benchmark_virtual==2*BENCH_FRAMES&&benchmark_heap==2*BENCH_FRAMES,"baseline allocation count unexpected");
#endif
    destroy_resource(0);destroy_resource(1);drain_cache();ID3D11DeviceContext_Release(context);
    require(!proxies&&!shadows&&!context_refs&&!heap_live&&!virtual_live,"guest/native ownership remains after teardown");
    say("{\"status\":\"PASS\",\"checks\":");number(checks);say(",\"frames\":");number(BENCH_FRAMES);
    say(",\"virtual_alloc_calls\":");number(benchmark_virtual);say(",\"heap_alloc_calls\":");number(benchmark_heap);
    say(",\"ticks\":");number(end.QuadPart-begin.QuadPart);say(",\"frequency\":");number(frequency.QuadPart);say(",\"bytes_copied_per_frame\":9437184,\"teardown_live_allocations\":0}\n");ExitProcess(0);
}
