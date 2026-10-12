/* SPDX-License-Identifier: MIT; original PE32 COM objects for native DXVK. */
#define WIN32_LEAN_AND_MEAN
#define COBJMACROS
#define CINTERFACE
#include <windows.h>
#include <d3d11.h>
#include <d3d10.h>
#include <dxgi.h>
#include <stdint.h>
#include "com_protocol.h"

/* Freestanding PE: keep CRT state and C++ runtime out of the x86 bridge. */
void *memcpy(void *dst,const void *src,size_t n) { unsigned char *d=dst;const unsigned char *s=src;while(n--)*d++=*s++;return dst; }
void *memset(void *dst,int value,size_t n) { unsigned char *d=dst;while(n--)*d++=(unsigned char)value;return dst; }
int memcmp(const void *a,const void *b,size_t n) { const unsigned char *x=a,*y=b;while(n--){if(*x!=*y)return *x-*y;++x;++y;}return 0; }
size_t strlen(const char *s) { size_t n=0;while(s[n])++n;return n; }

struct proxy {
    const void *vtbl;
    uint32_t magic, token, interface_id;
    LONG refs;
    /* Protected by proxy_lock. Each credit owns one native reference; local
     * AddRef does not need another. Outputs contribute both a ref and a credit.
     * Keep 1 <= native_refs <= refs until final Release. */
    uint32_t native_refs;
    struct proxy *next, **previous;
    struct proxy *hash_next, **hash_previous;
};
struct mapped_shadow {
    uint32_t id, bytes;
    void *memory, *context, *resource;
    struct mapped_shadow *next;
};
typedef LONG (WINAPI *query_memory_fn)(HANDLE,const void*,int,void*,SIZE_T,SIZE_T*);
typedef LONG (WINAPI *unix_call_fn)(uint64_t,unsigned,void*);
static HINSTANCE module;
struct unix_endpoint { uint64_t handle;unix_call_fn call; };
static struct unix_endpoint endpoint_storage;
static struct unix_endpoint *published_endpoint;
/* Names also used by the modeled-endpoint regression fixtures. */
#define unix_handle endpoint_storage.handle
#define unix_call endpoint_storage.call
static CRITICAL_SECTION proxy_lock;
static struct proxy *proxies;
/* Keep every generation bit in the key. Fixed storage avoids resize failures
 * while intrusive backlinks remove either list entry without a linear scan. */
#define PROXY_BUCKET_COUNT 4096u
static struct proxy *proxy_buckets[PROXY_BUCKET_COUNT];
static struct mapped_shadow *shadows;
/* Idle entries own memory only, never a context/resource or an active Map.
 * Bound retention independently of the number or sizes of active mappings. */
#define SHADOW_CACHE_BYTES (16u*1024u*1024u)
#define SHADOW_CACHE_ENTRIES 4u
static struct mapped_shadow *idle_shadows;
static uint32_t idle_shadow_bytes,idle_shadow_count;
#define PROXY_MAGIC 0x53444334u

/* Separate counters, not a hot-path clock or native call. Snapshots taken while
 * other threads run are approximate; their deltas converge after quiescence. */
static LONG local_addrefs,local_releases,native_releases,output_references;
static void proxy_ref_report(int force);

static uint32_t proxy_bucket(uint32_t token,uint32_t kind) {
    uint32_t key=token*0x9e3779b9u ^ kind*0x85ebca6bu;
    key^=key>>16;
    return key&(PROXY_BUCKET_COUNT-1);
}

static uint32_t guest_address(const void *p) { return (uint32_t)(uintptr_t)p; }
static uint32_t float_bits(float f) { union {float f;uint32_t u;} x={.f=f};return x.u; }
static float bits_float(uint32_t u) { union {float f;uint32_t u;} x={.u=u};return x.f; }
static UINT safe_array_count(UINT n) { return n==UINT32_MAX ? 0 : n<=SD_COM_MAX_ARRAY ? n : 0; }
static const void *proxy_vtable(uint32_t interface_id);
static uint32_t proxy_iid(REFIID iid);
static void *proxy_wrap(uint32_t token,uint32_t interface_id);
static ULONG proxy_release(void *object);

