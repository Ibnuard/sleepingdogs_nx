"""Exercise the actual Wine guest channel lookup and native log bridge on the host.

This checks diagnostics/exit handling, not FEX execution or game compatibility.
Run under WSL after preparing the copied source tree.
"""
from pathlib import Path
import argparse
import re
import shutil
import subprocess


def function(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


PREAMBLE = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include "std_stream_lines.h"
#define __SWITCH__ 1
#define __cdecl
#define WINAPI
#define ULongToPtr(v) ((void *)(uintptr_t)(uint32_t)(v))
typedef int32_t NTSTATUS;
typedef uint32_t ULONG;
/* WINE_DEBUG_TYPES */
struct wine_dbg_write_params { const char *str; unsigned int len; };
static struct __wine_debug_channel channel_options[5];
static struct __wine_debug_channel *debug_options;
static int nb_debug_options;
static void init_options(void) {
    debug_options=channel_options;
    nb_debug_options=0;
    while(debug_options[nb_debug_options].name[0])nb_debug_options++;
}
static int fx_debug_live;
static pthread_mutex_t fx_debug_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t fx_debug_file_lock=PTHREAD_MUTEX_INITIALIZER;
static char fx_debug_lines[21][120];
static unsigned fx_debug_total;
static FILE *fx_debug_file;
static int fx_first_present;
static uint64_t f1_guest_exit_state;
#define F1_RETURN_GUEST 1
/* This suite exercises the unarmed startup-error fallback. The dedicated
 * restart suite runs the same exit callback against the real armed module. */
static int wine_nx_f1_relaunch_request(unsigned kind,unsigned code){(void)kind;(void)code;return 0;}
static void wine_nx_f1_crash_note(const char *text) {(void)text;}
static void wine_nx_f1_crash_stage(const char *s,int r,unsigned long long a,unsigned long long b)
{(void)s;(void)r;(void)a;(void)b;}
#define RUNTIME_DIR "/unused"
static char failure[160];
static void fx_fail(const char *message) { snprintf(failure,sizeof(failure),"%s",message); }
'''

HARNESS = r'''
static unsigned char flags_for(const char *name) {
    struct __wine_debug_channel c={.flags=1<<__WINE_DBCL_INIT};
    snprintf(c.name,sizeof(c.name),"%s",name);
    return __wine_dbg_get_channel_flags(&c);
}
static void reset_channels(int debug) {
    fx_wine_debug_channels(channel_options,debug);
    debug_options=NULL;nb_debug_options=0;
}
static void *producer(void *id) {
    char line[64];
    for(int i=0;i<30;i++){
        snprintf(line,sizeof(line),"parallel-%ld-%d\n",(long)id,i);
        struct wine_dbg_write_params p={line,strlen(line)};
        assert(unixcall_wine_dbg_write(&p)==(int)p.len);
    }
    return NULL;
}
static void *blocked_file_writer(void *unused) {
    (void)unused;log_line("UI-ALIVE-WHILE-SD-WAITS");return NULL;
}
int main(void) {
    reset_channels(0);
    assert(flags_for("module")==1<<__WINE_DBCL_ERR);
    assert(flags_for("loaddll")==1<<__WINE_DBCL_ERR);
    assert(flags_for("heap")==1<<__WINE_DBCL_ERR);
    assert(flags_for("crypt")==1<<__WINE_DBCL_ERR);
    reset_channels(1);
    assert(flags_for("module")&(1<<__WINE_DBCL_TRACE));
    assert(flags_for("loaddll")&(1<<__WINE_DBCL_TRACE));
    assert(flags_for("crypt")&(1<<__WINE_DBCL_TRACE));
    assert(!(flags_for("heap")&(1<<__WINE_DBCL_TRACE)));
    assert(!(flags_for("relay")&(1<<__WINE_DBCL_TRACE)));
    assert(flags_for("seh")&(1<<__WINE_DBCL_WARN));
    fx_debug_file=tmpfile();assert(fx_debug_file);
    static char fail_line[]="0004:err:module:LdrInitializeThunk test-failing.dll failed to initialize, aborting\n";
    assert((uintptr_t)fail_line<=UINT32_MAX);
    struct { ULONG str; unsigned int len; } p32={(ULONG)(uintptr_t)fail_line,sizeof(fail_line)-1};
    assert(wow64_wine_dbg_write(&p32)==sizeof(fail_line)-1);
    assert(fx_debug_total==0);
    fx_debug_live=1;
    assert(wow64_wine_dbg_write(&p32)==sizeof(fail_line)-1);
    assert(fx_debug_total==1);
    static char long_line[930];memset(long_line,'x',sizeof(long_line));
    memcpy(long_line+900,"TAIL-SURVIVED\n",14);
    p32.str=(ULONG)(uintptr_t)long_line;p32.len=914;
    assert(wow64_wine_dbg_write(&p32)==914);
    wine_nx_runtime_wine_write("fragment-",9);
    wine_nx_runtime_wine_write("joined\n",7);
    wine_nx_runtime_wine_write("flushed-at-exit",15);
    wine_nx_runtime_std_write(2,"stderr-final",12);
    wine_nx_runtime_dump_std_streams();
    wine_nx_runtime_wine_write("idle-flush",10);
    for(int i=0;i<STD_STREAM_IDLE_TICKS;i++)runtime_tick_std_streams();
    pthread_t threads[3];
    for(long i=0;i<3;i++)assert(!pthread_create(threads+i,NULL,producer,(void *)i));
    for(int i=0;i<3;i++)assert(!pthread_join(threads[i],NULL));
    /* Simulate slow SD output. UI ring updates must not wait for file I/O. */
    unsigned before=fx_debug_total;
    pthread_mutex_lock(&fx_debug_file_lock);
    pthread_t writer;assert(!pthread_create(&writer,NULL,blocked_file_writer,NULL));
    int visible=0;
    for(int i=0;i<1000&&!visible;i++){
        if(!pthread_mutex_trylock(&fx_debug_lock)){
            visible=fx_debug_total>before;
            pthread_mutex_unlock(&fx_debug_lock);
        }
        struct timespec delay={0,1000000};nanosleep(&delay,NULL);
    }
    assert(visible);
    pthread_mutex_unlock(&fx_debug_file_lock);
    assert(!pthread_join(writer,NULL));
    wine_nx_runtime_process_exit(0xc0000142u);
    assert(strstr(failure,"DLL initialization failed (0xc0000142)"));
    assert(f1_guest_exit_state==((1ULL<<32)|0xc0000142u));
    wine_nx_runtime_process_exit(0xc0000135u);
    assert(strstr(failure,"DLL was not found (0xc0000135)"));
    assert(f1_guest_exit_state==((1ULL<<32)|0xc0000142u)); /* first exit remains visible */
    wine_nx_runtime_process_exit(3);
    assert(strstr(failure,"Game stopped"));
    wine_nx_runtime_std_write(1,"Resource temporarily unavailable\n",sizeof("Resource temporarily unavailable\n")-1);
    wine_nx_runtime_process_exit(3);
    assert(strstr(failure,"Game stopped"));
    wine_nx_runtime_std_write(2,"  what(): Resource temporarily ",sizeof("  what(): Resource temporarily ")-1);
    wine_nx_runtime_std_write(2,"unavailable\n",sizeof("unavailable\n")-1);
    wine_nx_runtime_process_exit(3);
    assert(strstr(failure,"startup resources unavailable"));
    wine_nx_runtime_process_exit(0xc0000142u);
    assert(strstr(failure,"DLL initialization failed"));
    fflush(fx_debug_file);rewind(fx_debug_file);
    char saved[32768]={0};assert(fread(saved,1,sizeof(saved)-1,fx_debug_file)>0);
    assert(strstr(saved,"[WINE] 0004:err:module:LdrInitializeThunk test-failing.dll failed to initialize"));
    assert(strstr(saved,"TAIL-SURVIVED"));assert(strstr(saved,"fragment-joined"));
    assert(strstr(saved,"flushed-at-exit"));assert(strstr(saved,"[STDERR] stderr-final"));
    assert(strstr(saved,"idle-flush"));
    assert(strstr(saved,"UI-ALIVE-WHILE-SD-WAITS"));
    for(int i=0;i<3;i++)for(int j=0;j<30;j++){
        char line[64];snprintf(line,sizeof(line),"[WINE] parallel-%d-%d\n",i,j);
        assert(strstr(saved,line));
    }
    fclose(fx_debug_file);
    puts("PASS: PE channel lookup, x86/native Wine bridges, long/partial/parallel writes, stderr, immediate exit notification, UI ring during blocked SD output.");
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    native = args.source.resolve() / 'wine-nx-probe/source'
    runtime = (native / 'runtime.c').read_text()
    debug = (args.source / 'dlls/ntdll/unix/debug.c').read_text()
    guest = (args.source / 'dlls/ntdll/thread.c').read_text()
    header = (args.source / 'include/wine/debug.h').read_text()
    debug_types = '\n'.join(re.search(pattern, header).group(0) for pattern in
        (r'enum __wine_debug_class\s*\{[^}]*\};', r'struct __wine_debug_channel\s*\{[^}]*\};'))
    program = PREAMBLE.replace('/* WINE_DEBUG_TYPES */', debug_types)
    program += function(runtime, 'static void log_line( const char *fmt, ... )\n')
    begin = runtime.index('struct std_stream\n')
    end = runtime.index('/* Present only in runtimes linked with the Box64 interpreter. */', begin)
    program += runtime[begin:end]
    for signature in ('static void fx_wine_debug_channels(', 'void wine_nx_runtime_process_exit('):
        program += function(runtime, signature)
    for signature in ('static int wine_nx_dbg_write(', 'NTSTATUS unixcall_wine_dbg_write(',
                      'NTSTATUS wow64_wine_dbg_write('):
        program += function(debug, signature)
    program += function(guest, 'unsigned char __cdecl __wine_dbg_get_channel_flags(')
    program += HARNESS
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.output.resolve() / 'startup-check.c'
    source.write_text(program)
    exe = source.with_suffix('')
    compiler = shutil.which('clang') or shutil.which('cc')
    if not compiler:
        raise SystemExit('A host C compiler is required')
    subprocess.run([compiler, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-O1', '-g', '-fno-pie', '-no-pie',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-I', str(native), str(source), '-pthread', '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
