"""Host fault injection for the actual startup observers, not a game execution test."""
from pathlib import Path
import argparse
import shutil
import subprocess
from check_startup import function

ROOT = Path(__file__).resolve().parents[1]
PREAMBLE = r'''
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#define F1_STARTUP_WATCH_IMPLEMENTATION
#include "f1_startup_watch.h"
typedef int32_t NTSTATUS;
typedef uintptr_t ULONG_PTR;
typedef uint32_t ULONG,ACCESS_MASK;
typedef int BOOL;
typedef void *HANDLE;
typedef void OBJECT_ATTRIBUTES,IO_STATUS_BLOCK,LARGE_INTEGER;
typedef void (*PIO_APC_ROUTINE)(void);
#define WINAPI
#define FALSE 0
#define STATUS_INVALID_SYSTEM_SERVICE ((NTSTATUS)0xc000001c)
static struct { struct { uintptr_t UniqueThread; } ClientId; } teb={{4}};
#define NtCurrentTeb() (&teb)
#define HandleToULong(x) ((uint32_t)(uintptr_t)(x))
static uint64_t now=100;
static uint64_t armGetSystemTick(void) { return now++; }
typedef struct { void **ServiceTable; unsigned ServiceLimit; unsigned char *ArgumentTable; } SYSTEM_SERVICE_TABLE;
static void *handlers[4]; static unsigned char arg_bytes[]={64,128,64,0};
static SYSTEM_SERVICE_TABLE KeServiceDescriptorTable[4]={{handlers,4,arg_bytes}};
static int wine_nx_runtime_verbose;
static unsigned wine_nx_syscalls,wine_nx_syscall_counts[0x2000];
static int fex_poll_count(unsigned id){(void)id;return 0;}
static void wine_nx_runtime_trace(const char *s){(void)s;}
static void NtQueryPerformanceCounter(void){}
static void NtDelayExecution(void){}
static NTSTATUS answer;
static NTSTATUS handler8(ULONG_PTR a,ULONG_PTR b,ULONG_PTR c,ULONG_PTR d,
                         ULONG_PTR e,ULONG_PTR f,ULONG_PTR g,ULONG_PTR h) {
    assert(a==1&&b==2&&c==3&&d==4&&e==5&&f==6&&g==7&&h==8);return answer;
}
static NTSTATUS handler16(ULONG_PTR a,ULONG_PTR b,ULONG_PTR c,ULONG_PTR d,
                         ULONG_PTR e,ULONG_PTR f,ULONG_PTR g,ULONG_PTR h,
                         ULONG_PTR i,ULONG_PTR j,ULONG_PTR k,ULONG_PTR l,
                         ULONG_PTR m,ULONG_PTR n,ULONG_PTR o,ULONG_PTR p) {
    handler8(a,b,c,d,e,f,g,h);assert(i==9&&j==10&&k==11&&l==12&&m==13&&n==14&&o==15&&p==16);return answer;
}
#define NtReadVirtualMemory handler8
static NTSTATUS ordinary_handler(ULONG_PTR a,ULONG_PTR b,ULONG_PTR c,ULONG_PTR d,
                                ULONG_PTR e,ULONG_PTR f,ULONG_PTR g,ULONG_PTR h) {
    return handler8(a,b,c,d,e,f,g,h);
}
static NTSTATUS f1_original_open_unix_file(HANDLE *h,const char *p,ACCESS_MASK a,OBJECT_ATTRIBUTES *o,
    ULONG attr,ULONG share,ULONG disposition,ULONG options,void *ea,ULONG ea_length) {
    assert(!strcmp(p,"/game/test.dat")&&a==1&&attr==2&&share==3&&disposition==4&&options==5&&ea_length==6);
    assert(!o&&!ea);if(!answer)*h=(void *)0x80;return answer;
}
static NTSTATUS f1_original_NtReadFile(HANDLE h,HANDLE event,PIO_APC_ROUTINE apc,void *user,
    IO_STATUS_BLOCK *io,void *buffer,ULONG length,LARGE_INTEGER *offset,ULONG *key) {
    assert(h==(void *)0x80&&!event&&!apc&&!user&&!io&&buffer==(void *)0x1234&&length==8192&&!offset&&!key);
    return answer;
}
'''

HARNESS = r'''
int main(void) {
    handlers[0]=(void *)ordinary_handler;handlers[1]=(void *)handler16;handlers[2]=(void *)NtReadVirtualMemory;
    ULONG_PTR stack[]={9,10,11,12,13,14,15,16};
    f1_startup_watch_enabled=1;
    const uint32_t statuses[]={0,0x103,0xc0000001,0xc0000011};
    for(unsigned i=0;i<4;++i){
        answer=statuses[i];
        assert(wine_nx_do_syscall(stack,1,2,3,4,5,6,7,8,0)==answer);
        assert(wine_nx_do_syscall(stack,1,2,3,4,5,6,7,8,1)==answer);
        HANDLE handle=NULL;
        assert(open_unix_file(&handle,"/game/test.dat",1,NULL,2,3,4,5,NULL,6)==answer);
        assert(NtReadFile((void *)0x80,NULL,NULL,NULL,NULL,(void *)0x1234,8192,NULL,NULL)==answer);
    }
    struct f1_watch_row rows[2];unsigned overflow;
    assert(f1_watch_snapshot(rows,2,&overflow)==1&&rows[0].calls==8&&rows[0].completed==8);
    assert(rows[0].status==0xc0000011&&rows[0].file_status==0xc0000011);
    assert(wine_nx_do_syscall(stack,1,2,3,4,5,6,7,8,3)==STATUS_INVALID_SYSTEM_SERVICE);
    assert(wine_nx_do_syscall(stack,1,2,3,4,5,6,7,8,4)==STATUS_INVALID_SYSTEM_SERVICE);
    assert(wine_nx_do_syscall(stack,1,2,3,4,5,6,7,8,2)==answer);
    assert(f1_watch_snapshot(rows,2,&overflow)==1&&rows[0].calls==8);
    puts("PASS: actual dispatcher/file wrappers preserve 8/16 arguments, success, pending, errors and invalid calls; FEX argument reads excluded.");
}
'''

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    unix = args.source/'dlls/ntdll/unix'
    signal = (unix/'signal_arm64.c').read_text()
    file = (unix/'file.c').read_text()
    harness = args.output/'dispatch.c'
    harness.write_text(PREAMBLE+function(signal,'NTSTATUS wine_nx_do_syscall(')+
        function(file,'NTSTATUS open_unix_file(')+function(file,'NTSTATUS WINAPI NtReadFile(')+HARNESS)
    cc = shutil.which('clang') or shutil.which('cc')
    for path in (ROOT/'tests/startup_watch.c',ROOT/'tests/startup_snapshot.c',harness):
        exe=args.output/path.stem
        subprocess.run([cc,'-std=c11','-D_POSIX_C_SOURCE=200809L','-O1','-g','-fsanitize=address,undefined',
            '-fno-sanitize-recover=all','-I',str(ROOT/'tools'),str(path),'-pthread','-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

if __name__=='__main__':main()
