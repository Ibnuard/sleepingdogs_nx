/* SPDX-License-Identifier: MIT; original FEXTendo controlled PE32 diagnostic.
 * One caller-owned arena/session, offscreen rendering only. No game COM proxy.
 * The caller must retain its VirtualAlloc arena until CLOSE has returned.
 */
#include "bridge_protocol.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <new>

extern "C" int virtual_check_buffer_for_read(const void*, size_t);
extern "C" int virtual_check_buffer_for_write(void*, size_t);
extern "C" void wine_nx_runtime_trace(const char*);

namespace {
constexpr int32_t success=0, invalid_parameter=int32_t(0xc000000du);
constexpr int32_t invalid_handle=int32_t(0xc0000008u), no_memory=int32_t(0xc0000017u);
constexpr int32_t access_violation=int32_t(0xc0000005u);
constexpr int32_t not_implemented=int32_t(0x80004001u);
std::mutex mutex;
void* session=nullptr;
uint32_t arena_base=0, generation=1;
uint64_t calls=0;

bool accessible(void* pointer, uint32_t bytes) {
    uintptr_t address=reinterpret_cast<uintptr_t>(pointer);
    if(!bytes || address<0x10000 || address>0xffffffffu || uint64_t(address)+bytes>(uint64_t(1)<<32)) return false;
    return virtual_check_buffer_for_read(pointer,bytes) && virtual_check_buffer_for_write(pointer,bytes);
}
bool contained(uint32_t address, uint32_t bytes) {
    return bytes && address>=arena_base && uint64_t(address)+bytes<=uint64_t(arena_base)+SD_NDX_BRIDGE_ARENA_BYTES;
}
void log(const char* stage, uint32_t value) {
    char line[192];
    std::snprintf(line,sizeof(line),"[SD-NDX-H2] %s value=0x%08x calls=%llu; real guest pointers, offscreen only",stage,value,(unsigned long long)calls);
    wine_nx_runtime_trace(line);
}

int32_t initialize(void* args) {
    std::lock_guard<std::mutex> guard(mutex);
    if(!accessible(args,sizeof(sd_ndx_bridge_init))) return access_violation;
    auto request=*static_cast<sd_ndx_bridge_init*>(args);
    static_cast<sd_ndx_bridge_init*>(args)->session=0;
    if(request.abi!=SD_NDX_BRIDGE_ABI || request.session || session ||
       request.bytes!=SD_NDX_BRIDGE_ARENA_BYTES || (request.arena&0xffffu)) return invalid_parameter;
    void* arena=reinterpret_cast<void*>(uintptr_t(request.arena));
    if(!accessible(arena,request.bytes)) return access_violation;
    // DXVK is only initialized by this explicit diagnostic entry point.
    if(setenv("DXVK_WSI_DRIVER","FEXTendoProbe",1)) return no_memory;
    session=sd_ndx_session_create(arena,request.arena,request.bytes,nullptr);
    if(!session) return no_memory;
    arena_base=request.arena;calls=0;
    static_cast<sd_ndx_bridge_init*>(args)->session=generation;
    log("INIT guest/native shared arena",arena_base);
    return success;
}

int32_t dispatch(void* args) {
    std::lock_guard<std::mutex> guard(mutex);
    if(!accessible(args,sizeof(sd_ndx_bridge_dispatch))) return access_violation;
    auto request=*static_cast<sd_ndx_bridge_dispatch*>(args);
    static_cast<sd_ndx_bridge_dispatch*>(args)->hresult=not_implemented;
    if(request.abi!=SD_NDX_BRIDGE_ABI) return invalid_parameter;
    if(!session || request.session!=generation) return invalid_handle;
    if((request.packet&3u) || !contained(request.packet,sizeof(sd_ndx_packet)) ||
       uint64_t(request.packet)+sizeof(sd_ndx_packet)>uint64_t(arena_base)+SD_NDX_BRIDGE_METADATA_BYTES) return invalid_parameter;
    void* pointer=reinterpret_cast<void*>(uintptr_t(request.packet));
    if(!accessible(pointer,sizeof(sd_ndx_packet))) return access_violation;
    // Controlled H2 caller retains this allocation until CLOSE. Recheck all
    // pages before dereferencing shaders or active Map shadows. This does not
    // pin memory against concurrent VirtualFree; that needs a production ABI.
    if(!accessible(reinterpret_cast<void*>(uintptr_t(arena_base)),SD_NDX_BRIDGE_ARENA_BYTES)) return access_violation;
    sd_ndx_packet packet;
    std::memcpy(&packet,pointer,sizeof(packet));
    // A map may not overwrite the reserved request/response metadata page.
    if(packet.op==SD_NDX_MAP && packet.args[0]<uint64_t(arena_base)+SD_NDX_BRIDGE_METADATA_BYTES) return invalid_parameter;
    int32_t hr=not_implemented;
    if(packet.op!=SD_NDX_CREATE_SWAPCHAIN && packet.op!=SD_NDX_GET_BACKBUFFER && packet.op!=SD_NDX_PRESENT)
        hr=sd_ndx_dispatch(session,&packet);
    else std::memset(packet.result,0,sizeof(packet.result));
    std::memcpy(pointer,&packet,sizeof(packet));
    static_cast<sd_ndx_bridge_dispatch*>(args)->hresult=hr;
    ++calls;
    if(packet.op==SD_NDX_CREATE_DEVICE || hr<0) log(hr<0?"D3D failure":"DEVICE",uint32_t(hr));
    return success;
}

int32_t close_session(void* args) {
    std::lock_guard<std::mutex> guard(mutex);
    if(!accessible(args,sizeof(sd_ndx_bridge_close))) return access_violation;
    auto request=*static_cast<sd_ndx_bridge_close*>(args);
    if(request.abi!=SD_NDX_BRIDGE_ABI || request.flags) return invalid_parameter;
    if(!session || request.session!=generation) return invalid_handle;
    sd_ndx_session_destroy(session);session=nullptr;arena_base=0;
    log("CLOSE",generation);
    if(++generation==0) generation=1;
    return success;
}
template<int32_t(*operation)(void*)> int32_t safe(void* args) {
    try { return operation(args); }
    catch(const std::bad_alloc&) { return no_memory; }
    catch(...) { return int32_t(0xc0000001u); }
}
}

extern "C" {
extern const sd_ndx_unix_entry wine_nx_sd_ndx_wow64_unix_funcs[]={safe<initialize>,safe<dispatch>,safe<close_session>};
extern const unsigned int wine_nx_sd_ndx_wow64_unix_count=3;
}
