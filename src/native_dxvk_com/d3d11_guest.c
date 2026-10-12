/* SPDX-License-Identifier: MIT; PE32 D3D11 exports backed by ARM64 DXVK. */
#define WIN32_LEAN_AND_MEAN
#define COBJMACROS
#include <windows.h>
#include <d3d11.h>
#include <dxgi.h>
__declspec(dllimport) HRESULT WINAPI SdCreateDevice(IDXGIAdapter*,D3D_DRIVER_TYPE,HMODULE,UINT,const D3D_FEATURE_LEVEL*,UINT,UINT,ID3D11Device**,D3D_FEATURE_LEVEL*,ID3D11DeviceContext**);
__declspec(dllexport) HRESULT WINAPI D3D11CreateDevice(IDXGIAdapter *a,D3D_DRIVER_TYPE t,HMODULE s,UINT f,const D3D_FEATURE_LEVEL *l,UINT n,UINT sdk,ID3D11Device **d,D3D_FEATURE_LEVEL *actual,ID3D11DeviceContext **c) {
    return SdCreateDevice(a,t,s,f,l,n,sdk,d,actual,c);
}
__declspec(dllexport) HRESULT WINAPI D3D11CreateDeviceAndSwapChain(IDXGIAdapter *a,D3D_DRIVER_TYPE t,HMODULE s,UINT f,const D3D_FEATURE_LEVEL *l,UINT n,UINT sdk,const DXGI_SWAP_CHAIN_DESC *desc,IDXGISwapChain **swap,ID3D11Device **d,D3D_FEATURE_LEVEL *actual,ID3D11DeviceContext **c) {
    ID3D11Device *device=NULL;ID3D11DeviceContext *context=NULL;
    IDXGIDevice *dxgi=NULL;IDXGIAdapter *adapter=NULL;IDXGIFactory *factory=NULL;
    if(swap)*swap=NULL;if(d)*d=NULL;if(c)*c=NULL;
    HRESULT hr=SdCreateDevice(a,t,s,f,l,n,sdk,&device,actual,c?&context:NULL);
    if(FAILED(hr))return hr;
    if(swap) {
        if(!desc){hr=E_INVALIDARG;goto done;}
        hr=ID3D11Device_QueryInterface(device,&IID_IDXGIDevice,(void**)&dxgi);
        if(SUCCEEDED(hr))hr=IDXGIDevice_GetAdapter(dxgi,&adapter);
        if(SUCCEEDED(hr))hr=IDXGIAdapter_GetParent(adapter,&IID_IDXGIFactory,(void**)&factory);
        if(SUCCEEDED(hr))hr=IDXGIFactory_CreateSwapChain(factory,(IUnknown*)device,(DXGI_SWAP_CHAIN_DESC*)desc,swap);
    }
done:
    if(factory)IDXGIFactory_Release(factory);if(adapter)IDXGIAdapter_Release(adapter);if(dxgi)IDXGIDevice_Release(dxgi);
    if(SUCCEEDED(hr)){if(d)*d=device;else ID3D11Device_Release(device);if(c)*c=context;}
    else {if(context)ID3D11DeviceContext_Release(context);ID3D11Device_Release(device);}
    return hr;
}
BOOL WINAPI DllMain(HINSTANCE self,DWORD reason,void *reserved) {(void)self;(void)reason;(void)reserved;return TRUE;}