static void proxy_fatal(LONG error) {
    ULONG_PTR detail=(ULONG_PTR)(uint32_t)error;
    RaiseException(0xe0534e44u, EXCEPTION_NONCONTINUABLE, 1, &detail);
}
static uint32_t proxy_token(const void *object) {
    if(!object)return 0;
    const struct proxy *p=object;
    if(p->magic!=PROXY_MAGIC){proxy_fatal(E_INVALIDARG);return 0;}
    return p->token;
}
static LONG proxy_call(struct sd_com_packet *packet) {
    /* Publish one immutable descriptor, including the complete 64-bit handle.
     * The one-time locked exchange orders its initialization even with FEX's
     * optional ordinary-store TSO disabled. Hot loads of handle/function stay
     * address-dependent on the published pointer (also checked in PE codegen).
     * Keep proxy/object locks elsewhere; never hold this lock across DXVK. */
    struct unix_endpoint *endpoint=__atomic_load_n(&published_endpoint,__ATOMIC_ACQUIRE);
    if(!endpoint) {
        EnterCriticalSection(&proxy_lock);
        if(!unix_call) {
            HMODULE ntdll=GetModuleHandleA("ntdll.dll");
            query_memory_fn query=(query_memory_fn)GetProcAddress(ntdll,"NtQueryVirtualMemory");
            unix_call_fn entry=(unix_call_fn)GetProcAddress(ntdll,"__wine_unix_call");
            uint64_t handle=0;
            LONG status=query && entry ? query((HANDLE)(intptr_t)-1,module,1000,&handle,sizeof(handle),NULL) : (LONG)0xc0000139u;
            if(status<0 || !handle){LeaveCriticalSection(&proxy_lock);return status<0?status:(LONG)0xc0000008u;}
            unix_handle=handle;
            unix_call=entry;
        }
        endpoint=&endpoint_storage;
        __atomic_store_n(&published_endpoint,endpoint,__ATOMIC_SEQ_CST);
        LeaveCriticalSection(&proxy_lock);
    }
    LONG status=endpoint->call(endpoint->handle,0,packet);
    if(status<0)return status;
    if(!packet->fault && packet->interface_id==SD_COM_IF_IDXGISwapChain && packet->method==8 &&
       packet->ret==S_OK && !(packet->args[1]&DXGI_PRESENT_TEST))
        proxy_ref_report(0);
    return (LONG)packet->fault;
}
/* Keep wire handles private until a complete PE32 proxy can be published.
 * A caller-visible COM output must never temporarily contain a native token. */
