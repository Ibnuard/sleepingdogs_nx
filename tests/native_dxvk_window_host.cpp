/* SPDX-License-Identifier: MIT; runtime handoff regression with modeled libnx. */
#include <switch.h>
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <pthread.h>
#include <sched.h>
#include <string>
#include <vector>

extern "C" void* sd_com_native_window(void);
static pthread_mutex_t fx_handoff_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t fx_ui_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t wine_nx_fb_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_t fx_ui_thread;
static int fx_ui_created,fx_ui_owned,fx_ui_stop,wine_nx_console_active;
static constexpr int FX_FAILED=3;
static struct { int screen,fatal,debug; } fx_ui_view;
static NWindow native_window{};
static AppletType applet_type=AppletType_Application;
static bool valid_window=true;
static Result forced_result;
static unsigned get_calls,dimension_calls,console_exits,ui_closes,timestamp_starts;
static std::vector<std::string> lines;
// Synthetic result codes; the test does not claim libnx/Horizon numeric codes.
static constexpr Result BUSY_RESULT=0x1001,FORCED_RESULT=0x1002;

static void log_line(const char* format,...) {
    char line[512];va_list args;va_start(args,format);
    vsnprintf(line,sizeof(line),format,args);va_end(args);lines.emplace_back(line);
}
extern "C" void wine_nx_runtime_trace(const char* line){lines.emplace_back(line);}
extern "C" void wine_nx_sd_com_first_present(void){}
static void wine_nx_f1_crash_note(const char*){}
static void fx_timestamp_start(void){++timestamp_starts;}
AppletType appletGetAppletType(void){return applet_type;}
NWindow* nwindowGetDefault(void){++get_calls;return &native_window;}
bool nwindowIsValid(NWindow* value){return valid_window&&value==&native_window;}
Result nwindowSetDimensions(NWindow* value,uint32_t width,uint32_t height) {
    ++dimension_calls;
    if(forced_result)return forced_result;
    // libnx disallows resizing a window with configured framebuffer slots.
    if((value->width||value->height)&&value->slots_configured)return BUSY_RESULT;
    value->width=width;value->height=height;return 0;
}
static void consoleExit(void*) {
    assert(wine_nx_console_active);++console_exits;
    native_window.slots_configured=0;native_window.width=native_window.height=0;
}
u64 armGetSystemTick(void){return 0;}
u64 armTicksToNs(u64 ticks){return ticks;}
Handle threadGetCurHandle(void){return 1;}
Result svcGetThreadCoreMask(s32* ideal,u64* mask,Handle){*ideal=0;*mask=7;return 0;}
Result svcGetThreadPriority(s32* priority,Handle){*priority=44;return 0;}

// Actual functions extracted from the generated production runtime, unchanged.
#include "runtime_window.inc"

static void occupy_window(void) {
    native_window.slots_configured=3;native_window.width=1280;
    native_window.height=720;native_window.is_connected=true;
}
static void* ui_worker(void*) {
    while(!__atomic_load_n(&fx_ui_stop,__ATOMIC_ACQUIRE))sched_yield();
    native_window.slots_configured=0;native_window.width=native_window.height=0;
    ++ui_closes;__atomic_store_n(&fx_ui_owned,0,__ATOMIC_RELEASE);return nullptr;
}
static void start_ui(bool debug) {
    occupy_window();fx_ui_view.debug=debug;fx_ui_created=fx_ui_owned=1;
    assert(!pthread_create(&fx_ui_thread,nullptr,ui_worker,nullptr));
}
static bool logged(const char* value) {
    for(const auto& line:lines)if(line.find(value)!=std::string::npos)return true;
    return false;
}
int main(int argc,char** argv) {
    assert(argc==2);const std::string name=argv[1];
    if(name=="old-game-order") {
        start_ui(false);
        assert(sd_com_native_window()==nullptr);
        assert(dimension_calls==1&&fx_owned()&&ui_closes==0);
        assert(native_window.slots_configured==3);
        assert(logged("dimensions rc=00001001"));
        assert(fx_handoff());assert(ui_closes==1&&!fx_owned());
    } else if(name=="gui"||name=="debug") {
        start_ui(name=="debug");assert(sd_com_prepare_screen());
        assert(!fx_ui_created&&!fx_owned()&&ui_closes==1&&timestamp_starts==1);
        assert(dimension_calls==1&&!console_exits&&!native_window.slots_configured);
        assert(native_window.width==1280&&native_window.height==720);
        assert(logged("handoff complete launcher_owned=0 console_active=0"));
        assert(logged("dimensions rc=00000000"));
    } else if(name=="com-console") {
        occupy_window();wine_nx_console_active=1;assert(sd_com_prepare_screen());
        assert(console_exits==1&&!wine_nx_console_active&&!ui_closes);
        assert(dimension_calls==1&&!native_window.slots_configured);
        assert(logged("handoff complete launcher_owned=0 console_active=0"));
    } else if(name=="handoff-failed") {
        start_ui(true);fx_ui_view.fatal=1;assert(!sd_com_prepare_screen());
        assert(!get_calls&&!dimension_calls&&!console_exits&&!ui_closes&&fx_owned());
        assert(logged("FAIL stage=launcher-handoff"));
        fx_ui_view.fatal=0;assert(fx_handoff());
    } else if(name=="wrong-applet") {
        applet_type=AppletType_LibraryApplet;assert(!sd_com_prepare_screen());
        assert(!get_calls&&!dimension_calls&&logged("FAIL stage=applet"));
    } else if(name=="invalid-window") {
        valid_window=false;assert(!sd_com_prepare_screen());
        assert(get_calls==1&&!dimension_calls&&logged("FAIL stage=invalid-default-window"));
    } else if(name=="other-owner-busy") {
        occupy_window();assert(!sd_com_prepare_screen());
        assert(dimension_calls==1&&!console_exits&&!ui_closes);
        assert(native_window.slots_configured==3&&logged("dimensions rc=00001001"));
    } else if(name=="dimension-failure-retry") {
        forced_result=FORCED_RESULT;assert(!sd_com_prepare_screen());
        assert(dimension_calls==1&&logged("dimensions rc=00001002"));
        forced_result=0;assert(sd_com_prepare_screen());assert(dimension_calls==2);
    } else if(name=="cached-window") {
        assert(sd_com_prepare_screen());assert(dimension_calls==1);
        occupy_window();assert(sd_com_native_window()==&native_window);
        assert(dimension_calls==1&&native_window.slots_configured==3);
    } else {assert(false&&"unknown test");}
    assert(!fx_ui_created);printf("PASS %s\n",name.c_str());
}
