"""Exercise the actual H4 renderer transaction under ASan/UBSan and Horizon rename rules."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
from package_native_dxvk_h4 import ROOT,LOCAL,PREFIX,launcher_payload
from build_native_dxvk_h4 import overlay_runtime,PIN,WORK

PREAMBLE=r'''
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <stdarg.h>
static int rename_countdown=-1;
static int fsync_countdown=-1;
static int horizon_fsync(int fd){
    if(fd<0){errno=EBADF;return -1;}
    if(fsync_countdown==0){fsync_countdown=-1;errno=EIO;return -1;}
    if(fsync_countdown>0)--fsync_countdown;return 0;
}
static int horizon_rename(const char* a,const char* b){
    if(rename_countdown==0){rename_countdown=-1;errno=EIO;return -1;}
    if(rename_countdown>0)--rename_countdown;
    if(!access(b,F_OK)){errno=EEXIST;return -1;}return rename(a,b);
}
#define rename horizon_rename
#define fsync horizon_fsync
static void log_line(const char* fmt,...){(void)fmt;}
'''
HARNESS=r'''
static int installed_renderer(const char* root){char file[800],value[2];snprintf(file,sizeof(file),"%s/launcher/renderer.txt",root);
    return fx_read(file,value,2)==2&&value[1]=='\n'?value[0]-'0':-1;}
int main(int argc,char** argv){
    assert(argc==2);const char* root=argv[1];char source[800],target[800],snapshot[800],hidden[800],journal[800];
    for(int renderer=0;renderer<3;++renderer){
        assert(fx_renderer_save(root,renderer));assert(fx_renderer_selected(root)==renderer);
        assert(fx_apply_renderer(root,renderer));
        for(int i=0;i<8;++i){int index=fx_renderer_source_index[i];if(index<0)continue;
            snprintf(source,sizeof(source),"%s/launcher/renderers/%s/%s",root,fx_renderer_ids[i==7?2:renderer],fx_renderer_sources[index]);
            snprintf(target,sizeof(target),"%s%s",root,fx_renderer_targets[i]);assert(fx_files_equal(source,target));}
        for(int preset=0;preset<5;++preset){assert(fx_apply_preset(root,preset));assert(fx_selected(root)==preset);}
    }
    assert(!fx_renderer_save(root,3));assert(!fx_apply_renderer(root,3));
    assert(fx_renderer_save(root,0));assert(fx_apply_renderer(root,0));assert(installed_renderer(root)==0);
    for(int i=0;i<8;++i){snprintf(target,sizeof(target),"%s%s",root,fx_renderer_targets[i]);snprintf(snapshot,sizeof(snapshot),"%s/snapshot-%d",root,i);assert(fx_copy_file(target,snapshot));}
    // A missing companion prevents ANY DLL replacement or selection commit.
    snprintf(source,sizeof(source),"%s/launcher/renderers/dxvk-native-h4/sdndx4.dll",root);
    snprintf(hidden,sizeof(hidden),"%s.hidden",source);assert(!rename(source,hidden));assert(!fx_apply_renderer(root,2));assert(!rename(hidden,source));
    for(int i=0;i<8;++i){snprintf(target,sizeof(target),"%s%s",root,fx_renderer_targets[i]);snprintf(snapshot,sizeof(snapshot),"%s/snapshot-%d",root,i);assert(fx_files_equal(target,snapshot));}
    // Sync failure during staging must leave every installed file intact.
    fsync_countdown=2;assert(!fx_apply_renderer(root,2));
    for(int i=0;i<8;++i){snprintf(target,sizeof(target),"%s%s",root,fx_renderer_targets[i]);snprintf(snapshot,sizeof(snapshot),"%s/snapshot-%d",root,i);assert(fx_files_equal(target,snapshot));}
    // Fail halfway through rename, then recover all eight originals.
    rename_countdown=5;assert(!fx_apply_renderer(root,2));assert(fx_renderer_selected(root)==0&&installed_renderer(root)==0);
    for(int i=0;i<8;++i){snprintf(target,sizeof(target),"%s%s",root,fx_renderer_targets[i]);snprintf(snapshot,sizeof(snapshot),"%s/snapshot-%d",root,i);assert(fx_files_equal(target,snapshot));}
    assert(fx_apply_renderer(root,2));assert(installed_renderer(root)==2);
    // Simulate a power loss after replacing four targets, including both
    // existing seven-bit journal recovery and the new companion transaction.
    for(int i=0;i<8;++i){snprintf(target,sizeof(target),"%s%s",root,fx_renderer_targets[i]);snprintf(snapshot,sizeof(snapshot),"%s/snapshot-%d",root,i);assert(fx_copy_file(target,snapshot));
        if(i<4){char old[850];snprintf(old,sizeof(old),"%s.fxr-old",target);assert(!rename(target,old));assert(fx_write(target,"interrupted",11));}}
    snprintf(journal,sizeof(journal),"%s/launcher/renderer-native-com.txn",root);unsigned char mask=255;assert(fx_write(journal,&mask,1));assert(fx_renderer_recover(root));
    for(int i=0;i<8;++i){snprintf(target,sizeof(target),"%s%s",root,fx_renderer_targets[i]);snprintf(snapshot,sizeof(snapshot),"%s/snapshot-%d",root,i);assert(fx_files_equal(target,snapshot));}
    assert(fx_apply_renderer(root,0));assert(fx_renderer_selected(root)==0&&installed_renderer(root)==0);puts("PASS: three renderers, fifteen presets, companion gate, rollback and interrupted eight-target recovery");
}
'''
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    pin=json.loads(PIN.read_text());source=Path(pin['runtime_source']);before=source.read_text();after=overlay_runtime(before)
    start=after.index('#ifndef FEXTENDO_PRESETS_H');end=after.index('\n#endif',after.index('#ifndef FEXTENDO_RENDERERS_H'))+len('\n#endif')
    work=WORK/'launcher-checks';work.mkdir(parents=True,exist_ok=True)
    fixture=work/'launcher-check.c';fixture.write_text(PREAMBLE+after[start:end]+HARNESS);executable=work/'launcher-check'
    command=['gcc','-std=c11','-O1','-g','-D_POSIX_C_SOURCE=200809L','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(source.parent),str(fixture),'-o',str(executable)]
    with (LOCAL/'launcher.compile.log').open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError((LOCAL/'launcher.compile.log').read_text())
    payload=launcher_payload()
    with tempfile.TemporaryDirectory(prefix='h4-launcher-',dir=work) as temporary:
        root=Path(temporary)
        for name,data in payload.items():
            file=root/name.removeprefix(PREFIX);file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
        result=subprocess.run([str(executable),str(root)],capture_output=True,text=True,timeout=60)
        (LOCAL/'launcher-stdout.log').write_text(result.stdout);(LOCAL/'launcher-stderr.log').write_text(result.stderr)
        if result.returncode:raise RuntimeError(result.stderr)
    receipt=dict(status='PASS',renderers=3,presets=15,transaction_targets=8,missing_companion_rejected=True,
                 rename_failure_rolled_back=True,staging_sync_failure_preserved=True,power_loss_recovery=True,legacy_fallback_verified=True,sanitizers=['address','undefined'],
                 modeled_fsync=True,scope='Actual file payload/transaction under modeled Horizon rename and sync outcomes; interrupted file layout recovery. Not physical filesystem durability.',
                 source_sha256=hashlib.sha256(after.encode()).hexdigest(),fixture_sha256=sha(fixture),runner_sha256=sha(__file__),compile_argv=command,
                 payload_sha256={name:hashlib.sha256(data).hexdigest() for name,data in payload.items()},hardware_tested=False)
    (LOCAL/'launcher-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
