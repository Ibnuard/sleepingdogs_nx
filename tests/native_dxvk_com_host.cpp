/* SPDX-License-Identifier: MIT
 * Actual DXVK/lavapipe; 32-bit wire descriptors in a low mmap. Direct Unix
 * entry and modeled Wine permissions: this does not execute PE32 or FEX.
 */
#include "../src/native_dxvk_com/com_protocol.h"
#include "../src/native_dxvk_com/com_methods.h"
#include "../src/native_dxvk_com/com_progress.h"
#include "../src/native_dxvk/probe_shaders.h"
#include <d3d11.h>
#include <d3d10.h>
#include <dxgi.h>
#include <sys/mman.h>
#include <xcb/xcb.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#include <functional>
#include <stdexcept>
#include <thread>
#include <vector>

namespace {
constexpr uint32_t base=0x10000000, arena_bytes=16*1024*1024, shadow=base+8*1024*1024;
unsigned char* arena=nullptr;uint32_t used=4096;
std::atomic<unsigned> checks{0},permissions{0},presented{0},thread_pairs{0};
unsigned rejections=0,verified_pixels=0,verified_bytes=0,verified_bc=0;
std::atomic<uint32_t> deny_write{0};
void* window_pointer=nullptr;
void require(bool ok,const char* reason="native COM fixture check") {
    ++checks;if(!ok)throw std::runtime_error(reason);
}
bool permission(const void* p,size_t n,bool write) {
    ++permissions;uint64_t a=reinterpret_cast<uintptr_t>(p);
    if(a<base||a>uint64_t(base)+arena_bytes||n>uint64_t(base)+arena_bytes-a)return false;
    uint32_t denied=deny_write.load();return !write||!denied||a+n<=denied||a>=uint64_t(denied)+4096;
}
template<typename T> uint32_t address(const T* p){return uint32_t(reinterpret_cast<uintptr_t>(p));}
template<typename T> T* allocate(uint32_t count=1) {
    used=(used+15)&~15u;uint64_t length=uint64_t(sizeof(T))*count;
    require(length<=8*1024*1024-used,"fixture metadata capacity");
    auto* p=reinterpret_cast<T*>(arena+used);used+=uint32_t(length);std::memset(p,0,size_t(length));return p;
}
template<typename T> uint32_t wire(const T& value) {auto* p=allocate<T>();*p=value;return address(p);}
struct Client {
    sd_com_packet* packet;
    explicit Client(unsigned n=0):packet(reinterpret_cast<sd_com_packet*>(arena+256+n*256)){}
    int32_t call(uint32_t type,uint32_t method,uint32_t object=0,std::initializer_list<uint32_t> args={},bool valid=true) {
        *packet={};packet->abi=SD_COM_ABI;packet->interface_id=type;packet->method=method;packet->object=object;
        unsigned j=0;for(auto a:args)packet->args[j++]=a;
        require(wine_nx_sd_com_wow64_unix_funcs[0](packet)==0,"transport dispatch");
        if(valid)require(!packet->fault,"unexpected bridge fault");
        return int32_t(packet->ret);
    }
    void release(uint32_t object){if(object)call(SD_COM_IF_IUnknown,2,object);}
    uint32_t create(uint32_t type,uint32_t method,uint32_t parent,std::initializer_list<uint32_t> args,uint32_t* output) {
        require(call(type,method,parent,args)>=0,"native create HRESULT");require(*output!=0,"native create token");return *output;
    }
    void reject(uint32_t type,uint32_t method,uint32_t object,std::initializer_list<uint32_t> args={}) {
        require(call(type,method,object,args,false)<0,"invalid request was accepted");++rejections;
    }
};
struct Window {
    struct Native {xcb_connection_t* connection;xcb_window_t window;} native={};
    Window() {
        int number=0;native.connection=xcb_connect(nullptr,&number);
        require(native.connection&&!xcb_connection_has_error(native.connection),"XCB connection");
        auto screens=xcb_setup_roots_iterator(xcb_get_setup(native.connection));for(int i=0;i<number;++i)xcb_screen_next(&screens);
        auto* screen=screens.data;native.window=xcb_generate_id(native.connection);
        auto request=xcb_create_window_checked(native.connection,XCB_COPY_FROM_PARENT,native.window,screen->root,0,0,1280,720,0,XCB_WINDOW_CLASS_INPUT_OUTPUT,screen->root_visual,0,nullptr);
        auto* error=xcb_request_check(native.connection,request);if(error){std::free(error);throw std::runtime_error("XCB window");}
        xcb_map_window(native.connection,native.window);xcb_flush(native.connection);window_pointer=&native;
    }
    ~Window(){sd_com_shutdown();window_pointer=nullptr;if(native.connection){xcb_destroy_window(native.connection,native.window);xcb_disconnect(native.connection);}}
};
uint32_t query(Client& c,uint32_t object,REFIID guid) {
    auto out=allocate<uint32_t>();return c.create(SD_COM_IF_IUnknown,0,object,{wire(guid),address(out)},out);
}
struct Mapped {sd_com_mapped32* info;uint32_t id,bytes;};
Mapped map(Client& c,uint32_t context,uint32_t resource,uint32_t subresource,uint32_t mode) {
    auto output=allocate<sd_com_mapped32>();
    require(c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Map,context,{resource,subresource,mode,0,address(output)})>=0,"native Map HRESULT");
    Mapped result{output,c.packet->aux,c.packet->high[0]};require(result.id&&result.bytes&&result.bytes<=8*1024*1024,"Map lifetime and bytes");
    require(c.call(0,SD_COM_BIND_MAP,0,{result.id,shadow,result.bytes})==0,"bind low shadow");return result;
}
void unmap(Client& c,uint32_t context,uint32_t resource,uint32_t subresource,uint32_t id) {
    c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Unmap,context,{resource,subresource});require(c.packet->aux==id,"Unmap lifetime identity");
}
void image(Client& c,uint32_t context,uint32_t source,uint32_t staging) {
    c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_CopyResource,context,{staging,source});
    auto m=map(c,context,staging,0,D3D11_MAP_READ);require(m.info->row_pitch>=5120&&m.bytes>=m.info->row_pitch*720,"image pitch");
    unsigned expected[4]={64,128,191,255};
    for(unsigned y=0;y<720;++y)for(unsigned x=0;x<1280;++x){auto p=arena+(shadow-base)+y*m.info->row_pitch+x*4;
        for(unsigned n=0;n<4;++n)require(std::abs(int(p[n])-int(expected[n]))<=1,"rendered pixel mismatch");
        ++verified_pixels;}
    unmap(c,context,staging,0,m.id);
}
}
extern "C" int virtual_check_buffer_for_read(const void* p,size_t n){return permission(p,n,false);}
extern "C" int virtual_check_buffer_for_write(void* p,size_t n){return permission(p,n,true);}
extern "C" void wine_nx_runtime_trace(const char* s){std::fprintf(stderr,"%s\n",s);}
extern "C" void* sd_com_native_window(){return window_pointer;}
extern "C" uint64_t sd_com_clock_ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
extern "C" uint64_t sd_com_thread_id(){return std::hash<std::thread::id>{}(std::this_thread::get_id());}
extern "C" void sd_com_presented(uint32_t,int32_t result){require(result==0);++presented;}
extern "C" void sd_com_test_fail_adopt_after(int32_t);
#ifdef SD_COM_PROGRESS_TEST
extern "C" int sd_com_test_progress_snapshot(uint64_t*);
#endif

