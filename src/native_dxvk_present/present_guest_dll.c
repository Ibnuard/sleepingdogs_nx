/* SPDX-License-Identifier: MIT; original CRT-free x86 diagnostic DLL.
 * Uses the existing Wine-NX WOW64 unix-call gate. No native COM pointer is
 * exposed by this DLL. Wine's opaque unixlib handle itself is 64-bit.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include "present_protocol.h"

typedef LONG (WINAPI *query_memory)(HANDLE,const void*,int,void*,SIZE_T,SIZE_T*);
typedef LONG (WINAPI *unix_call)(uint64_t,unsigned int,void*);
static HINSTANCE self;
static uint64_t handle;
static unix_call call;
// A PE32 caller requests MemoryWineUnixFuncs (1000). Wine's WOW64 thunk
// rewrites it to the native MemoryWineUnixWow64Funcs (1001). The latter is
// explicitly rejected if requested directly by a 32-bit caller.
#define MEMORY_WINE_UNIX_FUNCS 1000

BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,void* reserved) {
    (void)reserved;
    if(reason==DLL_PROCESS_ATTACH) self=module;
    return TRUE;
}
__declspec(dllexport) LONG WINAPI SdNdxCall(unsigned int code,void* args) {
    if(code>SD_NDX_BRIDGE_CLOSE) return (LONG)0xc000000du;
    if(!call) {
        HMODULE ntdll=GetModuleHandleA("ntdll.dll");
        query_memory query=(query_memory)GetProcAddress(ntdll,"NtQueryVirtualMemory");
        unix_call entry=(unix_call)GetProcAddress(ntdll,"__wine_unix_call");
        if(!query || !entry || !self) return (LONG)0xc0000139u;
        LONG status=query((HANDLE)(intptr_t)-1,self,MEMORY_WINE_UNIX_FUNCS,&handle,sizeof(handle),NULL);
        if(status<0) return status;
        if(!handle) return (LONG)0xc0000008u;
        call=entry;
    }
    return call(handle,code,args);
}