struct proxy_output {
    uint32_t *tokens;
    UINT capacity,published;
    uint32_t stack[128];
};
static int proxy_output_init(struct proxy_output *out,void *destination,UINT capacity) {
    out->capacity=destination?capacity:0;out->tokens=NULL;out->published=0;
    if(!out->capacity)return 1;
    memset(destination,0,out->capacity*sizeof(void*));
    out->tokens=out->capacity<=128?out->stack:HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,out->capacity*4);
    if(!out->tokens)return 0;
    if(out->capacity<=128)memset(out->tokens,0,out->capacity*4);
    return 1;
}
static void proxy_output_dispose(struct proxy_output *out,uint32_t kind) {
    if(!out->tokens)return;
    for(UINT i=0;i<out->capacity;++i)if(out->tokens[i]) {
        struct sd_com_packet release={SD_COM_ABI,out->tokens[i],kind,2};proxy_call(&release);
    }
    if(out->capacity>128)HeapFree(GetProcessHeap(),0,out->tokens);
    out->tokens=NULL;
}
static int proxy_output_publish(struct proxy_output *out,void *destination,UINT count,uint32_t kind) {
    if(!destination)return 1;
    if(count>out->capacity)count=out->capacity;
    for(UINT i=0;i<count;++i) {
        uint32_t token=out->tokens[i];out->tokens[i]=0;
        void *object=proxy_wrap(token,kind);
        if(token&&!object)return 0; /* proxy_wrap balanced this token's reference */
        memcpy((char*)destination+i*sizeof(void*),&object,sizeof(object));
        ++out->published;
    }
    return 1;
}
static void proxy_output_retract(struct proxy_output *out,void *destination) {
    for(UINT i=0;i<out->published;++i) {
        void *object;memcpy(&object,(char*)destination+i*sizeof(void*),sizeof(object));
        memset((char*)destination+i*sizeof(void*),0,sizeof(object));
        if(object)proxy_release(object);
    }
    out->published=0;
}
static HRESULT proxy_query(void *object,REFIID iid,void **output) {
    if(!output)return E_POINTER;
    *output=NULL;
    uint32_t kind=proxy_iid(iid);
    struct proxy *self=object;
    struct sd_com_packet p={SD_COM_ABI,proxy_token(object),self->interface_id,0};
    struct proxy_output wire;if(!proxy_output_init(&wire,output,1))return E_OUTOFMEMORY;
    p.args[0]=guest_address(iid);p.args[1]=guest_address(wire.tokens);
    LONG status=proxy_call(&p);
    if(status>=0&&SUCCEEDED((HRESULT)p.ret)&&!proxy_output_publish(&wire,output,1,kind))status=E_OUTOFMEMORY;
    proxy_output_dispose(&wire,kind);
    return status<0?status:(HRESULT)p.ret;
}
static ULONG proxy_addref(void *object) {
    struct proxy *self=object;
    proxy_token(object);
    ULONG refs=(ULONG)InterlockedIncrement(&self->refs);
    InterlockedIncrement(&local_addrefs);
    return refs;
}
static ULONG proxy_release(void *object) {
    struct proxy *self=object;
    uint32_t token=proxy_token(object),kind=self->interface_id;
    int release_native=0;
    /* Decide ownership and unlink atomically with output publication. Never
     * enter native while holding this lock: Multithread::Enter may be held by
     * a thread which needs to publish/release another guest proxy. */
    EnterCriticalSection(&proxy_lock);
    ULONG refs=(ULONG)InterlockedDecrement(&self->refs);
    if(self->native_refs>refs){--self->native_refs;release_native=1;}
    if(!refs) {
        *self->previous=self->next;
        if(self->next)self->next->previous=self->previous;
        *self->hash_previous=self->hash_next;
        if(self->hash_next)self->hash_next->hash_previous=self->hash_previous;
        self->magic=0;
        HeapFree(GetProcessHeap(),0,self);
    }
    LeaveCriticalSection(&proxy_lock);
    /* The detached credit stays owned even if a thread wraps the same token
     * after unlink. No access to self is permitted after dropping the lock. */
    if(release_native) {
        struct sd_com_packet p={SD_COM_ABI,token,kind,2};
        InterlockedIncrement(&native_releases);
        LONG status=proxy_call(&p);
        if(status<0){proxy_fatal(status);return 0;}
    } else InterlockedIncrement(&local_releases);
    return refs;
}
static void *proxy_wrap(uint32_t token,uint32_t kind) {
    if(!token)return NULL;
    const void *vtbl=proxy_vtable(kind);
    if(!vtbl){proxy_fatal(E_NOINTERFACE);return NULL;}
    EnterCriticalSection(&proxy_lock);
    struct proxy **bucket=&proxy_buckets[proxy_bucket(token,kind)];
    for(struct proxy *p=*bucket;p;p=p->hash_next) {
        if(p->token==token && p->interface_id==kind) {
            ++p->native_refs;InterlockedIncrement(&p->refs);
            InterlockedIncrement(&output_references);
            LeaveCriticalSection(&proxy_lock);return p;
        }
    }
    struct proxy *p=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(*p));
    if(p){
        p->vtbl=vtbl;p->magic=PROXY_MAGIC;p->token=token;p->interface_id=kind;p->refs=1;p->native_refs=1;
        InterlockedIncrement(&output_references);
        p->next=proxies;p->previous=&proxies;
        if(p->next)p->next->previous=&p->next;
        proxies=p;
        p->hash_next=*bucket;p->hash_previous=bucket;
        if(p->hash_next)p->hash_next->hash_previous=&p->hash_next;
        *bucket=p;
    }
    LeaveCriticalSection(&proxy_lock);
    if(!p) {
        /* Balance the native reference even if creating its x86 proxy fails. */
        struct sd_com_packet release={SD_COM_ABI,token,kind,2};proxy_call(&release);
    }
    return p;
}
static HRESULT proxy_private_get(void *object,uint32_t method,REFGUID guid,UINT *size,void *output) {
    if(!size)return E_POINTER;
    UINT capacity=output?*size:0;
    void *wire=output?HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,capacity?capacity:1):NULL;
    if(output&&!wire)return E_OUTOFMEMORY;
    struct proxy *self=object;
    struct sd_com_packet p={SD_COM_ABI,proxy_token(object),self->interface_id,method};
    p.args[0]=guest_address(guid);p.args[1]=guest_address(size);p.args[2]=guest_address(wire);
    LONG status=proxy_call(&p);
    if(status>=0&&SUCCEEDED((HRESULT)p.ret)&&wire) {
        if(p.aux==SD_COM_PRIVATE_INTERFACE) {
            if(capacity<sizeof(void*)||*size!=sizeof(void*))status=E_INVALIDARG;
            else {
                uint32_t token;memcpy(&token,wire,sizeof(token));
                void *wrapped=proxy_wrap(token,SD_COM_IF_IUnknown);
                if(token&&!wrapped)status=E_OUTOFMEMORY;
                else memcpy(output,&wrapped,sizeof(wrapped));
            }
        } else if(*size<=capacity)memcpy(output,wire,*size);
        else status=E_INVALIDARG;
    }
    if(wire)HeapFree(GetProcessHeap(),0,wire);
    return status<0?status:(HRESULT)p.ret;
}
static void shadow_destroy(struct mapped_shadow *shadow) {
    if(shadow){if(shadow->memory)VirtualFree(shadow->memory,0,MEM_RELEASE);HeapFree(GetProcessHeap(),0,shadow);}
}
static int shadow_cache_clear(void) {
    EnterCriticalSection(&proxy_lock);
    struct mapped_shadow *list=idle_shadows;
    int released=list!=NULL;
    idle_shadows=NULL;idle_shadow_bytes=idle_shadow_count=0;
    LeaveCriticalSection(&proxy_lock);
    while(list){struct mapped_shadow *next=list->next;shadow_destroy(list);list=next;}
    return released;
}
static struct mapped_shadow *shadow_take(uint32_t bytes) {
    struct mapped_shadow *shadow=NULL;
    EnterCriticalSection(&proxy_lock);
    struct mapped_shadow **at=&idle_shadows;
    while(*at&&(*at)->bytes!=bytes)at=&(*at)->next;
    if(*at){shadow=*at;*at=shadow->next;--idle_shadow_count;idle_shadow_bytes-=bytes;shadow->next=NULL;}
    LeaveCriticalSection(&proxy_lock);
    /* BindMap validates the full writable range and copies preserving modes.
     * WRITE_DISCARD contents are undefined, including on an exact-size reuse. */
    if(shadow)return shadow;
    for(unsigned attempt=0;attempt<2;++attempt) {
        shadow=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(*shadow));
        if(shadow)shadow->memory=VirtualAlloc(NULL,bytes,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
        if(shadow&&shadow->memory){shadow->bytes=bytes;return shadow;}
        shadow_destroy(shadow);
        if(!attempt)shadow_cache_clear(); /* Reclaim idle memory before one retry. */
    }
    return NULL;
}
static void shadow_return(struct mapped_shadow *shadow) {
    shadow->id=0;shadow->context=shadow->resource=NULL;shadow->next=NULL;
    if(shadow->bytes>SHADOW_CACHE_BYTES){shadow_destroy(shadow);return;}
    struct mapped_shadow *evicted=NULL;
    EnterCriticalSection(&proxy_lock);
    while(idle_shadows&&(idle_shadow_count>=SHADOW_CACHE_ENTRIES||shadow->bytes>SHADOW_CACHE_BYTES-idle_shadow_bytes)) {
        struct mapped_shadow **oldest=&idle_shadows;
        while((*oldest)->next)oldest=&(*oldest)->next;
        struct mapped_shadow *old=*oldest;*oldest=NULL;
        --idle_shadow_count;idle_shadow_bytes-=old->bytes;old->next=evicted;evicted=old;
    }
    shadow->next=idle_shadows;idle_shadows=shadow;++idle_shadow_count;idle_shadow_bytes+=shadow->bytes;
    LeaveCriticalSection(&proxy_lock);
    while(evicted){struct mapped_shadow *next=evicted->next;shadow_destroy(evicted);evicted=next;}
}
static HRESULT proxy_map(void *context,void *resource,UINT subresource,D3D11_MAP type,UINT flags,D3D11_MAPPED_SUBRESOURCE *output) {
    if(!output)return E_POINTER;
    memset(output,0,sizeof(*output));
    struct proxy *self=context;
    struct sd_com_packet p={SD_COM_ABI,proxy_token(context),self->interface_id,14};
    p.args[0]=proxy_token(resource);p.args[1]=subresource;p.args[2]=type;p.args[3]=flags;p.args[4]=guest_address(output);
    LONG status=proxy_call(&p);
    /* Idle memory must not cause a native Map allocation to fail. The native
     * adapter unwinds failed maps; retry only this exact error, once, and only
     * after freeing cached memory. Active mappings are never reclaimed. */
    if((status==E_OUTOFMEMORY||(status>=0&&(HRESULT)p.ret==E_OUTOFMEMORY))&&shadow_cache_clear())status=proxy_call(&p);
    if(status<0)return status;
    if(FAILED((HRESULT)p.ret))return (HRESULT)p.ret;
    uint32_t id=p.aux,bytes=p.high[0];
    struct mapped_shadow *shadow=shadow_take(bytes);
    struct sd_com_packet bind={SD_COM_ABI,0,0,SD_COM_BIND_MAP};
    bind.args[0]=id;bind.args[1]=shadow?guest_address(shadow->memory):0;bind.args[2]=bytes;
    status=shadow && shadow->memory ? proxy_call(&bind) : E_OUTOFMEMORY;
    if(status<0 || FAILED((HRESULT)bind.ret)) {
        struct sd_com_packet abort={SD_COM_ABI,0,0,SD_COM_ABORT_MAP};abort.args[0]=id;proxy_call(&abort);
        shadow_destroy(shadow);
        memset(output,0,sizeof(*output));return status<0?status:(HRESULT)bind.ret;
    }
    shadow->id=id;shadow->context=context;shadow->resource=resource;
    proxy_addref(context);proxy_addref(resource);
    EnterCriticalSection(&proxy_lock);shadow->next=shadows;shadows=shadow;LeaveCriticalSection(&proxy_lock);
    output->pData=shadow->memory;
    return (HRESULT)p.ret;
}
static void proxy_unmap(void *context,void *resource,UINT subresource) {
    struct proxy *self=context;
    struct sd_com_packet p={SD_COM_ABI,proxy_token(context),self->interface_id,15};
    p.args[0]=proxy_token(resource);p.args[1]=subresource;
    LONG status=proxy_call(&p);
    if(status<0){proxy_fatal(status);return;}
    struct mapped_shadow *shadow=NULL;
    EnterCriticalSection(&proxy_lock);
    struct mapped_shadow **at=&shadows;
    while(*at && (*at)->id!=p.aux)at=&(*at)->next;
    if(*at){shadow=*at;*at=shadow->next;}
    LeaveCriticalSection(&proxy_lock);
    if(shadow){proxy_release(shadow->resource);proxy_release(shadow->context);shadow_return(shadow);}
}
struct interface_guid {uint32_t kind;GUID guid;const char *name;};
static const struct interface_guid known_guids[]={
#include "com_guids.inc"
};
static uint32_t proxy_iid(REFIID iid) {
    if(!iid)return 0;
    for(UINT i=0;i<sizeof(known_guids)/sizeof(known_guids[0]);++i)
        if(!memcmp(iid,&known_guids[i].guid,sizeof(GUID)))return known_guids[i].kind;
    return 0;
}
#include "com_guest_vtables.inc"

