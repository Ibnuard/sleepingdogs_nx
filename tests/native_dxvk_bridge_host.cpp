/* SPDX-License-Identifier: MIT; H2 host regression fixture.
 * Real DXVK/lavapipe + low-address mmap; modeled Wine permission callbacks.
 * Direct unix-entry calls: this does NOT test Wine/FEX's actual WOW64 gate.
 */
#include "bridge_protocol.h"
#include "../src/native_dxvk/probe_shaders.h"
#include <sys/mman.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <initializer_list>

namespace {
constexpr uint32_t base=0x10000000, bytes=SD_NDX_BRIDGE_ARENA_BYTES;
unsigned checks=0,rejected=0,pixels=0,permission_queries=0;
bool deny=false;
unsigned char* arena=nullptr;
bool permission(const void* p,size_t n) {
    ++permission_queries;uintptr_t a=reinterpret_cast<uintptr_t>(p);
    return !deny && a>=base && a<=uint64_t(base)+bytes && n<=uint64_t(base)+bytes-a;
}
void require(bool ok) { ++checks;if(!ok)throw std::runtime_error("H2 bridge check failed"); }
void reject(int32_t status) { require(status<0);++rejected; }
sd_ndx_packet* packet;
sd_ndx_bridge_init* init;
sd_ndx_bridge_dispatch* dispatch;
sd_ndx_bridge_close* close;
uint32_t token;
int32_t call(uint32_t op,uint32_t object=0,std::initializer_list<uint32_t> args={}) {
    *packet={};packet->abi=SD_NDX_ABI;packet->op=op;packet->object=object;
    unsigned n=0;for(auto a:args)packet->args[n++]=a;
    *dispatch={SD_NDX_BRIDGE_ABI,token,base+256,0};
    require(wine_nx_sd_ndx_wow64_unix_funcs[SD_NDX_BRIDGE_DISPATCH](dispatch)==0);
    return dispatch->hresult;
}
uint32_t create(uint32_t op,std::initializer_list<uint32_t> args) { require(call(op,0,args)==0);require(packet->result[0]!=0);return packet->result[0]; }
}
extern "C" int virtual_check_buffer_for_read(const void* p,size_t n) { return permission(p,n); }
extern "C" int virtual_check_buffer_for_write(void* p,size_t n) { return permission(p,n); }
extern "C" void wine_nx_runtime_trace(const char* s) { std::fprintf(stderr,"%s\n",s); }

