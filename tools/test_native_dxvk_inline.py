"""Compile and execute real production PE32 input wrappers with a mock endpoint."""
from pathlib import Path
import json,os,subprocess,hashlib
from native_dxvk_inline import ROOT,methods,pointers
LOCAL=ROOT/'local/native-dxvk-inline-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build():
    source=LOCAL/'source/native_dxvk_com';work=LOCAL/'tests';work.mkdir(exist_ok=True)
    out=['static void generated_cases(void) {']
    for m in methods():
        ptr=pointers(m);params=m['params'];nargs=len(params)
        for null in (False,True):
            out+=['    {',f'        begin_case({m["index"]},{nargs},{0 if null else 1});']
            args=[]
            for i,p in enumerate(params):
                name=p['name']
                if i in ptr:
                    count,words=ptr[i];count=int(count) if count.isdigit() else 2
                    if null:
                        out.append(f'        pointer_case({i},NULL,0);');args.append('NULL')
                    elif p['pointer']==2:
                        out += [f'        {p["base"]} *a{i}[{count}];',f'        for(unsigned j=0;j<{count};++j)a{i}[j]=({p["base"]}*)object({1000+m["index"]*10+i}+j,SD_COM_IF_{p["base"]});',f'        token_case({i},(void*const*)a{i},{count});']
                        args.append('a'+str(i))
                    else:
                        out += [f'        uint32_t a{i}[{count*words}];for(unsigned j=0;j<{count*words};++j)a{i}[j]=0x3f800000+j;',f'        pointer_case({i},a{i},sizeof(a{i}));']
                        args.append(f'({p["base"]}*)a{i}')
                elif p['pointer']:
                    out += [f'        {p["base"]} *a{i}=({p["base"]}*)object({2000+m["index"]*10+i},SD_COM_IF_{p["base"]});',f'        expected.scalar[{i}]=proxy_token(a{i});'];args.append('a'+str(i))
                else:
                    out.append(f'        expected.scalar[{i}]=2;');args.append('2')
            out += [f'        ID3D11DeviceContext_{m["name"]}(ctx,'+','.join(args)+');','    }']
    out+=['}'];(work/'inline_generated.inc').write_text('\n'.join(out)+'\n')
    mingw='/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/i686-w64-mingw32-gcc'
    args=[mingw,'-O2','-std=c11','-DINITGUID','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib',
          '-Wl,--no-insert-timestamp','-Wl,--entry,start@0','-I'+str(source),'-I'+str(work),
          str(ROOT/'tests/native_dxvk_guest_inline.c'),'-o',str(work/'inline.exe'),'-lkernel32','-luser32']
    r=subprocess.run(args,capture_output=True,text=True);(work/'compile.log').write_text(r.stdout+r.stderr);assert not r.returncode,r.stderr
    (work/'command.json').write_text(json.dumps(args,indent=2)+'\n')

def execute():
    work=LOCAL/'tests';r=subprocess.run([str(work/'inline.exe')],capture_output=True,text=True,timeout=90)
    (work/'run.log').write_text(r.stdout+r.stderr);assert not r.returncode,(r.returncode,r.stdout,r.stderr)
    report=json.loads(r.stdout);report.update(hardware_tested=False,game_fps_measured=False,
        proxy_sha256=sha(LOCAL/'sdndx4.dll'),test_exe_sha256=sha(work/'inline.exe'),
        source_files=json.loads((LOCAL/'build.json').read_text())['source_files'])
    (LOCAL/'guest-test.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2)[:500])
if __name__=='__main__':
    if os.name=='posix':build()
    else:execute()
