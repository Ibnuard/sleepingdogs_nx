/* Host fault injection of the actual native reserve + actual thread wrapper.
 * Models Horizon borrowed source-page state and the libnx 4.12.0 stack ABI. */
#define _DEFAULT_SOURCE 1
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <malloc.h>
#include <switch.h>

unsigned char fake_tls[1480];
asm(".globl __tls_start\n.set __tls_start,fake_tls\n.globl __tls_end\n.set __tls_end,fake_tls+1480");
size_t __tls_align = 64;
char *fake_heap_start = (char *)(uintptr_t)0x10000000;
char *fake_heap_end = (char *)(uintptr_t)0x80000000;

struct block { void *ptr; size_t bytes; int borrowed, query_fail, split_bad; };
static struct block blocks[16];
static pthread_mutex_t blocks_mutex = PTHREAD_MUTEX_INITIALIZER;
static unsigned allocated, allocation_limit = 16;
static _Atomic unsigned plain_creates, reserve_creates, closes, trace_count;
static int create_failure, close_failure;
static void entry(void *arg) { (void)arg; }

void wine_nx_runtime_trace(const char *text)
{assert(text && text[0]);++trace_count;errno=EIO;}
void wine_nx_f1_crash_resource(uint64_t a,unsigned b,uint64_t c,uint64_t d,uint64_t e,uint64_t f)
{(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;errno=EIO;}
void wine_nx_f1_crash_stage(const char *s,unsigned code,uint64_t a,uint64_t b)
{(void)s;(void)code;(void)a;(void)b;errno=EIO;}
size_t wine_nx_release_idle_backing_pages(void) {return 0;}
size_t wine_nx_f1_release_idle_scratch(size_t bytes) {(void)bytes;return 0;}
void wine_nx_f1_guest_memory_snapshot(uint64_t out[6]) {memset(out,0,6*sizeof(*out));}
unsigned long long wine_nx_sd_cache_bytes(void) {return 0;}
void horizon_get_memory_info(unsigned long long *total,unsigned long long *used) {*total=2147483648;*used=0;}
int wine_nx_f1_relaunch_request(unsigned kind,unsigned code)
{(void)kind;(void)code;abort();}
Result svcGetInfo(u64 *value,int info,unsigned process,u64 sub)
{(void)info;(void)process;(void)sub;*value=145;return 0;}
int __real_pthread_create(pthread_t *thread,const pthread_attr_t *attr,void *(*func)(void *),void *arg)
{return pthread_create(thread,attr,func,arg);}

static struct block *lookup(uintptr_t ptr)
{
    for(unsigned i=0;i<allocated;i++)
        if(ptr >= (uintptr_t)blocks[i].ptr && ptr < (uintptr_t)blocks[i].ptr+blocks[i].bytes) return &blocks[i];
    return NULL;
}
void *__libnx_aligned_alloc(size_t alignment,size_t bytes)
{
    assert(alignment==4096 && !(bytes & 4095));
    assert(!pthread_mutex_lock(&blocks_mutex));
    if(allocated==allocation_limit) {pthread_mutex_unlock(&blocks_mutex);errno=ENOMEM;return NULL;}
    void *ptr=aligned_alloc(alignment,bytes);assert(ptr);
    blocks[allocated++]=(struct block){ptr,bytes,0,0,0};
    assert(!pthread_mutex_unlock(&blocks_mutex));
    errno=ERANGE;return ptr;
}
Result svcQueryMemory(MemoryInfo *info,u32 *page_info,u64 address)
{
    assert(!pthread_mutex_lock(&blocks_mutex));
    struct block *block=lookup((uintptr_t)address);assert(block);
    memset(info,0,sizeof(*info));*page_info=0;
    if(block->query_fail) {pthread_mutex_unlock(&blocks_mutex);errno=EIO;return 0xd401;}
    info->addr=(uintptr_t)block->ptr;info->size=block->bytes;
    info->type=MemType_Heap;info->perm=Perm_Rw;
    if(block->borrowed) {info->attr=MemAttr_IsBorrowed;info->perm=Perm_None;}
    if(block->split_bad) {
        info->size=block->bytes/2;
        if(address>=(uintptr_t)block->ptr+info->size) {
            info->addr+=info->size;info->size=block->bytes-info->size;
            info->attr=MemAttr_IsBorrowed;info->perm=Perm_None;
        }
    }
    assert(!pthread_mutex_unlock(&blocks_mutex));
    errno=EIO;return 0;
}
Result __real_threadCreate(Thread *thread,ThreadFunc func,void *arg,void *stack,size_t size,int priority,int core)
{
    assert(func==entry && arg==(void *)0x1234 && priority==59 && core==-2);
    if(!stack) {++plain_creates;assert(size && size<=1024*1024 && !(size&4095));errno=ENOMEM;return 0x559;}
    ++reserve_creates;
    assert(!pthread_mutex_lock(&blocks_mutex));
    struct block *block=lookup((uintptr_t)stack);assert(block && block->ptr==stack);
    assert(!block->borrowed && block->bytes==size && !(size&4095));
    size_t tls=(sizeof(fake_tls)+15)&~(size_t)15;
    size_t reent=(sizeof(struct _reent)+15)&~(size_t)15;
    size_t needed=(tls+reent+__tls_align-1)&~(__tls_align-1);
    assert(size>needed+48 && size-needed-48>=1024*1024);
    /* Failure 1 is map rejection, 2 is successful rollback after create failure,
     * 3 leaves borrowed pages after failed rollback, 4 is an unqueryable block,
     * 5 has a healthy first MemoryInfo region and a borrowed second one. */
    if(create_failure==1) {pthread_mutex_unlock(&blocks_mutex);errno=EPERM;return 0xd401;}
    block->borrowed=1;
    *thread=(Thread){.stack_mem=stack,.stack_mirror=(char *)stack+4096,
                     .stack_sz=size-needed-48,.owns_stack_mem=0,.handle=1};
    if(create_failure) {
        if(create_failure!=3)block->borrowed=0;
        if(create_failure==4)block->query_fail=1;
        if(create_failure==5)block->split_bad=1;
        pthread_mutex_unlock(&blocks_mutex);errno=EPERM;return 0xce01;
    }
    assert(!pthread_mutex_unlock(&blocks_mutex));
    errno=EDOM;return 0;
}
Result __real_threadClose(Thread *thread)
{
    ++closes;
    assert(!pthread_mutex_lock(&blocks_mutex));
    struct block *block=lookup((uintptr_t)thread->stack_mem);
    if(block) {
        assert(!thread->owns_stack_mem && block->borrowed);
        if(close_failure || thread->tls_array) {
            pthread_mutex_unlock(&blocks_mutex);errno=EBUSY;return 0xd401;
        }
        block->borrowed=0;
    }
    assert(!pthread_mutex_unlock(&blocks_mutex));
    errno=EDOM;return 0;
}

#include "f1_native_stacks.c"
#include "f1_thread_diagnostics.c"

static Result recover(Thread *thread)
{return wine_nx_f1_native_stack_retry(0x559,thread,entry,(void *)0x1234,NULL,1024*1024,59,-2);}
static unsigned state_count(enum f1_stack_state state)
{
    unsigned count=0;
    for(unsigned i=0;i<F1_STACK_COUNT;i++)count+=f1_native_stacks[i].state==state;
    return count;
}
static void reset(void)
{
    assert(!state_count(F1_STACK_ACTIVE) && !state_count(F1_STACK_CREATING) && !state_count(F1_STACK_CLOSING));
    for(unsigned i=0;i<allocated;i++)free(blocks[i].ptr);
    memset(blocks,0,sizeof(blocks));memset(f1_native_stacks,0,sizeof(f1_native_stacks));
    allocated=0;allocation_limit=16;create_failure=close_failure=0;
    f1_native_stack_initialized=0;f1_native_stack_bytes=0;
    f1_native_stack_recovered=f1_native_stack_exhausted=0;
    plain_creates=reserve_creates=closes=trace_count=0;
}
static void *worker(void *arg)
{
    (void)arg;
    for(unsigned i=0;i<250;i++) {
        Thread t={0};
        assert(!wine_nx_f1_native_stack_retry(0x559,&t,entry,(void *)0x1234,NULL,
            i & 1 ? 128*1024 : 1024*1024,59,-2));
        assert(t.stack_sz>=1024*1024 && !t.owns_stack_mem);
        assert(!__wrap_threadClose(&t));
    }
    return NULL;
}

int main(void)
{
    Thread t={0};errno=ENOENT;
    assert(recover(&t)==0x559 && !reserve_creates && errno==ENOENT);
    assert(__wrap_threadCreate(&t,entry,(void *)0x1234,NULL,1024*1024,59,-2)==0x559);
    assert(plain_creates==1 && errno==ENOMEM);
    errno=ENOENT;wine_nx_f1_native_stacks_init();
    assert(allocated==16 && state_count(F1_STACK_IDLE)==16 && errno==ENOENT);
    size_t bytes=f1_native_stack_bytes;assert(bytes<1024*1024+65536);
    wine_nx_f1_native_stacks_init();assert(allocated==16);
    assert(!__wrap_threadCreate(&t,entry,(void *)0x1234,NULL,1024*1024,59,-2));
    assert(plain_creates==2 && reserve_creates==1 && errno==EDOM);
    assert(t.stack_sz>=1024*1024 && state_count(F1_STACK_ACTIVE)==1);
    void *first=t.stack_mem;
    assert(!__wrap_threadClose(&t) && errno==EDOM && state_count(F1_STACK_IDLE)==16);
    assert(!recover(&t) && t.stack_mem==first);
    assert(!__wrap_threadClose(&t));
    puts("PASS: actual thread wrapper fails with fragmented normal heap, then recovers from the early reserve; full 1 MiB usable stack, TLS/reent, ownership, close and reuse preserved");

    for(unsigned n=0;n<3;n++) {
        unsigned prior=reserve_creates;errno=ENOENT;
        Result result=wine_nx_f1_native_stack_retry(n==0?0xd401:0x559,&t,entry,(void *)0x1234,
            n==1?(void *)0x4000:NULL,n==2?2*1024*1024:1024*1024,59,-2);
        assert(result==(n==0?0xd401:0x559) && reserve_creates==prior && errno==ENOENT);
    }
    for(size_t request=4096;request<=1024*1024;request+=4096) {
        assert(!wine_nx_f1_native_stack_retry(0x559,&t,entry,(void *)0x1234,NULL,request,59,-2));
        assert(t.stack_sz>=request && t.stack_sz>=1024*1024 && !t.owns_stack_mem);
        assert(!__wrap_threadClose(&t));
    }
    assert(!__wrap_threadCreate(&t,entry,(void *)0x1234,NULL,128*1024,59,-2));
    assert(!__wrap_threadClose(&t));
    for(unsigned invalid=0;invalid<3;invalid++) {
        size_t size=invalid==0?0:invalid==1?131073:1048577;
        unsigned before=reserve_creates;errno=ENOENT;
        assert(wine_nx_f1_native_stack_retry(0x559,&t,entry,(void *)0x1234,NULL,size,59,-2)==0x559);
        assert(reserve_creates==before && errno==ENOENT);
    }
    puts("PASS: all 256 page-aligned requests through 1 MiB, actual 128 KiB wrapper, invalid sizes rejected");
    Thread normal={0};assert(!__wrap_threadClose(&normal));
    errno=ENOENT;wine_nx_f1_native_stacks_snapshot();assert(errno==ENOENT);
    puts("PASS: caller stacks, wrong sizes and non-memory errors pass through; ordinary close and diagnostic errno preserved");

    reset();allocation_limit=3;errno=E2BIG;wine_nx_f1_native_stacks_init();
    assert(allocated==3 && state_count(F1_STACK_IDLE)==3 && errno==E2BIG);
    Thread all[16]={{0}};
    for(unsigned i=0;i<3;i++)assert(!recover(&all[i]));
    errno=ENOMEM;assert(recover(&t)==0x559 && errno==ENOMEM && f1_native_stack_exhausted==1);
    for(unsigned i=0;i<3;i++)assert(!__wrap_threadClose(&all[i]));
    assert(state_count(F1_STACK_IDLE)==3);
    reset();allocation_limit=0;wine_nx_f1_native_stacks_init();
    assert(!allocated && recover(&t)==0x559 && !reserve_creates);
    puts("PASS: partial initialization and exhausted/empty reserve remain bounded and return the original allocation error");

    reset();wine_nx_f1_native_stacks_init();
    for(unsigned failure=1;failure<=5;failure++) {
        create_failure=failure;unsigned idle=state_count(F1_STACK_IDLE);
        assert(recover(&t)==(failure==1?0xd401:0xce01) && errno==EPERM);
        assert(state_count(F1_STACK_IDLE)==idle-(failure>=3));
    }
    assert(state_count(F1_STACK_QUARANTINED)==3 && state_count(F1_STACK_IDLE)==13);
    create_failure=0;assert(!recover(&t));
    close_failure=1;assert(__wrap_threadClose(&t)==0xd401 && errno==EBUSY);
    assert(state_count(F1_STACK_QUARANTINED)==4 && state_count(F1_STACK_IDLE)==12);
    close_failure=0;assert(!recover(&t));
    t.tls_array=(void **)0x1234;
    assert(__wrap_threadClose(&t)==0xd401 && state_count(F1_STACK_QUARANTINED)==5);
    puts("PASS: failed map/rolled-back creation safely recycle; failed rollback, query failure, split borrowed pages, failed close and live-thread close quarantine backing");

    reset();wine_nx_f1_native_stacks_init();
    /* libnx pthread create calls threadClose if core mask or threadStart fails;
     * close before any thread runs must return the reserved block too. */
    assert(!recover(&t) && !t.tls_array);
    assert(!__wrap_threadClose(&t) && state_count(F1_STACK_IDLE)==16);
    pthread_t workers[8];
    for(unsigned i=0;i<8;i++)assert(!pthread_create(&workers[i],NULL,worker,NULL));
    for(unsigned i=0;i<8;i++)assert(!pthread_join(workers[i],NULL));
    assert(f1_native_stack_recovered==2001 && state_count(F1_STACK_IDLE)==16 && !f1_native_stack_exhausted);
    puts("PASS: start-failure cleanup and 2,000 concurrent create/close cycles do not reuse an active stack or allocate reserve backing on the failing path");
    reset();
    return 0;
}
