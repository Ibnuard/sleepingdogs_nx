"""Link the native-DXVK subset into a standalone Horizon/Mesa diagnostic NRO.

Consumes the verified v1 DXVK archive and v18's pinned Mesa inputs. No Wine,
FEX, LSFG, game prefix, global SDK files or baseline runtime are modified.
"""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import struct
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SDK=Path('/opt/devkitpro')
TOOLS=SDK/'devkitA64/bin'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(argv, log, cwd):
    environment=dict(os.environ,DEVKITPRO=str(SDK),DEVKITA64=str(SDK/'devkitA64'))
    with log.open('w') as output:
        result=subprocess.run(list(map(str,argv)),cwd=cwd,env=environment,stdout=output,stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text()[-6000:]);raise RuntimeError(str(log))

def inspect_elf(elf):
    reader=TOOLS/'aarch64-none-elf-readelf'
    header=subprocess.check_output([str(reader),'-h',str(elf)],text=True)
    assert re.search(r'Machine:\s+AArch64',header), 'ELF architecture'
    assert re.search(r'Type:\s+DYN',header), 'Horizon executable must be PIE'
    symbols=subprocess.check_output([str(reader),'-Ws',str(elf)],text=True)
    unresolved=[];weak=[];defined=set()
    for line in symbols.splitlines():
        fields=line.split()
        if len(fields)<8 or not fields[0].endswith(':'):continue
        name=fields[7]
        if fields[6]=='UND':
            (weak if fields[4]=='WEAK' else unresolved).append(name)
        else:defined.add(name)
    assert not unresolved, ('unresolved ELF symbols',unresolved)
    required=['main','sd_ndx_dispatch','sd_ndx_session_create','D3D11CreateDevice',
              'vkGetInstanceProcAddr','nvk_CreateDevice','wsi_CreateViSurfaceNN',
              'nak_compile_shader','nwindowQueueBuffer','nvMapCreate']
    assert all(name in defined for name in required), ('renderer symbols missing',set(required)-defined)
    sections=subprocess.check_output([str(reader),'-SW',str(elf)],text=True)
    assert '.tdata' in sections or '.tbss' in sections, 'native thread-local storage section'
    assert '.init_array' in sections, 'C++ static initialization section'
    return dict(status='PASS',machine='AArch64',type='PIE',unresolved_nonweak=unresolved,
                unresolved_weak=sorted(set(weak)),required_symbols=required,tls_section=True,
                cpp_initializers=True,reader_sha256=sha(reader))

