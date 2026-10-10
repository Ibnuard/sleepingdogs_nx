"""Fault-inject the actual renderer transaction and exercise startup dialog capture."""
from pathlib import Path
import argparse
import shutil
import struct
import subprocess
from check_startup import function

ROOT = Path(__file__).resolve().parents[1]
PREAMBLE = r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>
static int fail_rename,crash_rename,rename_count,fail_sync,sync_count;
static int test_rename(const char *a,const char *b){
    int n=++rename_count;
    if(n==fail_rename){errno=EIO;return -1;}
    int result=rename(a,b);
    if(n==crash_rename){assert(!result);_exit(17);}
    return result;
}
static int test_sync(int fd){
    if(++sync_count==fail_sync){errno=ENOSPC;return -1;}
    return fsync(fd);
}
#define rename test_rename
#define fsync test_sync
'''
RENDERERS = r'''
#undef rename
#undef fsync
static void reset(void){fail_rename=crash_rename=rename_count=fail_sync=sync_count=0;}
static void check(const char *root,int selected,int count){
    char src[768],dst[768],b[2];
    for(int i=0;i<count;i++){
        snprintf(dst,sizeof(dst),"%s%s",root,fx_renderer_targets[i]);
        int ix=fx_renderer_source_index[i];
        if(ix>=0){
            snprintf(src,sizeof(src),"%s/launcher/renderers/%s/%s",root,fx_renderer_ids[selected],fx_renderer_sources[ix]);
            assert(fx_files_equal(src,dst));
        }else assert(fx_read(dst,b,2)==2&&b[0]=='0'+selected&&b[1]=='\n');
    }
}
int main(int argc,char **argv){
    assert(argc==2);const char *root=argv[1];char p[768],bad[800];
    assert(!fx_apply_renderer(root,-1));assert(!fx_apply_renderer(root,2));
    assert(fx_apply_renderer(root,0));check(root,0,7);
    reset();assert(fx_apply_renderer(root,0));assert(!rename_count&&!sync_count);
    assert(fx_renderer_save(root,1));assert(fx_renderer_selected(root)==1);check(root,0,7);
    for(int n=1;n<=15;n++){
        reset();fail_rename=n;assert(!fx_apply_renderer(root,1));reset();assert(fx_renderer_recover(root));check(root,0,7);
    }
    for(int n=1;n<=8;n++){
        reset();fail_sync=n;assert(!fx_apply_renderer(root,1));reset();assert(fx_renderer_recover(root));check(root,0,7);
    }
    for(int n=1;n<=15;n++){
        pid_t child=fork();assert(child>=0);
        if(!child){reset();crash_rename=n;fx_apply_renderer(root,1);_exit(99);}
        int status;assert(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==17);
        reset();assert(fx_renderer_recover(root));check(root,0,7);
    }
    /* Upgrade from 0.1.5: absent D3D11/DXGI must roll back to absent, then install. */
    for(int n=1;n<=13;n++){
        for(int i=5;i<7;i++){snprintf(p,sizeof(p),"%s%s",root,fx_renderer_targets[i]);unlink(p);}
        pid_t child=fork();assert(child>=0);
        if(!child){reset();crash_rename=n;fx_apply_renderer(root,1);_exit(99);}
        int status;assert(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==17);
        reset();assert(fx_renderer_recover(root));check(root,0,5);
        for(int i=5;i<7;i++){snprintf(p,sizeof(p),"%s%s",root,fx_renderer_targets[i]);assert(access(p,F_OK));}
    }
    assert(fx_apply_renderer(root,1));check(root,1,7);
    /* Legacy journal does not touch the installed DX11 pair. */
    snprintf(p,sizeof(p),"%s/launcher/renderer.txn",root);unsigned char mask=31;
    assert(fx_write(p,&mask,1));assert(fx_renderer_recover(root));check(root,1,7);
    assert(fx_apply_renderer(root,0));check(root,0,7);
    for(int i=0;i<4;i++)if(i!=1){
        snprintf(p,sizeof(p),"%s/launcher/renderers/dxvk-2.7.1-async/%s",root,fx_renderer_sources[i]);
        snprintf(bad,sizeof(bad),"%s.test-backup",p);assert(!rename(p,bad));
        assert(fx_write(p,"MZ",2));assert(!fx_apply_renderer(root,1));check(root,0,7);
        assert(!unlink(p));assert(!fx_apply_renderer(root,1));check(root,0,7);assert(!rename(bad,p));
    }
    snprintf(p,sizeof(p),"%s/launcher/renderer-dx11.txn",root);assert(fx_write(p,"bad",3));
    assert(!fx_apply_renderer(root,1));assert(!unlink(p));
    puts("PASS: DX11/DXGI set; 15 rename/8 flush failures, 28 interruptions including upgrade, legacy journal, fast path, corrupt/missing DLL preflight.");
}
'''
DIALOG = r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
typedef uint16_t WCHAR;
typedef unsigned HWND;
typedef struct {unsigned short Length,MaximumLength;WCHAR *Buffer;} UNICODE_STRING;
#define FALSE 0
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define GW_CHILD 1
#define GW_HWNDNEXT 2
static HWND get_window_relative(HWND h,int relation){return relation==GW_CHILD?1:h<3?h+1:0;}
static void copy_text(WCHAR *out,unsigned cap,const char *s){unsigned n=0;while(*s&&n+1<cap)out[n++]=(unsigned char)*s++;out[n]=0;}
static void NtUserGetClassName(HWND h,int unused,UNICODE_STRING *s){(void)unused;copy_text(s->Buffer,s->MaximumLength/2,h==2?"Button":"Static");}
static void NtUserInternalGetWindowText(HWND h,WCHAR *out,unsigned cap){copy_text(out,cap,h==2?"OK":h==1?"DirectX 11":"device failed");}
static int wcsicmp(const WCHAR *a,const WCHAR *b){while(*a&&*a==*b){a++;b++;}return *a-*b;}
static int fx_boot_started=1,fx_first_present,fx_ui_owned=1;
static pthread_mutex_t fx_ui_lock=PTHREAD_MUTEX_INITIALIZER;
enum {FX_LOADING,FX_FAILED};
static struct {int debug,fatal,screen;const char *message;} fx_ui_view={.debug=1};
static char fx_ui_message[192],lastlog[2000];
static int fx_owned(void){return fx_ui_owned;}
static void fx_native_error(const char *s){(void)s;assert(0);}
static void log_line(const char *fmt,const char *s){snprintf(lastlog,sizeof(lastlog),fmt,s);}
'''
DIALOG_TEST = r'''
int main(void){
    char b[12];WCHAR input[]={'A',0x20ac,0xd83d,0xde00,'\n',0};
    f1_dialog_utf8(b,sizeof(b),input);assert(!strcmp(b,"A\xe2\x82\xac\xf0\x9f\x98\x80 "));
    f1_dialog_utf8(b,8,input);assert(!strcmp(b,"A\xe2\x82\xac"));
    f1_dialog_utf8(b,1,input);assert(!b[0]);
    WCHAR broken[]={0xd800,'x',0xdc00,0};
    f1_dialog_utf8(b,sizeof(b),broken);assert(!strcmp(b,"\xef\xbf\xbdx\xef\xbf\xbd"));
    wine_nx_runtime_startup_dialog("Notice","Loading");assert(!fx_ui_view.fatal);
    wine_nx_runtime_startup_dialog("Cannot initialise graphics","DirectX error");
    assert(fx_ui_view.fatal&&fx_ui_view.screen==FX_LOADING&&strstr(fx_ui_message,"Cannot initialise graphics"));
    fx_stage("Later startup stage");assert(strstr(fx_ui_message,"Cannot initialise graphics"));
    fx_ui_view.fatal=0;fx_ui_message[0]=0;fx_first_present=1;
    wine_nx_runtime_startup_dialog("Cannot initialise graphics","late");assert(!fx_ui_view.fatal);
    fx_first_present=0;fx_boot_started=0;
    wine_nx_runtime_startup_dialog("Cannot initialise graphics","early");assert(!fx_ui_view.fatal);
    fx_boot_started=1;WCHAR title[]={'N','o','t','i','c','e',0};
    f1_report_startup_dialog(1,title);assert(strstr(lastlog,"DirectX 11 device failed")&&!strstr(lastlog,"OK"));
    fx_ui_view.debug=0;
    wine_nx_runtime_startup_dialog("Cannot initialise graphics","DirectX error");
    assert(fx_ui_view.fatal&&fx_ui_view.screen==FX_FAILED);
    puts("PASS: actual dialog capture, UTF-8 bounds/surrogates, labels without buttons, sticky GUI/debug failure, later stages preserve error, gameplay unaffected.");
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    native = args.source / 'wine-nx-probe/source'
    source = (native / 'runtime.c').read_text()
    start = source.index('#ifndef FEXTENDO_PRESETS_H')
    end = source.index('\n#endif', source.index('#ifndef FEXTENDO_RENDERERS_H')) + len('\n#endif')
    renderer = out / 'renderers.c'
    renderer.write_text(PREAMBLE + source[start:end] + RENDERERS)
    fixture = out / 'prefix'; fixture.mkdir(exist_ok=True)
    from build_launcher import profile_config
    for index, name in enumerate(('dxvk-3.1.1', 'dxvk-2.7.1-async')):
        folder = fixture / 'launcher/renderers' / name; folder.mkdir(parents=True, exist_ok=True)
        for dll_index, dll in enumerate(('d3d9.dll', 'd3d11.dll', 'dxgi.dll')):
            data = bytearray(1024 * 1024); data[:2] = b'MZ'
            struct.pack_into('<I', data, 60, 64); data[64:70] = b'PE\0\0\x4c\x01'
            data[88:90] = b'\x0b\x01'; data[100] = index * 10 + dll_index
            (folder / dll).write_bytes(data)
        (folder / 'dxvk.conf').write_text(profile_config('balanced', index == 1))
    window = (args.source / 'dlls/win32u/window.c').read_text()
    dialog = out / 'dialog.c'
    dialog.write_text(DIALOG + function(window, 'static void f1_dialog_utf8(') +
                      function(source, 'static void fx_fail(') + function(source, 'static void fx_stage(') +
                      function(source, 'void wine_nx_runtime_startup_dialog(') +
                      function(window, 'static void f1_report_startup_dialog(') + DIALOG_TEST)
    cc = shutil.which('clang') or shutil.which('cc')
    for file, arguments in ((renderer, [str(fixture)]), (dialog, [])):
        exe = file.with_suffix('')
        subprocess.run([cc, '-std=c11', '-O1', '-g', '-D_POSIX_C_SOURCE=200809L',
                        '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                        '-I', str(native), str(file), '-pthread', '-o', str(exe)], check=True)
        subprocess.run([str(exe), *arguments], check=True)


if __name__ == '__main__':
    main()
