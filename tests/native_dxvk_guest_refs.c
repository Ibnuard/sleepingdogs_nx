/* SPDX-License-Identifier: MIT
 * Actual PE32 proxy code; only the native endpoint is modeled. Test ownership,
 * concurrent publication/last Release, and lock inversion with a native owner.
 */
#include "com_guest.c"
#include "com_methods.h"
static LONG checks,native_counts[65536],call_count,add_count,release_count;
static HANDLE release_entered,release_continue;
static LONG block_release;
static CRITICAL_SECTION model_lock;
static ID3D11Device *device;
static const uint32_t device_token=0x10001,sampler_token=0x10100;
static void say(const char *s){DWORD n;WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),s,(DWORD)strlen(s),&n,NULL);}
static void number(uint32_t value){char s[11],*end=s+sizeof(s),*at=end;do{*--at=(char)('0'+value%10);value/=10;}while(value);DWORD n;WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),at,(DWORD)(end-at),&n,NULL);}
static void require(int ok,const char *why){InterlockedIncrement(&checks);if(!ok){say(why);say("\n");ExitProcess(1);}}
static void give(uint32_t address,uint32_t token){if(address){InterlockedIncrement(&native_counts[token&65535]);*(uint32_t*)(uintptr_t)address=token;}}
static LONG WINAPI native_call(uint64_t handle,unsigned index,void *request){
    (void)handle;(void)index;struct sd_com_packet *p=request;
    InterlockedIncrement(&call_count);p->fault=p->ret=p->aux=0;
    if(p->method==2&&InterlockedCompareExchange(&block_release,0,1)==1){
        SetEvent(release_entered);require(WaitForSingleObject(release_continue,15000)==WAIT_OBJECT_0,"native release unblock timeout");
    }
    EnterCriticalSection(&model_lock);
    if(!p->interface_id&&p->method==SD_COM_CREATE_DEVICE)give(p->args[7],device_token);
    else if(p->method==1){InterlockedIncrement(&add_count);p->ret=++native_counts[p->object&65535];}
    else if(p->method==2){InterlockedIncrement(&release_count);p->ret=--native_counts[p->object&65535];require((LONG)p->ret>=0,"native reference underflow");}
    else if(p->method==0){require(native_counts[p->object&65535]>0,"QI after native destruction");give(p->args[1],p->object);}
    else if(p->interface_id==SD_COM_IF_ID3D11Device&&p->method==SD_COM_M_ID3D11Device_CreateSamplerState)give(p->args[1],sampler_token);
    else if(p->interface_id==SD_COM_IF_ID3D11SamplerState&&p->method==SD_COM_M_ID3D11SamplerState_GetDesc){
        require(native_counts[p->object&65535]>0,"method after native destruction");
        D3D11_SAMPLER_DESC *out=(void*)(uintptr_t)p->args[0];memset(out,0,sizeof(*out));out->MaxAnisotropy=13;
    }else require(0,"unexpected native call");
    LeaveCriticalSection(&model_lock);return 0;
}
static ID3D11SamplerState *create(void){ID3D11SamplerState *p=NULL;D3D11_SAMPLER_DESC desc={0};require(SUCCEEDED(ID3D11Device_CreateSamplerState(device,&desc,&p))&&p,"create sampler failed");return p;}
static void usable(ID3D11SamplerState *p){D3D11_SAMPLER_DESC desc={0};ID3D11SamplerState_GetDesc(p,&desc);require(desc.MaxAnisotropy==13,"surviving reference is unusable");}
static void ownership(void){
    ID3D11SamplerState *p=create();LONG before=call_count;
    for(UINT i=0;i<100000;++i){require(ID3D11SamplerState_AddRef(p)==2,"wrong AddRef count");require(ID3D11SamplerState_Release(p)==1,"wrong nonfinal Release count");}
#ifdef TEST_LOCAL_REFS
    require(call_count==before,"local reference pair entered native");
#else
    require(call_count-before==200000,"baseline negative control changed");
#endif
    usable(p);
    /* Native outputs and local ownership can be released in either order. */
    for(UINT mode=0;mode<3;++mode){
        ID3D11SamplerState_AddRef(p);ID3D11SamplerState_AddRef(p);
        ID3D11SamplerState *a=create(),*b=create();require(a==p&&b==p,"duplicate output lost identity");
        if(mode==1){ID3D11SamplerState_Release(a);ID3D11SamplerState_Release(b);}
        ID3D11SamplerState_Release(p);ID3D11SamplerState_Release(p);
        if(mode!=1){ID3D11SamplerState_Release(b);ID3D11SamplerState_Release(a);}
        require(((struct proxy*)p)->refs==1&&native_counts[sampler_token&65535]==1,"mixed credits did not return to one anchor");usable(p);
    }
    /* IUnknown alias has independent native ownership, canonical per kind. */
    IUnknown *a=NULL,*b=NULL;require(SUCCEEDED(ID3D11SamplerState_QueryInterface(p,&IID_IUnknown,(void**)&a)),"QI failed");
    require(SUCCEEDED(ID3D11SamplerState_QueryInterface(p,&IID_IUnknown,(void**)&b))&&a==b,"IUnknown identity changed");
    IUnknown_AddRef(a);IUnknown_Release(b);IUnknown_Release(a);IUnknown_Release(a);
    ID3D11SamplerState_Release(p);require(!native_counts[sampler_token&65535],"final release leaked native reference");
}
static ID3D11SamplerState *anchor;
static DWORD WINAPI churn(void *arg){
    (void)arg;
    for(UINT i=0;i<20000;++i){
        ID3D11SamplerState_AddRef(anchor);
        ID3D11SamplerState *p=create();require(p==anchor,"concurrent publication lost identity");
        ID3D11SamplerState_Release(anchor);ID3D11SamplerState_Release(p);
    }
    return 0;
}
static DWORD WINAPI drop(void *arg){ID3D11SamplerState *p=arg;ID3D11SamplerState_Release(p);return 0;}
static DWORD WINAPI make_and_drop(void *arg){(void)arg;ID3D11SamplerState *p=create();usable(p);ID3D11SamplerState_Release(p);return 0;}
static void races(void){
    anchor=create();HANDLE workers[8];
    for(UINT i=0;i<8;++i){workers[i]=CreateThread(NULL,0,churn,NULL,0,NULL);require(workers[i]!=NULL,"thread create failed");}
    require(WaitForMultipleObjects(8,workers,TRUE,60000)==WAIT_OBJECT_0,"churn timed out");
    for(UINT i=0;i<8;++i)CloseHandle(workers[i]);
    require(((struct proxy*)anchor)->refs==1&&native_counts[sampler_token&65535]==1,"concurrent credits leaked");
    /* A native Release can block behind Multithread::Enter. Output publication
     * by its owner must not wait on a guest lock held by the blocked releaser. */
    release_entered=CreateEventA(NULL,TRUE,FALSE,NULL);release_continue=CreateEventA(NULL,TRUE,FALSE,NULL);
    require(release_entered&&release_continue,"events failed");
    block_release=1;HANDLE releasing=CreateThread(NULL,0,drop,anchor,0,NULL);require(releasing!=NULL,"release thread failed");
    require(WaitForSingleObject(release_entered,15000)==WAIT_OBJECT_0,"no blocked release");
    HANDLE publishing=CreateThread(NULL,0,make_and_drop,NULL,0,NULL);require(publishing!=NULL,"publish thread failed");
    require(WaitForSingleObject(publishing,15000)==WAIT_OBJECT_0,"guest lock held across native release");
    SetEvent(release_continue);require(WaitForSingleObject(releasing,15000)==WAIT_OBJECT_0,"release stalled");
    CloseHandle(publishing);CloseHandle(releasing);CloseHandle(release_entered);CloseHandle(release_continue);
    require(!native_counts[sampler_token&65535],"blocked release race leaked native ownership");
}
void WINAPI start(void){
    InitializeCriticalSection(&proxy_lock);InitializeCriticalSection(&model_lock);unix_call=native_call;unix_handle=1;
    require(SUCCEEDED(SdCreateDevice(NULL,D3D_DRIVER_TYPE_HARDWARE,NULL,0,NULL,0,7,&device,NULL,NULL)),"device setup failed");
    ownership();races();ID3D11Device_Release(device);require(!proxies,"proxies remain");
    for(UINT i=0;i<65536;++i)require(!native_counts[i],"native reference remains");
    say("{\"status\":\"PASS\",\"checks\":");number(checks);say(",\"native_calls\":");number(call_count);
    say(",\"native_addrefs\":");number(add_count);say(",\"native_releases\":");number(release_count);
#ifdef TEST_LOCAL_REFS
    uint32_t refs[5];require(SdComRefStats(refs)==0&&refs[1]==refs[2],"balanced local refs diverged at teardown");
    require(!add_count,"native AddRef escaped");
    say(",\"local_addrefs\":");number(refs[1]);say(",\"local_releases\":");number(refs[2]);
#endif
    say("}\n");ExitProcess(0);
}
