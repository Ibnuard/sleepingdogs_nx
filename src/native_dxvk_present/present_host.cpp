/* SPDX-License-Identifier: MIT; original H3 PE32/native present diagnostic.
 * The single controlled caller retains its arena until CLOSE returns.
 * No memory pinning, game COM proxy or arbitrary guest HWND is implemented.
 */
#include "present_protocol.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <new>

extern "C" int virtual_check_buffer_for_read(const void*,size_t);
extern "C" int virtual_check_buffer_for_write(void*,size_t);
extern "C" void wine_nx_runtime_trace(const char*);

namespace {
constexpr int32_t success=0, invalid_parameter=int32_t(0xc000000du);
constexpr int32_t invalid_handle=int32_t(0xc0000008u), no_memory=int32_t(0xc0000017u);
constexpr int32_t access_violation=int32_t(0xc0000005u);
constexpr int32_t not_implemented=int32_t(0x80004001u), invalid_argument=int32_t(0x80070057u);
std::mutex mutex;
void* session=nullptr;
uint32_t arena_base=0,generation=1,swap_token=0,presents=0,arena_scans=0;
uint64_t calls=0,first_present_ns=0,last_present_ns=0,bridge_ns=0,renderer_ns=0;

bool accessible(void* pointer,uint32_t bytes) {
    uintptr_t address=reinterpret_cast<uintptr_t>(pointer);
    if(!bytes || address<0x10000 || address>0xffffffffu || uint64_t(address)+bytes>(uint64_t(1)<<32)) return false;
    return virtual_check_buffer_for_read(pointer,bytes) && virtual_check_buffer_for_write(pointer,bytes);
}
bool contained(uint32_t address,uint32_t bytes) {
    return bytes && address>=arena_base && uint64_t(address)+bytes<=uint64_t(arena_base)+SD_NDX_BRIDGE_ARENA_BYTES;
}
uint32_t microseconds(uint64_t ns) { return uint32_t(ns/1000>UINT32_MAX?UINT32_MAX:ns/1000); }
void log(const char* stage,uint32_t value) {
    char line[240];
    std::snprintf(line,sizeof(line),"[SD-NDX-H3] %s value=0x%08x calls=%llu presents=%u arena_scans=%u; real guest pointers, synthetic 720p only",
        stage,value,(unsigned long long)calls,presents,arena_scans);
    wine_nx_runtime_trace(line);
}
void destroy_locked(const char* reason) {
    sd_ndx_session_destroy(session);session=nullptr;arena_base=0;swap_token=0;
    log(reason,generation);
    if(++generation==0)generation=1;
}
int32_t initialize(void* args) {
    std::lock_guard<std::mutex> guard(mutex);
    if(!accessible(args,sizeof(sd_ndx_bridge_init))) return access_violation;
    auto request=*static_cast<sd_ndx_bridge_init*>(args);
    static_cast<sd_ndx_bridge_init*>(args)->session=0;
    if(request.abi!=SD_NDX_BRIDGE_ABI || request.session || session ||
       request.bytes!=SD_NDX_BRIDGE_ARENA_BYTES || (request.arena&0xffffu)) return invalid_parameter;
    auto* arena=reinterpret_cast<void*>(uintptr_t(request.arena));
    if(!accessible(arena,request.bytes)) return access_violation;
    void* window=sd_ndx_h3_native_window();
    if(!window) return invalid_handle;
    if(setenv("DXVK_WSI_DRIVER","FEXTendoProbe",1)) return no_memory;
    session=sd_ndx_session_create(arena,request.arena,request.bytes,window);
    if(!session) return no_memory;
    arena_base=request.arena;calls=0;swap_token=0;presents=0;arena_scans=1;
    first_present_ns=last_present_ns=bridge_ns=renderer_ns=0;
    static_cast<sd_ndx_bridge_init*>(args)->session=generation;
    log("INIT guest/native shared arena",arena_base);
    return success;
}
int32_t dispatch(void* args) {
    const uint64_t begin=sd_ndx_h3_clock_ns();
    std::lock_guard<std::mutex> guard(mutex);
    if(!accessible(args,sizeof(sd_ndx_bridge_dispatch))) return access_violation;
    auto request=*static_cast<sd_ndx_bridge_dispatch*>(args);
    static_cast<sd_ndx_bridge_dispatch*>(args)->hresult=not_implemented;
    if(request.abi!=SD_NDX_BRIDGE_ABI) return invalid_parameter;
    if(!session || request.session!=generation) return invalid_handle;
    if((request.packet&3u) || !contained(request.packet,sizeof(sd_ndx_packet)) ||
       uint64_t(request.packet)+sizeof(sd_ndx_packet)>uint64_t(arena_base)+SD_NDX_BRIDGE_METADATA_BYTES) return invalid_parameter;
    auto* pointer=reinterpret_cast<void*>(uintptr_t(request.packet));
    if(!accessible(pointer,sizeof(sd_ndx_packet))) return access_violation;
    sd_ndx_packet packet;std::memcpy(&packet,pointer,sizeof(packet));
    if(packet.abi!=SD_NDX_ABI || packet.flags) return invalid_parameter;
    if(packet.op==SD_NDX_MAP && packet.args[0]<uint64_t(arena_base)+SD_NDX_BRIDGE_METADATA_BYTES) return invalid_parameter;
    // Draw/Present use host-owned object tokens and never dereference payloads.
    // Retain full Wine page checks for every operation touching arena payloads
    // (including active Unmap shadows). The controlled caller must not unmap
    // concurrently: these checks still do not pin memory for production use.
    if(packet.op==SD_NDX_MAP || packet.op==SD_NDX_UNMAP ||
       packet.op==SD_NDX_CREATE_VS || packet.op==SD_NDX_CREATE_PS) {
        if(!accessible(reinterpret_cast<void*>(uintptr_t(arena_base)),SD_NDX_BRIDGE_ARENA_BYTES)) return access_violation;
        ++arena_scans;
    }
    const uint64_t validated=sd_ndx_h3_clock_ns();
    int32_t hr=invalid_argument;
    std::memset(packet.result,0,sizeof(packet.result));
    if(packet.op==SD_NDX_H3_STATS) {
        if(!packet.object && packet.args[0]<=1) {
            hr=success;
            if(!packet.args[0]) {
                packet.result[0]=presents;
                packet.result[1]=microseconds(presents?last_present_ns-first_present_ns:0);
                packet.result[2]=arena_scans;packet.result[3]=uint32_t(calls+1);
            } else {
                packet.result[0]=microseconds(bridge_ns);
                packet.result[1]=microseconds(renderer_ns);
                packet.result[2]=uint32_t(calls+1);
            }
        }
    } else if(packet.op==SD_NDX_CREATE_SWAPCHAIN && swap_token) {
        // One swapchain per diagnostic session, even after explicit Release.
        hr=invalid_argument;
    } else {
        if(packet.op==SD_NDX_PRESENT && !presents) first_present_ns=sd_ndx_h3_clock_ns();
        hr=sd_ndx_dispatch(session,&packet);
        if(hr==0 && packet.op==SD_NDX_CREATE_SWAPCHAIN)swap_token=packet.result[0];
        if(hr==0 && packet.op==SD_NDX_PRESENT) { ++presents;last_present_ns=sd_ndx_h3_clock_ns(); }
    }
    const uint64_t rendered=sd_ndx_h3_clock_ns();
    std::memcpy(pointer,&packet,sizeof(packet));
    static_cast<sd_ndx_bridge_dispatch*>(args)->hresult=hr;
    ++calls;renderer_ns+=rendered-validated;
    bridge_ns+=validated-begin+sd_ndx_h3_clock_ns()-rendered;
    if(packet.op==SD_NDX_CREATE_DEVICE || hr<0 ||
       (packet.op==SD_NDX_PRESENT && (presents==1 || presents%60==0)))
        log(hr<0?"D3D failure":packet.op==SD_NDX_PRESENT?"PRESENT":"DEVICE",uint32_t(hr));
    return success;
}
int32_t close_session(void* args) {
    std::lock_guard<std::mutex> guard(mutex);
    if(!accessible(args,sizeof(sd_ndx_bridge_close))) return access_violation;
    auto request=*static_cast<sd_ndx_bridge_close*>(args);
    if(request.abi!=SD_NDX_BRIDGE_ABI || request.flags) return invalid_parameter;
    if(!session || request.session!=generation) return invalid_handle;
    destroy_locked("CLOSE");return success;
}
template<int32_t(*operation)(void*)> int32_t safe(void* args) {
    try {return operation(args);}
    catch(const std::bad_alloc&) {return no_memory;}
    catch(...) {return int32_t(0xc0000001u);}
}
}
extern "C" {
extern const sd_ndx_unix_entry wine_nx_sd_ndx_wow64_unix_funcs[]={safe<initialize>,safe<dispatch>,safe<close_session>};
extern const unsigned int wine_nx_sd_ndx_wow64_unix_count=3;
void sd_ndx_h3_shutdown(void) {
    std::lock_guard<std::mutex> guard(mutex);
    if(session) destroy_locked("EXIT cleanup");
}
}
