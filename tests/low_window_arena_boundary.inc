/* Linux integration boundary: one memfd mapped at high source and low alias.
 * Deliberately make high backing inaccessible while the kernel owns it.
 * This catches zeroing/freeing through the source instead of the alias. */
typedef unsigned Result;
typedef unsigned Handle;
typedef struct { uint64_t addr,size; unsigned type,perm; } MemoryInfo;
typedef unsigned u32;
typedef uint64_t u64;
#define R_FAILED(x) ((x)!=0)
#define R_SUCCEEDED(x) ((x)==0)
#define STATUS_NO_MEMORY 0xc0000017u
enum { Perm_None=0,Perm_R=1,Perm_Rw=3,MemType_Unmapped=0 };
static unsigned calls,fail_call,allocation_mode,frees,map_fail,process_fail,unmap_fail,low_busy;
static void *mapping,*alias;
static size_t mapping_size;
static int backing_fd=-1,ready=1;
static Handle envGetOwnProcessHandle(void) { return 42; }
static int sd_low_window_ready(void) { return ready; }
static void virtmemLock(void) {}
static void virtmemUnlock(void) {}
static Result svcQueryMemory(MemoryInfo *info,u32 *page,uint64_t addr)
{
    *info=(MemoryInfo){.addr=addr,.size=SD_GUEST_ARENA_BYTES,.type=low_busy?9:0};*page=0;return 0;
}
static Result svcSetMemoryPermission(void *p,uint64_t size,unsigned perm)
{
    if (++calls==fail_call) return 0x1234;
    return mprotect(p,size,perm)?0x5678:0;
}
static Result svcMapProcessCodeMemory(Handle h,u64 low,u64 high,uint64_t size)
{
    assert(h==42 && high==(uintptr_t)mapping && low==0x30000000 && size==mapping_size);
    if(map_fail)return 7;
    alias=mmap((void *)low,size,PROT_NONE,MAP_SHARED|MAP_FIXED_NOREPLACE,backing_fd,0);
    assert(alias==(void *)low);assert(!mprotect(mapping,size,PROT_NONE));return 0;
}
static Result svcSetProcessMemoryPermission(Handle h,u64 low,uint64_t size,unsigned perm)
{
    assert(h==42 && (void *)low==alias && perm==Perm_Rw);
    if(process_fail)return 8;
    return mprotect(alias,size,perm)?9:0;
}
static Result svcUnmapProcessCodeMemory(Handle h,u64 low,u64 high,uint64_t size)
{
    assert(h==42 && (void *)low==alias && (void *)high==mapping);
    if(unmap_fail)return 10;
    assert(!munmap(alias,size));alias=NULL;assert(!mprotect(mapping,size,PROT_READ|PROT_WRITE));return 0;
}
void wine_nx_runtime_trace(const char *s) { (void)s; }
static void *test_memalign(size_t align,size_t size)
{
    assert(align==65536);
    if(allocation_mode==1)return NULL;
    if(allocation_mode==2)return (void *)0x20000000; /* wrong, low backing */
    mapping_size=size;
    backing_fd=memfd_create("sd-low-window-test",0);assert(backing_fd>=0);
    assert(!ftruncate(backing_fd,size));
    mapping=mmap((void *)UINT64_C(0x2000000000),size,PROT_READ|PROT_WRITE,
                 MAP_SHARED|MAP_FIXED_NOREPLACE,backing_fd,0);
    assert(mapping==(void *)UINT64_C(0x2000000000));
    memset(mapping,0xc7,size);return mapping;
}
static void test_free(void *p)
{
    ++frees; assert(!alias); /* still owned by the kernel => must never free */
    if(p==mapping){assert(!munmap(mapping,mapping_size));mapping=NULL;close(backing_fd);backing_fd=-1;}
}
