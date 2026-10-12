/* SPDX-License-Identifier: MIT; trusted Horizon window for H3 only.
 * Runtime releases the console framebuffer BEFORE prepare. No guest HWND or
 * guest-controlled pointer is accepted as an NWindow. libnx owns its lifetime.
 */
#include "present_protocol.h"
#include <switch.h>
#include <cstdio>

extern "C" void wine_nx_runtime_trace(const char*);
namespace { NWindow* window=nullptr; }

extern "C" int sd_ndx_h3_window_prepare(void) {
    if(appletGetAppletType()!=AppletType_Application) return 0;
    auto* candidate=nwindowGetDefault();
    if(!nwindowIsValid(candidate) || R_FAILED(nwindowSetDimensions(candidate,1280,720))) return 0;
    window=candidate;
    char line[192];
    std::snprintf(line,sizeof(line),"[SD-NDX-H3] trusted NWindow=%p 1280x720; console framebuffer released; no guest HWND",window);
    wine_nx_runtime_trace(line);
    return 1;
}
extern "C" void* sd_ndx_h3_native_window(void) { return window; }
extern "C" uint64_t sd_ndx_h3_clock_ns(void) { return armTicksToNs(armGetSystemTick()); }
