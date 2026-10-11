"""Compare PE32 and ARM64 layouts of every directly forwarded COM POD type."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
from build_native_dxvk_h4 import A64,MINGW,SOURCES,LOCAL,WORK

EXPLICIT={'void','char','LPCSTR','LPSTR','HANDLE','HWND','HDC','HMONITOR','HMODULE',
          'D3D11_SUBRESOURCE_DATA','D3D11_MAPPED_SUBRESOURCE','D3D11_INPUT_ELEMENT_DESC',
          'D3D11_SO_DECLARATION_ENTRY','DXGI_ADAPTER_DESC','DXGI_ADAPTER_DESC1','DXGI_OUTPUT_DESC','DXGI_SWAP_CHAIN_DESC',
          'SIZE_T','DXGI_MAPPED_RECT','DXGI_SHARED_RESOURCE'}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    inventory=json.loads((SOURCES/'com_inventory.json').read_text());interfaces=inventory['interfaces']
    types={'GUID','uint32_t','uint64_t','sd_com_packet','sd_com_swapchain32','sd_com_mapped32','sd_com_subresource32','sd_com_input32','sd_com_so32'}
    for interface in interfaces.values():
        for method in interface['methods']:
            for param in method['params']:
                if param['pointer'] and param['base'] not in interfaces and param['base'] not in EXPLICIT:types.add(param['base'])
    names=sorted(types);work=WORK/'abi';work.mkdir(parents=True,exist_ok=True)
    file=work/'layouts.cpp'
    file.write_text('#include <d3d11.h>\n#include <d3d10.h>\n#include <dxgi.h>\n#include "com_protocol.h"\n'
        +'uint32_t sd_layouts[]={\n'+',\n'.join(f' sizeof({name}), __alignof__({name})' for name in names)+'\n};\n')
    source=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1/source');values={};commands={}
    for target in ('pe32','arm64'):
        obj=work/(target+'.o');binary=work/(target+'.bin')
        if target=='pe32':
            command=[str(MINGW/'i686-w64-mingw32-g++'),'-std=c++17','-I'+str(SOURCES),'-c',str(file),'-o',str(obj)]
            copy=str(MINGW/'llvm-objcopy')
        else:
            command=[str(A64/'aarch64-none-elf-g++'),'-std=c++17','-I'+str(SOURCES),
                     *['-I'+str(source/p) for p in ('include/native/windows','include/native/directx','include/native','include')],
                     '-c',str(file),'-o',str(obj)]
            copy=str(A64/'aarch64-none-elf-objcopy')
        commands[target]=command;subprocess.run(command,check=True,capture_output=True)
        subprocess.run([copy,'--dump-section','.data='+str(binary),str(obj)],check=True,capture_output=True)
        data=binary.read_bytes();assert len(data)==len(names)*8,(target,len(data),len(names))
        values[target]=list(struct.iter_unpack('<II',data))
    differences={name:dict(pe32=x,arm64=y) for name,x,y in zip(names,values['pe32'],values['arm64']) if x!=y}
    assert not differences,differences
    receipt=dict(status='PASS',direct_layout_types=len(names),layouts={name:dict(bytes=x[0],alignment=x[1]) for name,x in zip(names,values['pe32'])},
                 explicit_pointer_or_wchar_adapters=sorted(EXPLICIT-{'void','char','LPCSTR','LPSTR','DXGI_MAPPED_RECT','DXGI_SHARED_RESOURCE'}),
                 excluded_unsupported_structures=['DXGI_MAPPED_RECT','DXGI_SHARED_RESOURCE'],compile_commands=commands,
                 inventory_sha256=sha(SOURCES/'com_inventory.json'),fixture_sha256=sha(file),runner_sha256=sha(__file__),
                 hardware_tested=False,com_guest_execution_tested=False,scope='Compiled PE32/ARM64 size/alignment equality; pointer-bearing descriptors use separate adapters.')
    LOCAL.mkdir(parents=True,exist_ok=True);(LOCAL/'abi-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
