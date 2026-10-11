/* SPDX-License-Identifier: MIT; original FEXTendo DXVK correctness probe.
 * Xvfb/lavapipe validate rendering and marshaling, not Switch performance.
 */
#include "probe_protocol.h"
#include "probe_shaders.h"
#include <d3d11.h>
#include <xcb/xcb.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace {
constexpr uint32_t base = 0x10000000, arena_size = 8*1024*1024;
constexpr uint32_t upload = base+0x10000, readback = base+0x100000;
struct XcbWindow { xcb_connection_t* connection; xcb_window_t window; };
struct Probe {
    std::vector<unsigned char> memory = std::vector<unsigned char>(arena_size);
    XcbWindow window = {};
    void* session = nullptr;
    unsigned checks = 0, rejected = 0, frames = 0;
    Probe() {
        int screen_number = 0;
        window.connection = xcb_connect(nullptr, &screen_number);
        if (!window.connection || xcb_connection_has_error(window.connection)) throw std::runtime_error("XCB connection");
        auto it = xcb_setup_roots_iterator(xcb_get_setup(window.connection));
        for (int i=0; i<screen_number; ++i) xcb_screen_next(&it);
        auto* screen = it.data;
        window.window = xcb_generate_id(window.connection);
        uint32_t values[] = {screen->black_pixel, XCB_EVENT_MASK_STRUCTURE_NOTIFY};
        auto cookie = xcb_create_window_checked(window.connection, XCB_COPY_FROM_PARENT, window.window,
            screen->root, 0,0,1280,720,0,XCB_WINDOW_CLASS_INPUT_OUTPUT,screen->root_visual,
            XCB_CW_BACK_PIXEL|XCB_CW_EVENT_MASK,values);
        auto* error = xcb_request_check(window.connection, cookie);
        if (error) { std::free(error); throw std::runtime_error("XCB window"); }
        xcb_map_window(window.connection, window.window); xcb_flush(window.connection);
        session = sd_ndx_session_create(memory.data(), base, arena_size, &window);
        if (!session) throw std::runtime_error("create session");
    }
    ~Probe() {
        sd_ndx_session_destroy(session);
        if (window.connection) {
            if (window.window) xcb_destroy_window(window.connection, window.window);
            xcb_disconnect(window.connection);
        }
    }
    sd_ndx_packet packet(uint32_t op, uint32_t object=0, std::initializer_list<uint32_t> args={}) {
        sd_ndx_packet p = {}; p.abi = SD_NDX_ABI; p.op=op; p.object=object;
        unsigned i=0; for (auto arg : args) p.args[i++]=arg;
        return p;
    }
    sd_ndx_packet call(uint32_t op, uint32_t object=0, std::initializer_list<uint32_t> args={}) {
        auto p = packet(op, object, args);
        int32_t hr = sd_ndx_dispatch(session, &p);
        if (hr < 0) {
            char text[100]; std::snprintf(text,sizeof(text),"op %u failed HRESULT 0x%08x",op,uint32_t(hr));
            throw std::runtime_error(text);
        }
        ++checks; return p;
    }
    void reject(sd_ndx_packet p) {
        int32_t hr = sd_ndx_dispatch(session,&p);
        if (hr >= 0 || p.result[0] || p.result[1] || p.result[2] || p.result[3]) throw std::runtime_error("invalid request accepted");
        ++rejected;
    }
    void require(bool ok, const char* text) { if (!ok) throw std::runtime_error(text); ++checks; }
    uint32_t buffer(uint32_t bytes, uint32_t usage, uint32_t bind, uint32_t access) {
        return call(SD_NDX_CREATE_BUFFER,0,{bytes,usage,bind,access}).result[0];
    }
    uint32_t texture(uint32_t usage, uint32_t bind, uint32_t access, uint32_t width=1280, uint32_t height=720) {
        return call(SD_NDX_CREATE_TEXTURE,0,{width,height,usage,bind,access}).result[0];
    }
    void release(uint32_t token) { call(SD_NDX_RELEASE,token); }
};
}

