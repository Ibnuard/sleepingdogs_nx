/* SPDX-License-Identifier: MIT; PE32 DXGI exports backed by ARM64 DXVK. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <dxgi.h>
__declspec(dllimport) HRESULT WINAPI SdCreateFactory(UINT,REFIID,void**);
__declspec(dllexport) HRESULT WINAPI CreateDXGIFactory(REFIID iid,void **out) {return SdCreateFactory(0,iid,out);}
__declspec(dllexport) HRESULT WINAPI CreateDXGIFactory1(REFIID iid,void **out) {return SdCreateFactory(0,iid,out);}
__declspec(dllexport) HRESULT WINAPI CreateDXGIFactory2(UINT flags,REFIID iid,void **out) {return SdCreateFactory(flags,iid,out);}
__declspec(dllexport) HRESULT WINAPI DXGIGetDebugInterface1(UINT flags,REFIID iid,void **out) {(void)flags;(void)iid;if(out)*out=NULL;return E_NOINTERFACE;}
BOOL WINAPI DllMain(HINSTANCE self,DWORD reason,void *reserved) {(void)self;(void)reason;(void)reserved;return TRUE;}