int main() {
    try {
        arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(uintptr_t(base)),bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
        require(arena!=MAP_FAILED && uintptr_t(arena)==base);
        init=reinterpret_cast<sd_ndx_bridge_init*>(arena+16);
        dispatch=reinterpret_cast<sd_ndx_bridge_dispatch*>(arena+64);
        close=reinterpret_cast<sd_ndx_bridge_close*>(arena+96);
        packet=reinterpret_cast<sd_ndx_packet*>(arena+256);
        require(wine_nx_sd_ndx_wow64_unix_count==3);
        reject(wine_nx_sd_ndx_wow64_unix_funcs[0](nullptr));
        unsigned before=permission_queries;
        reject(wine_nx_sd_ndx_wow64_unix_funcs[0](reinterpret_cast<void*>(uintptr_t(0x100000000ull))));
        require(before==permission_queries); /* high pointer never dereferenced */
        *init={0,base,bytes,0};reject(wine_nx_sd_ndx_wow64_unix_funcs[0](init));
        *init={SD_NDX_BRIDGE_ABI,base+4,bytes,0};reject(wine_nx_sd_ndx_wow64_unix_funcs[0](init));
        *init={SD_NDX_BRIDGE_ABI,base,bytes-1,0};reject(wine_nx_sd_ndx_wow64_unix_funcs[0](init));
        *init={SD_NDX_BRIDGE_ABI,base,bytes,0};deny=true;reject(wine_nx_sd_ndx_wow64_unix_funcs[0](init));deny=false;
        require(wine_nx_sd_ndx_wow64_unix_funcs[0](init)==0);token=init->session;require(token!=0);
        *init={SD_NDX_BRIDGE_ABI,base,bytes,0};reject(wine_nx_sd_ndx_wow64_unix_funcs[0](init));
        *dispatch={SD_NDX_BRIDGE_ABI,token,base+4096,0};reject(wine_nx_sd_ndx_wow64_unix_funcs[1](dispatch));
        dispatch->packet=base+257;reject(wine_nx_sd_ndx_wow64_unix_funcs[1](dispatch));
        dispatch->packet=0xfffffff0u;reject(wine_nx_sd_ndx_wow64_unix_funcs[1](dispatch));
        require(call(SD_NDX_CREATE_DEVICE)==0);require(packet->result[0]==0xb000);
        reject(call(SD_NDX_CREATE_DEVICE));
        reject(call(SD_NDX_CREATE_SWAPCHAIN,0,{1280,720}));
        reject(call(SD_NDX_PRESENT));
        uint32_t dynamic=create(SD_NDX_CREATE_BUFFER,{1024,2,1,0x10000});
        uint32_t staging=create(SD_NDX_CREATE_BUFFER,{1024,3,0,0x20000});
        *packet={};packet->abi=SD_NDX_ABI;packet->op=SD_NDX_MAP;packet->object=dynamic;packet->args[0]=base+256;
        *dispatch={SD_NDX_BRIDGE_ABI,token,base+256,0};reject(wine_nx_sd_ndx_wow64_unix_funcs[1](dispatch));
        require(call(SD_NDX_MAP,dynamic,{base+0x10000,1024,4})==0);
        for(unsigned i=0;i<1024;++i)arena[0x10000+i]=uint8_t(i*37+11);
        require(call(SD_NDX_UNMAP,dynamic)==0);require(call(SD_NDX_COPY,staging,{dynamic})==0);
        require(call(SD_NDX_MAP,staging,{base+0x100000,1024,1})==0);
        require(std::memcmp(arena+0x10000,arena+0x100000,1024)==0);
        require(call(SD_NDX_UNMAP,staging)==0);
        require(call(SD_NDX_RELEASE,dynamic)==0);reject(call(SD_NDX_RELEASE,dynamic));require(call(SD_NDX_RELEASE,staging)==0);
        std::memcpy(arena+0x20000,probe_vs,sizeof(probe_vs));std::memcpy(arena+0x21000,probe_ps,sizeof(probe_ps));
        uint32_t vs=create(SD_NDX_CREATE_VS,{base+0x20000,sizeof(probe_vs)});
        uint32_t ps=create(SD_NDX_CREATE_PS,{base+0x21000,sizeof(probe_ps)});
        uint32_t target=create(SD_NDX_CREATE_TEXTURE,{1280,720,0,0x20,0});
        require(call(SD_NDX_CREATE_RTV,target)==0);uint32_t view=packet->result[0];require(view!=0);
        uint32_t image=create(SD_NDX_CREATE_TEXTURE,{1280,720,3,0,0x20000});
        require(call(SD_NDX_SET_PIPELINE,0,{vs,ps,view,1280,720})==0);require(call(SD_NDX_DRAW,0,{3,0})==0);
        require(call(SD_NDX_COPY,image,{target})==0);require(call(SD_NDX_MAP,image,{base+0x100000,6*1024*1024,1})==0);
        uint32_t pitch=packet->result[1];require(pitch>=5120 && pitch<=6*1024*1024/720 && packet->result[3]==pitch*720);
        const unsigned expected[]={64,128,191,255};
        for(unsigned y=0;y<720;++y)for(unsigned x=0;x<1280;++x) {
            auto* p=arena+0x100000+y*pitch+x*4;
            for(unsigned c=0;c<4;++c)require(std::abs(int(p[c])-int(expected[c]))<=1);
            ++pixels;
        }
        require(call(SD_NDX_UNMAP,image)==0);require(call(SD_NDX_CLEAR_STATE)==0);
        for(auto resource:{view,image,target,vs,ps})require(call(SD_NDX_RELEASE,resource)==0);
        *close={SD_NDX_BRIDGE_ABI,token,0};require(wine_nx_sd_ndx_wow64_unix_funcs[2](close)==0);
        reject(wine_nx_sd_ndx_wow64_unix_funcs[2](close));
        *init={SD_NDX_BRIDGE_ABI,base,bytes,0};require(wine_nx_sd_ndx_wow64_unix_funcs[0](init)==0);
        require(init->session!=token);*dispatch={SD_NDX_BRIDGE_ABI,token,base+256,0};reject(wine_nx_sd_ndx_wow64_unix_funcs[1](dispatch));
        close->session=init->session;require(wine_nx_sd_ndx_wow64_unix_funcs[2](close)==0);
        require(munmap(arena,bytes)==0);
        std::printf("{\"status\":\"PASS\",\"checks\":%u,\"rejected_requests\":%u,\"draw_pixels_verified\":%u,\"buffer_bytes_verified\":1024,\"wine_permission_callbacks\":\"modeled fixture\",\"wow64_gate_tested\":false,\"fex_guest_tested\":false,\"software_vulkan\":true,\"game_fps_measured\":false}\n",checks,rejected,pixels);
    } catch(const std::exception& e) { std::fprintf(stderr,"%s\n",e.what());return 1; }
}