int main(int argc,char** argv){
    try {
        Window window;
        arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(uintptr_t(base)),arena_bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
        require(arena!=MAP_FAILED&&uintptr_t(arena)==base,"low-address mmap");Client c;
        require(wine_nx_sd_com_wow64_unix_count==1);
        require(wine_nx_sd_com_wow64_unix_funcs[0](nullptr)<0);++rejections;
        unsigned permission_before=permissions.load();require(wine_nx_sd_com_wow64_unix_funcs[0](reinterpret_cast<void*>(uintptr_t(0x100000000ull)))<0);
        require(permissions.load()==permission_before,"high pointer was dereferenced");++rejections;
        *c.packet={};require(wine_nx_sd_com_wow64_unix_funcs[0](c.packet)<0);++rejections;
        *c.packet={};c.packet->abi=SD_COM_ABI;c.packet->reserved=1;require(wine_nx_sd_com_wow64_unix_funcs[0](c.packet)<0);++rejections;
        auto out=allocate<uint32_t>();auto level=allocate<D3D_FEATURE_LEVEL>();*level=D3D_FEATURE_LEVEL_11_0;
        auto device_out=allocate<uint32_t>(),context_out=allocate<uint32_t>();auto actual=allocate<D3D_FEATURE_LEVEL>();
        auto failed_stats=allocate<uint32_t>(8);
        for(int32_t after:{0,1}){
            *device_out=*context_out=0x12345678;sd_com_test_fail_adopt_after(after);
            require(c.call(0,SD_COM_CREATE_DEVICE,0,{0,D3D_DRIVER_TYPE_HARDWARE,0,0,address(level),1,D3D11_SDK_VERSION,address(device_out),address(actual),address(context_out)},false)==E_OUTOFMEMORY,"device allocation failure HRESULT");
            require(c.packet->fault==uint32_t(E_OUTOFMEMORY)&&!*device_out&&!*context_out,"failed device creation must clear both outputs");++rejections;
            c.call(0,SD_COM_STATS,0,{address(failed_stats)});require(failed_stats[3]==0&&failed_stats[4]==0,"partial device adoption must not retain bridge objects");
        }
        require(c.call(0,SD_COM_CREATE_DEVICE,0,{0,D3D_DRIVER_TYPE_HARDWARE,0,0,address(level),1,D3D11_SDK_VERSION,address(device_out),address(actual),address(context_out)})==0);
        uint32_t device=*device_out,context=*context_out;require(device&&context&&*actual==D3D_FEATURE_LEVEL_11_0);
        const bool array_bench=argc==2&&!std::strcmp(argv[1],"--array-dispatch-bench");
        if(array_bench||(argc==2&&!std::strcmp(argv[1],"--dispatch-bench"))) {
            // Exercise the actual dispatcher without GPU work in the measured
            // region. Wine permissions are modeled; no PE32/FEX or game FPS.
            *c.packet={SD_COM_ABI,context,SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_GetType};
            auto null_samplers=allocate<uint32_t>(12);
            if(array_bench) {
                c.packet->method=SD_COM_M_ID3D11DeviceContext_PSSetSamplers;
                c.packet->args[0]=0;c.packet->args[1]=12;c.packet->args[2]=address(null_samplers);
            }
            constexpr unsigned iterations=1000000;
            auto start=std::chrono::steady_clock::now();
            for(unsigned i=0;i<iterations;++i) {
                auto rc=wine_nx_sd_com_wow64_unix_funcs[0](c.packet);
                if(rc||c.packet->fault||c.packet->ret!=(array_bench?0:D3D11_DEVICE_CONTEXT_IMMEDIATE))throw std::runtime_error("dispatch benchmark result changed");
            }
            auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();
#ifdef SD_COM_PROGRESS_TEST
            using namespace sd_com_progress;Snapshot snapshot{};
            require(sd_com_test_progress_snapshot(snapshot.data())&&snapshot[Phase]==Idle&&snapshot[Method]==uint64_t(array_bench?SD_COM_M_ID3D11DeviceContext_PSSetSamplers:SD_COM_M_ID3D11DeviceContext_GetType));
            require(snapshot[Entry]%256==0&&snapshot[Calls]>iterations-256&&snapshot[Calls]<iterations+100,"periodic progress snapshot stayed fresh");
            c.packet->object=0xdeadbeef;
            require(wine_nx_sd_com_wow64_unix_funcs[0](c.packet)==0&&c.packet->fault==uint32_t(E_INVALIDARG));
            require(sd_com_test_progress_snapshot(snapshot.data())&&snapshot[Phase]==Idle&&snapshot[Object]==0xdeadbeef&&snapshot[FaultCode]==uint32_t(E_INVALIDARG),"unsampled call failure was not published");
#endif
            if(array_bench) {
                auto observed=allocate<uint32_t>(12);for(unsigned i=0;i<12;++i)observed[i]=UINT32_MAX;
                c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_PSGetSamplers,context,{0,12,address(observed)});
                for(unsigned i=0;i<12;++i)require(observed[i]==0,"array benchmark changed sampler binding");
            }
            c.release(context);c.release(device);sd_com_shutdown();
            std::printf("{\"status\":\"PASS\",\"iterations\":%u,\"elapsed_ns\":%lld,\"ns_per_call\":%.3f,\"game_fps_measured\":false}\n",iterations,(long long)ns,double(ns)/iterations);
            return 0;
        }
        c.call(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_GetImmediateContext,device,{address(out)});require(*out==context);c.release(*out);
        uint32_t factory=c.create(0,SD_COM_CREATE_FACTORY,0,{0,wire(__uuidof(IDXGIFactory1)),address(out)},out);
        uint32_t adapter=c.create(SD_COM_IF_IDXGIFactory1,SD_COM_M_IDXGIFactory1_EnumAdapters1,factory,{0,address(out)},out);
        auto adapter_desc=allocate<unsigned char>(300);*reinterpret_cast<uint32_t*>(adapter_desc+296)=0x1234abcd;
        require(c.call(SD_COM_IF_IDXGIAdapter1,SD_COM_M_IDXGIAdapter1_GetDesc1,adapter,{address(adapter_desc)})==0);
        require(*reinterpret_cast<uint32_t*>(adapter_desc+296)==0x1234abcd&&*reinterpret_cast<uint16_t*>(adapter_desc),"32-bit adapter descriptor boundary");
        uint32_t output=c.create(SD_COM_IF_IDXGIAdapter1,SD_COM_M_IDXGIAdapter1_EnumOutputs,adapter,{0,address(out)},out);
        auto output_desc=allocate<unsigned char>(96);*reinterpret_cast<uint32_t*>(output_desc+92)=0x4321abcd;
        require(c.call(SD_COM_IF_IDXGIOutput,SD_COM_M_IDXGIOutput_GetDesc,output,{address(output_desc)})==0);
        require(*reinterpret_cast<uint32_t*>(output_desc+92)==0x4321abcd,"32-bit output descriptor boundary");
        c.call(SD_COM_IF_IDXGIFactory1,SD_COM_M_IDXGIFactory1_MakeWindowAssociation,factory,{0x12345678,0});
        c.call(SD_COM_IF_IDXGIFactory1,SD_COM_M_IDXGIFactory1_GetWindowAssociation,factory,{address(out)});require(*out==0x12345678,"guest HWND metadata");
        auto factory_base=query(c,factory,__uuidof(IDXGIFactory));
        c.call(SD_COM_IF_IDXGIFactory,SD_COM_M_IDXGIFactory_GetWindowAssociation,factory_base,{address(out)});require(*out==0x12345678,"factory metadata survives QueryInterface");
        c.call(SD_COM_IF_IDXGIFactory,SD_COM_M_IDXGIFactory_MakeWindowAssociation,factory_base,{0x76543210,0});
        c.call(SD_COM_IF_IDXGIFactory1,SD_COM_M_IDXGIFactory1_GetWindowAssociation,factory,{address(out)});require(*out==0x76543210,"factory metadata synchronized across aliases");
        c.release(factory_base);
        auto dxgi_device=query(c,device,__uuidof(IDXGIDevice));
        auto device_adapter=c.create(SD_COM_IF_IDXGIDevice,SD_COM_M_IDXGIDevice_GetAdapter,dxgi_device,{address(out)},out);
        auto parent_factory=c.create(SD_COM_IF_IDXGIAdapter,SD_COM_M_IDXGIAdapter_GetParent,device_adapter,{wire(__uuidof(IDXGIFactory)),address(out)},out);
        c.release(parent_factory);c.release(device_adapter);c.release(dxgi_device);
        D3D11_BUFFER_DESC bd={1024,D3D11_USAGE_DYNAMIC,D3D11_BIND_VERTEX_BUFFER,D3D11_CPU_ACCESS_WRITE,0,0};uint32_t desc=wire(bd);
        uint32_t dynamic=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateBuffer,device,{desc,0,address(out)},out);
        uint32_t resource=query(c,dynamic,__uuidof(ID3D11Resource)),unknown_a=query(c,dynamic,__uuidof(IUnknown)),unknown_b=query(c,resource,__uuidof(IUnknown));
        require(unknown_a==unknown_b,"canonical IUnknown identity");c.release(resource);c.release(unknown_a);c.release(unknown_b);
        c.call(SD_COM_IF_ID3D11Buffer,SD_COM_M_ID3D11Buffer_GetDevice,dynamic,{address(out)});require(*out==device);c.release(*out);
        auto expected=allocate<unsigned char>(1024);for(unsigned i=0;i<1024;++i)expected[i]=uint8_t(i*13+3);
        auto m=map(c,context,dynamic,0,D3D11_MAP_WRITE_DISCARD);std::memcpy(arena+shadow-base,expected,1024);unmap(c,context,dynamic,0,m.id);
        m=map(c,context,dynamic,0,D3D11_MAP_WRITE_NO_OVERWRITE);require(!std::memcmp(arena+shadow-base,expected,1024),"NO_OVERWRITE preserves data");
        for(unsigned i=512;i<544;++i){expected[i]^=0x55;arena[shadow-base+i]=expected[i];}unmap(c,context,dynamic,0,m.id);
        bd.Usage=D3D11_USAGE_STAGING;bd.BindFlags=0;bd.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
        uint32_t readback=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateBuffer,device,{wire(bd),0,address(out)},out);
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_CopyResource,context,{readback,dynamic});
        m=map(c,context,readback,0,D3D11_MAP_READ);for(unsigned i=0;i<1024;++i){require(arena[shadow-base+i]==expected[i]);++verified_bytes;}unmap(c,context,readback,0,m.id);
        bd.Usage=D3D11_USAGE_IMMUTABLE;bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;bd.CPUAccessFlags=0;
        sd_com_subresource32 initial={address(expected),0,0};
        uint32_t immutable=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateBuffer,device,{wire(bd),wire(initial),address(out)},out);
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_CopyResource,context,{readback,immutable});
        m=map(c,context,readback,0,D3D11_MAP_READ);for(unsigned i=0;i<1024;++i){require(arena[shadow-base+i]==expected[i]);++verified_bytes;}unmap(c,context,readback,0,m.id);
        bd.Usage=D3D11_USAGE_DEFAULT;
        uint32_t update_target=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateBuffer,device,{wire(bd),wire(initial),address(out)},out);
        for(const auto& empty:{D3D11_BOX{64,0,0,64,1,1},D3D11_BOX{64,0,0,32,1,1},D3D11_BOX{0,1,0,16,1,1}})
            require(c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_UpdateSubresource,context,{update_target,0,wire(empty),0,0,0})==0,"empty UpdateSubresource box must not read a null source");
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_CopyResource,context,{readback,update_target});
        m=map(c,context,readback,0,D3D11_MAP_READ);for(unsigned i=0;i<1024;++i){require(arena[shadow-base+i]==expected[i],"empty updates must preserve native buffer contents");++verified_bytes;}unmap(c,context,readback,0,m.id);
        auto mapped=allocate<sd_com_mapped32>();require(c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Map,context,{readback,0,D3D11_MAP_READ,0,address(mapped)})==0);
        uint32_t map_id=c.packet->aux,map_length=c.packet->high[0];deny_write=shadow;
        c.reject(0,SD_COM_BIND_MAP,0,{map_id,shadow,map_length});deny_write=0;c.call(0,SD_COM_ABORT_MAP,0,{map_id});
        c.reject(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_VSSetShaderResources,context,{0,UINT32_MAX,0});
        c.reject(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_VSSetShaderResources,context,{0,SD_COM_MAX_ARRAY+1,0});
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_OMSetRenderTargetsAndUnorderedAccessViews,context,{UINT32_MAX,0,0,0,UINT32_MAX,0,0});
        auto bc_data=allocate<sd_com_subresource32>(4);auto blocks=allocate<unsigned char>(128);
        for(unsigned i=0;i<4;++i){for(unsigned j=0;j<32;++j)blocks[i*32+j]=uint8_t(i*33+j);bc_data[i]={address(blocks+i*32),i%2?8u:16u,i%2?8u:32u};}
        D3D11_TEXTURE2D_DESC td={8,8,2,2,DXGI_FORMAT_BC1_UNORM,{1,0},D3D11_USAGE_IMMUTABLE,D3D11_BIND_SHADER_RESOURCE,0,0};
        uint32_t bc=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateTexture2D,device,{wire(td),address(bc_data),address(out)},out);
        td.Usage=D3D11_USAGE_STAGING;td.BindFlags=0;td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
        uint32_t bc_staging=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateTexture2D,device,{wire(td),0,address(out)},out);
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_CopyResource,context,{bc_staging,bc});
        for(unsigned i=0;i<4;++i){m=map(c,context,bc_staging,i,D3D11_MAP_READ);unsigned rows=i%2?1:2,length=i%2?8:16;
            for(unsigned y=0;y<rows;++y)for(unsigned x=0;x<length;++x){require(arena[shadow-base+y*m.info->row_pitch+x]==blocks[i*32+y*length+x],"BC1 mip/array data");++verified_bc;}
            unmap(c,context,bc_staging,i,m.id);}
        auto vs_code=allocate<unsigned char>(sizeof(probe_vs)),ps_code=allocate<unsigned char>(sizeof(probe_ps));std::memcpy(vs_code,probe_vs,sizeof(probe_vs));std::memcpy(ps_code,probe_ps,sizeof(probe_ps));
        uint32_t vs=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateVertexShader,device,{address(vs_code),sizeof(probe_vs),0,address(out)},out);
        uint32_t ps=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreatePixelShader,device,{address(ps_code),sizeof(probe_ps),0,address(out)},out);
        const GUID private_id={0x50e0dfe4,0x2504,0x4917,{0xaf,0x12,0x17,0x01,0,0,0,1}};uint32_t private_guid=wire(private_id);
        c.call(SD_COM_IF_ID3D11Buffer,SD_COM_M_ID3D11Buffer_SetPrivateDataInterface,dynamic,{private_guid,vs});auto private_size=allocate<uint32_t>();*private_size=4;
        c.call(SD_COM_IF_ID3D11Buffer,SD_COM_M_ID3D11Buffer_GetPrivateData,dynamic,{private_guid,address(private_size),address(out)});
        require(*private_size==4&&c.packet->aux==SD_COM_PRIVATE_INTERFACE,"private interface pointer width");uint32_t private_unknown=*out;
        uint32_t private_vs=query(c,private_unknown,__uuidof(ID3D11VertexShader));require(private_vs==vs);c.release(private_vs);c.release(private_unknown);
        c.call(SD_COM_IF_ID3D11Buffer,SD_COM_M_ID3D11Buffer_SetPrivateDataInterface,dynamic,{private_guid,0});
        td.Width=1280;td.Height=720;td.MipLevels=td.ArraySize=1;td.Format=DXGI_FORMAT_R8G8B8A8_UNORM;td.Usage=D3D11_USAGE_DEFAULT;td.BindFlags=D3D11_BIND_RENDER_TARGET;td.CPUAccessFlags=0;
        uint32_t target=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateTexture2D,device,{wire(td),0,address(out)},out);
        uint32_t view=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateRenderTargetView,device,{target,0,address(out)},out);
        td.Usage=D3D11_USAGE_STAGING;td.BindFlags=0;td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
        uint32_t staging=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateTexture2D,device,{wire(td),0,address(out)},out);
        D3D11_RASTERIZER_DESC rd={};rd.FillMode=D3D11_FILL_SOLID;rd.CullMode=D3D11_CULL_NONE;rd.DepthClipEnable=TRUE;
        uint32_t raster=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateRasterizerState,device,{wire(rd),address(out)},out);
        D3D11_VIEWPORT vp={0,0,1280,720,0,1};uint32_t view_array=wire(view);
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_RSSetState,context,{raster});
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_RSSetViewports,context,{1,wire(vp)});
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_IASetPrimitiveTopology,context,{D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST});
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_VSSetShader,context,{vs,0,0});
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_PSSetShader,context,{ps,0,0});
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_OMSetRenderTargets,context,{1,view_array,0});
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Draw,context,{3,0});image(c,context,target,staging);
        auto views=allocate<uint32_t>(),count=allocate<uint32_t>();*count=1;auto observed_viewport=allocate<D3D11_VIEWPORT>();
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_OMGetRenderTargets,context,{1,address(views),0});require(*views==view);c.release(*views);
        auto depth_guard=allocate<uint32_t>(8);
        for(uint32_t n:{8u,0u}) {
            for(unsigned i=0;i<8;++i)depth_guard[i]=0x13572460u+i;
            c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_OMGetRenderTargets,context,{n,0,address(depth_guard)});
            require(depth_guard[0]==0,"scalar DSV output with zero/eight RTVs");
            for(unsigned i=1;i<8;++i)require(depth_guard[i]==0x13572460u+i,"scalar DSV overwrote adjacent guest memory");
        }
        D3D11_SAMPLER_DESC sd={};sd.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;
        sd.AddressU=sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;sd.MaxAnisotropy=1;sd.ComparisonFunc=D3D11_COMPARISON_NEVER;sd.MaxLOD=D3D11_FLOAT32_MAX;
        uint32_t sampler=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateSamplerState,device,{wire(sd),address(out)},out);
        auto sample_in=allocate<uint32_t>(12),sample_out=allocate<uint32_t>(12);
        for(unsigned i=0;i<12;++i)sample_in[i]=i%3?sampler:0;
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_PSSetSamplers,context,{0,12,address(sample_in)});
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_PSGetSamplers,context,{0,12,address(sample_out)});
        for(unsigned i=0;i<12;++i){require(sample_out[i]==sample_in[i],"native sampler output identity");if(sample_out[i])c.release(sample_out[i]);sample_in[i]=0;}
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_PSSetSamplers,context,{0,12,address(sample_in)});c.release(sampler);
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_RSGetViewports,context,{address(count),address(observed_viewport)});require(*count==1&&observed_viewport->Width==1280);
        c.reject(SD_COM_IF_ID3D11Buffer,SD_COM_M_ID3D11Buffer_GetDesc,ps,{desc});
        auto multithread=query(c,context,__uuidof(ID3D10Multithread));
        c.call(SD_COM_IF_ID3D10Multithread,SD_COM_M_ID3D10Multithread_Enter,multithread);
        std::vector<std::thread> workers;std::atomic<unsigned> ready{0};std::atomic<bool> worker_failed{false};
        for(unsigned n=1;n<=4;++n)workers.emplace_back([&,n]{++ready;try{Client worker(n);for(unsigned i=0;i<500;++i){worker.call(SD_COM_IF_IUnknown,1,dynamic);worker.release(dynamic);++thread_pairs;}}catch(...){worker_failed=true;}});
        while(ready.load()!=4)std::this_thread::yield();
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Draw,context,{3,0});
        c.call(SD_COM_IF_ID3D10Multithread,SD_COM_M_ID3D10Multithread_Leave,multithread);for(auto& t:workers)t.join();require(!worker_failed&&thread_pairs==2000,"concurrent references and held Enter");c.release(multithread);
        sd_com_swapchain32 sc={};sc.mode[0]=1280;sc.mode[1]=720;sc.mode[2]=60;sc.mode[3]=1;sc.mode[4]=DXGI_FORMAT_R8G8B8A8_UNORM;
        sc.sample[0]=1;sc.usage=DXGI_USAGE_RENDER_TARGET_OUTPUT;sc.count=2;sc.window=0x12345678;sc.windowed=TRUE;sc.effect=DXGI_SWAP_EFFECT_DISCARD;
        uint32_t swap=c.create(SD_COM_IF_IDXGIFactory1,SD_COM_M_IDXGIFactory1_CreateSwapChain,factory,{device,wire(sc),address(out)},out);
        auto observed=allocate<sd_com_swapchain32>();c.call(SD_COM_IF_IDXGISwapChain,SD_COM_M_IDXGISwapChain_GetDesc,swap,{address(observed)});require(observed->window==sc.window&&observed->mode[0]==1280&&observed->mode[1]==720);
        uint32_t back=c.create(SD_COM_IF_IDXGISwapChain,SD_COM_M_IDXGISwapChain_GetBuffer,swap,{0,wire(__uuidof(ID3D11Texture2D)),address(out)},out);
        uint32_t back_view=c.create(SD_COM_IF_ID3D11Device,SD_COM_M_ID3D11Device_CreateRenderTargetView,device,{back,0,address(out)},out);
        *reinterpret_cast<uint32_t*>(uintptr_t(view_array))=back_view;
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_OMSetRenderTargets,context,{1,view_array,0});
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Draw,context,{3,0});image(c,context,back,staging);
        require(c.call(SD_COM_IF_IDXGISwapChain,SD_COM_M_IDXGISwapChain_Present,swap,{1,DXGI_PRESENT_TEST})==0);require(presented==0,"test Present must not count as frames");
        auto start=std::chrono::steady_clock::now();for(unsigned i=0;i<60;++i){c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Draw,context,{3,0});require(c.call(SD_COM_IF_IDXGISwapChain,SD_COM_M_IDXGISwapChain_Present,swap,{1,0})==0);}require(presented==60);
        auto elapsed=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-start).count();
        c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_ClearState,context);c.call(SD_COM_IF_ID3D11DeviceContext,SD_COM_M_ID3D11DeviceContext_Flush,context);
        for(auto token:{back_view,back,swap,staging,view,target,raster,vs,ps,bc,bc_staging,update_target,immutable,readback,dynamic,output,adapter,factory,context,device})c.release(token);
        c.reject(SD_COM_IF_IUnknown,1,dynamic);
        auto stats=allocate<uint32_t>(8);c.call(0,SD_COM_STATS,0,{address(stats)});require(stats[3]==0&&stats[4]==0,"no live external interfaces or maps");require(stats[2]==60&&stats[6]==7,"only intentional bridge failures");
        auto calls=stats[0];sd_com_shutdown();c.reject(SD_COM_IF_IUnknown,1,device);
        std::printf("{\"status\":\"PASS\",\"checks\":%u,\"rejected_requests\":%u,\"pixels_verified\":%u,\"buffer_bytes_verified\":%u,\"mip_array_bytes_verified\":%u,\"present_calls\":60,\"synthetic_present_elapsed_us\":%lld,\"concurrent_reference_pairs\":%u,\"bridge_calls\":%u,\"live_interfaces\":0,\"live_maps\":0,\"permission_queries\":%u,\"hardware_tested\":false,\"com_guest_execution_tested\":false,\"game_integration_tested\":false,\"game_fps_measured\":false}\n",checks.load(),rejections,verified_pixels,verified_bytes,verified_bc,(long long)elapsed,thread_pairs.load(),calls,permissions.load());
        require(munmap(arena,arena_bytes)==0);arena=nullptr;
    }catch(const std::exception& e){std::fprintf(stderr,"H4 host fixture: %s\n",e.what());return 1;}
}
