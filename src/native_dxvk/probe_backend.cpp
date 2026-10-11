/* SPDX-License-Identifier: MIT; original FEXTendo prototype marshaling.
 * Deliberately bounded API subset: this is not a drop-in game d3d11.dll.
 */
#include "probe_protocol.h"
#include <d3d11.h>
#include <dxgi.h>
#include <array>
#include <cstring>
#include <mutex>
#include <new>
#include <vector>

namespace {
enum class Kind { Empty, Buffer, Texture, Rtv, Vs, Ps, Swapchain };
struct Slot {
    IUnknown* object = nullptr;
    Kind kind = Kind::Empty;
    uint32_t generation = 1;
    uint32_t bytes = 0, height = 0;
    D3D11_MAPPED_SUBRESOURCE map = {};
    void* shadow = nullptr;
    uint32_t shadow_bytes = 0, map_type = 0;
};
struct Session {
    unsigned char* memory;
    uint32_t base, size;
    HWND window;
    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* context = nullptr;
    bool pipeline = false;
    std::array<Slot, 128> objects;
    std::mutex mutex;
    Session(void* p, uint32_t b, uint32_t s, void* w)
        : memory(static_cast<unsigned char*>(p)), base(b), size(s), window(static_cast<HWND>(w)) {}
    ~Session() {
        if (context) context->ClearState();
        for (auto& slot : objects) {
            if (slot.shadow && context) context->Unmap(static_cast<ID3D11Resource*>(slot.object), 0);
            if (slot.object) slot.object->Release();
        }
        if (context) { context->Flush(); context->Release(); }
        if (device) device->Release();
    }
    void* span(uint32_t address, uint32_t length) {
        if (!length || address < base || uint64_t(address) + length > uint64_t(base) + size) return nullptr;
        return memory + (address - base);
    }
    Slot* get(uint32_t token, Kind kind = Kind::Empty) {
        uint32_t index = token & 0xffu;
        if (!index || index > objects.size()) return nullptr;
        auto& slot = objects[index-1];
        return slot.object && slot.generation == (token >> 8) && (kind == Kind::Empty || slot.kind == kind) ? &slot : nullptr;
    }
    uint32_t add(IUnknown* object, Kind kind, uint32_t bytes = 0, uint32_t height = 0) {
        if (!object) return 0;
        for (unsigned i = 0; i < objects.size(); ++i) {
            auto& slot = objects[i];
            if (!slot.object) {
                slot.object = object; slot.kind = kind; slot.bytes = bytes; slot.height = height;
                return (slot.generation << 8) | (i + 1);
            }
        }
        object->Release(); return 0;
    }
};

HRESULT execute(Session& s, sd_ndx_packet& p) {
    std::memset(p.result, 0, sizeof(p.result));
    if (p.abi != SD_NDX_ABI || p.flags) return E_INVALIDARG;
    if (p.op == SD_NDX_CREATE_DEVICE) {
        if (s.device) return E_INVALIDARG;
        D3D_FEATURE_LEVEL level = D3D_FEATURE_LEVEL_11_0, actual;
        HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0,
            &level, 1, D3D11_SDK_VERSION, &s.device, &actual, &s.context);
        if (SUCCEEDED(hr)) p.result[0] = actual;
        return hr;
    }
    if (!s.device) return E_INVALIDARG;
    Slot* slot = s.get(p.object);
    switch (p.op) {
    case SD_NDX_CREATE_BUFFER: {
        if (!p.args[0] || p.args[0] > 16u*1024u*1024u) return E_INVALIDARG;
        D3D11_BUFFER_DESC desc = {p.args[0], D3D11_USAGE(p.args[1]), p.args[2], p.args[3], 0, 0};
        ID3D11Buffer* buffer = nullptr;
        HRESULT hr = s.device->CreateBuffer(&desc, nullptr, &buffer);
        if (SUCCEEDED(hr)) {
            p.result[0] = s.add(buffer, Kind::Buffer, desc.ByteWidth);
            if (!p.result[0]) return E_OUTOFMEMORY;
        }
        return hr;
    }
    case SD_NDX_MAP: {
        if (!slot || slot->shadow || (slot->kind != Kind::Buffer && slot->kind != Kind::Texture)) return E_INVALIDARG;
        auto type = D3D11_MAP(p.args[2]);
        if (type != D3D11_MAP_READ && type != D3D11_MAP_READ_WRITE && type != D3D11_MAP_WRITE_DISCARD) return E_NOTIMPL;
        void* shadow = s.span(p.args[0], p.args[1]);
        if (!shadow) return E_INVALIDARG;
        for (auto& active : s.objects) {
            if (active.shadow && static_cast<unsigned char*>(shadow) < static_cast<unsigned char*>(active.shadow) + active.shadow_bytes &&
                static_cast<unsigned char*>(active.shadow) < static_cast<unsigned char*>(shadow) + p.args[1]) return E_INVALIDARG;
        }
        D3D11_MAPPED_SUBRESOURCE mapped = {};
        HRESULT hr = s.context->Map(static_cast<ID3D11Resource*>(slot->object), 0, type, 0, &mapped);
        if (FAILED(hr)) return hr;
        uint64_t bytes = slot->kind == Kind::Buffer ? slot->bytes : uint64_t(mapped.RowPitch)*slot->height;
        if (!bytes || bytes > p.args[1]) {
            s.context->Unmap(static_cast<ID3D11Resource*>(slot->object), 0); return E_INVALIDARG;
        }
        slot->map = mapped; slot->shadow = shadow; slot->shadow_bytes = uint32_t(bytes); slot->map_type = type;
        if (type == D3D11_MAP_READ || type == D3D11_MAP_READ_WRITE) std::memcpy(shadow, mapped.pData, size_t(bytes));
        else std::memset(shadow, 0, size_t(bytes));
        p.result[0] = p.args[0]; p.result[1] = mapped.RowPitch;
        p.result[2] = mapped.DepthPitch; p.result[3] = uint32_t(bytes);
        return S_OK;
    }
    case SD_NDX_UNMAP:
        if (!slot || !slot->shadow) return E_INVALIDARG;
        if (slot->map_type != D3D11_MAP_READ) std::memcpy(slot->map.pData, slot->shadow, slot->shadow_bytes);
        s.context->Unmap(static_cast<ID3D11Resource*>(slot->object), 0);
        slot->map = {}; slot->shadow = nullptr; slot->shadow_bytes = slot->map_type = 0;
        return S_OK;
    case SD_NDX_CREATE_TEXTURE: {
        if (!p.args[0] || !p.args[1] || p.args[0] > 1280 || p.args[1] > 720) return E_INVALIDARG;
        D3D11_TEXTURE2D_DESC desc = {};
        desc.Width = p.args[0]; desc.Height = p.args[1]; desc.MipLevels = desc.ArraySize = 1;
        desc.Format = DXGI_FORMAT_R8G8B8A8_UNORM; desc.SampleDesc.Count = 1;
        desc.Usage = D3D11_USAGE(p.args[2]); desc.BindFlags = p.args[3]; desc.CPUAccessFlags = p.args[4];
        ID3D11Texture2D* texture = nullptr;
        HRESULT hr = s.device->CreateTexture2D(&desc, nullptr, &texture);
        if (SUCCEEDED(hr)) {
            p.result[0] = s.add(texture, Kind::Texture, 0, desc.Height);
            if (!p.result[0]) return E_OUTOFMEMORY;
        }
        return hr;
    }
    case SD_NDX_CREATE_RTV: {
        if (!slot || slot->kind != Kind::Texture) return E_INVALIDARG;
        ID3D11RenderTargetView* view = nullptr;
        HRESULT hr = s.device->CreateRenderTargetView(static_cast<ID3D11Resource*>(slot->object), nullptr, &view);
        if (SUCCEEDED(hr)) { p.result[0] = s.add(view, Kind::Rtv); if (!p.result[0]) return E_OUTOFMEMORY; }
        return hr;
    }
    case SD_NDX_CREATE_VS: case SD_NDX_CREATE_PS: {
        const void* bytes = s.span(p.args[0], p.args[1]);
        if (!bytes || p.args[1] > 1024u*1024u) return E_INVALIDARG;
        IUnknown* shader = nullptr;
        HRESULT hr;
        if (p.op == SD_NDX_CREATE_VS) {
            ID3D11VertexShader* vs = nullptr;
            hr = s.device->CreateVertexShader(bytes, p.args[1], nullptr, &vs); shader = vs;
        } else {
            ID3D11PixelShader* ps = nullptr;
            hr = s.device->CreatePixelShader(bytes, p.args[1], nullptr, &ps); shader = ps;
        }
        if (SUCCEEDED(hr)) {
            p.result[0] = s.add(shader, p.op == SD_NDX_CREATE_VS ? Kind::Vs : Kind::Ps);
            if (!p.result[0]) return E_OUTOFMEMORY;
        }
        return hr;
    }
    case SD_NDX_SET_PIPELINE: {
        auto* vs = s.get(p.args[0], Kind::Vs); auto* ps = s.get(p.args[1], Kind::Ps);
        auto* rtv = s.get(p.args[2], Kind::Rtv);
        if (!vs || !ps || !rtv || !p.args[3] || !p.args[4] || p.args[3] > 1280 || p.args[4] > 720) return E_INVALIDARG;
        ID3D11RenderTargetView* view = static_cast<ID3D11RenderTargetView*>(rtv->object);
        s.context->OMSetRenderTargets(1, &view, nullptr);
        s.context->VSSetShader(static_cast<ID3D11VertexShader*>(vs->object), nullptr, 0);
        s.context->PSSetShader(static_cast<ID3D11PixelShader*>(ps->object), nullptr, 0);
        s.context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
        D3D11_VIEWPORT viewport = {0,0,float(p.args[3]),float(p.args[4]),0,1};
        s.context->RSSetViewports(1, &viewport);
        D3D11_RASTERIZER_DESC desc = {};
        desc.FillMode = D3D11_FILL_SOLID; desc.CullMode = D3D11_CULL_NONE; desc.DepthClipEnable = TRUE;
        ID3D11RasterizerState* state = nullptr;
        HRESULT hr = s.device->CreateRasterizerState(&desc, &state);
        if (FAILED(hr)) return hr;
        s.context->RSSetState(state); state->Release(); s.pipeline = true; return S_OK;
    }
    case SD_NDX_DRAW:
        if (!s.pipeline || p.args[0] != 3 || p.args[1]) return E_INVALIDARG;
        s.context->Draw(p.args[0], p.args[1]); return S_OK;
    case SD_NDX_COPY: {
        auto* other = s.get(p.args[0]);
        if (!slot || !other || slot->kind != other->kind || slot->shadow || other->shadow ||
            (slot->kind != Kind::Texture && slot->kind != Kind::Buffer)) return E_INVALIDARG;
        if (slot == other) return E_INVALIDARG;
        if (slot->kind == Kind::Buffer && slot->bytes != other->bytes) return E_INVALIDARG;
        if (slot->kind == Kind::Texture) {
            D3D11_TEXTURE2D_DESC a = {}, b = {};
            static_cast<ID3D11Texture2D*>(slot->object)->GetDesc(&a);
            static_cast<ID3D11Texture2D*>(other->object)->GetDesc(&b);
            if (a.Width != b.Width || a.Height != b.Height || a.Format != b.Format || a.SampleDesc.Count != b.SampleDesc.Count) return E_INVALIDARG;
        }
        s.context->CopyResource(static_cast<ID3D11Resource*>(slot->object), static_cast<ID3D11Resource*>(other->object));
        return S_OK;
    }
    case SD_NDX_RELEASE:
        if (!slot || slot->shadow) return E_INVALIDARG;
        slot->object->Release(); slot->object = nullptr; slot->kind = Kind::Empty;
        slot->generation = (slot->generation % 0xffffffu) + 1; return S_OK;
    case SD_NDX_CREATE_SWAPCHAIN: {
        if (!s.window || p.args[0] != 1280 || p.args[1] != 720) return E_INVALIDARG;
        IDXGIDevice* dxgi = nullptr; IDXGIAdapter* adapter = nullptr; IDXGIFactory* factory = nullptr;
        HRESULT hr = s.device->QueryInterface(__uuidof(IDXGIDevice), reinterpret_cast<void**>(&dxgi));
        if (SUCCEEDED(hr)) hr = dxgi->GetAdapter(&adapter);
        if (SUCCEEDED(hr)) hr = adapter->GetParent(__uuidof(IDXGIFactory), reinterpret_cast<void**>(&factory));
        DXGI_SWAP_CHAIN_DESC desc = {};
        desc.BufferDesc.Width = 1280; desc.BufferDesc.Height = 720;
        desc.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM; desc.BufferDesc.RefreshRate = {60,1};
        desc.SampleDesc.Count = 1; desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
        desc.BufferCount = 2; desc.OutputWindow = s.window; desc.Windowed = TRUE;
        desc.SwapEffect = DXGI_SWAP_EFFECT_DISCARD;
        IDXGISwapChain* swapchain = nullptr;
        if (SUCCEEDED(hr)) hr = factory->CreateSwapChain(s.device, &desc, &swapchain);
        if (factory) factory->Release(); if (adapter) adapter->Release(); if (dxgi) dxgi->Release();
        if (SUCCEEDED(hr)) { p.result[0] = s.add(swapchain, Kind::Swapchain); if (!p.result[0]) return E_OUTOFMEMORY; }
        return hr;
    }
    case SD_NDX_GET_BACKBUFFER: {
        if (!slot || slot->kind != Kind::Swapchain) return E_INVALIDARG;
        ID3D11Texture2D* texture = nullptr;
        HRESULT hr = static_cast<IDXGISwapChain*>(slot->object)->GetBuffer(0, __uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&texture));
        if (SUCCEEDED(hr)) { p.result[0] = s.add(texture, Kind::Texture, 0, 720); if (!p.result[0]) return E_OUTOFMEMORY; }
        return hr;
    }
    case SD_NDX_PRESENT:
        if (!slot || slot->kind != Kind::Swapchain || p.args[0] > 1) return E_INVALIDARG;
        return static_cast<IDXGISwapChain*>(slot->object)->Present(p.args[0], 0);
    case SD_NDX_CLEAR_STATE:
        s.context->ClearState(); s.context->Flush(); s.pipeline = false; return S_OK;
    default: return E_NOTIMPL;
    }
}
}
extern "C" void* sd_ndx_session_create(void* arena, uint32_t base, uint32_t size, void* window) {
    if (!arena || !size || uint64_t(base)+size > (uint64_t(1)<<32)) return nullptr;
    try { return new Session(arena, base, size, window); } catch (...) { return nullptr; }
}
extern "C" void sd_ndx_session_destroy(void* s) { delete static_cast<Session*>(s); }
extern "C" int32_t sd_ndx_dispatch(void* opaque, sd_ndx_packet* packet) {
    if (!opaque || !packet) return E_INVALIDARG;
    auto& s = *static_cast<Session*>(opaque);
    std::lock_guard<std::mutex> guard(s.mutex);
    try { return execute(s, *packet); }
    catch (const std::bad_alloc&) { std::memset(packet->result,0,sizeof(packet->result)); return E_OUTOFMEMORY; }
    catch (...) { std::memset(packet->result,0,sizeof(packet->result)); return E_FAIL; }
}