__declspec(dllexport) HRESULT WINAPI SdCreateDevice(IDXGIAdapter *adapter,D3D_DRIVER_TYPE type,HMODULE software,UINT flags,
    const D3D_FEATURE_LEVEL *levels,UINT count,UINT sdk,ID3D11Device **device,D3D_FEATURE_LEVEL *actual,ID3D11DeviceContext **context) {
    if(device)*device=NULL;if(context)*context=NULL;
    struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_CREATE_DEVICE};
    p.args[0]=proxy_token(adapter);p.args[1]=type;p.args[2]=guest_address(software);p.args[3]=flags;
    p.args[4]=guest_address(levels);p.args[5]=count;p.args[6]=sdk;
    struct proxy_output wd,wc;
    if(!proxy_output_init(&wd,device,1))return E_OUTOFMEMORY;
    if(!proxy_output_init(&wc,context,1)){proxy_output_dispose(&wd,SD_COM_IF_ID3D11Device);return E_OUTOFMEMORY;}
    p.args[7]=guest_address(wd.tokens);p.args[8]=guest_address(actual);p.args[9]=guest_address(wc.tokens);
    LONG status=proxy_call(&p);
    if(status>=0&&SUCCEEDED((HRESULT)p.ret)) {
        if(!proxy_output_publish(&wd,device,1,SD_COM_IF_ID3D11Device)||
           !proxy_output_publish(&wc,context,1,SD_COM_IF_ID3D11DeviceContext))status=E_OUTOFMEMORY;
    }
    if(status<0||FAILED((HRESULT)p.ret)){proxy_output_retract(&wd,device);proxy_output_retract(&wc,context);}
    proxy_output_dispose(&wd,SD_COM_IF_ID3D11Device);proxy_output_dispose(&wc,SD_COM_IF_ID3D11DeviceContext);
    return status<0?status:(HRESULT)p.ret;
}
__declspec(dllexport) HRESULT WINAPI SdCreateFactory(UINT flags,REFIID iid,void **factory) {
    if(!factory)return E_POINTER;*factory=NULL;
    uint32_t kind=proxy_iid(iid);
    struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_CREATE_FACTORY};
    struct proxy_output wire;if(!proxy_output_init(&wire,factory,1))return E_OUTOFMEMORY;
    p.args[0]=flags;p.args[1]=guest_address(iid);p.args[2]=guest_address(wire.tokens);
    LONG status=proxy_call(&p);
    if(status>=0&&SUCCEEDED((HRESULT)p.ret)&&!proxy_output_publish(&wire,factory,1,kind))status=E_OUTOFMEMORY;
    proxy_output_dispose(&wire,kind);
    return status<0?status:(HRESULT)p.ret;
}
__declspec(dllexport) LONG WINAPI SdComStats(uint32_t *stats) {
    struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_STATS};p.args[0]=guest_address(stats);
    LONG status=proxy_call(&p);proxy_ref_report(1);return status;
}
/* A guest-only diagnostic export: no native protocol or NRO change. */
__declspec(dllexport) LONG WINAPI SdComRefStats(uint32_t *stats) {
    if(!stats)return E_POINTER;
    stats[0]=1;
    stats[1]=(uint32_t)InterlockedCompareExchange(&local_addrefs,0,0);
    stats[2]=(uint32_t)InterlockedCompareExchange(&local_releases,0,0);
    stats[3]=(uint32_t)InterlockedCompareExchange(&native_releases,0,0);
    stats[4]=(uint32_t)InterlockedCompareExchange(&output_references,0,0);
    return 0;
}
static void ref_text(char **at,const char *s){while(*s)*(*at)++=*s++;}
static void ref_number(char **at,uint32_t value){char digits[10];unsigned n=0;
    do{digits[n++]=(char)('0'+value%10);value/=10;}while(value);while(n)*(*at)++=digits[--n];}
