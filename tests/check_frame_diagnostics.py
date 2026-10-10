"""Run the production passive collector and patched Wine client with sanitizers."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from port_common import ROOT, sha, write_json
from sleepingdogs_frame_diagnostics import apply, FILES, MODIFIED, COPIES
from sleepingdogs_direct_sync import function

V10_SHA='b352ef810914d90fc2cda9b153b5c2f871e85004678102f8c9b77aabcc73bacf'

def prepare():
    package=ROOT/'dist/sleepingdogs-fex-low-window-direct-sync.zip'
    assert sha(package)==V10_SHA
    stage=ROOT/'local/frame-diagnostics-v11-source'
    prefix='source/low-window-direct-sync/'
    with zipfile.ZipFile(package) as z:
        receipt=json.loads(z.read(prefix+'native.json'))
        for name in MODIFIED:
            target=stage/name; target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(z.read(prefix+'native/'+name))
            assert sha(target)==receipt['source_files'][name],name
        name='dlls/ntdll/unix/sd_sync_client.h'
        (stage/name).write_bytes(z.read(prefix+'native/'+name))
    apply(stage)
    return stage

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native',type=Path)
    a=p.parse_args()
    stage=prepare()
    assert sys.platform!='win32', 'Use Linux sanitizer runtime'
    compiler=shutil.which('clang') or shutil.which('cc')
    assert compiler
    exe=Path('/tmp/sleepingdogs-frame-diagnostics-v11-tests')
    cmd=[compiler,'-std=gnu11','-O1','-g','-pthread','-fsanitize=address,undefined',
         '-fno-sanitize-recover=all','-fno-omit-frame-pointer','-Werror=implicit-function-declaration',
         '-I'+str(stage/'wine-nx-probe/source'), '-I'+str(stage/'dlls/ntdll/unix')]
    subprocess.run(cmd+[str(ROOT/'tests/frame_diagnostics.c'),'-o',str(exe)],check=True)
    result=subprocess.run([str(exe)],check=True,capture_output=True,text=True,timeout=30)
    print(result.stdout,end='',flush=True)
    client=(ROOT/'tests/direct_sync_client.c').read_text()
    hook='''#define STATUS_TIMEOUT 0x102
static unsigned notes;
static void wine_nx_sd_diag_note(unsigned stage, uint64_t begin, uint64_t end,
                               unsigned timeout, unsigned error, unsigned route) {
    assert(stage==1 && begin && end==begin+1 && !timeout && !error);
    assert(route==++notes);
}
'''
    client=client.replace('/* ACTUAL_SERVER_CALL */',hook+function((stage/'dlls/ntdll/unix/server.c').read_text(),'server_call_unlocked'))
    client=client.replace('    puts("PASS actual client dispatch:', '    assert(notes==2);\n    puts("PASS actual client dispatch:')
    generated=ROOT/'local/frame-diagnostics-v11-tests/client.c'
    generated.parent.mkdir(parents=True,exist_ok=True); generated.write_text(client,newline='\n')
    subprocess.run(cmd+[str(generated),'-o',str(exe)],check=True)
    result2=subprocess.run([str(exe)],check=True,capture_output=True,text=True,timeout=15)
    print(result2.stdout,end='',flush=True)
    tested={name:sha(stage/name) for name in sorted(FILES)}
    if a.native:
        for name,digest in tested.items(): assert sha(a.native/name)==digest,name
    inputs=set(COPIES.values())|{'tools/sleepingdogs_frame_diagnostics.py',
        'tests/check_frame_diagnostics.py','tests/frame_diagnostics.c','tests/direct_sync_client.c'}
    write_json(ROOT/'reports/low-window-v11-frame-diagnostics.json',dict(status='PASS',
        source_files=tested,sources={n:sha(ROOT/n) for n in sorted(inputs)},
        sanitizer='AddressSanitizer + UndefinedBehaviorSanitizer',
        compiler=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
        test_output=(result.stdout+result2.stdout).strip().splitlines(),
        native_source_verified=bool(a.native),hardware_tested=False,fps_gain_measured=False))

if __name__=='__main__': main()
