/* Test the shipped arena and Wine view helpers against real Linux page access.
 * Only the Switch permission/allocation boundary and Wine bookkeeping are
 * replaced. The arena is 1 MiB here; its production size is separately checked. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
#define SD_ARENA_HOST_TEST 1
#ifndef SD_GUEST_ARENA_BYTES
#define SD_GUEST_ARENA_BYTES ((size_t)1024 * 1024)
#endif
typedef unsigned Result;
#define R_FAILED(x) ((x) != 0)
enum { Perm_None=0, Perm_R=1, Perm_Rw=3 };
static unsigned calls, fail_call, allocation_mode, frees;
static void *mapping;
static size_t mapping_size;

static Result svcSetMemoryPermission(void *p, uint64_t size, unsigned perm)
{
    if (++calls == fail_call) return 0x1234;
    return mprotect(p, size, perm) ? 0x5678 : 0;
}
void wine_nx_runtime_trace(const char *s) { (void)s; }
static void *test_memalign(size_t align, size_t size)
{
    if (allocation_mode == 1) return NULL;
    if (allocation_mode == 2) return (void *)UINT64_C(0x100000000);
    mapping_size=size+2*align;
    /* Fixed NOREPLACE keeps a production-sized 1000 MiB fixture below 2 GiB,
     * without replacing any existing mappings or ASan shadow. */
    mapping=mmap((void *)0x20000000,mapping_size,PROT_READ|PROT_WRITE,
                 MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
    assert(mapping!=MAP_FAILED);
    return (void *)(((uintptr_t)mapping+align*2-1)&~(uintptr_t)(align-1));
}
static void test_free(void *p)
{
    ++frees;
    if ((uintptr_t)p < UINT64_C(0x100000000))
    { assert(!munmap(mapping,mapping_size)); mapping=NULL; }
}
#define memalign test_memalign
#define free test_free
#include "sd_guest_arena.c"
#undef free
#undef memalign

typedef unsigned NTSTATUS;
#define STATUS_SUCCESS 0
#define STATUS_NOT_SUPPORTED 0xc00000bbu
#define STATUS_ACCESS_DENIED 0xc0000022u
#define STATUS_INVALID_PAGE_PROTECTION 0xc0000045u
#define STATUS_MEMORY_NOT_ALLOCATED 0xc00000a0u
#define STATUS_UNABLE_TO_FREE_VM 0xc000001au
#define MEM_RESERVE 0x2000
#define MEM_COMMIT 0x1000
#define MEM_TOP_DOWN 0x100000
#define VPROT_READ 0x01
#define VPROT_WRITE 0x02
#define VPROT_EXEC 0x04
#define VPROT_WRITECOPY 0x08
#define VPROT_GUARD 0x10
#define VPROT_COMMITTED 0x20
#define VPROT_WRITEWATCH 0x40
#define VPROT_SYSTEM 0x200
struct file_view { void *base; size_t size; unsigned protect; };
static struct file_view views[8];
static unsigned nviews;
static unsigned char vpages[SD_GUEST_ARENA_BYTES/4096];
static NTSTATUS create_view(struct file_view **out,void *p,size_t size,unsigned prot)
{
    for(unsigned i=0;i<nviews;i++)
        assert((uintptr_t)p+size<=(uintptr_t)views[i].base ||
               (uintptr_t)views[i].base+views[i].size<=(uintptr_t)p);
    assert(nviews<8);
    *out=&views[nviews++];**out=(struct file_view){p,size,prot};return 0;
}
static void set_page_vprot(void *p,size_t size,unsigned prot)
{
    assert(sd_guest_arena_contains(p,size));
    memset(vpages+((uintptr_t)p-(uintptr_t)sd_arena_base)/4096,prot,size/4096);
}
static void set_page_vprot_bits(void *p,size_t size,unsigned set,unsigned clear)
{
    assert(sd_guest_arena_contains(p,size));
    size_t begin=((uintptr_t)p-(uintptr_t)sd_arena_base)/4096;
    for(size_t i=begin;i<begin+size/4096;i++)vpages[i]=(vpages[i]&~clear)|set;
}
static int get_unix_prot(unsigned p)
{
    if(!(p&VPROT_COMMITTED)||p&VPROT_GUARD)return PROT_NONE;
    return (p&VPROT_WRITE)?PROT_READ|PROT_WRITE:(p&VPROT_READ)?PROT_READ:PROT_NONE;
}
#include "sd_guest_view.inc"

