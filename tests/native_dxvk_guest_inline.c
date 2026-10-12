/* SPDX-License-Identifier: MIT; production PE32 wrappers, modeled endpoint. */
#include "com_guest.c"
#include "com_compact.h"
static unsigned checks,calls,nested_calls;
static ID3D11DeviceContext *ctx;
struct expected_call {
    uint32_t method,nargs,scalar[16],bytes[16],data[16][160];
    unsigned pointer_mask,inline_packet;
};
static struct expected_call expected;
static struct expected_call nested_expected[4];
static unsigned depth;
static int reenter;
static void say(const char *s){DWORD n;WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),s,(DWORD)strlen(s),&n,NULL);}
static void require(int good,const char *s){++checks;if(!good){say(s);say("\n");ExitProcess(1);}}
static void begin_case(unsigned method,unsigned nargs,unsigned inlined) {
    memset(&expected,0,sizeof(expected));expected.method=method;expected.nargs=nargs;expected.inline_packet=inlined;
}
static void pointer_case(unsigned arg,const void *memory,unsigned bytes) {
    expected.pointer_mask|=1u<<arg;expected.bytes[arg]=memory?bytes:0;
    if(memory&&bytes){require(bytes<=sizeof(expected.data[arg]),"expectation capacity");memcpy(expected.data[arg],memory,bytes);}
}
static void token_case(unsigned arg,void *const *objects,unsigned count) {
    expected.pointer_mask|=1u<<arg;expected.bytes[arg]=objects?count*4:0;
    require(count<=160,"expectation token capacity");
    if(objects)for(unsigned i=0;i<count;++i)expected.data[arg][i]=proxy_token(objects[i]);
}
static LONG WINAPI endpoint(uint64_t handle,unsigned index,void *request) {
    struct sd_com_packet *wire=request,p;
    require(depth<4,"endpoint nesting bound");
    struct expected_call *saved=&nested_expected[depth++];*saved=expected;
    require(handle==42&&!index,"endpoint identity");require(sd_com_wire_decode(&p,wire),"wire decode");++calls;
    require(p.method==saved->method,"method changed");
    require(p.reserved==((saved->inline_packet?SD_COM_INLINE_MAGIC:SD_COM_COMPACT_MAGIC)|saved->nargs),"packet marker");
    for(unsigned i=0;i<saved->nargs;++i) {
        if(saved->pointer_mask&(1u<<i)) {
            if(!saved->bytes[i])require(!p.args[i],"empty input did not stay NULL");
            else {
                uint64_t start=p.args[i],end=start+saved->bytes[i];
                uint64_t low=(uintptr_t)wire+32+4*saved->nargs,high=(uintptr_t)wire+sizeof(*wire);
                if(saved->inline_packet)require(start>=low&&end<=high,"inline bounds");
                require(!memcmp((void*)(uintptr_t)p.args[i],saved->data[i],saved->bytes[i]),"input contents differ");
            }
        } else require(p.args[i]==saved->scalar[i],"scalar or token changed");
    }
    for(unsigned i=saved->nargs;i<32;++i)require(p.words[i]==0,"decoded unused words uninitialized");
    if(reenter) {
        reenter=0;uint32_t outer[160];unsigned bytes=saved->bytes[2];
        if(bytes)memcpy(outer,(void*)(uintptr_t)p.args[2],bytes);
        begin_case(7,3,0);expected.scalar[0]=3;expected.scalar[1]=0;token_case(2,NULL,0);
        ID3D11DeviceContext_VSSetConstantBuffers(ctx,3,0,NULL);++nested_calls;expected=*saved;
        if(bytes)require(!memcmp(outer,(void*)(uintptr_t)p.args[2],bytes),"nested call overwrote outer payload");
    }
    p.ret=S_OK;p.fault=0;p.aux=0;sd_com_wire_encode(wire,&p);--depth;return 0;
}
static void *object(uint32_t token,uint32_t kind) {
    struct proxy *p=proxy_wrap(token,kind);require(p!=NULL,"proxy allocation");return p;
}
static void generated_cases(void);
static void edge_cases(void) {
    ID3D11ShaderResourceView *views[128];for(unsigned i=0;i<128;++i)views[i]=(ID3D11ShaderResourceView*)object(200+i,SD_COM_IF_ID3D11ShaderResourceView);
    for(unsigned count=0;count<=128;++count) {
        begin_case(8,3,count>0&&count<=29);expected.scalar[0]=0;expected.scalar[1]=count;token_case(2,(void*const*)views,count);
        ID3D11DeviceContext_PSSetShaderResources(ctx,0,count,views);
    }
    /* Changed contents at an identical address must always cross and survive. */
    for(unsigned n=0;n<1000;++n) {
        views[1]=views[2+(n%100)];
        begin_case(8,3,1);expected.scalar[0]=n%16;expected.scalar[1]=12;token_case(2,(void*const*)views,12);
        if(n==5)reenter=1;
        unsigned before=calls;ID3D11DeviceContext_PSSetShaderResources(ctx,n%16,12,views);
        require(calls==before+1+(n==5),"input call was suppressed");
    }
    /* Zero and NULL inputs do not read inaccessible memory. */
    begin_case(8,3,0);expected.scalar[1]=8;token_case(2,NULL,0);ID3D11DeviceContext_PSSetShaderResources(ctx,0,8,NULL);
    begin_case(8,3,0);token_case(2,NULL,0);ID3D11DeviceContext_PSSetShaderResources(ctx,0,0,(void*)1);
    begin_case(8,3,0);expected.scalar[1]=0xffffffffu;token_case(2,NULL,0);
    ID3D11DeviceContext_PSSetShaderResources(ctx,0,0xffffffffu,NULL);
    begin_case(8,3,0);expected.scalar[1]=SD_COM_MAX_ARRAY+1;token_case(2,NULL,0);
    ID3D11DeviceContext_PSSetShaderResources(ctx,0,SD_COM_MAX_ARRAY+1,NULL);
    /* Alias three source arrays, then let the encoder independently snapshot. */
    ID3D11Buffer *buffers[9];UINT stride[9];for(unsigned i=0;i<9;++i){buffers[i]=(ID3D11Buffer*)object(400+i,SD_COM_IF_ID3D11Buffer);stride[i]=4*i;}
    for(unsigned count=8;count<=9;++count){
        begin_case(18,5,count<=9);expected.scalar[1]=count;token_case(2,(void*const*)buffers,count);
        pointer_case(3,stride,count*4);pointer_case(4,stride,count*4);ID3D11DeviceContext_IASetVertexBuffers(ctx,0,count,buffers,stride,stride);
    }
    struct sd_com_packet wire={0},decoded;memset(&wire,0xa5,sizeof(wire));wire.abi=SD_COM_ABI;wire.interface_id=SD_COM_IF_ID3D11DeviceContext;wire.method=8;
    wire.reserved=SD_COM_INLINE_MAGIC|3;require(sd_com_wire_decode(&decoded,&wire),"poisoned unused payload rejected");
    for(unsigned i=3;i<32;++i)require(decoded.words[i]==0,"poison propagated to decoded arguments");
    for(unsigned count=0;count<32;++count)if(count!=3){wire.reserved=SD_COM_INLINE_MAGIC|count;require(!sd_com_wire_decode(&decoded,&wire),"forged argument count accepted");}
    wire.reserved=SD_COM_INLINE_MAGIC|3;wire.method=12;require(!sd_com_wire_decode(&decoded,&wire),"inline marker accepted for Draw");
    wire.method=8;wire.abi=SD_COM_ABI+1;require(!sd_com_wire_decode(&decoded,&wire),"unknown ABI accepted");
}
#include "inline_generated.inc"
void WINAPI start(void) {
    InitializeCriticalSection(&proxy_lock);endpoint_storage.handle=42;endpoint_storage.call=endpoint;published_endpoint=&endpoint_storage;
    ctx=(ID3D11DeviceContext*)object(1,SD_COM_IF_ID3D11DeviceContext);
    generated_cases();edge_cases();require(nested_calls==1,"nested test missing");
    say("{\"status\":\"PASS\",\"real_pe32\":true,\"methods\":32,\"array_lengths\":129,\"mutated_bindings\":1000,\"nested_calls\":1,\"no_call_suppression\":true}\n");ExitProcess(0);
}
