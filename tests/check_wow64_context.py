"""Exercise the real old/new WoW64 context thunk with counted NT operations."""
from pathlib import Path
import argparse
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from wow64_context_fix import ORIGINAL, FIXED
from port_common import write_json

PREAMBLE = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t UINT, ULONG;
typedef int32_t NTSTATUS;
typedef int BOOL;
typedef void *HANDLE;
typedef struct { ULONG ContextFlags; ULONG Dr0, Dr1, Dr2, Dr3, Dr6, Dr7; } WOW64_CONTEXT;
typedef struct { HANDLE UniqueProcess, UniqueThread; } CLIENT_ID;
typedef struct { CLIENT_ID ClientId; } THREAD_BASIC_INFORMATION;
#define WINAPI
#define FALSE 0
#define TRUE 1
#define WOW64_CPUFLAGS_SOFTWARE 2
#define ThreadBasicInformation 0
#define GetCurrentThread() ((HANDLE)(intptr_t)-2)
static struct { CLIENT_ID ClientId; } teb;
#define NtCurrentTeb() (&teb)
static struct { ULONG CpuFlags; } info_storage, *wow64info=&info_storage;
static WOW64_CONTEXT ctx;
static char events[20];
static unsigned events_n, unsafe_self_suspend;
static ULONG suspend_count;
static NTSTATUS query_status, suspend_status, context_status;
static HANDLE got_handle;
static HANDLE get_handle(UINT **args) { return (HANDLE)(intptr_t)(int32_t)*(*args)++; }
static void *get_ptr(UINT **args) { assert(*(*args)++==0x1234); return &ctx; }
static void event(char c) { assert(events_n<sizeof(events)-1); events[events_n++]=c; }
static NTSTATUS NtQueryInformationThread(HANDLE handle, int kind, void *out, ULONG size, void *ret) {
    assert(kind==ThreadBasicInformation && size==sizeof(THREAD_BASIC_INFORMATION) && !ret);
    event('Q');
    if(query_status) return query_status;
    THREAD_BASIC_INFORMATION *info=out;
    info->ClientId.UniqueProcess=(HANDLE)(uintptr_t)(handle==(HANDLE)0x88?200:100);
    info->ClientId.UniqueThread=(HANDLE)(uintptr_t)(handle==(HANDLE)0x48?8:4);
    return 0;
}
static NTSTATUS RtlWow64SuspendThread(HANDLE handle, ULONG *count) {
    event('S');
    if(handle==GetCurrentThread() || handle==(HANDLE)0x44) unsafe_self_suspend++;
    if(suspend_status) return suspend_status;
    *count=suspend_count++;
    return 0;
}
static NTSTATUS RtlWow64GetThreadContext(HANDLE handle, WOW64_CONTEXT *context) {
    event('G'); got_handle=handle;
    assert(context==&ctx && context->ContextFlags==0x10010);
    if(!context_status) context->Dr7=0x400;
    return context_status;
}
static NTSTATUS NtResumeThread(HANDLE handle, ULONG *count) {
    (void)handle; event('R'); *count=suspend_count;
    if(suspend_count) suspend_count--;
    return 0;
}
static void reset(void) {
    memset(events,0,sizeof(events)); events_n=unsafe_self_suspend=0;
    suspend_count=3; query_status=suspend_status=context_status=0;
    got_handle=NULL; ctx=(WOW64_CONTEXT){.ContextFlags=0x10010};
    teb.ClientId=(CLIENT_ID){(HANDLE)100,(HANDLE)4};
    wow64info->CpuFlags=WOW64_CPUFLAGS_SOFTWARE;
}
'''
HARNESS = r'''
static NTSTATUS call(UINT handle) {
    UINT args[]={handle,0x1234}; return wow64_NtGetContextThread(args);
}
int main(void) {
    reset(); UINT old_args[]={0xfffffffe,0x1234};
    assert(!before_wow64_NtGetContextThread(old_args));
    assert(unsafe_self_suspend==1 && !strcmp(events,"SGR"));
    puts("REPRODUCED: original thunk attempts synchronous self-suspend before its own resume.");
    reset(); assert(!call(0xfffffffe));
    assert(!strcmp(events,"G") && got_handle==GetCurrentThread() && ctx.Dr7==0x400);
    assert(!unsafe_self_suspend && suspend_count==3);
    reset(); assert(!call(0x44));
    assert(!strcmp(events,"QG") && got_handle==GetCurrentThread() && !unsafe_self_suspend);
    reset(); assert(!call(0x48));
    assert(!strcmp(events,"QSGR") && got_handle==(HANDLE)0x48 && suspend_count==3);
    reset(); assert(!call(0x88));
    assert(!strcmp(events,"QSGR") && got_handle==(HANDLE)0x88 && suspend_count==3);
    reset(); query_status=(NTSTATUS)0xc0000008; assert(call(0x48)==query_status);
    assert(!strcmp(events,"Q") && suspend_count==3);
    reset(); suspend_status=(NTSTATUS)0xc00000bb; assert(call(0x48)==suspend_status);
    assert(!strcmp(events,"QS") && suspend_count==3);
    reset(); context_status=(NTSTATUS)0xc000000d; assert(call(0x48)==context_status);
    assert(!strcmp(events,"QSGR") && suspend_count==3);
    reset(); context_status=(NTSTATUS)0xc000000d; assert(call(0xfffffffe)==context_status);
    assert(!strcmp(events,"G") && suspend_count==3);
    reset(); wow64info->CpuFlags=0; assert(!call(0x48));
    assert(!strcmp(events,"G") && got_handle==(HANDLE)0x48 && suspend_count==3);
    puts("PASS: 9 context-query cases; self/alias never suspend, remote counts balanced, errors propagated.");
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    file = output / 'wow64-context.c'
    file.write_text(PREAMBLE + ORIGINAL.replace('wow64_NtGetContextThread', 'before_wow64_NtGetContextThread')
                    + '\n' + FIXED + '\n' + HARNESS)
    temp = output / 'tmp'
    temp.mkdir(exist_ok=True)
    env = dict(os.environ, TMPDIR=str(temp))
    exe = file.with_suffix('')
    subprocess.run([shutil.which('cc'), '-std=c11', '-O1', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    str(file), '-o', str(exe)], env=env, check=True)
    subprocess.run([str(exe)], check=True)
    write_json(ROOT / 'reports/wow64-context-host-check.json', {
        'status': 'PASS', 'cases': 9, 'original_self_suspend_reproduced': True,
        'fixed_function_sha256': hashlib.sha256(FIXED.encode()).hexdigest(),
        'sanitizers': ['AddressSanitizer', 'UndefinedBehaviorSanitizer'],
        'hardware_tested': False})


if __name__ == '__main__':
    main()