int main() {
    setenv("DXVK_WSI_DRIVER","FEXTendoProbe",1);
    try {
        Probe p;
        p.require(uint64_t(reinterpret_cast<uintptr_t>(p.memory.data())) > UINT32_MAX,"test requires a host arena above 4 GiB");
        auto wrong = p.packet(SD_NDX_CREATE_DEVICE); wrong.abi=2; p.reject(wrong);
        wrong=p.packet(SD_NDX_CREATE_DEVICE); wrong.flags=1; p.reject(wrong);
        p.require(p.call(SD_NDX_CREATE_DEVICE).result[0] == D3D_FEATURE_LEVEL_11_0,"feature level");
        p.reject(p.packet(SD_NDX_CREATE_DEVICE));
        p.reject(p.packet(0xffffffff));
        p.reject(p.packet(SD_NDX_DRAW,0,{3,0}));
        p.reject(p.packet(SD_NDX_CREATE_BUFFER,0,{0,D3D11_USAGE_DYNAMIC,D3D11_BIND_VERTEX_BUFFER,D3D11_CPU_ACCESS_WRITE}));
        uint32_t dynamic=p.buffer(1024,D3D11_USAGE_DYNAMIC,D3D11_BIND_VERTEX_BUFFER,D3D11_CPU_ACCESS_WRITE);
        uint32_t staging=p.buffer(1024,D3D11_USAGE_STAGING,0,D3D11_CPU_ACCESS_READ);
        uint32_t small=p.buffer(512,D3D11_USAGE_STAGING,0,D3D11_CPU_ACCESS_READ);
        p.reject(p.packet(SD_NDX_COPY,small,{dynamic}));
        p.reject(p.packet(SD_NDX_COPY,dynamic,{dynamic}));
        p.reject(p.packet(SD_NDX_MAP,dynamic,{0xfffffff0,4096,D3D11_MAP_WRITE_DISCARD}));
        p.reject(p.packet(SD_NDX_MAP,dynamic,{base-1,1024,D3D11_MAP_WRITE_DISCARD}));
        p.reject(p.packet(SD_NDX_MAP,dynamic,{base+arena_size-512,1024,D3D11_MAP_WRITE_DISCARD}));
        p.reject(p.packet(SD_NDX_MAP,dynamic,{upload,128,D3D11_MAP_WRITE_DISCARD}));
        p.reject(p.packet(SD_NDX_MAP,dynamic,{upload,1024,D3D11_MAP_WRITE_NO_OVERWRITE}));
        auto mapped=p.call(SD_NDX_MAP,dynamic,{upload,1024,D3D11_MAP_WRITE_DISCARD});
        p.require(mapped.result[0]==upload && mapped.result[3]==1024,"map returns guest address and size");
        p.reject(p.packet(SD_NDX_MAP,dynamic,{upload,1024,D3D11_MAP_WRITE_DISCARD}));
        p.reject(p.packet(SD_NDX_RELEASE,dynamic));
        p.reject(p.packet(SD_NDX_COPY,staging,{dynamic}));
        for (unsigned i=0;i<1024;++i) p.memory[upload-base+i]=static_cast<unsigned char>((i*37+11)&255);
        p.call(SD_NDX_UNMAP,dynamic);
        p.reject(p.packet(SD_NDX_UNMAP,dynamic));
        p.call(SD_NDX_COPY,staging,{dynamic});
        mapped=p.call(SD_NDX_MAP,staging,{readback,1024,D3D11_MAP_READ});
        p.require(std::memcmp(p.memory.data()+upload-base,p.memory.data()+readback-base,1024)==0,"buffer readback mismatch");
        p.reject(p.packet(SD_NDX_MAP,dynamic,{readback,1024,D3D11_MAP_WRITE_DISCARD})); // overlapping shadows
        p.call(SD_NDX_UNMAP,staging);
        p.release(dynamic); p.reject(p.packet(SD_NDX_RELEASE,dynamic));
        uint32_t replacement=p.buffer(1024,D3D11_USAGE_DYNAMIC,D3D11_BIND_VERTEX_BUFFER,D3D11_CPU_ACCESS_WRITE);
        p.require(replacement!=dynamic,"stale token generation");
        p.reject(p.packet(SD_NDX_MAP,dynamic,{upload,1024,D3D11_MAP_WRITE_DISCARD}));
        p.release(replacement);p.release(staging);p.release(small);

        std::memcpy(p.memory.data()+0x20000,probe_vs,sizeof(probe_vs));
        std::memcpy(p.memory.data()+0x21000,probe_ps,sizeof(probe_ps));
        uint32_t vs=p.call(SD_NDX_CREATE_VS,0,{base+0x20000,sizeof(probe_vs)}).result[0];
        uint32_t ps=p.call(SD_NDX_CREATE_PS,0,{base+0x21000,sizeof(probe_ps)}).result[0];
        p.reject(p.packet(SD_NDX_CREATE_PS,0,{base-1,sizeof(probe_ps)}));
        uint32_t target=p.texture(D3D11_USAGE_DEFAULT,D3D11_BIND_RENDER_TARGET,0);
        uint32_t view=p.call(SD_NDX_CREATE_RTV,target).result[0];
        uint32_t image=p.texture(D3D11_USAGE_STAGING,0,D3D11_CPU_ACCESS_READ);
        uint32_t wrong_image=p.texture(D3D11_USAGE_STAGING,0,D3D11_CPU_ACCESS_READ,640,360);
        p.reject(p.packet(SD_NDX_COPY,wrong_image,{target})); p.release(wrong_image);
        p.reject(p.packet(SD_NDX_SET_PIPELINE,0,{ps,vs,view,1280,720}));
        p.call(SD_NDX_SET_PIPELINE,0,{vs,ps,view,1280,720});
        p.call(SD_NDX_DRAW,0,{3,0});
        p.call(SD_NDX_COPY,image,{target});
        mapped=p.call(SD_NDX_MAP,image,{readback,6*1024*1024,D3D11_MAP_READ});
        p.require(mapped.result[0]==readback && mapped.result[1]>=1280*4 && mapped.result[3]==mapped.result[1]*720,"texture map layout");
        const unsigned expected[4]={64,128,191,255};
        unsigned pixels=0;
        for (unsigned y=0;y<720;++y) for (unsigned x=0;x<1280;++x) {
            auto* pixel=p.memory.data()+readback-base+size_t(y)*mapped.result[1]+x*4;
            for (unsigned c=0;c<4;++c) if (std::abs(int(pixel[c])-int(expected[c]))>1) throw std::runtime_error("draw pixel mismatch");
            ++pixels;
        }
        p.call(SD_NDX_UNMAP,image);
        p.call(SD_NDX_CLEAR_STATE);
        p.reject(p.packet(SD_NDX_DRAW,0,{3,0}));
        p.release(view);p.release(image);p.release(target);

        uint32_t swap=p.call(SD_NDX_CREATE_SWAPCHAIN,0,{1280,720}).result[0];
        uint32_t back=p.call(SD_NDX_GET_BACKBUFFER,swap).result[0];
        view=p.call(SD_NDX_CREATE_RTV,back).result[0];
        p.call(SD_NDX_SET_PIPELINE,0,{vs,ps,view,1280,720});
        for (unsigned i=0;i<60;++i) { p.call(SD_NDX_DRAW,0,{3,0});p.call(SD_NDX_PRESENT,swap,{0});++p.frames; }
        p.reject(p.packet(SD_NDX_PRESENT,swap,{2}));
        p.call(SD_NDX_CLEAR_STATE);p.release(view);p.release(back);p.release(swap);p.release(vs);p.release(ps);
        std::printf("{\"status\":\"PASS\",\"target\":\"linux-x86_64-native\",\"transport\":\"modeled-guest32-arena\",\"native_arena_above_4g\":true,\"checks\":%u,\"rejected_requests\":%u,\"buffer_bytes_verified\":1024,\"draw_pixels_verified\":%u,\"present_calls\":%u,\"game_integration\":false,\"hardware_tested\":false,\"fps_gain_measured\":false}\n",p.checks,p.rejected,pixels,p.frames);
        return 0;
    } catch(const std::exception& e) { std::fprintf(stderr,"PROBE FAILED: %s\n",e.what());return 1; }
}