static void proxy_ref_report(int force) {
    static LONG present_count,reporting;
    static int opened;
    static HANDLE file=INVALID_HANDLE_VALUE;
    uint32_t presents=force?(uint32_t)InterlockedCompareExchange(&present_count,0,0):(uint32_t)InterlockedIncrement(&present_count);
    if(!force&&presents!=1&&presents%600)return;
    if(InterlockedCompareExchange(&reporting,1,0))return;
    /* One short buffered line per 600 Presents. No FlushFileBuffers per frame.
     * Never called under proxy_lock or from DllMain's loader lock. */
#ifndef SD_COM_REF_LOG_PATH
#define SD_COM_REF_LOG_PATH "C:\\native-dxvk-ref-v1.log"
#endif
    if(!opened){opened=1;file=CreateFileA(SD_COM_REF_LOG_PATH,GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);}
    if(file!=INVALID_HANDLE_VALUE){
        uint32_t stats[5];SdComRefStats(stats);char line[384],*at=line;DWORD written;
        ref_text(&at,"[SD-NDX-REF] v1 presents=");ref_number(&at,presents);
        ref_text(&at," local_addrefs=");ref_number(&at,stats[1]);
        ref_text(&at," local_releases=");ref_number(&at,stats[2]);
        ref_text(&at," native_releases=");ref_number(&at,stats[3]);
        ref_text(&at," output_refs=");ref_number(&at,stats[4]);
        ref_text(&at,"; local calls skip FEX/Wine/native transport\r\n");
        WriteFile(file,line,(DWORD)(at-line),&written,NULL);
    }
    InterlockedExchange(&reporting,0);
}
BOOL WINAPI DllMain(HINSTANCE self,DWORD reason,void *reserved) {
    (void)reserved;
    if(reason==DLL_PROCESS_ATTACH){module=self;InitializeCriticalSection(&proxy_lock);DisableThreadLibraryCalls(self);}
    /* Native process-exit cleanup runs before Wine tears down guest mappings. */
    return TRUE;
}
