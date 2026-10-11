"""Generate PE32 COM vtables and typed native dispatch from pinned DXVK headers.

The generated code has explicit adapters for pointer-bearing structures and
Map. It does not reinterpret a guest vtable or expose a native COM pointer.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'src/native_dxvk_com'
CUSTOM = {
    'QueryInterface', 'AddRef', 'Release', 'Map', 'Unmap',
    'GetPrivateData', 'SetPrivateData', 'SetPrivateDataInterface',
    'CreateBuffer', 'CreateTexture1D', 'CreateTexture2D', 'CreateTexture3D',
    'CreateInputLayout', 'CreateGeometryShaderWithStreamOutput',
    'UpdateSubresource', 'CreateSwapChain', 'GetFullscreenState',
    'SetFullscreenState', 'ResizeBuffers', 'GetWindowAssociation',
    'MakeWindowAssociation', 'GetDesc', 'GetDesc1',
    'GetInstanceName', 'GetTypeName', 'CheckCounter', 'Enter', 'Leave',
    'Present',
}
UNSUPPORTED = {
    'OpenSharedResource', 'GetSharedHandle', 'CreateSoftwareAdapter',
    'GetDC', 'ReleaseDC', 'CreateSurface',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_params(text):
    # WIDL header parameter lists have no nested function pointers.
    return [x.strip() for x in text.replace('\n', ' ').split(',') if x.strip()]


def parse_param(text):
    text = re.sub(r'\s+', ' ', text).strip()
    m = re.fullmatch(r'(.*?)\b(\w+)\s*(\[\s*(\d+)\s*\])?', text)
    if not m:
        raise ValueError(text)
    ty, name, _, array = m.groups()
    ty = ty.strip()
    ty = re.sub(r'\bLPCSTR\b', 'const char *', ty)
    ty = re.sub(r'\bLPSTR\b', 'char *', ty)
    return dict(type=ty, name=name, array=int(array) if array else None,
                pointer=ty.count('*') + bool(array),
                base=re.sub(r'\bconst\b|\*', '', ty).strip())


def parse_headers(source):
    files = [source / 'include/native/directx' / x for x in ('d3d11.h', 'dxgi.h', 'd3d10.h')]
    interfaces = {}
    for path in files:
        text = path.read_text()
        for m in re.finditer(r'typedef struct (I\w+)Vtbl\s*\{(.*?)\}\s*\1Vtbl;', text, re.S):
            name, body = m.groups()
            if path.name == 'd3d10.h' and name != 'ID3D10Multithread':
                continue
            if any(x in name for x in ('Video','Authenticated','CryptoSession')):
                continue
            methods = []
            for ret, method, args in re.findall(r'(\w+)\s*\(STDMETHODCALLTYPE\s*\*(\w+)\)\s*\((.*?)\);', body, re.S):
                params = [parse_param(x) for x in split_params(args)]
                assert params[0]['name'] == 'This', (name, method)
                methods.append(dict(name=method, ret=ret, params=params[1:]))
            if not methods:
                continue
            guid = re.search(r'DEFINE_GUID\(IID_' + re.escape(name) + r',\s*(.*?)\);', text)
            parent = re.search(re.escape(name) + r'\s*:\s*public\s+(I\w+)\s*\{', text)
            assert guid and parent, name
            interfaces[name] = dict(name=name, parent=parent[1], guid=guid[1], methods=methods)
    interfaces['IUnknown'] = dict(name='IUnknown', parent=None,
        guid='0x00000000, 0x0000, 0x0000, 0xc0,0x00,0x00,0x00,0x00,0x00,0x00,0x46',
        methods=[dict(name='QueryInterface', ret='HRESULT', params=[parse_param('REFIID riid'), parse_param('void **ppvObject')]),
                 dict(name='AddRef', ret='ULONG', params=[]), dict(name='Release', ret='ULONG', params=[])])
    # Annotate parameters from the exact Wine IDL input, using ordinal matching
    # because a few DXGI header parameter names differ from their IDL names.
    idl_root = Path('/home/blekjek/sleepingdogs-low-window-v1/native-source/include')
    idl_files = [idl_root / x for x in ('d3d11.idl', 'dxgi.idl', 'd3d10.idl', 'unknwn.idl')]
    declarations = {}
    for path in idl_files:
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', path.read_text(), flags=re.S)
        for name, body in re.findall(r'interface\s+(I\w+)\s*:\s*I\w+\s*\{(.*?)\}', text, re.S):
            for ret, method, args in re.findall(r'(\w+)\s+(\w+)\s*\((.*?)\)\s*;', body, re.S):
                pieces = re.split(r',\s*(?![^\[]*\])', args)
                declarations[(name, method)] = ['out' if re.search(r'\[[^\]]*\bout\b', p) else 'in' for p in pieces if p.strip()]
    for i, name in enumerate(sorted(interfaces), 1):
        interface = interfaces[name]
        interface['id'] = i
        for index, method in enumerate(interface['methods']):
            method['index'] = index
            owner = interface
            while owner['parent'] in interfaces and any(x['name'] == method['name'] for x in interfaces[owner['parent']]['methods']):
                owner = interfaces[owner['parent']]
            method['owner'] = owner['name']
            directions = declarations.get((owner['name'], method['name']), [])
            for j, p in enumerate(method['params']):
                p['direction'] = directions[j] if j < len(directions) else 'in'
                # The IDL labels GetData's writable query destination [in].
                if method['name'] == 'GetData' and p['name'] == 'pData':
                    p['direction'] = 'out'
    return interfaces, files + idl_files


def count_expr(interface, method, p, host=False):
    name, params = p['name'], method['params']
    names = {x['name']: x for x in params}
    if p['array']:
        return str(p['array'])
    if name in ('pViewports','pRects'):
        stem = 'Viewports' if name == 'pViewports' else 'Rects'
        if 'pNum'+stem in names:
            return '(pNum'+stem+' ? *pNum'+stem+' : 0)'
    if name in ('pStrides', 'pOffsets'):
        return 'NumBuffers'
    if name == 'pUAVInitialCounts':
        return 'NumUAVs'
    if p['base'].startswith('I') and p['pointer'] >= 2:
        if 'ClassInstances' in name:
            if 'NumClassInstances' in names:
                return 'NumClassInstances'
            return '(pNumClassInstances ? *pNumClassInstances : 0)'
        # A method's count belongs to its named array, not every COM output.
        # OMGetRenderTargets returns NumViews RTVs but exactly one DSV.
        arrays = {'ppRenderTargetViews': ('NumRTVs','NumViews'),
                  'ppUnorderedAccessViews': ('NumUAVs','NumViews'),
                  'ppConstantBuffers': ('NumBuffers',), 'ppVertexBuffers': ('NumBuffers',),
                  'ppSOTargets': ('NumBuffers',), 'ppShaderResourceViews': ('NumViews',),
                  'ppSamplers': ('NumSamplers',), 'ppResources': ('NumResources',)}
        for n in arrays.get(name, ()):
            if n in names:
                return n
        return '1'
    for pn, n in [('pViewports','NumViewports'), ('pRects','NumRects'), ('pResources','NumResources'),
                  ('pResidencyStatus','NumResources'), ('pStrides','NumBuffers'), ('pBufferStrides','NumStrides')]:
        if pn == name and n in names:
            return n
    if method['name'] == 'GetDisplayModeList' and name in ('pDesc', 'desc'):
        n = 'pNumModes' if 'pNumModes' in names else 'mode_count'
        return '(' + n + ' ? *' + n + ' : 0)'
    return '1'


def is_custom(interface, method):
    name, owner = method['name'], method['owner']
    if name == 'GetDesc':
        return interface.startswith(('IDXGIAdapter', 'IDXGIOutput', 'IDXGISwapChain'))
    if name == 'GetDesc1':
        return interface == 'IDXGIAdapter1'
    if name in ('Map', 'Unmap'):
        return True
    return name in CUSTOM


def return_fail(ret):
    return 'proxy_fatal(E_OUTOFMEMORY); return;' if ret == 'void' else 'return (' + ret + ')E_OUTOFMEMORY;'


def guest_method(interface, method, interfaces):
    name, ret, params = method['name'], method['ret'], method['params']
    signature = ', '.join([interface + ' *This'] + [p['type'] + ' ' + p['name'] + ('['+str(p['array'])+']' if p['array'] else '') for p in params])
    lines = [f'static {ret} STDMETHODCALLTYPE g_{interface}_{name}({signature}) {{',
             f'    struct sd_com_packet packet = {{SD_COM_ABI, proxy_token(This), SD_COM_IF_{interface}, {method["index"]}}};']
    if name in ('QueryInterface','AddRef','Release'):
        call = {'QueryInterface':'proxy_query(This, riid, ppvObject)', 'AddRef':'proxy_addref(This)', 'Release':'proxy_release(This)'}[name]
        return '\n'.join([lines[0], '    return '+call+';', '}'])
    if name == 'Map' and method['owner'] == 'ID3D11DeviceContext':
        return '\n'.join([lines[0], '    return proxy_map(This, pResource, Subresource, MapType, MapFlags, pMappedResource);', '}'])
    if name == 'Unmap' and method['owner'] == 'ID3D11DeviceContext':
        return '\n'.join([lines[0], '    proxy_unmap(This, pResource, Subresource);', '}'])
    if name == 'GetPrivateData':
        return '\n'.join([lines[0], '    return proxy_private_get(This, '+str(method['index'])+', '+', '.join(p['name'] for p in params)+');', '}'])
    outputs, input_arrays = [], []
    def cleanup():
        return ' '.join([f'if(tokens_{pn} && count_{pn}>128) HeapFree(GetProcessHeap(),0,tokens_{pn});' for pn in input_arrays] +
                        [f'proxy_output_dispose(&wire_{pn},{kind});' for pn,_,kind in outputs])
    for j, p in enumerate(params):
        ty, pn, base, ptr = p['type'], p['name'], p['base'], p['pointer']
        iid = next((x['name'] for x in params if x['type'] == 'REFIID'), None)
        typed_output = base in interfaces and ptr >= 2 and p['direction'] == 'out'
        iid_output = base == 'void' and ptr == 2 and iid
        if typed_output or iid_output:
            count = count_expr(interface, method, p) if typed_output else '1'
            kind = f'SD_COM_IF_{base}' if typed_output else f'proxy_iid({iid})'
            lines += [f'    struct proxy_output wire_{pn};',
                      f'    if (!proxy_output_init(&wire_{pn},{pn},safe_array_count({count}))) {{ {cleanup()} {return_fail(ret)} }}',
                      f'    packet.args[{j}] = guest_address(wire_{pn}.tokens);']
            outputs.append((pn,count,kind))
        elif base in interfaces and ptr >= 2:
            count = count_expr(interface, method, p)
            lines += [f'    UINT count_{pn} = safe_array_count({count});',
                      f'    uint32_t stack_{pn}[128];',
                      f'    uint32_t *tokens_{pn} = {pn} && count_{pn} ? (count_{pn}<=128 ? stack_{pn} : HeapAlloc(GetProcessHeap(), 0, count_{pn}*4)) : NULL;',
                      f'    if ({pn} && count_{pn} && !tokens_{pn}) {{ {cleanup()} {return_fail(ret)} }}',
                      f'    for (UINT i=0; i<count_{pn} && {pn}; ++i) tokens_{pn}[i] = proxy_token({pn}[i]);',
                      f'    packet.args[{j}] = guest_address(tokens_{pn});']
            input_arrays.append(pn)
        elif base in interfaces and ptr == 1:
            lines.append(f'    packet.args[{j}] = proxy_token({pn});')
        elif ptr or ty.startswith('REF') or base in ('HANDLE','HWND','HDC','HMONITOR','HMODULE'):
            lines.append(f'    packet.args[{j}] = guest_address({pn});')
        elif base in ('UINT64','ULONGLONG'):
            lines += [f'    packet.args[{j}] = (uint32_t){pn};', f'    packet.high[{j}] = (uint32_t)({pn} >> 32);']
        elif base in ('FLOAT','float'):
            lines.append(f'    packet.args[{j}] = float_bits({pn});')
        else:
            lines.append(f'    packet.args[{j}] = (uint32_t){pn};')
    lines.append('    LONG status = proxy_call(&packet);')
    for pn in input_arrays:
        lines.append(f'    if (tokens_{pn} && count_{pn}>128) HeapFree(GetProcessHeap(), 0, tokens_{pn});')
    success='status >= 0'+(' && SUCCEEDED((HRESULT)packet.ret)' if ret=='HRESULT' else '')
    for pn,count,kind in outputs:
        lines.append(f'    if ({success} && !proxy_output_publish(&wire_{pn},{pn},safe_array_count({count}),{kind})) status=E_OUTOFMEMORY;')
    for pn,count,kind in outputs:
        lines.append(f'    if (!({success})) proxy_output_retract(&wire_{pn},{pn});')
        lines.append(f'    proxy_output_dispose(&wire_{pn},{kind});')
    lines.append(f'    if (status < 0) {{ {"proxy_fatal(status); return;" if ret == "void" else "return ("+ret+")status;"} }}')
    if ret == 'void':
        lines.append('    if ((LONG)packet.fault < 0) proxy_fatal((LONG)packet.fault);')
    if name == 'GetDesc' and interface == 'IDXGIOutput':
        out = params[0]['name']
        lines.append(f'    if ({out} && SUCCEEDED((HRESULT)packet.ret)) {out}->Monitor = MonitorFromWindow(NULL, MONITOR_DEFAULTTOPRIMARY);')
    if ret != 'void':
        lines.append('    return bits_float(packet.ret);' if ret == 'FLOAT' else '    return ('+ret+')packet.ret;')
    lines.append('}')
    return '\n'.join(lines)


def host_method(interface, method, interfaces):
    ret, name, params = method['ret'], method['name'], method['params']
    lines = [f'case {method["index"]}: {{ // {interface}::{name}']
    if name in ('QueryInterface','AddRef','Release'):
        return '\n'.join(lines + [f'    return c.{name}(p);', '}'])
    if name in UNSUPPORTED:
        return '\n'.join(lines + [f'    return c.unsupported(p, "{interface}::{name}");', '}'])
    if is_custom(interface, method):
        return '\n'.join(lines + [f'    return custom_{method["owner"]}_{name}(c, object, p);', '}'])
    after = []
    for j, param in enumerate(params):
        ty, pn, base, ptr, direction = (param[k] for k in ('type','name','base','pointer','direction'))
        raw = f'p.args[{j}]'
        counter='c.keep_array_count' if name=='OMSetRenderTargetsAndUnorderedAccessViews' else 'c.array_count'
        if base in interfaces and ptr >= 2:
            count = count_expr(interface, method, param)
            lines.append(f'    const uint32_t count_{pn} = {counter}({count});')
            if direction == 'out':
                lines += [f'    auto guest_{pn} = c.write<uint32_t>({raw}, count_{pn});',
                          f'    if (guest_{pn}) std::fill_n(guest_{pn}, count_{pn}, 0u);',
                          f'    std::vector<{base}*> native_{pn}(count_{pn}, nullptr);',
                          f'    auto {pn} = guest_{pn} ? native_{pn}.data() : nullptr;']
                after.append(f'    if (guest_{pn}) for (uint32_t i=0; i<count_{pn}; ++i) guest_{pn}[i] = c.adopt(native_{pn}[i], SD_COM_IF_{base});')
            else:
                lines += [f'    auto tokens_{pn} = c.read<uint32_t>({raw}, count_{pn});',
                          f'    std::vector<{base}*> native_{pn}(tokens_{pn} ? count_{pn} : 0);',
                          f'    for (uint32_t i=0; i<native_{pn}.size(); ++i) native_{pn}[i] = c.object<{base}>(tokens_{pn}[i], SD_COM_IF_{base});',
                          f'    auto {pn} = tokens_{pn} ? native_{pn}.data() : nullptr;']
        elif base in interfaces and ptr == 1:
            lines.append(f'    auto {pn} = c.object<{base}>({raw}, SD_COM_IF_{base});')
        elif ty.startswith('REF'):
            lines.append(f'    auto {pn} = *c.required_read<GUID>({raw});')
        elif ptr:
            count = count_expr(interface, method, param)
            # Length-bearing raw byte buffers and null-terminated class names.
            if base == 'void' and ptr == 1:
                names = {x['name'] for x in params}
                length = next((n for n in ('BytecodeLength','FeatureSupportDataSize','DataSize','BufferSize','DataSizeInBytes') if n in names), None)
                if not length:
                    raise ValueError((interface, name, pn, 'unclassified byte buffer'))
                op = 'write' if direction == 'out' else 'read'
                lines.append(f'    auto {pn} = c.{op}<unsigned char>({raw}, {length});')
            elif base == 'void' and ptr == 2:
                iid = next((x['name'] for x in params if x['type'] == 'REFIID'), None)
                if not iid:
                    raise ValueError((interface, name, pn, 'void** without iid'))
                lines += [f'    auto guest_{pn} = c.write<uint32_t>({raw});', f'    void *native_{pn} = nullptr;', f'    auto {pn} = guest_{pn} ? &native_{pn} : nullptr;']
                after.append(f'    if (guest_{pn}) *guest_{pn} = c.adopt((IUnknown*)native_{pn}, c.iid({iid}));')
            else:
                op = 'write' if direction == 'out' else 'read'
                if base in ('LPCSTR','char'):
                    lines.append(f'    auto {pn} = c.string({raw});')
                else:
                    lines.append(f'    auto {pn} = c.{op}<{base}>({raw}, {counter}({count}));')
        elif base in ('LPCSTR', 'PCSTR'):
            lines.append(f'    auto {pn} = c.string({raw});')
        elif base in ('HANDLE','HWND','HDC','HMONITOR','HMODULE'):
            raise ValueError((interface, name, pn, 'native handle conversion required'))
        elif base in ('UINT64','ULONGLONG'):
            lines.append(f'    auto {pn} = uint64_t({raw}) | uint64_t(p.high[{j}])<<32;')
        elif base in ('FLOAT','float'):
            lines.append(f'    auto {pn} = bits_float({raw});')
        else:
            lines.append(f'    auto {pn} = ({ty}){raw};')
    # Parameters can refer to a later scalar/count pointer: declarations must
    # precede array construction. Preserve relative order inside each category.
    prefix, declarations = lines[:1], lines[1:]
    scalar_names = {x['name'] for x in params if x['pointer']==0 and x['type'] not in ('LPCSTR','PCSTR')}
    count_names = {x['name'] for x in params if x['base']=='UINT' and x['pointer']==1}
    first = [x for x in declarations if any(re.match(r'    auto '+re.escape(n)+r' = ', x) for n in scalar_names | count_names)]
    lines = prefix + first + [x for x in declarations if x not in first]
    invocation = f'object->{name}(' + ', '.join(x['name'] for x in params) + ')'
    if method['owner'] == 'ID3D11DeviceContext' and name.startswith('Draw'):
        lines.append('    ++c.draws;')
    if ret == 'void':
        lines.append('    '+invocation+';')
    else:
        lines.append('    auto result = '+invocation+';')
    if ret == 'HRESULT' and after:
        lines.append('    if (FAILED(result)) { p.ret = result; return; }')
    lines += after
    lines.append('    p.ret = bits_float(result);' if ret == 'FLOAT' else '    p.ret = result;' if ret != 'void' else '    p.ret = 0;')
    lines += ['    return;', '}']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path, default=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1/source'))
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    interfaces, files = parse_headers(args.source)
    names = sorted(interfaces)
    decl = ['/* Generated by tools/generate_native_dxvk_com.py. */', '#pragma once', 'enum sd_com_interface { SD_COM_IF_NONE = 0,']
    decl += [f'    SD_COM_IF_{name} = {interfaces[name]["id"]},' for name in names]
    decl += ['};', '#define SD_COM_INTERFACE_COUNT '+str(len(names)+1)]
    (DEST/'com_interfaces.h').write_text('\n'.join(decl)+'\n',newline='\n')
    methods=['/* Generated COM ordinals for validation fixtures. */','#pragma once','enum sd_com_method {']
    for name in names:
        methods += [f'    SD_COM_M_{name}_{m["name"]} = {m["index"]},' for m in interfaces[name]['methods']]
    methods += ['};']
    (DEST/'com_methods.h').write_text('\n'.join(methods)+'\n',newline='\n')
    ids = ['/* Generated GUID/interface inventory. */']
    ids += [f'{{SD_COM_IF_{name}, {{{interfaces[name]["guid"]}}}, "{name}"}},' for name in names]
    (DEST/'com_guids.inc').write_text('\n'.join(ids)+'\n',newline='\n')
    inheritance = ['/* Generated type compatibility. */', 'static bool interface_is_a(uint32_t actual, uint32_t expected) {', '    if (actual == expected) return true;', '    switch (actual) {']
    for name in names:
        parents=[];parent=interfaces[name]['parent']
        while parent in interfaces:
            parents.append('expected == SD_COM_IF_'+parent);parent=interfaces[parent]['parent']
        inheritance.append('    case SD_COM_IF_'+name+': return '+(' || '.join(parents) if parents else 'false')+';')
    inheritance += ['    default: return false;', '    }', '}']
    (DEST/'com_inheritance.inc').write_text('\n'.join(inheritance)+'\n',newline='\n')
    guest, native = [], []
    for name in names:
        interface = interfaces[name]
        for method in interface['methods']:
            guest.append(guest_method(name, method, interfaces))
        guest += ['static const '+name+'Vtbl vtbl_'+name+' = {', ',\n'.join('    g_'+name+'_'+m['name'] for m in interface['methods']), '};']
        native += [f'case SD_COM_IF_{name}: {{', f'    auto object = c.object<{name}>(p.object, SD_COM_IF_{name});', '    if (!object) throw Fault(E_POINTER);', '    switch (p.method) {']
        native += [host_method(name,m,interfaces) for m in interface['methods']]
        native += ['    default: return c.unsupported(p, "invalid method index");', '    }', '}']
    guest += ['static const void *proxy_vtable(uint32_t interface_id) {', '    switch (interface_id) {']
    guest += [f'    case SD_COM_IF_{name}: return &vtbl_{name};' for name in names]
    guest += ['    default: return NULL;', '    }', '}']
    (DEST/'com_guest_vtables.inc').write_text('\n'.join(guest)+'\n',newline='\n')
    (DEST/'com_native_dispatch.inc').write_text('\n'.join(native)+'\n',newline='\n')
    manifest=dict(status='GENERATED',interfaces=interfaces,header_inputs={str(p):sha(p) for p in files},
                  generator_sha256=sha(Path(__file__)),unsupported_methods=sorted(UNSUPPORTED),
                  interface_count=len(names),vtable_entries=sum(len(i['methods']) for i in interfaces.values()))
    (DEST/'com_inventory.json').write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')
    print(json.dumps({k:manifest[k] for k in ('status','interface_count','vtable_entries','unsupported_methods')},indent=2))


if __name__ == '__main__':
    main()
