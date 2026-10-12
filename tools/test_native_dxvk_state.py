"""Test real PE wrappers; model transport, not the cache implementation."""
from pathlib import Path
import json,os,subprocess,hashlib
from native_dxvk_state import ROOT,METHODS
LOCAL=ROOT/'local/native-dxvk-state-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build():
    source=LOCAL/'source/native_dxvk_com';work=LOCAL/'tests';work.mkdir(exist_ok=True)
    inventory=json.loads((source/'com_inventory.json').read_text())['interfaces']['ID3D11DeviceContext']['methods']
    out=['static void generated_cases(void) {','    void *buffer=object(400,SD_COM_IF_ID3D11Buffer),*sampler=object(401,SD_COM_IF_ID3D11SamplerState);','    void *array[2]={NULL,NULL};']
    for name in METHODS:
        m=next(m for m in inventory if m['name']==name)
        if 'ConstantBuffers' in name or 'Samplers' in name:
            out.append('    array[0]='+('buffer' if 'ConstantBuffers' in name else 'sampler')+';')
            args='0,2,('+m['params'][2]['type']+')array'
        elif name.endswith('SetShader'):args='NULL,NULL,0'
        elif name=='OMSetDepthStencilState':args='NULL,1'
        elif name=='OMSetBlendState':args='NULL,NULL,~0u'
        elif name=='IASetPrimitiveTopology':args='D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST'
        elif name in ('RSSetViewports','RSSetScissorRects'):args='0,NULL'
        else:args='NULL'
        out+=['    clear();','    require(sd_state_slot('+str(m['index'])+')>=0,"method mapping '+name+'");',
              '    ID3D11DeviceContext_'+name+'(ctx,'+args+');','    require(calls==1,"initial '+name+'");',
              '    ID3D11DeviceContext_'+name+'(ctx,'+args+');','    require(calls==1,"repeat '+name+'");']
    out+=['}'];(work/'state_generated.inc').write_text('\n'.join(out)+'\n')
    mingw='/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/i686-w64-mingw32-gcc'
    args=[mingw,'-O2','-std=c11','-DINITGUID','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib',
          '-Wl,--no-insert-timestamp','-Wl,--entry,start@0','-I'+str(source),'-I'+str(work),
          str(ROOT/'tests/native_dxvk_guest_state.c'),'-o',str(work/'state.exe'),'-lkernel32','-luser32']
    r=subprocess.run(args,capture_output=True,text=True);(work/'compile.log').write_text(r.stdout+r.stderr);assert not r.returncode,r.stderr
    (work/'command.json').write_text(json.dumps(args,indent=2)+'\n')
def execute():
    work=LOCAL/'tests';r=subprocess.run([str(work/'state.exe')],capture_output=True,text=True,timeout=90)
    (work/'run.log').write_text(r.stdout+r.stderr);assert not r.returncode,(r.returncode,r.stdout,r.stderr)
    report=json.loads(r.stdout);report.update(hardware_tested=False,game_fps_measured=False,
        proxy_sha256=sha(LOCAL/'sdndx4.dll'),test_exe_sha256=sha(work/'state.exe'),
        source_files=json.loads((LOCAL/'build.json').read_text())['source_files'])
    (LOCAL/'guest-test.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2)[:500])
if __name__=='__main__':
    if os.name=='posix':build()
    else:execute()
