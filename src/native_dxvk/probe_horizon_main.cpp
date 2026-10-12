/* SPDX-License-Identifier: MIT; original FEXTendo standalone Horizon probe.
 * Tests the native renderer only; no Wine, FEX, game or LSFG is loaded.
 */
#include <switch.h>
#include "probe_protocol.h"
#include "probe_shaders.h"
#include <d3d11.h>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <initializer_list>
#include <stdexcept>
#include <vector>
#include <sys/stat.h>

namespace {
constexpr uint32_t base = 0x10000000, arena_size = 8*1024*1024;
constexpr uint32_t upload = base+0x10000, readback = base+0x100000;
const char* directory = "sdmc:/switch/sd-dxvk-native-probe";
FILE* log_file = nullptr;
uint64_t start_tick;
unsigned checks=0, frames=0;

void trace(const char* format, ...) {
    if (!log_file) return;
    std::fprintf(log_file,"[SD-NDX-H1] %.3f ",double(armTicksToNs(armGetSystemTick()-start_tick))/1e9);
    va_list args; va_start(args,format); std::vfprintf(log_file,format,args); va_end(args);
    std::fputc('\n',log_file); std::fflush(log_file);
}
void require(bool ok, const char* reason) {
    if (!ok) throw std::runtime_error(reason);
    ++checks;
}
struct Probe {
    std::vector<unsigned char> memory = std::vector<unsigned char>(arena_size);
    void* session = nullptr;
    explicit Probe(NWindow* window) {
        session = sd_ndx_session_create(memory.data(),base,arena_size,window);
        require(session != nullptr,"create-session");
        trace("arena native=%p guest=0x%08x bytes=%u",memory.data(),base,arena_size);
    }
    ~Probe() { sd_ndx_session_destroy(session); }
    sd_ndx_packet call(uint32_t op, uint32_t object=0, std::initializer_list<uint32_t> args={}) {
        sd_ndx_packet p={}; p.abi=SD_NDX_ABI; p.op=op; p.object=object;
        unsigned i=0; for (auto a:args) p.args[i++]=a;
        // Map and device creation are logged before dispatch so a hang has a location.
        if (op==SD_NDX_CREATE_DEVICE || op==SD_NDX_MAP || op==SD_NDX_CREATE_SWAPCHAIN)
            trace("dispatch op=%u object=0x%08x",op,object);
        int32_t hr=sd_ndx_dispatch(session,&p);
        if (hr<0) {
            trace("FAIL op=%u object=0x%08x HRESULT=0x%08x",op,object,uint32_t(hr));
            throw std::runtime_error("native-dispatch");
        }
        ++checks; return p;
    }
    void release(uint32_t token) { call(SD_NDX_RELEASE,token); }
    void run() {
        require(call(SD_NDX_CREATE_DEVICE).result[0]==D3D_FEATURE_LEVEL_11_0,"feature-level");
        trace("PASS device FL11_0");
        uint32_t dynamic=call(SD_NDX_CREATE_BUFFER,0,{1024,D3D11_USAGE_DYNAMIC,D3D11_BIND_VERTEX_BUFFER,D3D11_CPU_ACCESS_WRITE}).result[0];
        uint32_t staging=call(SD_NDX_CREATE_BUFFER,0,{1024,D3D11_USAGE_STAGING,0,D3D11_CPU_ACCESS_READ}).result[0];
        auto mapped=call(SD_NDX_MAP,dynamic,{upload,1024,D3D11_MAP_WRITE_DISCARD});
        require(mapped.result[0]==upload && mapped.result[3]==1024,"guest-map-layout");
        for(unsigned i=0;i<1024;++i) memory[upload-base+i]=static_cast<unsigned char>((i*37+11)&255);
        call(SD_NDX_UNMAP,dynamic); call(SD_NDX_COPY,staging,{dynamic});
        call(SD_NDX_MAP,staging,{readback,1024,D3D11_MAP_READ});
        require(std::memcmp(memory.data()+upload-base,memory.data()+readback-base,1024)==0,"buffer-readback");
        call(SD_NDX_UNMAP,staging);release(staging);release(dynamic);
        trace("PASS buffer shadow Map/Unmap/copy/readback bytes=1024");
        std::memcpy(memory.data()+0x20000,probe_vs,sizeof(probe_vs));
        std::memcpy(memory.data()+0x21000,probe_ps,sizeof(probe_ps));
        uint32_t vs=call(SD_NDX_CREATE_VS,0,{base+0x20000,sizeof(probe_vs)}).result[0];
        uint32_t ps=call(SD_NDX_CREATE_PS,0,{base+0x21000,sizeof(probe_ps)}).result[0];
        uint32_t target=call(SD_NDX_CREATE_TEXTURE,0,{1280,720,D3D11_USAGE_DEFAULT,D3D11_BIND_RENDER_TARGET,0}).result[0];
        uint32_t view=call(SD_NDX_CREATE_RTV,target).result[0];
        uint32_t image=call(SD_NDX_CREATE_TEXTURE,0,{1280,720,D3D11_USAGE_STAGING,0,D3D11_CPU_ACCESS_READ}).result[0];
        call(SD_NDX_SET_PIPELINE,0,{vs,ps,view,1280,720});call(SD_NDX_DRAW,0,{3,0});call(SD_NDX_COPY,image,{target});
        mapped=call(SD_NDX_MAP,image,{readback,6*1024*1024,D3D11_MAP_READ});
        require(mapped.result[0]==readback && mapped.result[1]>=5120 && mapped.result[3]==mapped.result[1]*720,"texture-map-layout");
        const unsigned expected[]={64,128,191,255};
        unsigned bad_pixels=0;
        for(unsigned y=0;y<720;++y) for(unsigned x=0;x<1280;++x) {
            const unsigned char* pixel=memory.data()+readback-base+size_t(y)*mapped.result[1]+x*4;
            bool bad=false;
            for(unsigned c=0;c<4;++c) bad |= std::abs(int(pixel[c])-int(expected[c]))>1;
            if(bad) {
                if(bad_pixels<4) trace("pixel mismatch x=%u y=%u rgba=%u,%u,%u,%u",x,y,pixel[0],pixel[1],pixel[2],pixel[3]);
                ++bad_pixels;
            }
        }
        call(SD_NDX_UNMAP,image);
        trace("draw readback pixels=921600 bad=%u row_pitch=%u",bad_pixels,mapped.result[1]);
        require(bad_pixels==0,"draw-readback");
        call(SD_NDX_CLEAR_STATE);release(view);release(image);release(target);
        uint32_t swap=call(SD_NDX_CREATE_SWAPCHAIN,0,{1280,720}).result[0];
        uint32_t back=call(SD_NDX_GET_BACKBUFFER,swap).result[0];
        view=call(SD_NDX_CREATE_RTV,back).result[0];
        call(SD_NDX_SET_PIPELINE,0,{vs,ps,view,1280,720});
        trace("present begin frames=300 interval=1; expected blue screen; PLUS cancels");
        PadState pad; padInitializeDefault(&pad);
        uint64_t begin=armGetSystemTick();
        for(unsigned i=0;i<300;++i) {
            if(!appletMainLoop()) throw std::runtime_error("applet-exit-request");
            padUpdate(&pad);
            if(padGetButtonsDown(&pad)&HidNpadButton_Plus) throw std::runtime_error("user-cancelled");
            call(SD_NDX_DRAW,0,{3,0});call(SD_NDX_PRESENT,swap,{1});++frames;
            if(frames==1 || frames%60==0) trace("present progress frames=%u",frames);
        }
        double seconds=double(armTicksToNs(armGetSystemTick()-begin))/1e9;
        trace("PASS present calls=%u seconds=%.3f; synthetic triangle, no game FPS measurement",frames,seconds);
        call(SD_NDX_CLEAR_STATE);release(view);release(back);release(swap);release(vs);release(ps);
    }
};
}

