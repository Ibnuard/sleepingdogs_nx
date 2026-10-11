/* SPDX-License-Identifier: MIT; original CRT-free PE32 native-DXVK H2 test.
 * Uses real VirtualAlloc addresses and Wine/FEX's existing WOW64 unix gate.
 * One thread owns the arena until CLOSE. No game or COM proxy is loaded.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include "bridge_protocol.h"
#include "../native_dxvk/probe_shaders.h"

typedef LONG (WINAPI *bridge_call)(unsigned int,void*);
static bridge_call bridge;
static unsigned char* arena;
static struct sd_ndx_packet* packet;
static uint32_t session, checks, rejected, pixels, bad_pixels, calls;
static HANDLE output=INVALID_HANDLE_VALUE;
static char text[2048];
static unsigned used;
static const char* stage="startup";
static uint32_t error;

/* Compiler-generated aggregate copies also resolve here, never into a CRT. */
void* memcpy(void* dst,const void* src,size_t bytes) {
    volatile unsigned char* d=dst; const volatile unsigned char* s=src;
    while(bytes--) *d++=*s++;
    return dst;
}
void* memset(void* dst,int value,size_t bytes) {
    volatile unsigned char* d=dst; while(bytes--) *d++=(unsigned char)value; return dst;
}
static void append(const char* value) { while(*value && used+1<sizeof(text)) text[used++]=*value++; }
static void number(uint32_t value) {
    char digits[10]; unsigned count=0;
    do { digits[count++]=(char)('0'+value%10);value/=10; } while(value);
    while(count) { char one[2]={digits[--count],0};append(one); }
}
static void hex(uint32_t value) {
    unsigned i; append("0x");
    for(i=0;i<8;i++) { char one[2]={"0123456789abcdef"[(value>>(28-i*4))&15],0};append(one); }
}
static void flush(HANDLE file) { DWORD written; if(file!=INVALID_HANDLE_VALUE) { WriteFile(file,text,used,&written,NULL);FlushFileBuffers(file); } }
static void log_stage(const char* value) {
    stage=value;used=0;append("[SD-NDX-H2-GUEST] ");append(value);append(" arena=");hex((uint32_t)(uintptr_t)arena);
    append(" checks=");number(checks);append(" calls=");number(calls);append("\r\n");flush(output);
}
static int require(int condition,uint32_t failure) { ++checks;if(!condition)error=failure;return condition; }
static LONG transport(unsigned op,void* args) { ++calls;return bridge(op,args); }
static int invoke(uint32_t op,uint32_t object,uint32_t a,uint32_t b,uint32_t c,uint32_t d,uint32_t e) {
    struct sd_ndx_bridge_dispatch request={SD_NDX_BRIDGE_ABI,session,(uint32_t)(uintptr_t)packet,0};
    memset(packet,0,sizeof(*packet));packet->abi=SD_NDX_ABI;packet->op=op;packet->object=object;
    packet->args[0]=a;packet->args[1]=b;packet->args[2]=c;packet->args[3]=d;packet->args[4]=e;
    LONG status=transport(SD_NDX_BRIDGE_DISPATCH,&request);
    return require(status>=0,(uint32_t)status) && require(request.hresult>=0,(uint32_t)request.hresult);
}
static int reject(uint32_t op,uint32_t object,uint32_t address) {
    struct sd_ndx_bridge_dispatch request={SD_NDX_BRIDGE_ABI,session,(uint32_t)(uintptr_t)packet,0};
    memset(packet,0,sizeof(*packet));packet->abi=SD_NDX_ABI;packet->op=op;packet->object=object;
    packet->args[0]=address;packet->args[1]=1024;packet->args[2]=4; /* WRITE_DISCARD */
    LONG status=transport(SD_NDX_BRIDGE_DISPATCH,&request);
    int ok=require(status<0 || request.hresult<0,0xe2010001u);if(ok)++rejected;return ok;
}
static void result(int ok) {
    HANDLE file=CreateFileA("C:\\native-dxvk-h2-result.json",GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    used=0;append("{\"status\":\"");append(ok>0?"PASS":ok==0?"FAIL":"RUNNING");append("\",\"build\":\"native-dxvk-h2-v1\",\"stage\":\"");append(stage);
    append("\",\"error\":");number(error);append(",\"checks\":");number(checks);append(",\"rejected_requests\":");number(rejected);
    append(",\"bridge_calls\":");number(calls);append(",\"guest_arena\":");number((uint32_t)(uintptr_t)arena);
    append(",\"buffer_bytes_verified\":");number(ok>0?1024:0);append(",\"draw_pixels_verified\":");number(pixels);
    append(",\"bad_pixels\":");number(bad_pixels);
    append(",\"guest_execution\":true,\"game_integration\":false,\"present_calls\":0,\"game_fps_measured\":false}\r\n");
    flush(file);if(file!=INVALID_HANDLE_VALUE)CloseHandle(file);flush(output);
}
static int run(void) {
    uint32_t dynamic,staging,vs,ps,target,view,image,upload,readback,old_session,rowpitch,x,y,i;
    struct sd_ndx_bridge_init init={SD_NDX_BRIDGE_ABI,0,SD_NDX_BRIDGE_ARENA_BYTES,0};
    struct sd_ndx_bridge_close close={SD_NDX_BRIDGE_ABI,0,0};
    HMODULE library=LoadLibraryA("sdndx.dll");
    log_stage("load static WOW64 gate");
    if(!require(library!=NULL,GetLastError()))return 0;
    bridge=(bridge_call)GetProcAddress(library,"SdNdxCall");
    if(!require(bridge!=NULL,GetLastError()))return 0;
    arena=VirtualAlloc(NULL,SD_NDX_BRIDGE_ARENA_BYTES,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    if(!require(arena!=NULL,GetLastError()) || !require(((uintptr_t)arena&0xffffu)==0,0xe2010002u))return 0;
    packet=(struct sd_ndx_packet*)(arena+256);upload=(uint32_t)(uintptr_t)(arena+0x10000);readback=(uint32_t)(uintptr_t)(arena+0x100000);
    init.arena=(uint32_t)(uintptr_t)arena;init.abi=0;
    if(!require(transport(SD_NDX_BRIDGE_INIT,&init)<0,0xe2010003u))return 0;++rejected;
    init.abi=SD_NDX_BRIDGE_ABI;
    LONG status=transport(SD_NDX_BRIDGE_INIT,&init);
    if(!require(status>=0,(uint32_t)status) || !require(init.session!=0,0xe2010004u))return 0;
    session=init.session;log_stage("native device");
    if(!invoke(SD_NDX_CREATE_DEVICE,0,0,0,0,0,0) || !require(packet->result[0]==0xb000,0xe2010005u))return 0;
    if(!reject(SD_NDX_CREATE_SWAPCHAIN,0,1280))return 0; /* offscreen H2 */
    log_stage("buffer shadow map");
    if(!invoke(SD_NDX_CREATE_BUFFER,0,1024,2,1,0x10000,0))return 0;dynamic=packet->result[0]; /* dynamic/vertex/write */
    if(!invoke(SD_NDX_CREATE_BUFFER,0,1024,3,0,0x20000,0))return 0;staging=packet->result[0]; /* staging/read */
    if(!reject(SD_NDX_MAP,dynamic,(uint32_t)(uintptr_t)packet))return 0; /* metadata overlap */
    if(!invoke(SD_NDX_MAP,dynamic,upload,1024,4,0,0) || !require(packet->result[0]==upload,0xe2010006u))return 0;
    for(i=0;i<1024;i++)arena[0x10000+i]=(unsigned char)(i*37+11);
    if(!invoke(SD_NDX_UNMAP,dynamic,0,0,0,0,0) || !invoke(SD_NDX_COPY,staging,dynamic,0,0,0,0))return 0;
    if(!invoke(SD_NDX_MAP,staging,readback,1024,1,0,0) || !require(packet->result[3]==1024,0xe2010007u))return 0;
    for(i=0;i<1024;i++)if(!require(arena[0x100000+i]==(unsigned char)(i*37+11),0xe2010008u))return 0;
    if(!invoke(SD_NDX_UNMAP,staging,0,0,0,0,0))return 0;
    if(!invoke(SD_NDX_RELEASE,dynamic,0,0,0,0,0) || !reject(SD_NDX_RELEASE,dynamic,0) || !invoke(SD_NDX_RELEASE,staging,0,0,0,0,0))return 0;
    log_stage("720p shader draw and readback");
    memcpy(arena+0x20000,probe_vs,sizeof(probe_vs));memcpy(arena+0x21000,probe_ps,sizeof(probe_ps));
    if(!invoke(SD_NDX_CREATE_VS,0,(uint32_t)(uintptr_t)(arena+0x20000),sizeof(probe_vs),0,0,0))return 0;vs=packet->result[0];
    if(!invoke(SD_NDX_CREATE_PS,0,(uint32_t)(uintptr_t)(arena+0x21000),sizeof(probe_ps),0,0,0))return 0;ps=packet->result[0];
    if(!invoke(SD_NDX_CREATE_TEXTURE,0,1280,720,0,0x20,0))return 0;target=packet->result[0];
    if(!invoke(SD_NDX_CREATE_RTV,target,0,0,0,0,0))return 0;view=packet->result[0];
    if(!invoke(SD_NDX_CREATE_TEXTURE,0,1280,720,3,0,0x20000))return 0;image=packet->result[0];
    if(!invoke(SD_NDX_SET_PIPELINE,0,vs,ps,view,1280,720) || !invoke(SD_NDX_DRAW,0,3,0,0,0,0))return 0;
    if(!invoke(SD_NDX_COPY,image,target,0,0,0,0) || !invoke(SD_NDX_MAP,image,readback,6*1024*1024,1,0,0))return 0;
    rowpitch=packet->result[1];
    if(!require(packet->result[0]==readback && rowpitch>=5120 && rowpitch<=6*1024*1024/720 && packet->result[3]==rowpitch*720,0xe2010009u))return 0;
    for(y=0;y<720;y++)for(x=0;x<1280;x++) {
        unsigned char* p=arena+0x100000+y*rowpitch+x*4;
        if(p[0]<63||p[0]>65||p[1]<127||p[1]>129||p[2]<190||p[2]>192||p[3]!=255)++bad_pixels;
        ++pixels;
    }
    if(!require(bad_pixels==0,0xe201000au))return 0;
    if(!invoke(SD_NDX_UNMAP,image,0,0,0,0,0) || !invoke(SD_NDX_CLEAR_STATE,0,0,0,0,0,0))return 0;
    if(!invoke(SD_NDX_RELEASE,view,0,0,0,0,0) || !invoke(SD_NDX_RELEASE,image,0,0,0,0,0) || !invoke(SD_NDX_RELEASE,target,0,0,0,0,0) ||
       !invoke(SD_NDX_RELEASE,vs,0,0,0,0,0) || !invoke(SD_NDX_RELEASE,ps,0,0,0,0,0))return 0;
    log_stage("close and stale-session rejection");
    close.session=session;old_session=session;
    status=transport(SD_NDX_BRIDGE_CLOSE,&close);if(!require(status>=0,(uint32_t)status))return 0;session=0;
    init.session=0;status=transport(SD_NDX_BRIDGE_INIT,&init);if(!require(status>=0,(uint32_t)status))return 0;session=init.session;
    if(!require(session!=old_session,0xe201000bu))return 0;
    struct sd_ndx_bridge_dispatch stale={SD_NDX_BRIDGE_ABI,old_session,(uint32_t)(uintptr_t)packet,0};
    if(!require(transport(SD_NDX_BRIDGE_DISPATCH,&stale)<0,0xe201000cu))return 0;++rejected;
    close.session=session;status=transport(SD_NDX_BRIDGE_CLOSE,&close);if(!require(status>=0,(uint32_t)status))return 0;session=0;
    log_stage("PASS");return 1;
}
void WINAPI start(void) {
    output=CreateFileA("C:\\native-dxvk-h2-guest.log",GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    result(-1); /* Replace any previous PASS before starting the first call. */
    int ok=run();
    result(ok);
    if(session && bridge) { struct sd_ndx_bridge_close close={SD_NDX_BRIDGE_ABI,session,0};if(transport(SD_NDX_BRIDGE_CLOSE,&close)>=0)session=0; }
    if(arena && !session)VirtualFree(arena,0,MEM_RELEASE);
    if(output!=INVALID_HANDLE_VALUE)CloseHandle(output);
    ExitProcess(ok?0:1);
}
