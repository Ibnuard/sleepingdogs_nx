/* SPDX-License-Identifier: MIT; execute production PE32 wrappers on Windows.
 * Only the Wine endpoint is modeled. Tests inspect calls and state, including
 * overwritten arrays, overlap, command-list resets, failure and reentrancy.
 */
#include "com_guest.c"
#include "com_compact.h"
static unsigned checks,calls,last_method;
static LONG next_error;
static int reenter;
static ID3D11DeviceContext *ctx;
static struct proxy *context_proxy;
static uint32_t values[128],last_args[16];
static void say(const char *s){DWORD n;WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),s,(DWORD)strlen(s),&n,NULL);}
static void require(int good,const char *s){++checks;if(!good){say(s);say("\n");ExitProcess(1);}}
static LONG WINAPI endpoint(uint64_t handle,unsigned index,void *request) {
    struct sd_com_packet *p=request,decoded;
    require(handle==42&&!index,"endpoint identity");require(sd_com_wire_decode(&decoded,p),"wire decoder");
    ++calls;last_method=p->method;memcpy(last_args,decoded.args,sizeof(last_args));
    if(reenter){int action=reenter;reenter=0;if(action==1)ID3D11DeviceContext_ClearState(ctx);else ID3D11DeviceContext_RSSetState(ctx,NULL);}
    LONG status=next_error;next_error=0;p->fault=0;p->ret=S_OK;
    return status;
}
static struct proxy *object(uint32_t token,uint32_t kind) {
    struct proxy *p=proxy_wrap(token,kind);require(p!=NULL,"proxy allocation");return p;
}
static void clear(void){ID3D11DeviceContext_ClearState(ctx);calls=0;}
static void generated_cases(void);
static void array_cases(void) {
    ID3D11SamplerState *s[4];for(unsigned i=0;i<4;++i)s[i]=(ID3D11SamplerState*)object(100+i,SD_COM_IF_ID3D11SamplerState);
    clear();ID3D11DeviceContext_PSSetSamplers(ctx,0,4,s);require(calls==1,"first sampler bind");
    ID3D11DeviceContext_PSSetSamplers(ctx,0,4,s);require(calls==1,"identical sampler bind crossed");
    s[1]=s[2];ID3D11DeviceContext_PSSetSamplers(ctx,0,4,s);require(calls==2,"mutated same-address sampler array lost");
    ID3D11DeviceContext_PSSetSamplers(ctx,1,2,s);require(calls==3,"overlapping sampler range lost");
    ID3D11DeviceContext_PSSetSamplers(ctx,0,4,s);require(calls==4,"overlap invalidation lost");
    ID3D11DeviceContext_PSSetSamplers(ctx,0,4,NULL);require(calls==5,"NULL array bypass");
    ID3D11DeviceContext_PSSetSamplers(ctx,0,4,s);require(calls==6,"NULL array did not invalidate");
    /* Differential random overlapping ranges. Independent reference stores
     * the actual 16 slots, rather than the optimization's last-call key. */
    uint32_t expected[16]={0},actual[16]={0},seed=0x67332;
    clear();for(unsigned i=0;i<20000;++i) {
        seed=seed*1664525u+1013904223u;UINT start=seed%12,count=1+(seed>>8)%4;
        ID3D11SamplerState *list[4];for(unsigned j=0;j<count;++j)list[j]=s[(seed>>(j*2))%4];
        for(unsigned j=0;j<count;++j)expected[start+j]=proxy_token(list[j]);
        unsigned before=calls;ID3D11DeviceContext_PSSetSamplers(ctx,start,count,list);
        if(calls!=before)for(unsigned j=0;j<count;++j)actual[start+j]=proxy_token(list[j]);
        require(!memcmp(expected,actual,sizeof(actual)),"random binding state diverged");
        before=calls;ID3D11DeviceContext_PSSetSamplers(ctx,start,count,list);require(calls==before,"random repeated binding crossed");
    }
}
static void fixed_cases(void) {
    D3D11_VIEWPORT vp={0,0,1280,720,0,1};clear();
    ID3D11DeviceContext_RSSetViewports(ctx,1,&vp);ID3D11DeviceContext_RSSetViewports(ctx,1,&vp);require(calls==1,"viewport miss");
    vp.Width=960;ID3D11DeviceContext_RSSetViewports(ctx,1,&vp);require(calls==2,"viewport contents ignored");
    D3D11_RECT rect={0,0,1280,720};ID3D11DeviceContext_RSSetScissorRects(ctx,1,&rect);
    unsigned n=calls;ID3D11DeviceContext_RSSetScissorRects(ctx,1,&rect);require(calls==n,"scissor miss");
    rect.right=640;ID3D11DeviceContext_RSSetScissorRects(ctx,1,&rect);require(calls==n+1,"scissor mutation lost");
    FLOAT factor[4]={1,1,1,1};clear();ID3D11DeviceContext_OMSetBlendState(ctx,NULL,NULL,~0u);
    ID3D11DeviceContext_OMSetBlendState(ctx,NULL,factor,~0u);require(calls==1,"default blend factor mismatch");
    factor[2]=0.5f;ID3D11DeviceContext_OMSetBlendState(ctx,NULL,factor,~0u);require(calls==2,"blend factor lost");
    ID3D11DeviceContext_OMSetBlendState(ctx,NULL,factor,3);require(calls==3,"sample mask lost");
    clear();ID3D11DeviceContext_OMSetDepthStencilState(ctx,NULL,5);ID3D11DeviceContext_OMSetDepthStencilState(ctx,NULL,5);
    require(calls==1,"stencil miss");ID3D11DeviceContext_OMSetDepthStencilState(ctx,NULL,6);require(calls==2,"stencil ref lost");
}
static void reset_and_errors(void) {
    clear();ID3D11DeviceContext_RSSetState(ctx,NULL);ID3D11DeviceContext_ClearState(ctx);calls=0;
    ID3D11DeviceContext_RSSetState(ctx,NULL);require(calls==1,"ClearState did not invalidate");
    for(unsigned restore=0;restore<2;++restore) {
        ID3D11DeviceContext_ExecuteCommandList(ctx,NULL,restore);calls=0;
        ID3D11DeviceContext_RSSetState(ctx,NULL);require(calls==1,"ExecuteCommandList did not invalidate");
        ID3D11DeviceContext_FinishCommandList(ctx,restore,NULL);calls=0;
        ID3D11DeviceContext_RSSetState(ctx,NULL);require(calls==1,"FinishCommandList did not invalidate");
    }
    struct sd_com_packet p={SD_COM_ABI,context_proxy->token,SD_COM_IF_ID3D11DeviceContext,43};
    proxy_state_invalidate(ctx);next_error=E_FAIL;require(proxy_state_call(ctx,&p)==E_FAIL,"transport error swallowed");
    unsigned n=calls;require(proxy_state_call(ctx,&p)==0&&calls==n+1,"failed call cached");
    proxy_state_invalidate(ctx);reenter=1;require(proxy_state_call(ctx,&p)==0,"reentrant call error");
    n=calls;require(proxy_state_call(ctx,&p)==0&&calls==n+1,"reentrant reset cached stale key");
    clear();ID3D11DeviceContext_PSSetShader(ctx,NULL,NULL,0);
    ID3D11ClassInstance *ci=(ID3D11ClassInstance*)object(211,SD_COM_IF_ID3D11ClassInstance);
    ID3D11DeviceContext_PSSetShader(ctx,NULL,&ci,1);calls=0;
    ID3D11DeviceContext_PSSetShader(ctx,NULL,NULL,0);require(calls==1,"class-instance bind did not invalidate");
    clear();reenter=2;ID3D11DeviceContext_PSSetShader(ctx,NULL,&ci,1);unsigned after=calls;
    ID3D11DeviceContext_RSSetState(ctx,NULL);require(calls==after+1,"uncacheable reentrant call published a key");
    for(unsigned reset=0;reset<3;++reset){
        clear();reenter=2;
        if(reset==0)ID3D11DeviceContext_ClearState(ctx);
        else if(reset==1)ID3D11DeviceContext_ExecuteCommandList(ctx,NULL,FALSE);
        else ID3D11DeviceContext_FinishCommandList(ctx,FALSE,NULL);
        after=calls;ID3D11DeviceContext_RSSetState(ctx,NULL);require(calls==after+1,"reentrant reset retained a key");
    }
    /* Native token generation, not heap/proxy addresses, forms the key. */
    struct proxy *shader=object(0x10022,SD_COM_IF_ID3D11PixelShader);
    ID3D11DeviceContext_PSSetShader(ctx,(ID3D11PixelShader*)shader,NULL,0);n=calls;
    shader->token=0x20022;ID3D11DeviceContext_PSSetShader(ctx,(ID3D11PixelShader*)shader,NULL,0);
    require(calls==n+1,"new token generation aliased");shader->token=0x10022;
    n=calls;for(unsigned i=0;i<10;++i){ID3D11DeviceContext_DrawIndexed(ctx,3,0,0);ID3D11DeviceContext_Dispatch(ctx,1,1,1);}
    require(calls==n+20,"draw/dispatch suppressed");
}
static DWORD WINAPI migrate(void *unused){(void)unused;ID3D11DeviceContext_RSSetState(ctx,NULL);return 0;}
static void thread_cases(void) {
    clear();ID3D11DeviceContext_RSSetState(ctx,NULL);unsigned n=calls;
    /* A foreign setter must never wait for the unrelated proxy-table lock. */
    EnterCriticalSection(&proxy_lock);HANDLE t=CreateThread(NULL,0,migrate,NULL,0,NULL);require(t!=NULL,"thread create");
    DWORD result=WaitForSingleObject(t,5000);LeaveCriticalSection(&proxy_lock);
    require(result==WAIT_OBJECT_0,"cache lock inversion");CloseHandle(t);
    require(calls==n+1&&context_proxy->state_cache->disabled,"thread migration not disabled");
    n=calls;ID3D11DeviceContext_RSSetState(ctx,NULL);ID3D11DeviceContext_RSSetState(ctx,NULL);require(calls==n+2,"owner reused migrated cache");
    struct proxy fallback={.magic=PROXY_MAGIC,.token=99,.interface_id=SD_COM_IF_ID3D11DeviceContext};
    struct sd_com_packet p={SD_COM_ABI,99,SD_COM_IF_ID3D11DeviceContext,43};n=calls;
    proxy_state_call(&fallback,&p);proxy_state_call(&fallback,&p);require(calls==n+2,"allocation fallback changed behavior");
}
#include "state_generated.inc"
void WINAPI start(void) {
    InitializeCriticalSection(&proxy_lock);endpoint_storage.handle=42;endpoint_storage.call=endpoint;published_endpoint=&endpoint_storage;
    context_proxy=object(1,SD_COM_IF_ID3D11DeviceContext);ctx=(ID3D11DeviceContext*)context_proxy;
    require(context_proxy->state_cache!=NULL,"context cache missing");
    generated_cases();array_cases();fixed_cases();reset_and_errors();thread_cases();proxy_state_report(600);
    require(last_method==SD_COM_STATE_REPORT,"state report missing");
    say("{\"status\":\"PASS\",\"random_bindings\":20000,\"methods\":25,\"real_pe32\":true,\"thread_migration\":true,\"reentrant_reset\":true}\n");
    ExitProcess(0);
}