def inspect_nro(nro, nacp):
    data=nro.read_bytes()
    assert data[0x10:0x14]==b'NRO0', 'NRO magic'
    version,size,flags=struct.unpack_from('<III',data,0x14)
    assert version==0 and 0x80<=size<=len(data), 'NRO header bounds'
    segments=[]
    for name,offset in [('text',0x20),('rodata',0x28),('data',0x30)]:
        start,length=struct.unpack_from('<II',data,offset)
        assert start%0x1000==0 and length%0x1000==0 and start+length<=size, (name,'NRO segment')
        segments.append(dict(name=name,offset=start,bytes=length))
    assert data[size:size+4]==b'ASET', 'NRO metadata asset header'
    nacp_offset,nacp_size=struct.unpack_from('<QQ',data,size+0x18)
    assert nacp_size==0x4000 and size+nacp_offset+nacp_size<=len(data), 'NACP bounds'
    embedded=data[size+nacp_offset:size+nacp_offset+nacp_size]
    assert embedded==nacp.read_bytes(), 'embedded application metadata'
    assert embedded.split(b'\0',1)[0]==b'FEXTendo Native DXVK Probe', 'application name'
    return dict(status='PASS',format='NRO0',segments=segments,asset_metadata=True,nacp_bytes=nacp_size)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1'))
    args=parser.parse_args()
    assert os.name=='posix', 'Run under WSL/Linux'
    out=args.work/'horizon-executable';out.mkdir(parents=True,exist_ok=True)
    lock=(out/'build.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    receipt=json.loads((ROOT/'local/native-dxvk-probe-v1/build-horizon.json').read_text())
    library=Path(receipt['library']);assert sha(library)==receipt['sha256']
    assert receipt['elf_machine']=='AArch64' and receipt['static_vulkan_import']
    for name,digest in receipt['adapted_files'].items():assert sha(args.work/'source'/name)==digest,name
    for name,digest in receipt['probe_sources'].items():assert sha(ROOT/name)==digest,name
    assert sha(ROOT/'tools/build_native_dxvk_probe.py')==receipt['builder_sha256'], 'DXVK build recipe changed'
    prior=json.loads((ROOT/'local/apc-v18/native.json').read_text())
    # Retain the proven driver's explicit NAK/identity/channel replacements.
    objects=[Path(x) for x in prior['link_argv'] if x.startswith('/home/blekjek/sleepingdogs-mesa-') and x.endswith('.o')]
    begin=prior['link_argv'].index('-Wl,--start-group');end=prior['link_argv'].index('-Wl,--end-group')
    dependencies=[Path(x) for x in prior['link_argv'][begin+1:end] if x.endswith('.a') and not x.endswith(('libEGL.a','libGL.a','libglapi.a'))]
    inputs={str(p):sha(p) for p in objects+dependencies}
    for p in objects+dependencies:assert inputs[str(p)]==prior['inputs'][str(p)],('v18 Mesa input changed',str(p))
    driver=next(p for p in dependencies if p.name=='libvulkan.a')
    assert sha(driver)==prior['driver_library_sha256']
    flags=['-O2','-std=gnu++17','-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft',
           '-ffixed-x18','-ftls-model=local-exec','-ffunction-sections','-fdata-sections','-fPIE',
           '-D__SWITCH__','-DNX','-isystem',str(SDK/'libnx/include'),'-isystem',str(SDK/'portlibs/switch/include')]
    source=args.work/'source'
    includes=[ROOT/'src/native_dxvk',source/'include/native',source/'include/native/windows',source/'include/native/directx']
    command=[str(TOOLS/'aarch64-none-elf-g++'),*flags,*['-I'+str(p) for p in includes],
             '-MD','-MF',str(out/'main.d'),
             '-c',str(ROOT/'src/native_dxvk/probe_horizon_main.cpp'),'-o',str(out/'main.o')]
    run(command,out/'main.compile.log',out)
    elf=out/'sd-dxvk-native-probe.elf'
    link=[str(TOOLS/'aarch64-none-elf-g++'),*flags,'-specs='+str(SDK/'libnx/switch.specs'),
          '-L'+str(SDK/'libnx/lib'),'-L'+str(SDK/'portlibs/switch/lib'),'-Wl,-Map='+str(out/'probe.map'),
          str(out/'main.o'),*map(str,objects),'-Wl,--start-group',str(library),*map(str,dependencies),'-lnx','-lm','-Wl,--end-group',
          '-o',str(elf)]
    run(link,out/'link.log',out)
    elf_audit=inspect_elf(elf)
    subprocess.run([str(SDK/'tools/bin/nacptool'),'--create','FEXTendo Native DXVK Probe','AndroSwitch Project','0.1.0-h1',str(out/'app.nacp')],check=True)
    nro=out/'sd-dxvk-native-probe.nro'
    subprocess.run([str(SDK/'tools/bin/elf2nro'),str(elf),str(nro),'--nacp='+str(out/'app.nacp')],check=True)
    nro_audit=inspect_nro(nro,out/'app.nacp')
    for name,digest in inputs.items():assert sha(name)==digest,('link input changed',name)
    assert sha(library)==receipt['sha256'], 'DXVK archive changed during link'
    # Record resolved SDK/runtime inputs, including implicit C++/C/TLS libraries.
    resolved=[Path(p.strip()) for p in re.findall(r'^LOAD (.+)$',(out/'probe.map').read_text(),re.M)]
    inputs.update({str(p):sha(p) for p in resolved if p.is_file()})
    dependencies_text=(out/'main.d').read_text().replace('\\\n','')
    headers=[Path(p) for p in shlex.split(dependencies_text.split(':',1)[1])]
    header_inputs={str(p):sha(p) for p in headers}
    destination=ROOT/'local/native-dxvk-probe-v1'
    destination.mkdir(parents=True,exist_ok=True)
    shutil.copy2(nro,destination/nro.name)
    result=dict(status='BUILT',build='native-dxvk-horizon-v1',nro=str(destination/nro.name),nro_sha256=sha(nro),nro_bytes=nro.stat().st_size,
                elf=str(elf),elf_sha256=sha(elf),native_dxvk_sha256=sha(library),driver_library_sha256=sha(driver),
                inputs=inputs,header_inputs=header_inputs,compile_argv=command,link_argv=link,
                elf_audit=elf_audit,nro_audit=nro_audit,
                dxvk_build_receipt_sha256=sha(ROOT/'local/native-dxvk-probe-v1/build-horizon.json'),
                mesa_input_receipt_sha256=sha(ROOT/'local/apc-v18/native.json'),
                source_sha256=sha(ROOT/'src/native_dxvk/probe_horizon_main.cpp'),
                builder_sha256=sha(__file__),game_integration=False,guest_execution=False,hardware_tested=False,fps_gain_measured=False)
    (destination/'horizon-executable.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('inputs','header_inputs','compile_argv','link_argv')},indent=2))

if __name__=='__main__':main()
