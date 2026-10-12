/* SPDX-License-Identifier: MIT
 * Execute the real PE32 proxy on Windows; model only the Unix/native endpoint.
 * Observing caller storage inside that endpoint reproduces its publication gap.
 */
#include "com_guest.c"
#include "com_methods.h"
static unsigned checks,exposures,setters;
static LONG references[65536];
static void **watch;
static UINT watch_count;
static int fail_sampler;
static const uint32_t sampler_token=0x1119e,device_token=0x10004,context_token=0x10005,factory_token=0x10001;
static void say(const char *s){DWORD n;WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),s,(DWORD)strlen(s),&n,NULL);}
static void require(int good,const char *message){++checks;if(!good){say(message);say("\n");ExitProcess(1);}}
static void give(uint32_t address,uint32_t token){if(address){*(uint32_t*)(uintptr_t)address=token;if(token)++references[token&65535];}}
static LONG WINAPI native_call(uint64_t handle,unsigned index,void *request) {
    (void)handle;(void)index;struct sd_com_packet *p=request;p->ret=p->fault=p->aux=0;
    if(!p->interface_id) {
        if(p->method==SD_COM_CREATE_DEVICE){give(p->args[7],device_token);give(p->args[9],context_token);}
        else if(p->method==SD_COM_CREATE_FACTORY)give(p->args[2],factory_token);
        else require(0,"unexpected global method");
    } else if(p->method==0)give(p->args[1],p->object);
    else if(p->method==1)++references[p->object&65535];
    else if(p->method==2)--references[p->object&65535];
    else if(p->interface_id==SD_COM_IF_ID3D11Device&&p->method==SD_COM_M_ID3D11Device_CreateSamplerState)give(p->args[1],sampler_token);
    else if(p->interface_id==SD_COM_IF_ID3D11DeviceContext) {
        if(p->method==SD_COM_M_ID3D11DeviceContext_PSGetSamplers) {
            for(UINT i=0;i<p->args[1];++i)if(p->args[2])give(p->args[2]+4*i,i%3?sampler_token:0);
        } else if(p->method==SD_COM_M_ID3D11DeviceContext_PSSetSamplers) {
            const uint32_t *tokens=(const uint32_t*)(uintptr_t)p->args[2];
            for(UINT i=0;i<p->args[1];++i)require(tokens[i]==(i%3?sampler_token:0),"sampler setter did not receive tokens");
            ++setters;
        } else if(p->method==SD_COM_M_ID3D11DeviceContext_OMGetRenderTargets) {
            if(p->args[1])for(UINT i=0;i<p->args[0];++i)give(p->args[1]+4*i,0);
            give(p->args[2],0); /* DSV is scalar even for zero or eight RTVs. */
        } else require(0,"unexpected context method");
    } else if(p->interface_id==SD_COM_IF_ID3D11SamplerState&&p->method==SD_COM_M_ID3D11SamplerState_GetPrivateData) {
        UINT *size=(UINT*)(uintptr_t)p->args[1];
        if(p->args[2]&&*size>=4){give(p->args[2],sampler_token);p->aux=SD_COM_PRIVATE_INTERFACE;}
        *size=4;
    } else require(0,"unexpected interface method");
    if(fail_sampler&&p->interface_id==SD_COM_IF_ID3D11Device&&p->method==SD_COM_M_ID3D11Device_CreateSamplerState)p->fault=E_INVALIDARG;
    for(UINT i=0;i<watch_count;++i)if(watch[i]&&(uintptr_t)watch[i]<=0x1ffff)++exposures;
    return 0;
}
static void publication_test(void) {
    ID3D11Device *device=NULL;ID3D11DeviceContext *context=NULL;IDXGIFactory1 *factory=NULL;
    watch=(void**)&device;watch_count=1;
    require(SUCCEEDED(SdCreateDevice(NULL,D3D_DRIVER_TYPE_HARDWARE,NULL,0,NULL,0,7,&device,NULL,&context)),"create device failed");
    watch=(void**)&factory;
    require(SUCCEEDED(SdCreateFactory(0,&IID_IDXGIFactory1,(void**)&factory)),"create factory failed");
    ID3D11SamplerState *sampler=NULL;D3D11_SAMPLER_DESC desc={0};
    watch=(void**)&sampler;
    require(SUCCEEDED(ID3D11Device_CreateSamplerState(device,&desc,&sampler)),"create sampler failed");
    IUnknown *identity=NULL;watch=(void**)&identity;
    require(SUCCEEDED(ID3D11SamplerState_QueryInterface(sampler,&IID_IUnknown,(void**)&identity)),"QI failed");
    watch=NULL;watch_count=0;IUnknown_Release(identity);identity=NULL;
    const GUID guid={0x11112222,0,0,{0}};UINT size=4;watch=(void**)&identity;watch_count=1;
    require(SUCCEEDED(ID3D11SamplerState_GetPrivateData(sampler,&guid,&size,&identity)),"private interface failed");
    watch=NULL;watch_count=0;IUnknown_Release(identity);
    ID3D11SamplerState *array[129]={0};
    for(UINT pass=0;pass<2;++pass) {
        UINT count=pass?129:12;watch=(void**)array;watch_count=count;
        ID3D11DeviceContext_PSGetSamplers(context,0,count,array);
        watch=NULL;watch_count=0;
        ID3D11DeviceContext_PSSetSamplers(context,0,count,array);
        for(UINT i=0;i<count;++i){require(array[i]==(i%3?sampler:NULL),"proxy identity mismatch");if(array[i])ID3D11SamplerState_Release(array[i]);array[i]=NULL;}
    }
    require(!exposures,"FAIL: native token exposed in caller COM output during transport");
    LONG refs=references[sampler_token&65535];ID3D11SamplerState *failed=NULL;fail_sampler=1;
    require(ID3D11Device_CreateSamplerState(device,&desc,&failed)==E_INVALIDARG&&!failed,"failed output was published");
    require(references[sampler_token&65535]==refs,"failed output leaked a native reference");fail_sampler=0;
    ID3D11SamplerState_Release(sampler);IDXGIFactory1_Release(factory);
    ID3D11DeviceContext_Release(context);ID3D11Device_Release(device);
    require(setters==2,"setter coverage missing");
}
static void scalar_test(void) {
    ID3D11DeviceContext *context=proxy_wrap(context_token,SD_COM_IF_ID3D11DeviceContext);++references[context_token&65535];
    struct {ID3D11DepthStencilView *depth;uint32_t guard[7];} out;
    for(UINT pass=0;pass<2;++pass) {
        out.depth=(void*)1;for(UINT i=0;i<7;++i)out.guard[i]=0x13572460+i;
        ID3D11DeviceContext_OMGetRenderTargets(context,pass?0:8,NULL,&out.depth);
        require(!out.depth,"FAIL: zero RTVs incorrectly suppress the scalar DSV output");
        for(UINT i=0;i<7;++i)require(out.guard[i]==0x13572460+i,"FAIL: scalar DSV output overwrites adjacent caller storage");
    }
    ID3D11DeviceContext_Release(context);
}
void WINAPI start(void) {
    InitializeCriticalSection(&proxy_lock);unix_call=native_call;unix_handle=1;
#if defined(TEST_ONLY_SCALAR)
    scalar_test();
#elif defined(TEST_ONLY_PUBLICATION)
    publication_test();
#else
    publication_test();scalar_test();
#endif
    require(!proxies,"proxy references remain");
    for(UINT i=0;i<65536;++i)require(!references[i],"native references remain");
    say("PASS: real PE32 outputs stay private; sampler identity/setter, QI, factory/device, private interface, heap arrays and scalar DSV guards\n");
    ExitProcess(0);
}
