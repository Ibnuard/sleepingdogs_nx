/* SPDX-License-Identifier: MIT; real PE32 application using ordinary COM APIs. */
#define WIN32_LEAN_AND_MEAN
#define COBJMACROS
#include <windows.h>
#include <d3d11.h>
#include <d3d10.h>
#include <dxgi.h>
#include <stdint.h>
#include "../native_dxvk/probe_shaders.h"
#ifndef SD_COM_BUILD
#error SD_COM_BUILD must identify the packaged native runtime
#endif

void* memcpy(void *d,const void *s,size_t n){unsigned char *a=d;const unsigned char*b=s;while(n--)*a++=*b++;return d;}
void* memset(void *d,int v,size_t n){unsigned char*a=d;while(n--)*a++=(unsigned char)v;return d;}
static HANDLE log_file=INVALID_HANDLE_VALUE;
static uint32_t checks,error,pixels,bad,presents,buffers,mip_bytes,sampler_slots,dsv_guards;
static uint32_t stats[8],elapsed_ms;
static char text[2048];static unsigned used;
static const char* stage="startup";
static void append(const char*s){while(*s&&used+1<sizeof(text))text[used++]=*s++;}
static void number(uint32_t n){char d[10];unsigned i=0;do{d[i++]=(char)('0'+n%10);n/=10;}while(n);while(i){char s[2]={d[--i],0};append(s);}}
static void flush(HANDLE file){DWORD written;if(file!=INVALID_HANDLE_VALUE){WriteFile(file,text,used,&written,NULL);FlushFileBuffers(file);}}
static void record(const char* name){stage=name;used=0;append("[SD-NDX-H4-GUEST] ");append(name);append(" checks=");number(checks);append("\r\n");flush(log_file);}
static int check(int value,uint32_t code){++checks;if(!value){error=code;return 0;}return 1;}
static void result(int passed){
    HANDLE file=CreateFileA("C:\\native-dxvk-h4-result.json",GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    used=0;append("{\"status\":\"");append(passed>0?"PASS":passed<0?"RUNNING":"FAIL");append("\",\"build\":\"" SD_COM_BUILD "\",\"stage\":\"");append(stage);
    append("\",\"error\":");number(error);append(",\"checks\":");number(checks);append(",\"buffer_bytes_verified\":");number(buffers);
    append(",\"mip_array_bytes_verified\":");number(mip_bytes);append(",\"pixels_verified\":");number(pixels);append(",\"bad_pixels\":");number(bad);
    append(",\"present_calls\":");number(presents);append(",\"present_elapsed_ms\":");number(elapsed_ms);
    append(",\"bridge_calls\":");number(stats[0]);append(",\"native_draws\":");number(stats[1]);append(",\"live_interfaces\":");number(stats[3]);append(",\"live_maps\":");number(stats[4]);
    append(",\"sampler_roundtrip_slots_verified\":");number(sampler_slots);append(",\"dsv_guard_checks\":");number(dsv_guards);
    append(",\"bridge_failures\":");number(stats[6]);append(",\"guest_execution\":true,\"com_proxy\":true,\"game_integration_tested\":false,\"game_fps_measured\":false}\r\n");
    flush(file);if(file!=INVALID_HANDLE_VALUE)CloseHandle(file);
}
typedef HRESULT (WINAPI* create_device_fn)(IDXGIAdapter*,D3D_DRIVER_TYPE,HMODULE,UINT,const D3D_FEATURE_LEVEL*,UINT,UINT,ID3D11Device**,D3D_FEATURE_LEVEL*,ID3D11DeviceContext**);
typedef HRESULT (WINAPI* create_factory_fn)(REFIID,void**);
typedef LONG (WINAPI* stats_fn)(uint32_t*);
struct ref_worker {ID3D11Buffer *buffer;HANDLE ready;volatile LONG pairs;};
static DWORD WINAPI ref_thread(void* data){struct ref_worker* w=data;SetEvent(w->ready);
    for(UINT i=0;i<256;++i){ID3D11Buffer_AddRef(w->buffer);ID3D11Buffer_Release(w->buffer);InterlockedIncrement(&w->pairs);}return 0;}
#define HR(call) do{HRESULT hr_=(call);if(!check(SUCCEEDED(hr_),(uint32_t)hr_))goto done;}while(0)
#define REQUIRE(v,code) do{if(!check((v),(code)))goto done;}while(0)
#define DROP(type,p) do{if(p){type##_Release(p);p=NULL;}}while(0)
static int image(ID3D11DeviceContext* context,ID3D11Texture2D* src,ID3D11Texture2D* staging){
    ID3D11DeviceContext_CopyResource(context,(ID3D11Resource*)staging,(ID3D11Resource*)src);
    D3D11_MAPPED_SUBRESOURCE map={0};HRESULT hr=ID3D11DeviceContext_Map(context,(ID3D11Resource*)staging,0,D3D11_MAP_READ,0,&map);
    if(!check(SUCCEEDED(hr),(uint32_t)hr))return 0;
    if(!check(map.pData&&(uintptr_t)map.pData<=UINT32_MAX&&map.RowPitch>=5120,0xe4010101u)){ID3D11DeviceContext_Unmap(context,(ID3D11Resource*)staging,0);return 0;}
    for(UINT y=0;y<720;++y)for(UINT x=0;x<1280;++x){const unsigned char*p=(const unsigned char*)map.pData+y*map.RowPitch+x*4;
        if(!check(p[0]>=63&&p[0]<=65&&p[1]>=127&&p[1]<=129&&p[2]>=190&&p[2]<=192&&p[3]==255,0xe4010102u))++bad;++pixels;}
    ID3D11DeviceContext_Unmap(context,(ID3D11Resource*)staging,0);return bad==0;
}
static int run(void){
    ID3D11Device *device=NULL,*same_device=NULL;ID3D11DeviceContext *context=NULL,*same_context=NULL;
    IDXGIFactory1 *factory=NULL;IDXGIAdapter1 *adapter=NULL;IDXGIOutput *output=NULL;IDXGISwapChain *swap=NULL;
    ID3D11Buffer *dynamic=NULL,*readback=NULL,*immutable=NULL;ID3D11Resource *resource=NULL;
    ID3D11Texture2D *target=NULL,*staging=NULL,*back=NULL,*bc=NULL,*bc_staging=NULL;
    ID3D11RenderTargetView *view=NULL,*back_view=NULL;ID3D11VertexShader *vs=NULL,*same_vs=NULL;ID3D11PixelShader *ps=NULL;
    ID3D11RasterizerState *raster=NULL;IUnknown *unknown_a=NULL,*unknown_b=NULL,*private_object=NULL;
    ID3D10Multithread *multithread=NULL;ID3D11SamplerState *sampler=NULL,*samplers[12]={0};
    D3D11_MAPPED_SUBRESOURCE map={0};D3D_FEATURE_LEVEL requested=D3D_FEATURE_LEVEL_11_0,actual=0;
    int passed=0;stats_fn get_stats=NULL;
    HMODULE d3d=LoadLibraryExA("C:\\SleepingDogs\\d3d11.dll",NULL,LOAD_WITH_ALTERED_SEARCH_PATH);
    HMODULE dxgi=LoadLibraryExA("C:\\SleepingDogs\\dxgi.dll",NULL,LOAD_WITH_ALTERED_SEARCH_PATH);
    REQUIRE(d3d&&dxgi,GetLastError());
    create_device_fn create_device=(create_device_fn)GetProcAddress(d3d,"D3D11CreateDevice");
    create_factory_fn create_factory=(create_factory_fn)GetProcAddress(dxgi,"CreateDXGIFactory1");
    get_stats=(stats_fn)GetProcAddress(GetModuleHandleA("sdndx4.dll"),"SdComStats");
    REQUIRE(create_device&&create_factory&&get_stats,GetLastError());
    record("COM factory, adapter, device and identity");result(-1);
    HR(create_factory(&IID_IDXGIFactory1,(void**)&factory));HR(IDXGIFactory1_EnumAdapters1(factory,0,&adapter));
    struct {DXGI_ADAPTER_DESC1 desc;uint32_t guard;} ad={0};ad.guard=0x1234abcdu;
    HR(IDXGIAdapter1_GetDesc1(adapter,&ad.desc));REQUIRE(ad.guard==0x1234abcdu&&ad.desc.Description[0]!=0,0xe4010001u);
    HR(IDXGIAdapter1_EnumOutputs(adapter,0,&output));struct {DXGI_OUTPUT_DESC desc;uint32_t guard;} od={0};od.guard=0x4321abcdu;
    HR(IDXGIOutput_GetDesc(output,&od.desc));REQUIRE(od.guard==0x4321abcdu&&od.desc.DesktopCoordinates.right==1280,0xe4010002u);
    HR(create_device(NULL,D3D_DRIVER_TYPE_HARDWARE,NULL,0,&requested,1,D3D11_SDK_VERSION,&device,&actual,&context));REQUIRE(actual==requested,0xe4010003u);
    ID3D11Device_GetImmediateContext(device,&same_context);REQUIRE(same_context==context,0xe4010004u);DROP(ID3D11DeviceContext,same_context);
    unsigned char initial[1024];for(UINT i=0;i<1024;++i)initial[i]=(unsigned char)(i*13+3);
    D3D11_BUFFER_DESC bd={1024,D3D11_USAGE_DYNAMIC,D3D11_BIND_VERTEX_BUFFER,D3D11_CPU_ACCESS_WRITE,0,0};
    HR(ID3D11Device_CreateBuffer(device,&bd,NULL,&dynamic));
    ID3D11Buffer_GetDevice(dynamic,&same_device);REQUIRE(same_device==device,0xe4010005u);DROP(ID3D11Device,same_device);
    HR(ID3D11Buffer_QueryInterface(dynamic,&IID_ID3D11Resource,(void**)&resource));
    HR(ID3D11Buffer_QueryInterface(dynamic,&IID_IUnknown,(void**)&unknown_a));HR(ID3D11Resource_QueryInterface(resource,&IID_IUnknown,(void**)&unknown_b));
    REQUIRE(unknown_a==unknown_b,0xe4010006u);DROP(IUnknown,unknown_a);DROP(IUnknown,unknown_b);DROP(ID3D11Resource,resource);
    record("guest/native multithread references and critical section");result(-1);
    HR(ID3D11DeviceContext_QueryInterface(context,&IID_ID3D10Multithread,(void**)&multithread));
    struct ref_worker workers[2]={{dynamic,NULL,0},{dynamic,NULL,0}};HANDLE threads[2]={0};int threaded_ok=1;
    workers[0].ready=CreateEventA(NULL,TRUE,FALSE,NULL);workers[1].ready=CreateEventA(NULL,TRUE,FALSE,NULL);
    REQUIRE(workers[0].ready&&workers[1].ready,GetLastError());
    ID3D10Multithread_Enter(multithread);
    for(UINT i=0;i<2;++i){threads[i]=CreateThread(NULL,0,ref_thread,&workers[i],0,NULL);if(!threads[i]||WaitForSingleObject(workers[i].ready,10000)!=WAIT_OBJECT_0)threaded_ok=0;}
    ID3D11Device_GetImmediateContext(device,&same_context);
    ID3D10Multithread_Leave(multithread);DROP(ID3D11DeviceContext,same_context);
    for(UINT i=0;i<2;++i){if(threads[i]){if(WaitForSingleObject(threads[i],10000)!=WAIT_OBJECT_0)threaded_ok=0;CloseHandle(threads[i]);}CloseHandle(workers[i].ready);}
    REQUIRE(threaded_ok&&workers[0].pairs==256&&workers[1].pairs==256,0xe4010011u);DROP(ID3D10Multithread,multithread);
    record("dynamic Map DISCARD, NO_OVERWRITE and initial-data conversion");result(-1);
    HR(ID3D11DeviceContext_Map(context,(ID3D11Resource*)dynamic,0,D3D11_MAP_WRITE_DISCARD,0,&map));REQUIRE(map.pData!=NULL,0xe4010007u);
    memcpy(map.pData,initial,1024);ID3D11DeviceContext_Unmap(context,(ID3D11Resource*)dynamic,0);
    HR(ID3D11DeviceContext_Map(context,(ID3D11Resource*)dynamic,0,D3D11_MAP_WRITE_NO_OVERWRITE,0,&map));
    for(UINT i=512;i<544;++i){initial[i]^=0x55;((unsigned char*)map.pData)[i]=initial[i];}ID3D11DeviceContext_Unmap(context,(ID3D11Resource*)dynamic,0);
    bd.Usage=D3D11_USAGE_STAGING;bd.BindFlags=0;bd.CPUAccessFlags=D3D11_CPU_ACCESS_READ;HR(ID3D11Device_CreateBuffer(device,&bd,NULL,&readback));
    ID3D11DeviceContext_CopyResource(context,(ID3D11Resource*)readback,(ID3D11Resource*)dynamic);
    HR(ID3D11DeviceContext_Map(context,(ID3D11Resource*)readback,0,D3D11_MAP_READ,0,&map));
    for(UINT i=0;i<1024;++i){REQUIRE(((unsigned char*)map.pData)[i]==initial[i],0xe4010008u);++buffers;}ID3D11DeviceContext_Unmap(context,(ID3D11Resource*)readback,0);
    bd.Usage=D3D11_USAGE_IMMUTABLE;bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;bd.CPUAccessFlags=0;D3D11_SUBRESOURCE_DATA init={initial,0,0};
    HR(ID3D11Device_CreateBuffer(device,&bd,&init,&immutable));ID3D11DeviceContext_CopyResource(context,(ID3D11Resource*)readback,(ID3D11Resource*)immutable);
    HR(ID3D11DeviceContext_Map(context,(ID3D11Resource*)readback,0,D3D11_MAP_READ,0,&map));
    for(UINT i=0;i<1024;++i){REQUIRE(((unsigned char*)map.pData)[i]==initial[i],0xe4010009u);++buffers;}ID3D11DeviceContext_Unmap(context,(ID3D11Resource*)readback,0);
    record("scalar DSV guards and six-stage sampler roundtrips");result(-1);
    struct {ID3D11DepthStencilView *depth;uint32_t guard[7];} guarded;
    for(UINT pass=0;pass<2;++pass) {
        guarded.depth=(void*)1;for(UINT i=0;i<7;++i)guarded.guard[i]=0x13572460u+i;
        ID3D11DeviceContext_OMGetRenderTargets(context,pass?0:8,NULL,&guarded.depth);
        REQUIRE(!guarded.depth,0xe4010200u);++dsv_guards;
        for(UINT i=0;i<7;++i){REQUIRE(guarded.guard[i]==0x13572460u+i,0xe4010201u);++dsv_guards;}
    }
    D3D11_SAMPLER_DESC sampler_desc={0};sampler_desc.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    sampler_desc.AddressU=sampler_desc.AddressV=sampler_desc.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler_desc.MaxAnisotropy=1;sampler_desc.ComparisonFunc=D3D11_COMPARISON_NEVER;sampler_desc.MaxLOD=D3D11_FLOAT32_MAX;
    HR(ID3D11Device_CreateSamplerState(device,&sampler_desc,&sampler));
    ID3D11SamplerState *bound[12],*empty[12]={0};for(UINT i=0;i<12;++i)bound[i]=i%3?sampler:NULL;
#define SAMPLER_STAGE(S) do { \
    ID3D11DeviceContext_##S##SetSamplers(context,0,12,bound); \
    ID3D11DeviceContext_##S##GetSamplers(context,0,12,samplers); \
    for(UINT i=0;i<12;++i){REQUIRE(samplers[i]==bound[i],0xe4010202u);++sampler_slots;DROP(ID3D11SamplerState,samplers[i]);} \
    ID3D11DeviceContext_##S##SetSamplers(context,0,12,empty); \
} while(0)
    SAMPLER_STAGE(PS);SAMPLER_STAGE(VS);SAMPLER_STAGE(GS);SAMPLER_STAGE(HS);SAMPLER_STAGE(DS);SAMPLER_STAGE(CS);
#undef SAMPLER_STAGE
    DROP(ID3D11SamplerState,sampler);
    record("BC1 mip/array upload and readback");result(-1);
    unsigned char blocks[4][32];D3D11_SUBRESOURCE_DATA bc_init[4];
    for(UINT i=0;i<4;++i){for(UINT j=0;j<32;++j)blocks[i][j]=(unsigned char)(i*33+j);bc_init[i].pSysMem=blocks[i];bc_init[i].SysMemPitch=i%2?8:16;bc_init[i].SysMemSlicePitch=i%2?8:32;}
    D3D11_TEXTURE2D_DESC td={8,8,2,2,DXGI_FORMAT_BC1_UNORM,{1,0},D3D11_USAGE_IMMUTABLE,D3D11_BIND_SHADER_RESOURCE,0,0};
    HR(ID3D11Device_CreateTexture2D(device,&td,bc_init,&bc));td.Usage=D3D11_USAGE_STAGING;td.BindFlags=0;td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
    HR(ID3D11Device_CreateTexture2D(device,&td,NULL,&bc_staging));ID3D11DeviceContext_CopyResource(context,(ID3D11Resource*)bc_staging,(ID3D11Resource*)bc);
    for(UINT i=0;i<4;++i){HR(ID3D11DeviceContext_Map(context,(ID3D11Resource*)bc_staging,i,D3D11_MAP_READ,0,&map));UINT rows=i%2?1:2,bytes=i%2?8:16;
        for(UINT y=0;y<rows;++y)for(UINT x=0;x<bytes;++x){REQUIRE(((unsigned char*)map.pData)[y*map.RowPitch+x]==blocks[i][y*bytes+x],0xe401000au);++mip_bytes;}ID3D11DeviceContext_Unmap(context,(ID3D11Resource*)bc_staging,i);}
    record("native shaders, state arrays and private interface conversion");result(-1);
    HR(ID3D11Device_CreateVertexShader(device,probe_vs,sizeof(probe_vs),NULL,&vs));HR(ID3D11Device_CreatePixelShader(device,probe_ps,sizeof(probe_ps),NULL,&ps));
    const GUID private_id={0x50e0dfe4,0x2504,0x4917,{0xaf,0x12,0x17,0x01,0,0,0,1}};
    HR(ID3D11Buffer_SetPrivateDataInterface(dynamic,&private_id,(IUnknown*)vs));UINT private_size=sizeof(private_object);
    HR(ID3D11Buffer_GetPrivateData(dynamic,&private_id,&private_size,&private_object));REQUIRE(private_size==4&&private_object,0xe401000bu);
    HR(IUnknown_QueryInterface(private_object,&IID_ID3D11VertexShader,(void**)&same_vs));REQUIRE(same_vs==vs,0xe401000cu);
    DROP(ID3D11VertexShader,same_vs);DROP(IUnknown,private_object);HR(ID3D11Buffer_SetPrivateDataInterface(dynamic,&private_id,NULL));
    td.Width=1280;td.Height=720;td.MipLevels=td.ArraySize=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.Usage=D3D11_USAGE_DEFAULT;td.BindFlags=D3D11_BIND_RENDER_TARGET;td.CPUAccessFlags=0;
    HR(ID3D11Device_CreateTexture2D(device,&td,NULL,&target));HR(ID3D11Device_CreateRenderTargetView(device,(ID3D11Resource*)target,NULL,&view));
    td.Usage=D3D11_USAGE_STAGING;td.BindFlags=0;td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;HR(ID3D11Device_CreateTexture2D(device,&td,NULL,&staging));
    D3D11_RASTERIZER_DESC rd={0};rd.FillMode=D3D11_FILL_SOLID;rd.CullMode=D3D11_CULL_NONE;rd.DepthClipEnable=TRUE;HR(ID3D11Device_CreateRasterizerState(device,&rd,&raster));
    D3D11_VIEWPORT viewport={0,0,1280,720,0,1};ID3D11DeviceContext_RSSetState(context,raster);ID3D11DeviceContext_RSSetViewports(context,1,&viewport);
    ID3D11DeviceContext_IASetPrimitiveTopology(context,D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);ID3D11DeviceContext_VSSetShader(context,vs,NULL,0);ID3D11DeviceContext_PSSetShader(context,ps,NULL,0);
    ID3D11DeviceContext_OMSetRenderTargets(context,1,&view,NULL);ID3D11DeviceContext_Draw(context,3,0);REQUIRE(image(context,target,staging),0xe401000du);
    record("COM swapchain, guest HWND metadata and backbuffer draw");result(-1);
    DXGI_SWAP_CHAIN_DESC sc={0};sc.BufferDesc.Width=1280;sc.BufferDesc.Height=720;sc.BufferDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;sc.BufferDesc.RefreshRate.Numerator=60;sc.BufferDesc.RefreshRate.Denominator=1;
    sc.SampleDesc.Count=1;sc.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;sc.BufferCount=2;sc.OutputWindow=(HWND)(uintptr_t)0x12345678;sc.Windowed=TRUE;sc.SwapEffect=DXGI_SWAP_EFFECT_DISCARD;
    HR(IDXGIFactory1_CreateSwapChain(factory,(IUnknown*)device,&sc,&swap));DXGI_SWAP_CHAIN_DESC observed={0};HR(IDXGISwapChain_GetDesc(swap,&observed));REQUIRE(observed.OutputWindow==sc.OutputWindow&&observed.BufferDesc.Width==1280,0xe401000eu);
    HR(IDXGISwapChain_GetBuffer(swap,0,&IID_ID3D11Texture2D,(void**)&back));HR(ID3D11Device_CreateRenderTargetView(device,(ID3D11Resource*)back,NULL,&back_view));
    ID3D11DeviceContext_OMSetRenderTargets(context,1,&back_view,NULL);ID3D11DeviceContext_Draw(context,3,0);REQUIRE(image(context,back,staging),0xe401000fu);
    record("300 native Present calls through COM");result(-1);DWORD began=GetTickCount();
    for(UINT i=0;i<300;++i){ID3D11DeviceContext_Draw(context,3,0);HR(IDXGISwapChain_Present(swap,1,0));++presents;if(presents%60==0){record("COM Present progress");result(-1);}}
    elapsed_ms=GetTickCount()-began;passed=1;
done:
    if(context){ID3D11DeviceContext_ClearState(context);ID3D11DeviceContext_Flush(context);}
    DROP(IUnknown,private_object);DROP(IUnknown,unknown_a);DROP(IUnknown,unknown_b);DROP(ID3D11Resource,resource);
    DROP(ID3D11VertexShader,same_vs);DROP(ID3D11DeviceContext,same_context);DROP(ID3D11Device,same_device);
    DROP(ID3D10Multithread,multithread);
    for(UINT i=0;i<12;++i)DROP(ID3D11SamplerState,samplers[i]);DROP(ID3D11SamplerState,sampler);
    DROP(ID3D11RenderTargetView,back_view);DROP(ID3D11RenderTargetView,view);DROP(ID3D11Texture2D,back);DROP(IDXGISwapChain,swap);
    DROP(ID3D11Texture2D,staging);DROP(ID3D11Texture2D,target);DROP(ID3D11Texture2D,bc_staging);DROP(ID3D11Texture2D,bc);
    DROP(ID3D11Buffer,dynamic);DROP(ID3D11Buffer,readback);DROP(ID3D11Buffer,immutable);
    DROP(ID3D11VertexShader,vs);DROP(ID3D11PixelShader,ps);DROP(ID3D11RasterizerState,raster);
    DROP(IDXGIOutput,output);DROP(IDXGIAdapter1,adapter);DROP(IDXGIFactory1,factory);
    DROP(ID3D11DeviceContext,context);DROP(ID3D11Device,device);
    if(get_stats){LONG status=get_stats(stats);if(!check(status>=0,(uint32_t)status))passed=0;}
    if(passed && !check(stats[3]==0&&stats[4]==0&&stats[6]==0,0xe4010010u))passed=0;
    record(passed?"PASS":"FAIL");result(passed);return passed;
}
void WINAPI start(void){
    log_file=CreateFileA("C:\\native-dxvk-h4-guest.log",GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    record("startup real PE32 COM client");result(-1);int passed=run();if(log_file!=INVALID_HANDLE_VALUE)CloseHandle(log_file);ExitProcess(passed?0:1);
}
