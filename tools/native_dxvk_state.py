"""Generate a conservative guest binding cache on the compact synchronous ABI."""
from pathlib import Path
import json
from native_dxvk_compact import ROOT
from launcher_v1_overlay import replace

METHODS=('VSSetConstantBuffers PSSetConstantBuffers GSSetConstantBuffers HSSetConstantBuffers DSSetConstantBuffers CSSetConstantBuffers '
         'VSSetSamplers PSSetSamplers GSSetSamplers HSSetSamplers DSSetSamplers CSSetSamplers '
         'VSSetShader PSSetShader GSSetShader HSSetShader DSSetShader CSSetShader '
         'IASetInputLayout IASetPrimitiveTopology RSSetState OMSetDepthStencilState OMSetBlendState RSSetViewports RSSetScissorRects').split()
INVALIDATE=('ClearState','ExecuteCommandList','FinishCommandList')

def guest(source):
    text=(source/'com_guest.c').read_text()
    text=replace(text,'#include "com_protocol.h"','#include "com_protocol.h"\n#include "com_state_cache.h"\n#include <intrin.h>')
    text=replace(text,'    LONG refs;','    LONG refs;\n    struct sd_state_cache *state_cache;')
    text=replace(text,'/* Keep wire handles private','\n#include "com_state_guest.inc"\n\n/* Keep wire handles private')
    text=replace(text,'    struct proxy *p=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(*p));',
        '    size_t extra=kind==SD_COM_IF_ID3D11DeviceContext?sizeof(struct sd_state_cache):0;\n'
        '    struct proxy *p=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(*p)+extra);\n'
        '    if(!p&&extra){extra=0;p=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(*p));}')
    text=replace(text,'        p->vtbl=vtbl;','        p->state_cache=extra?(struct sd_state_cache*)(p+1):NULL;\n        p->vtbl=vtbl;')
    text=replace(text,'    InterlockedExchange(&reporting,0);','    proxy_state_report(presents);\n    InterlockedExchange(&reporting,0);')
    (source/'com_guest.c').write_text(text,newline='\n')
    text=(source/'com_guest_vtables.inc').read_text()
    inventory=json.loads((source/'com_inventory.json').read_text())['interfaces']
    assert not any(n.startswith('ID3D11DeviceContext') and n!='ID3D11DeviceContext' for n in inventory)
    for name in METHODS+list(INVALIDATE):
        pos=text.index('g_ID3D11DeviceContext_'+name+'(');end=text.index('\n}',pos)
        body=text[pos:end]
        before='LONG status = proxy_call(&packet);'
        after='LONG status = proxy_state_call(This,&packet);' if name in METHODS else 'proxy_state_invalidate(This);\n    '+before+'\n    proxy_state_invalidate(This);'
        body=replace(body,before,after);text=text[:pos]+body+text[end:]
    (source/'com_guest_vtables.inc').write_text(text,newline='\n')

def native(text):
    text=replace(text,'#include "com_protocol.h"','#include "com_protocol.h"\n#include "com_state_cache.h"')
    return replace(text,'    case SD_COM_SHUTDOWN:', '''    case SD_COM_STATE_REPORT: {
        char line[384];
        std::snprintf(line,sizeof(line),"[SD-NDX-STATE] v1 presents=%u attempts=%u skipped=%u disabled_contexts=%u contexts=%u cb=%u sampler=%u shader=%u fixed=%u; redundant bindings only; draws/maps unchanged",
            p.args[1],p.args[2],p.args[3],p.args[4],p.args[5],p.args[6],p.args[7],p.args[8],p.args[9]);
        wine_nx_runtime_trace(line);p.ret=0;return;
    }
    case SD_COM_SHUTDOWN:''')