// Mesa's optional trace hooks are weak imports; route them to this probe log.
extern "C" void wine_nx_runtime_trace(const char* message) { trace("Mesa: %s",message?message:""); }

int main() {
    start_tick=armGetSystemTick();
    mkdir("sdmc:/switch",0777); mkdir(directory,0777);
    log_file=std::fopen("sdmc:/switch/sd-dxvk-native-probe/probe.log","w");
    if(!log_file) return 2;
    std::freopen("sdmc:/switch/sd-dxvk-native-probe/stderr.log","w",stderr);
    setvbuf(stderr,nullptr,_IONBF,0);
    trace("BEGIN native-dxvk-horizon-v1; game_integration=0 guest_execution=0");
    trace("applet_type=%d operation_mode=%d",int(appletGetAppletType()),int(appletGetOperationMode()));
    FILE* started=std::fopen("sdmc:/switch/sd-dxvk-native-probe/result.json","w");
    if(started) {
        std::fputs("{\"status\":\"RUNNING\",\"build\":\"native-dxvk-horizon-v1\",\"game_integration\":false,\"guest_execution\":false}\n",started);
        std::fclose(started);
    }
    bool success=false;
    try {
        require(appletGetAppletType()==AppletType_Application,"full-application-mode-required");
        setenv("DXVK_WSI_DRIVER","FEXTendoProbe",1);
        setenv("DXVK_LOG_PATH",directory,1);
        setenv("DXVK_STATE_CACHE_PATH",directory,1);
        setenv("DXVK_CONFIG_FILE","sdmc:/switch/sd-dxvk-native-probe/probe.conf",1);
        FILE* conf=std::fopen("sdmc:/switch/sd-dxvk-native-probe/probe.conf","w");
        require(conf!=nullptr,"write-config");
        std::fputs("# Isolated native diagnostic; no game overrides.\ndxvk.numCompilerThreads = 2\n",conf);std::fclose(conf);
        padConfigureInput(1,HidNpadStyleSet_NpadStandard);
        NWindow* window=nwindowGetDefault();
        require(nwindowIsValid(window),"native-window");
        require(R_SUCCEEDED(nwindowSetDimensions(window,1280,720)),"window-dimensions");
        trace("PASS native window 1280x720; default libnx heap");
        { Probe p(window);p.run(); }
        success=true;
        trace("PASS all checks=%u presents=%u",checks,frames);
    } catch(const std::exception& e) { trace("FAIL stage=%s checks=%u presents=%u",e.what(),checks,frames); }
    catch(...) { trace("FAIL unknown exception checks=%u presents=%u",checks,frames); }
    FILE* result=std::fopen("sdmc:/switch/sd-dxvk-native-probe/result.json","w");
    if(result) {
        std::fprintf(result,"{\"status\":\"%s\",\"build\":\"native-dxvk-horizon-v1\",\"checks\":%u,\"present_calls\":%u,\"game_integration\":false,\"guest_execution\":false,\"game_fps_measured\":false}\n",success?"PASS":"FAIL",checks,frames);
        std::fclose(result);
    }
    trace("END; exiting diagnostic");std::fclose(log_file);log_file=nullptr;
    return success?0:1;
}
