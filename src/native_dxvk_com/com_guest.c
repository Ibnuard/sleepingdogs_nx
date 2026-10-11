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
    struct proxy *next;
};
struct mapped_shadow {
    uint32_t id;
    void *memory, *context, *resource;
    struct mapped_shadow *next;
};
typedef LONG (WINAPI *query_memory_fn)(HANDLE,const void*,int,void*,SIZE_T,SIZE_T*);
typedef LONG (WINAPI *unix_call_fn)(uint64_t,unsigned,void*);
static HINSTANCE module;
static uint64_t unix_handle;
static unix_call_fn unix_call;
static CRITICAL_SECTION proxy_lock;
static struct proxy *proxies;
static struct mapped_shadow *shadows;
#define PROXY_MAGIC 0x53444334u

static uint32_t guest_address(const void *p) { return (uint32_t)(uintptr_t)p; }
static uint32_t float_bits(float f) { union {float f;uint32_t u;} x={.f=f};return x.u; }
static float bits_float(uint32_t u) { union {float f;uint32_t u;} x={.u=u};return x.f; }
static UINT safe_array_count(UINT n) { return n==UINT32_MAX ? 0 : n<=SD_COM_MAX_ARRAY ? n : 0; }
static const void *proxy_vtable(uint32_t interface_id);
static uint32_t proxy_iid(REFIID iid);
static void *proxy_wrap(uint32_t token,uint32_t interface_id);

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
    unix_call_fn call;
    EnterCriticalSection(&proxy_lock);
    if(!unix_call) {
        HMODULE ntdll=GetModuleHandleA("ntdll.dll");
        query_memory_fn query=(query_memory_fn)GetProcAddress(ntdll,"NtQueryVirtualMemory");
        unix_call_fn entry=(unix_call_fn)GetProcAddress(ntdll,"__wine_unix_call");
        LONG status=query && entry ? query((HANDLE)(intptr_t)-1,module,1000,&unix_handle,sizeof(unix_handle),NULL) : (LONG)0xc0000139u;
        if(status<0 || !unix_handle){LeaveCriticalSection(&proxy_lock);return status<0?status:(LONG)0xc0000008u;}
        unix_call=entry;
    }
    call=unix_call;
    LeaveCriticalSection(&proxy_lock);
    LONG status=call(unix_handle,0,packet);
    if(status<0)return status;
    return (LONG)packet->fault;
}
static HRESULT proxy_query(void *object,REFIID iid,void **output) {
    if(!output)return E_POINTER;
    *output=NULL;
    uint32_t kind=proxy_iid(iid);
    struct proxy *self=object;
    struct sd_com_packet p={SD_COM_ABI,proxy_token(object),self->interface_id,0};
    p.args[0]=guest_address(iid);p.args[1]=guest_address(output);
    LONG status=proxy_call(&p);
    if(status<0)return status;
    if(SUCCEEDED((HRESULT)p.ret)) {
        uint32_t token=*(uint32_t*)output;
        *output=proxy_wrap(token,kind);
        if(token && !*output)return E_OUTOFMEMORY;
    }
    return (HRESULT)p.ret;
}
static ULONG proxy_addref(void *object) {
    struct proxy *self=object;
    struct sd_com_packet p={SD_COM_ABI,proxy_token(object),self->interface_id,1};
    LONG status=proxy_call(&p);
    if(status<0){proxy_fatal(status);return 0;}
    ULONG refs=(ULONG)InterlockedIncrement(&self->refs);
    return refs;
}
static ULONG proxy_release(void *object) {
    struct proxy *self=object;
    struct sd_com_packet p={SD_COM_ABI,proxy_token(object),self->interface_id,2};
    LONG status=proxy_call(&p);
    if(status<0){proxy_fatal(status);return 0;}
    /* Never hold the guest lock while entering native DXVK: another thread
     * can be waiting in the bridge while the caller owns Multithread::Enter. */
    EnterCriticalSection(&proxy_lock);
    ULONG refs=(ULONG)InterlockedDecrement(&self->refs);
    if(!refs) {
        struct proxy **at=&proxies;
        while(*at && *at!=self)at=&(*at)->next;
        if(*at)*at=self->next;
        self->magic=0;
        HeapFree(GetProcessHeap(),0,self);
    }
    LeaveCriticalSection(&proxy_lock);
    return refs;
}
static void *proxy_wrap(uint32_t token,uint32_t kind) {
    if(!token)return NULL;
    const void *vtbl=proxy_vtable(kind);
    if(!vtbl){proxy_fatal(E_NOINTERFACE);return NULL;}
    EnterCriticalSection(&proxy_lock);
    for(struct proxy *p=proxies;p;p=p->next) {
        if(p->token==token && p->interface_id==kind) {
            InterlockedIncrement(&p->refs);LeaveCriticalSection(&proxy_lock);return p;
        }
    }
    struct proxy *p=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(*p));
    if(p){p->vtbl=vtbl;p->magic=PROXY_MAGIC;p->token=token;p->interface_id=kind;p->refs=1;p->next=proxies;proxies=p;}
    LeaveCriticalSection(&proxy_lock);
    if(!p) {
        /* Balance the native reference even if creating its x86 proxy fails. */
        struct sd_com_packet release={SD_COM_ABI,token,kind,2};proxy_call(&release);
    }
    return p;
}
static HRESULT proxy_map(void *context,void *resource,UINT subresource,D3D11_MAP type,UINT flags,D3D11_MAPPED_SUBRESOURCE *output) {
    if(!output)return E_POINTER;
    memset(output,0,sizeof(*output));
    struct proxy *self=context;
    struct sd_com_packet p={SD_COM_ABI,proxy_token(context),self->interface_id,14};
    p.args[0]=proxy_token(resource);p.args[1]=subresource;p.args[2]=type;p.args[3]=flags;p.args[4]=guest_address(output);
    LONG status=proxy_call(&p);
    if(status<0)return status;
    if(FAILED((HRESULT)p.ret))return (HRESULT)p.ret;
    uint32_t id=p.aux,bytes=p.high[0];
    struct mapped_shadow *shadow=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(*shadow));
    if(shadow)shadow->memory=VirtualAlloc(NULL,bytes,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    struct sd_com_packet bind={SD_COM_ABI,0,0,SD_COM_BIND_MAP};
    bind.args[0]=id;bind.args[1]=shadow?guest_address(shadow->memory):0;bind.args[2]=bytes;
    status=shadow && shadow->memory ? proxy_call(&bind) : E_OUTOFMEMORY;
    if(status<0 || FAILED((HRESULT)bind.ret)) {
        struct sd_com_packet abort={SD_COM_ABI,0,0,SD_COM_ABORT_MAP};abort.args[0]=id;proxy_call(&abort);
        if(shadow){if(shadow->memory)VirtualFree(shadow->memory,0,MEM_RELEASE);HeapFree(GetProcessHeap(),0,shadow);}
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
    if(shadow){VirtualFree(shadow->memory,0,MEM_RELEASE);proxy_release(shadow->resource);proxy_release(shadow->context);HeapFree(GetProcessHeap(),0,shadow);}
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
    p.args[7]=guest_address(device);p.args[8]=guest_address(actual);p.args[9]=guest_address(context);
    LONG status=proxy_call(&p);
    if(status<0)return status;
    if(SUCCEEDED((HRESULT)p.ret)) {
        if(device)*device=proxy_wrap(*(uint32_t*)device,SD_COM_IF_ID3D11Device);
        if(context)*context=proxy_wrap(*(uint32_t*)context,SD_COM_IF_ID3D11DeviceContext);
        if((device&&!*device)||(context&&!*context)) {
            if(device&&*device){proxy_release(*device);*device=NULL;}
            if(context&&*context){proxy_release(*context);*context=NULL;}
            return E_OUTOFMEMORY;
        }
    }
    return (HRESULT)p.ret;
}
__declspec(dllexport) HRESULT WINAPI SdCreateFactory(UINT flags,REFIID iid,void **factory) {
    if(!factory)return E_POINTER;*factory=NULL;
    uint32_t kind=proxy_iid(iid);
    struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_CREATE_FACTORY};
    p.args[0]=flags;p.args[1]=guest_address(iid);p.args[2]=guest_address(factory);
    LONG status=proxy_call(&p);if(status<0)return status;
    if(SUCCEEDED((HRESULT)p.ret))*factory=proxy_wrap(*(uint32_t*)factory,kind);
    if(SUCCEEDED((HRESULT)p.ret)&&!*factory)return E_OUTOFMEMORY;
    return (HRESULT)p.ret;
}
__declspec(dllexport) LONG WINAPI SdComStats(uint32_t *stats) {
    struct sd_com_packet p={SD_COM_ABI,0,0,SD_COM_STATS};p.args[0]=guest_address(stats);return proxy_call(&p);
}
BOOL WINAPI DllMain(HINSTANCE self,DWORD reason,void *reserved) {
    (void)reserved;
    if(reason==DLL_PROCESS_ATTACH){module=self;InitializeCriticalSection(&proxy_lock);DisableThreadLibraryCalls(self);}
    /* Native process-exit cleanup runs before Wine tears down guest mappings. */
    return TRUE;
}
