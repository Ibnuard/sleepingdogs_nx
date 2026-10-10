"""Run the real launcher control flow with deterministic UI/resource fixtures."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json

FIXTURE = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#define RUNTIME_DIR "sdmc:/switch/sleepingdogs-fex"
#define CUR_PROCESS_HANDLE 42
#define InfoType_AslrRegionAddress 12
#define InfoType_AslrRegionSize 13
#define FX_FAILED 5
#define R_FAILED(x) ((x)!=0)
typedef unsigned Result;
typedef unsigned long long u64;
typedef int pthread_attr_t;
static int fx_ui_thread,fx_ui_created,fx_ui_command,fx_ui_lock,fx_boot_started;
static char fx_ui_message[192];
static const char *fx_renderer_ids[]={"dxvk-2.7.1-async","dxvk-3.1.1"};
static const char *fx_renderer_error_text="renderer failed",*fx_renderer_error_detail="fixture";
static struct {int renderer,selected,debug,screen,fatal;const char *message;} fx_ui_view;
enum {GOOD,PROBE_FAIL,ARENA_FAIL,RENDER_FAIL,THREAD_RETRY,CANCEL};
static int mode,probed,arena,stacks,probe_calls,arena_calls,thread_calls,arm_calls,crash_calls,failures;
static int sequence[32],nseq;
static void event(int n){assert(nseq<32);sequence[nseq++]=n;}
static void reset(int m,int debug){
    mode=m;probed=arena=stacks=probe_calls=arena_calls=thread_calls=arm_calls=crash_calls=failures=nseq=0;
    fx_ui_command=fx_ui_created=fx_boot_started=0;fx_ui_message[0]=0;
    memset(&fx_ui_view,0,sizeof(fx_ui_view));fx_ui_view.renderer=1;fx_ui_view.debug=debug;
}
static void wine_nx_runtime_trace(const char *s){(void)s;}
static void wine_nx_f1_native_stacks_init(void){if(!stacks){stacks=1;event(1);}}
static void sd_low_window_init(void){if(!probed){probed=1;probe_calls++;event(2);}}
static int sd_low_window_ready(void){return probed && mode!=PROBE_FAIL;}
static int sd_is_low_window(u64 b,u64 s){return b==0x200000 && s==0x7fffe00000ULL;}
static void sd_guest_arena_init(void){
    assert(sd_low_window_ready());if(!arena_calls){arena_calls++;event(3);arena=mode!=ARENA_FAIL;}
}
static void *sd_guest_arena_base(void){return arena?(void *)(uintptr_t)0x30000000:NULL;}
static size_t sd_guest_arena_size(void){return arena?1048576000:0;}
static int pthread_attr_init(pthread_attr_t *p){*p=0;return 0;}
static int pthread_attr_setstacksize(pthread_attr_t *p,size_t s){(void)p;assert(s==256*1024);return 0;}
static void pthread_attr_destroy(pthread_attr_t *p){(void)p;}
static void *fx_ui_main(void *p){return p;}
static int pthread_create(int *t,pthread_attr_t *a,void *(*fn)(void *),void *arg){
    (void)a;(void)arg;assert(fn==fx_ui_main);*t=1;fx_ui_command=mode==CANCEL?-1:1;return 0;
}
static int pthread_join(int t,void *p){assert(t==1);(void)p;return 0;}
static void fx_native_error(const char *s){fprintf(stderr,"unexpected native error: %s\n",s);assert(0);}
static int fx_apply_renderer(const char *p,int r){(void)p;assert(r==1);return mode!=RENDER_FAIL;}
static int fx_apply_preset(const char *p,int s){(void)p;(void)s;return 1;}
static Result svcGetInfo(u64 *out,int type,int handle,int sub){
    assert(handle==42&&!sub);*out=type==12?0x200000:0x7fffe00000ULL;return 0;
}
static void svcSleepThread(unsigned long long ns){(void)ns;assert(0&&"UI fixture should supply a command");}
static void log_line(const char *format,...){(void)format;}
int wine_nx_f1_prepare_threads(char *error,size_t size){
    assert(arena&&sd_low_window_ready());thread_calls++;event(4);
    if(mode==THREAD_RETRY&&thread_calls==1){snprintf(error,size,"temporary thread failure");return 0;}
    return 1;
}
static unsigned wine_nx_f1_relaunch_arm(void){assert(arena&&thread_calls);arm_calls++;event(5);return 0;}
static void wine_nx_f1_relaunch_disarm(void){}
static unsigned wine_nx_f1_crash_init(int debug,int renderer,int selected){
    assert(debug==fx_ui_view.debug&&renderer==1&&!selected&&arm_calls);crash_calls++;event(6);return 0;
}
static void pthread_mutex_lock(int *p){assert(p==&fx_ui_lock);}
static void pthread_mutex_unlock(int *p){
    assert(p==&fx_ui_lock&&fx_ui_command==0&&fx_ui_view.screen==FX_FAILED);
    assert(fx_ui_view.message==fx_ui_message&&fx_ui_message[0]);failures++;
    fx_ui_command=(mode==THREAD_RETRY&&failures==1)?1:-1;
}
static void fx_exit_check(void){}
static int test_atexit(void (*p)(void)){assert(p==fx_exit_check);return 0;}
#define atexit test_atexit
'''

TESTS = r'''
int main(void){
    reset(GOOD,1);
#ifdef OLD_LAUNCHER
    assert(!fx_launcher_start());
    assert(failures==1&&!probed&&!arena_calls&&!thread_calls&&!crash_calls);
    assert(strstr(fx_ui_message,"Boot CFW"));
    puts("PASS old launcher reproduces rejection before memory initialization");
#else
    for(int debug=0;debug<2;debug++){
        reset(GOOD,debug);assert(fx_launcher_start());
        assert(probe_calls==1&&arena_calls==1&&thread_calls==1&&arm_calls==1&&crash_calls==1&&!failures);
        assert(nseq==6);for(int i=0;i<6;i++)assert(sequence[i]==i+1);
        puts(debug?"PASS Launch Debug initializes memory before validation":"PASS Launch GUI initializes memory before validation");
    }
    reset(PROBE_FAIL,1);assert(!fx_launcher_start());
    assert(probe_calls==1&&!arena_calls&&!thread_calls&&!arm_calls&&!crash_calls&&failures==1);
    assert(strstr(fx_ui_message,"Low-window memory check failed"));
    puts("PASS failed probe blocks guest without blaming boot selection");
    reset(ARENA_FAIL,1);assert(!fx_launcher_start());
    assert(probe_calls==1&&arena_calls==1&&!thread_calls&&!arm_calls&&!crash_calls&&failures==1);
    assert(strstr(fx_ui_message,"data arena"));
    puts("PASS failed arena blocks guest");
    reset(RENDER_FAIL,1);assert(!fx_launcher_start());
    assert(!probed&&!arena_calls&&!thread_calls&&failures==1);
    puts("PASS renderer failure does not initialize memory");
    reset(THREAD_RETRY,1);assert(fx_launcher_start());
    assert(probe_calls==1&&arena_calls==1&&thread_calls==2&&arm_calls==1&&crash_calls==1&&failures==1);
    puts("PASS retry retains one probe and one arena allocation");
    reset(CANCEL,1);assert(!fx_launcher_start());assert(!probed&&!arena_calls&&!thread_calls&&!failures);
    puts("PASS exit without Play does not allocate guest arena");
#endif
}
'''


def function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError('Unterminated function')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    p.add_argument('--report', type=Path, default=ROOT / 'reports/low-window-launch-order.json')
    a = p.parse_args()
    source = a.work / 'native-source/wine-nx-probe/source'
    out = a.work / 'launch-order-check'
    out.mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT / 'dist/sleepingdogs-fex-low-window-fix.zip') as z:
        old = z.read('source/low-window-fix/native/wine-nx-probe/source/runtime.c').decode()
    new = (source / 'runtime.c').read_text()
    helper = re.sub(r'^#include.*\n', '', (source / 'sd_launch_memory.c').read_text(), flags=re.M)
    results = []
    for label, text in (('old', old), ('new', new)):
        c = out / f'{label}.c'
        c.write_text(FIXTURE + helper + function(text, 'static int fx_launcher_start(void)') + TESTS)
        exe = out / label
        flags = ['-DOLD_LAUNCHER'] if label == 'old' else []
        subprocess.run(['gcc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-function', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                        *flags, str(c), '-o', str(exe)], check=True)
        run = subprocess.run([exe], text=True, capture_output=True)
        print(run.stdout + run.stderr, end='', flush=True)
        run.check_returncode()
        results += [s[5:] for s in run.stdout.splitlines() if s.startswith('PASS ')]
    # The guest-test entry path must use the same admission helper before Wine.
    main_source = function(new, 'int main( int argc, char **argv )')
    branch = main_source.split('if (guest_tests) {', 1)[1].split('else if (!fx_launcher_start())', 1)[0]
    assert 'sd_launch_memory_prepare(memory_error,sizeof(memory_error))' in branch
    assert 'return 1;' in branch
    assert '    sd_guest_arena_init();' not in main_source
    assert len(results) == 8
    write_json(a.report, {
        'status': 'PASS', 'hardware_tested': False, 'scope': __doc__,
        'cases': results, 'guest_test_path_uses_shared_admission': True,
        'source_files': {p.name: sha(p) for p in (source / 'runtime.c', source / 'sd_launch_memory.c')},
        'old_runtime_sha256': hashlib.sha256(old.encode()).hexdigest(),
        'test_sha256': sha(Path(__file__))})


if __name__ == '__main__':
    main()