static void on_fault(int sig) { (void)sig; _exit(42); }
static void expect_fault(unsigned char *p,int write)
{
    pid_t pid=fork();assert(pid>=0);
    if(!pid){signal(SIGSEGV,on_fault);if(write)*(volatile unsigned char*)p=9;else (void)*(volatile unsigned char*)p;_exit(0);}
    int st;assert(waitpid(pid,&st,0)==pid);assert(WIFEXITED(st)&&WEXITSTATUS(st)==42);
}
static void reset_fixture(void)
{
    if(mapping){assert(!munmap(mapping,mapping_size));mapping=NULL;}
    sd_arena_base=NULL;sd_arena_started=0;calls=fail_call=allocation_mode=frees=0;
    nviews=0;sd_direct_view=NULL;memset(vpages,0,sizeof(vpages));
}
static void pass(const char *s) { printf("PASS %s\n",s); }

int main(void)
{
    struct file_view *view=NULL;
    unsigned rw=VPROT_COMMITTED|VPROT_READ|VPROT_WRITE;
    unsigned type=MEM_RESERVE|MEM_COMMIT|MEM_TOP_DOWN;
    allocation_mode=1;sd_guest_arena_init();assert(!sd_guest_arena_base());pass("allocation failure remains disabled");
    reset_fixture();allocation_mode=2;sd_guest_arena_init();assert(!sd_arena_base&&frees==1);pass("reject backing above 4 GiB");
    reset_fixture();fail_call=1;sd_guest_arena_init();assert(!sd_arena_base&&frees==1);pass("failed initial protection releases backing");
    reset_fixture();sd_guest_arena_init();unsigned char *p=sd_arena_base;size_t size=sd_guest_arena_size();assert(p&&size);
    sd_guest_arena_init();assert(calls==1);expect_fault(p,0);expect_fault(p+size-1,1);pass("idle arena inaccessible and initialization idempotent");
    assert(sd_guest_arena_contains(p,size));assert(!sd_guest_arena_contains(p-1,size));
    assert(!sd_guest_arena_contains(p+size,1));assert(!sd_guest_arena_contains(p,SIZE_MAX));
    assert(sd_guest_arena_overlaps(p-1,2));assert(!sd_guest_arena_overlaps(p-1,1));assert(!sd_guest_arena_overlaps(p+size,1));
    unsigned oldcalls=calls;assert(sd_guest_arena_protect(p+1,4096,3));assert(sd_guest_arena_protect(p,size+4096,3));assert(sd_guest_arena_protect(p,4096,4));assert(calls==oldcalls);pass("bounds alignment overflow and executable access rejected");
    assert(!sd_register_kernel_range(p-65536,size+131072));assert(nviews==3&&sd_direct_view==&views[1]);
    assert(views[0].size==65536&&views[2].size==65536);pass("three non-overlapping Wine guards preserve surrounding heap");
    assert(sd_map_direct_view(&view,NULL,size,type,rw,0,(uintptr_t)p+size-2,65535,UINT64_C(0x100000000))==STATUS_NOT_SUPPORTED);
    assert(sd_map_direct_view(&view,NULL,size,type,rw,(uintptr_t)p+1,0,65535,UINT64_C(0x100000000))==STATUS_NOT_SUPPORTED);
    assert(sd_map_direct_view(&view,NULL,size,type,rw,0,0,65535,(uintptr_t)p+size-1)==STATUS_NOT_SUPPORTED);
    assert(sd_map_direct_view(&view,p,size,type,rw,0,0,65535,UINT64_C(0x100000000))==STATUS_NOT_SUPPORTED);
    assert(sd_map_direct_view(&view,NULL,size-4096,type,rw,0,0,65535,UINT64_C(0x100000000))==STATUS_NOT_SUPPORTED);
    assert(sd_map_direct_view(&view,NULL,size,MEM_RESERVE,rw,0,0,65535,UINT64_C(0x100000000))==STATUS_NOT_SUPPORTED);
    assert(sd_map_direct_view(&view,NULL,size,type,rw|VPROT_EXEC,0,0,65535,UINT64_C(0x100000000))==STATUS_NOT_SUPPORTED);
    assert(sd_map_direct_view(&view,NULL,size,type,rw,0,0,UINT32_MAX,UINT64_C(0x100000000))==STATUS_NOT_SUPPORTED);
    assert(calls==oldcalls);pass("limits flags size fixed address and alignment preserve ordinary path");
    fail_call=calls+1;assert(sd_map_direct_view(&view,NULL,size,type,rw,0,0,65535,UINT64_C(0x100000000))==STATUS_ACCESS_DENIED);
    assert(sd_direct_view->protect==VPROT_SYSTEM);expect_fault(p,0);fail_call=0;pass("failed activation preserves inaccessible guard");
    assert(!sd_map_direct_view(&view,NULL,size,type,rw,0,(uintptr_t)p+size-1,65535,(uintptr_t)p+size));
    assert(view==sd_direct_view&&view->base==p&&view->protect==rw&&vpages[0]==rw&&vpages[size/4096-1]==rw);
    for(size_t i=0;i<size;i++)assert(p[i]==0);memset(p,0x6a,size);
    assert(sd_map_direct_view(&view,NULL,size,type,rw,0,0,65535,UINT64_C(0x100000000))==STATUS_NOT_SUPPORTED);pass("exact backing identity zero initialized and cannot be double allocated");
    assert(!sd_direct_protection(view,p,4096,VPROT_READ));assert(p[0]==0x6a);expect_fault(p,1);
    assert(!sd_direct_protection(view,p,4096,VPROT_READ|VPROT_WRITE));assert(p[0]==0x6a);
    assert(sd_direct_protection(view,p,4096,VPROT_EXEC)==STATUS_INVALID_PAGE_PROTECTION);assert(vpages[0]==rw);pass("read-only protection enforced and unsupported execution leaves metadata intact");
    fail_call=calls+1;assert(sd_direct_decommit(view,p+4096,4096)==STATUS_ACCESS_DENIED);assert(p[4096]==0x6a&&vpages[1]==rw);fail_call=0;
    assert(!sd_direct_decommit(view,p+4096,4096));assert(!(vpages[1]&VPROT_COMMITTED));expect_fault(p+4096,0);
    assert(!sd_direct_protection(view,p+4096,4096,VPROT_READ|VPROT_WRITE));assert(p[4096]==0&&p[4095]==0x6a&&p[8192]==0x6a);pass("partial decommit recommit zeros only discarded pages; failed decommit preserves data");
    assert(!sd_direct_decommit(view,p+4096,4096));fail_call=calls+2;
    assert(sd_direct_protection(view,p,3*4096,VPROT_READ)==STATUS_ACCESS_DENIED);fail_call=0;
    assert(vpages[0]==rw&&!(vpages[1]&VPROT_COMMITTED)&&vpages[2]==rw);expect_fault(p+4096,0);p[0]=0x6a;p[8192]=0x6a;
    assert(!sd_direct_protection(view,p,3*4096,VPROT_READ));assert(p[4096]==0);expect_fault(p+4096,1);
    assert(!sd_direct_protection(view,p,3*4096,VPROT_READ|VPROT_WRITE));pass("failed mixed recommit rolls back each old protection group");
    assert(!sd_direct_protection(view,p,4096,VPROT_READ|VPROT_WRITE|VPROT_GUARD));expect_fault(p,0);
    assert(!sd_guest_arena_protect(p,4096,PROT_READ|PROT_WRITE));assert(p[0]==0x6a);pass("guard access change preserves committed contents");
    assert(sd_direct_release(view,p,4096)==STATUS_UNABLE_TO_FREE_VM);assert(view->protect==rw);
    fail_call=calls+1;assert(sd_direct_release(view,p,size)==STATUS_ACCESS_DENIED);assert(view->protect==rw);fail_call=0;
    assert(!sd_direct_release(view,p,size));assert(view->protect==VPROT_SYSTEM);expect_fault(p,0);
    assert(sd_direct_protection(view,p,4096,VPROT_READ|VPROT_WRITE)==STATUS_ACCESS_DENIED);
    assert(sd_direct_decommit(view,p,4096)==STATUS_ACCESS_DENIED);
    assert(sd_direct_release(view,p,size)==STATUS_MEMORY_NOT_ALLOCATED);pass("full release restores guard and rejects stale or partial operations");
    assert(!sd_map_direct_view(&view,NULL,size,type,rw,0,0,65535,UINT64_C(0x100000000)));
    for(size_t i=0;i<size;i++)assert(p[i]==0);assert(nviews==3&&views[0].protect==VPROT_SYSTEM&&views[2].protect==VPROT_SYSTEM);pass("reuse zeros all data without releasing neighbour guards");
    reset_fixture();puts("ALL DIRECT ARENA CHECKS PASSED");return 0;
}
