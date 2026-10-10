/* Host test of the actual bridge; NT policy and CPU backend are test boundaries. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
typedef uint32_t ULONG;
typedef uintptr_t ULONG_PTR;
typedef int32_t NTSTATUS;
typedef void *HANDLE;
typedef int BOOL;
typedef pthread_mutex_t RTL_SRWLOCK;
#define RTL_SRWLOCK_INIT PTHREAD_MUTEX_INITIALIZER
#define GetCurrentProcess() ((HANDLE)(intptr_t)-1)
#define ProcessBasicInformation 0
#define ProcessExecuteFlags 34
#define WARN(...) ((void)0)
typedef struct { ULONG_PTR UniqueProcessId; } PROCESS_BASIC_INFORMATION;
static struct { struct { HANDLE UniqueProcess; } ClientId; } teb = {{(HANDLE)100}};
#define NtCurrentTeb() (&teb)
static void RtlAcquireSRWLockExclusive(RTL_SRWLOCK *l) { assert(!pthread_mutex_lock(l)); }
static void RtlReleaseSRWLockExclusive(RTL_SRWLOCK *l) { assert(!pthread_mutex_unlock(l)); }
static ULONG wine_flags, backend_flags, notifications, queries, sets;
static NTSTATUS set_error, query_error, identity_error;
static char order[32]; static unsigned order_n;
static void event(char c) { if (order_n < sizeof(order)-1) order[order_n++]=c; }
static NTSTATUS NtSetInformationProcess(HANDLE h, int c, void *p, ULONG len) {
    assert(c == ProcessExecuteFlags); ++sets; event('S');
    if (set_error) return set_error;
    if (len != 4) return (NTSTATUS)0xc0000004;
    if (!p) return (NTSTATUS)0xc0000005;
    if (h == GetCurrentProcess() || h == (HANDLE)0x44) wine_flags=*(ULONG *)p;
    return 0;
}
static NTSTATUS NtQueryInformationProcess(HANDLE h, int c, void *p, ULONG len, void *ret) {
    assert(!ret); ++queries;
    if (c == ProcessBasicInformation) {
        event('I'); assert(len == sizeof(PROCESS_BASIC_INFORMATION));
        if (identity_error) return identity_error;
        ((PROCESS_BASIC_INFORMATION *)p)->UniqueProcessId = h == (HANDLE)0x44 ? 100 : 200;
        return 0;
    }
    event('Q'); assert(c == ProcessExecuteFlags && h == GetCurrentProcess() && len == 4);
    if (query_error) return query_error;
    *(ULONG *)p=wine_flags; return 0;
}
static void notify(ULONG flags) { event('N'); ++notifications; backend_flags=flags; }
static void (*pBTCpuNotifyProcessExecuteFlagsChange)(ULONG) = notify;
#include "../src/sd_wow64_dep.inc"
static void reset(void) {
    wine_flags=backend_flags=1; notifications=queries=sets=0;
    set_error=query_error=identity_error=0; pBTCpuNotifyProcessExecuteFlagsChange=notify;
    memset(order,0,sizeof(order)); order_n=0;
}
static void *worker(void *arg) {
    for (unsigned i=0;i<2000;i++) { ULONG f=1+(i+(uintptr_t)arg)%2;
        assert(!sd_wow64_set_execute_flags(GetCurrentProcess(),&f,4)); }
    return NULL;
}
int main(void) {
    ULONG flags=2;
    reset(); assert(!NtSetInformationProcess(GetCurrentProcess(),34,&flags,4));
    assert(wine_flags==2 && backend_flags==1);
    puts("REPRODUCED: prior Wine pass-through leaves FEX DEP enabled after Wine disables it");
    reset(); wine_flags=2; sd_wow64_sync_execute_flags();
    assert(backend_flags==2 && notifications==1 && !strcmp(order,"QN"));
    reset(); assert(!sd_wow64_set_execute_flags(GetCurrentProcess(),&flags,4));
    assert(backend_flags==2 && !strcmp(order,"SQN"));
    flags=9; assert(!sd_wow64_set_execute_flags(GetCurrentProcess(),&flags,4));
    assert(backend_flags==9 && notifications==2);
    reset(); flags=2; assert(!sd_wow64_set_execute_flags((HANDLE)0x44,&flags,4));
    assert(backend_flags==2 && !strcmp(order,"SIQN"));
    reset(); assert(!sd_wow64_set_execute_flags((HANDLE)0x88,&flags,4));
    assert(!notifications && !strcmp(order,"SI"));
    reset(); set_error=(NTSTATUS)0xc0000022;
    assert(sd_wow64_set_execute_flags(GetCurrentProcess(),NULL,4)==set_error);
    assert(!queries && !notifications);
    reset(); assert(sd_wow64_set_execute_flags(GetCurrentProcess(),&flags,3)==(NTSTATUS)0xc0000004);
    assert(!notifications && !queries);
    reset(); query_error=(NTSTATUS)0xc0000001;
    assert(!sd_wow64_set_execute_flags(GetCurrentProcess(),&flags,4)); assert(!notifications);
    reset(); identity_error=(NTSTATUS)0xc0000008;
    assert(!sd_wow64_set_execute_flags((HANDLE)0x44,&flags,4)); assert(!notifications);
    reset(); pBTCpuNotifyProcessExecuteFlagsChange=NULL;
    sd_wow64_sync_execute_flags(); assert(!queries);
    assert(!sd_wow64_set_execute_flags(GetCurrentProcess(),&flags,4));
    assert(!queries && !notifications && wine_flags==2);
    puts("PASS initial sync, enable/disable, real self, remote, denied, bad size, query failures, optional backend");
    reset(); pthread_t a,b;
    assert(!pthread_create(&a,NULL,worker,(void *)0)); assert(!pthread_create(&b,NULL,worker,(void *)1));
    assert(!pthread_join(a,NULL) && !pthread_join(b,NULL));
    assert(wine_flags==backend_flags && notifications==4000 && sets==4000);
    puts("PASS 4000 concurrent changes preserve Wine/backend policy ordering");
}
