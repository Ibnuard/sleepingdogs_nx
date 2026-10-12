"""Inline short input payloads without deferring or suppressing a COM call.

Applied only to the immutable Compact v1 source copy. The 160-byte wire layout
stays unchanged. A new marker rejects mismatched old native builds cleanly.
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
# Method -> pointer argument -> (element count expression, 32-bit words/element).
POINTERS={}
for i in (7,8,10,16,22,25,26,31,32,59,61,62,63,65,66,67,70,71):
    POINTERS[i]={2:('param1',1)}
for i in (9,11,23,60,64,69):POINTERS[i]={1:('param2',1)}
POINTERS.update({18:{2:('param1',1),3:('param1',1),4:('param1',1)},
    33:{1:('param0',1)},34:{1:('param0',1),5:('param4',1),6:('param4',1)},
    35:{1:('4',1)},37:{1:('param0',1),2:('param0',1)},
    44:{1:('param0',6)},45:{1:('param0',4)},68:{2:('param1',1),3:('param1',1)}})

def methods():
    items=json.loads((ROOT/'src/native_dxvk_com/com_inventory.json').read_text())
    return [m for m in items['interfaces']['ID3D11DeviceContext']['methods'] if m['index'] in POINTERS]

def pointers(m):
    return {i:((m['params'][int(n[5:])]['name'] if n.startswith('param') else n),words)
            for i,(n,words) in POINTERS[m['index']].items()}

def fast_body(m):
    params=m['params'];nargs=len(params);ptr=pointers(m)
    counts=sorted({n for n,_ in ptr.values() if not n.isdigit()})
    # Check counts before any multiplication. Even a NULL pointer with an
    # invalid count retains the exact old fallback/validation path.
    conditions=[n+'<=SD_COM_MAX_ARRAY' for n in counts]
    sizes=[f'({params[i]["name"]} ? ({count})*{words}u : 0u)' for i,(count,words) in ptr.items()]
    conditions.append('('+'+'.join(sizes)+')!=0u')
    conditions.append(f'{nargs}u+'+'+'.join(sizes)+'<=32u')
    out=['    /* Short input arrays share the already-validated packet storage. */',
         '    if('+ ' && '.join(conditions)+') {','        struct sd_com_packet packet;',
         '        packet.abi=SD_COM_ABI;packet.object=proxy_token(This);',
         f'        packet.interface_id=SD_COM_IF_ID3D11DeviceContext;packet.method={m["index"]};',
         f'        packet.ret=packet.fault=packet.aux=0;packet.reserved=SD_COM_INLINE_MAGIC|{nargs}u;',
         f'        UINT inline_at={nargs}u;']
    for i,p in enumerate(params):
        name=p['name']
        if i in ptr:
            count,words=ptr[i]
            out += [f'        packet.args[{i}]=0;',f'        if({name} && ({count})) {{',
                    f'            packet.args[{i}]=guest_address(&packet.words[inline_at]);']
            if p['pointer']==2 and p['base'].startswith('I'):
                out.append(f'            for(UINT k=0;k<({count});++k)packet.words[inline_at+k]=proxy_token({name}[k]);')
            else:
                out.append(f'            memcpy(&packet.words[inline_at],{name},({count})*{words}u*4u);')
            out += [f'            inline_at+=({count})*{words}u;', '        }']
        elif p['base'].startswith('I') and p['pointer']==1:
            out.append(f'        packet.args[{i}]=proxy_token({name});')
        else:
            assert p['pointer']==0,(m['name'],p)
            out.append(f'        packet.args[{i}]=(uint32_t){name};')
    out += ['        LONG status=proxy_call(&packet);',
            '        if(status<0){proxy_fatal(status);return;}',
            '        if((LONG)packet.fault<0)proxy_fatal((LONG)packet.fault);',
            '        return;','    }']
    return '\n'.join(out)+'\n'

def guest(source):
    source=Path(source)
    text=(source/'com_guest_vtables.inc').read_text()
    for m in methods():
        pos=text.index('g_ID3D11DeviceContext_'+m['name']+'(')
        pos=text.index('{\n',pos)+2
        text=text[:pos]+fast_body(m)+text[pos:]
    (source/'com_guest_vtables.inc').write_text(text,newline='\n')
    path=source/'com_guest.c';text=path.read_text()
    assert text.count('#include "com_protocol.h"')==1
    path.write_text(text.replace('#include "com_protocol.h"','#include "com_protocol.h"\n#include "com_inline.h"'),newline='\n')
    path=source/'com_protocol.h';text=path.read_text()
    before='    uint32_t args[16], high[16];';assert text.count(before)==1
    # A real 32-element array avoids crossing the former args[16] subobject.
    text=text.replace(before,'''    union {
        struct { uint32_t args[16], high[16]; };
        uint32_t words[32];
    };''')
    path.write_text(text,newline='\n')
    path=source/'com_compact.h';text=path.read_text()
    text=text.replace('#include "com_protocol.h"','#include "com_protocol.h"\n#include "com_inline.h"')
    before='if(n<0||p->reserved!=(SD_COM_COMPACT_MAGIC|(uint32_t)n))return 0;'
    assert text.count(before)==1
    text=text.replace(before,'''if(n<0)return 0;
    if(p->reserved!=(SD_COM_COMPACT_MAGIC|(uint32_t)n) &&
       (sd_com_inline_count(p->interface_id,p->method)!=n ||
        p->reserved!=(SD_COM_INLINE_MAGIC|(uint32_t)n)))return 0;''')
    text=text.replace('memcpy(p->args,wire->args,128)','memcpy(p->words,wire->words,128)')
    text=text.replace('memset(p->args,0,128)','memset(p->words,0,128)')
    path.write_text(text,newline='\n')

def native(text):
    def change(before,after):
        nonlocal text
        assert text.count(before)==1,before
        text=text.replace(before,after)
    change('#include "com_compact.h"','#include "com_compact.h"\n#include "com_inline.h"')
    change('uint64_t compact_calls=0,compact_bytes_saved=0;',
           'uint64_t compact_calls=0,compact_bytes_saved=0;\n    uint64_t inline_packets=0,inline_reads_saved=0,inline_bytes_saved=0,external_read_probes=0;\n    uint64_t sampler_create_calls=0,format_check_calls=0;')
    before='''        if(count>UINT32_MAX/sizeof(T)||address<0x10000||uint64_t(address)+bytes>(uint64_t(1)<<32)||
           !virtual_check_buffer_for_read(reinterpret_cast<void*>(uintptr_t(address)),size_t(bytes)))throw Fault(E_POINTER);'''
    change(before,'''        if(count>UINT32_MAX/sizeof(T)||address<0x10000||uint64_t(address)+bytes>(uint64_t(1)<<32))throw Fault(E_POINTER);
        if(sd_com::current_inline_range().covers(address,bytes)) {
            ++inline_reads_saved;inline_bytes_saved+=bytes;
        } else {
            ++external_read_probes;
            if(!virtual_check_buffer_for_read(reinterpret_cast<void*>(uintptr_t(address)),size_t(bytes)))throw Fault(E_POINTER);
        }''')
    change('''    sd_com_packet* output=nullptr;
    try {''','''    sd_com_packet* output=nullptr;
    // Clear the outer range before even the nested packet's permission check.
    sd_com::InlineScope inline_scope;
    try {''')
    change('''        if(!sd_com_wire_decode(&p,output))return int32_t(0xc000000du);''','''        if(!sd_com_wire_decode(&p,output))return int32_t(0xc000000du);
        inline_scope.allow(uint32_t(address),p);
        if((p.reserved&0xffff0000u)==SD_COM_INLINE_MAGIC)++state.inline_packets;
        if(p.interface_id==SD_COM_IF_ID3D11Device) {
            if(p.method==SD_COM_M_ID3D11Device_CreateSamplerState)++state.sampler_create_calls;
            if(p.method==SD_COM_M_ID3D11Device_CheckFormatSupport)++state.format_check_calls;
        }''')
    marker='''        wine_nx_runtime_trace(line);
    }
    void abort_map'''
    change(marker,'''        wine_nx_runtime_trace(line);
        std::snprintf(line,sizeof(line),"[SD-NDX-INLINE] v1 packets=%llu reads_reused=%llu bytes_reused=%llu external_read_probes=%llu sampler_create=%llu format_check=%llu",
            (unsigned long long)inline_packets,(unsigned long long)inline_reads_saved,
            (unsigned long long)inline_bytes_saved,(unsigned long long)external_read_probes,
            (unsigned long long)sampler_create_calls,(unsigned long long)format_check_calls);
        wine_nx_runtime_trace(line);
    }
    void abort_map''')
    change('#ifdef SD_COM_HOST_FAULT_TESTS\nvoid sd_com_test_fail_adopt_after',
           '''#ifdef SD_COM_HOST_FAULT_TESTS
void sd_com_test_inline_stats(uint64_t* out) {
    std::lock_guard<std::recursive_mutex> guard(state.mutex);
    out[0]=state.inline_packets;out[1]=state.inline_reads_saved;
    out[2]=state.inline_bytes_saved;out[3]=state.external_read_probes;
}
void sd_com_test_fail_adopt_after''')
    return text
