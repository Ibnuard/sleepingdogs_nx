"""ASan/UBSan: compiled production stack reserve and configured GPU arena."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    a = p.parse_args(); out = a.work / 'host-check'; out.mkdir(exist_ok=True)
    native = a.work / 'native-source/wine-nx-probe/source'
    (out / 'sys').mkdir(exist_ok=True)
    (out / 'sys/reent.h').write_text('#pragma once\nstruct _reent { unsigned char bytes[264]; };\n')
    (out / 'switch.h').write_text('''#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <pthread.h>
#include <sys/reent.h>
typedef uint64_t u64;
typedef uint32_t u32;
typedef unsigned Result;
typedef void (*ThreadFunc)(void *);
typedef pthread_mutex_t Mutex;
static inline void mutexLock(Mutex *m) { pthread_mutex_lock(m); }
static inline void mutexUnlock(Mutex *m) { pthread_mutex_unlock(m); }
typedef struct Thread {
 unsigned handle; int owns_stack_mem; void *stack_mem,*stack_mirror;
 size_t stack_sz; void **tls_array; struct Thread *next,**prev_next;
} Thread;
typedef struct {u64 addr,size;u32 type,attr,perm,ipc_refcount,device_refcount,padding;} MemoryInfo;
#define MAKERESULT(m,d) ((m)|((d)<<9))
#define Module_Libnx 345
#define LibnxError_OutOfMemory 2
#define R_FAILED(r) ((r)!=0)
#define R_SUCCEEDED(r) ((r)==0)
#define InfoType_FreeThreadCount 24
#define InfoType_TotalMemorySize 6
#define InfoType_UsedMemorySize 7
#define InfoType_SystemResourceSizeTotal 16
#define InfoType_SystemResourceSizeUsed 17
#define CUR_PROCESS_HANDLE 0xffff8001u
#define MemState_Type 255
#define MemType_Heap 5
#define Perm_Rw 3
#define Perm_None 0
#define MemAttr_IsBorrowed 1
Result svcQueryMemory(MemoryInfo *,u32 *,u64);
Result svcGetInfo(u64 *,int,unsigned,u64);
''')
    checks = []
    for name in ('memory_native_stacks', 'memory_gpu_arena'):
        exe = out / name
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-pthread', '-fsanitize=address,undefined',
            '-fno-sanitize-recover=all', '-fno-pie', '-no-pie', '-I' + str(out), '-I' + str(native),
            str(ROOT / 'tests' / (name + '.c')), '-o', str(exe)], check=True,
            env=dict(os.environ, TMPDIR=str(out)))
        result = subprocess.run([str(exe)], check=True, text=True, capture_output=True)
        checks += result.stdout.splitlines(); print(result.stdout, end='')
    report = {'status': 'PASS', 'sanitizers': ['address', 'undefined'], 'checks': checks,
        'gpu_arena_bytes': 134217728, 'stack_request_sizes': 256, 'mixed_stack_lifetime_cycles': 2000,
        'gpu_lifetime_cycles': 1024,
        'compiled_sources': {n: sha(native / n) for n in
            ('f1_native_stacks.c', 'f1_native_stacks.h', 'f1_thread_diagnostics.c', 'f1_gpu_arena.h')},
        'sources': {n: sha(ROOT / n) for n in ('tests/memory_native_stacks.c',
            'tests/memory_gpu_arena.c', 'tests/check_memory_budget.py')},
        'scope': 'Real production C and GPU header; modeled Horizon/libnx boundaries and TLS metadata.',
        'hardware_tested': False}
    write_json(ROOT / 'reports/memory-budget-host-check.json', report)

if __name__ == '__main__': main()
