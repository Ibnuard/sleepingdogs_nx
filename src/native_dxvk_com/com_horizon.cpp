/* SPDX-License-Identifier: MIT; Horizon window and native-frame diagnostics. */
#include "com_protocol.h"
#include <switch.h>
#include <cstdio>
#include <mutex>
extern "C" void wine_nx_runtime_trace(const char*);
extern "C" void wine_nx_sd_com_first_present(void);
namespace { NWindow* window=nullptr;std::mutex metrics_mutex; }
extern "C" void* sd_com_native_window(void) {
    if(window)return window;
    auto type=appletGetAppletType();
    if(type!=AppletType_Application){
        char line[128];std::snprintf(line,sizeof(line),"[SD-NDX-WINDOW] FAIL stage=applet type=%d; Application required",int(type));wine_nx_runtime_trace(line);return nullptr;
    }
    NWindow* candidate=nwindowGetDefault();
    if(!nwindowIsValid(candidate)){wine_nx_runtime_trace("[SD-NDX-WINDOW] FAIL stage=invalid-default-window");return nullptr;}
    Result rc=nwindowSetDimensions(candidate,1280,720);
    char line[192];std::snprintf(line,sizeof(line),"[SD-NDX-WINDOW] dimensions rc=%08x slots=%llx connected=%d size=%ux%u",
        rc,(unsigned long long)candidate->slots_configured,int(candidate->is_connected),candidate->width,candidate->height);wine_nx_runtime_trace(line);
    if(R_FAILED(rc))return nullptr;
    window=candidate;wine_nx_runtime_trace("[SD-NDX-COM] trusted Horizon NWindow 1280x720; guest HWND is metadata only");return window;
}
extern "C" uint64_t sd_com_clock_ns(void){return armTicksToNs(armGetSystemTick());}
extern "C" uint64_t sd_com_thread_id(void){return threadGetCurHandle();}
extern "C" void sd_com_presented(uint32_t token,int32_t result) {
    if(result)return;
    std::lock_guard<std::mutex> guard(metrics_mutex);
    static uint32_t last_token=0;static uint64_t previous=0,sum=0,count=0,minimum=UINT64_MAX,maximum=0,total=0;
    uint64_t now=sd_com_clock_ns();
    if(last_token!=token){previous=sum=count=maximum=0;minimum=UINT64_MAX;last_token=token;}
    if(previous&&now>=previous){uint64_t gap=now-previous;sum+=gap;++count;minimum=minimum<gap?minimum:gap;maximum=maximum>gap?maximum:gap;}
    previous=now;
    if(++total==1){wine_nx_runtime_trace("[SD-NDX-COM] FIRST_PRESENT real COM path; game/probe identified by runtime target");wine_nx_sd_com_first_present();}
    if(count>=600) {
        char line[240];std::snprintf(line,sizeof(line),"[SD-NDX-FPS] swapchain=%08x intervals=%llu elapsed_us=%llu mean_frame_us=%llu min_us=%llu max_us=%llu total_presents=%llu LSFG=OFF",
            token,(unsigned long long)count,(unsigned long long)(sum/1000),(unsigned long long)(sum/count/1000),
            (unsigned long long)(minimum/1000),(unsigned long long)(maximum/1000),(unsigned long long)total);
        wine_nx_runtime_trace(line);count=sum=maximum=0;minimum=UINT64_MAX;
    }
}
extern "C" void sd_com_native_worker(const char* name) {
    u64 mask=0;s32 ideal=0,priority=0;Handle thread=threadGetCurHandle();
    Result core=svcGetThreadCoreMask(&ideal,&mask,thread);Result prio=svcGetThreadPriority(&priority,thread);
    char line[224];std::snprintf(line,sizeof(line),"[SD-NDX-WORKER] name=%s handle=%u ideal=%d mask=%llx priority=%d query=%08x/%08x; native host thread, outside FEX guest registry",
        name?name:"?",thread,ideal,(unsigned long long)mask,priority,core,prio);wine_nx_runtime_trace(line);
}
