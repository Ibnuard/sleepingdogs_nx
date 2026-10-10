#define _GNU_SOURCE
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <malloc.h>
#include <string.h>
#include <errno.h>
static _Thread_local unsigned failures, page_fail, page_allocs, page_frees, libc_calls;
static _Thread_local struct { void *p; size_t n; } pages[64];
static void wine_nx_runtime_trace(const char *s) { assert(strstr(s,"[SD-SHADER-CACHE]")); }
#include "sd_shader_cache.c"
static void *try_alloc(size_t n,size_t a) {
    ++libc_calls;if(failures){--failures;return NULL;}
    void *p=NULL;if(posix_memalign(&p,a<sizeof(void*)?sizeof(void*):a,n))return NULL;return p;
}
static void *try_realloc(void *p,size_t n) {
    ++libc_calls;if(failures){--failures;return NULL;}return realloc(p,n);
}
static void *try_malloc(size_t n) { return try_alloc(n,16); }
void *pes13_cpu_pages_allocate(size_t n,size_t a) {
    if(page_fail)return NULL;
    for(unsigned i=0;i<64;i++)if(!pages[i].p){
        void *p=NULL;if(posix_memalign(&p,a<sizeof(void*)?sizeof(void*):a,n))return NULL;
        pages[i].p=p;pages[i].n=n;++page_allocs;return p;
    }
    assert(0);return NULL;
}
int pes13_cpu_pages_owned(void *p) { for(unsigned i=0;i<64;i++)if(p&&pages[i].p==p)return 1;return 0; }
size_t pes13_cpu_pages_size(void *p) { for(unsigned i=0;i<64;i++)if(p&&pages[i].p==p)return pages[i].n;assert(0);return 0; }
int pes13_cpu_pages_release(void *p) {
    for(unsigned i=0;i<64;i++)if(p&&pages[i].p==p){free(p);pages[i].p=NULL;++page_frees;return 1;}return 0;
}
size_t wine_nx_release_idle_backing_pages(void) { return 0; }
void wine_nx_crash_rust_allocation(unsigned a,size_t b,size_t c,size_t d,uintptr_t e) { (void)a;(void)b;(void)c;(void)d;(void)e; }
#include "native_heap/fextendo_rust_symbols.h"
void *fx_rust_real_alloc(size_t n,size_t a) { return try_alloc(n,a); }
void *fx_rust_real_alloc_zeroed(size_t n,size_t a) { void *p=try_alloc(n,a);if(p)memset(p,0,n);return p; }
void fx_rust_real_dealloc(void *p,size_t n,size_t a) { (void)n;(void)a;free(p); }
void *fx_rust_real_realloc(void *old,size_t old_n,size_t a,size_t n) {
    if(a<=16)return try_realloc(old,n);
    void *p=try_alloc(n,a);if(p){memcpy(p,old,n<old_n?n:old_n);free(old);}return p;
}
#include "native_heap/fextendo_rust_heap.h"
#define malloc try_malloc
#define realloc try_realloc
#include "native_heap/fextendo_mesa_heap.h"
#undef malloc
#undef realloc

static void bounds(void) {
    size_t bytes=0,large=0;unsigned counts[BIN_COUNT]={0};uint64_t bits=0;
    for(unsigned i=0;i<CLASS_COUNT;i++){
        if(cache.bins[i])bits|=UINT64_C(1)<<i;
        for(struct cached_block *p=cache.bins[i];p;p=p->next){
            unsigned b=size_bin(p->usable);assert(size_class(p->usable)==i);
            bytes+=p->usable+sizeof(size_t);if(b>=SMALL_BIN_COUNT)large+=p->usable+sizeof(size_t);
            assert(++counts[b]<=(b<SMALL_BIN_COUNT?SMALL_BIN_LIMIT:BIN_LIMIT));
        }
    }
    assert(bits==cache.nonempty&&bytes==cache.bytes&&large==cache.large_bytes);
    assert(bytes<=CACHE_LIMIT&&large<=LARGE_LIMIT);
    for(unsigned i=0;i<BIN_COUNT;i++)assert(counts[i]==cache.counts[i]);
}
static void basic(void) {
    sd_shader_cache_begin();assert(!sd_shader_cache_active);sd_shader_cache_end();
    sd_shader_cache_enabled=1;sd_shader_cache_begin();assert(sd_shader_cache_active);
    unsigned char *p=pes13_mesa_malloc(128);assert(p);memset(p,77,128);pes13_mesa_free(p);
    unsigned calls=libc_calls;
    unsigned char *q=pes13_rust_alloc_zeroed(128,16);assert(q==p&&libc_calls==calls);
    for(unsigned i=0;i<128;i++)assert(!q[i]);
    sd_shader_cache_begin();sd_shader_cache_end();assert(sd_shader_cache_active);
    memset(q,37,128);sd_shader_cache_end();assert(!sd_shader_cache_active&&!cache.bytes);
    for(unsigned i=0;i<128;i++)assert(q[i]==37);pes13_rust_dealloc(q,128,16);
    sd_shader_cache_begin();
    for(size_t a=16;a<=256;a*=2){
        p=pes13_rust_alloc(4096,a);assert(p&&!((uintptr_t)p&(a-1)));pes13_rust_dealloc(p,4096,a);
        q=pes13_rust_alloc(4000,a);assert(q==p&&!((uintptr_t)q&(a-1)));pes13_rust_dealloc(q,4000,a);
    }
    assert(!sd_shader_cache_take(0,16)&&!sd_shader_cache_take(65537,16));
    assert(!sd_shader_cache_take(128,3)&&!sd_shader_cache_take(128,512));
    assert(!sd_shader_cache_put(NULL,128));
    for(size_t n=1;n<=BLOCK_LIMIT;n++)assert(size_class(n)<CLASS_COUNT&&size_class(n)>=size_class(n-1));
    p=pes13_mesa_malloc(128);memset(p,21,128);q=pes13_mesa_malloc(8192);pes13_mesa_free(q);
    assert(pes13_mesa_realloc(p,8192)==q);for(unsigned i=0;i<128;i++)assert(q[i]==21);
    assert(pes13_mesa_realloc(q,8100)==q);assert(!pes13_mesa_realloc(q,0));
    bounds();errno=EIO;sd_shader_cache_end();assert(errno==EIO&&!cache.bytes);
    sd_shader_cache_end();assert(!cache.depth); /* unbalanced cleanup is harmless */
}
static void pressure(void) {
    sd_shader_cache_begin();
    unsigned char *p=pes13_rust_alloc(128,16);memset(p,42,128);pes13_rust_dealloc(p,128,16);
    assert(cache.bytes);failures=1;p=pes13_rust_alloc(100000,16);assert(p&&!failures&&!cache.bytes);pes13_rust_dealloc(p,100000,16);
    p=pes13_mesa_malloc(128);memset(p,71,128);void *q=pes13_mesa_malloc(4096);pes13_mesa_free(q);
    failures=2;page_fail=1;assert(!pes13_mesa_realloc(p,1000000));
    for(unsigned i=0;i<128;i++)assert(p[i]==71);assert(!cache.bytes);page_fail=0;pes13_mesa_free(p);
    sd_shader_cache_trim();failures=1;p=pes13_mesa_malloc(2048);assert(pes13_cpu_pages_owned(p));
    memset(p,19,2048);q=pes13_mesa_realloc(p,4096);assert(q&&!pes13_cpu_pages_owned(q));
    for(unsigned i=0;i<2048;i++)assert(((unsigned char*)q)[i]==19);pes13_mesa_free(q);
    sd_shader_cache_trim();failures=1;p=pes13_rust_alloc_zeroed(4096,64);assert(pes13_cpu_pages_owned(p));
    for(unsigned i=0;i<4096;i++)assert(!p[i]);
    q=pes13_rust_realloc(p,4096,64,8192);assert(q&&!pes13_cpu_pages_owned(q));pes13_rust_dealloc(q,8192,64);
    sd_shader_cache_trim();p=pes13_rust_alloc(128,64);memset(p,11,128);
    q=pes13_rust_alloc(4096,64);pes13_rust_dealloc(q,4096,64);
    failures=2;page_fail=1;assert(!pes13_rust_realloc(p,128,64,1000000));
    for(unsigned i=0;i<128;i++)assert(p[i]==11);page_fail=0;pes13_rust_dealloc(p,128,64);
    sd_shader_cache_end();assert(!cache.bytes&&page_allocs==page_frees);
}
static void limits(void) {
    void *items[2048];sd_shader_cache_begin();
    for(unsigned i=0;i<2048;i++)items[i]=pes13_mesa_malloc(i<1024?768:256);
    for(unsigned i=0;i<2048;i++){pes13_mesa_free(items[i]);bounds();}
    assert(cache.bytes>CACHE_LIMIT-1024);sd_shader_cache_end();
    sd_shader_cache_begin();for(unsigned i=0;i<256;i++)items[i]=pes13_mesa_malloc(32768);
    for(unsigned i=0;i<256;i++){pes13_mesa_free(items[i]);bounds();}
    assert(cache.large_bytes>LARGE_LIMIT/2);sd_shader_cache_end();
}
static void *stress(void *arg) {
    unsigned seed=(uintptr_t)arg+17;unsigned char *p[32]={0};size_t sizes[32]={0},aligns[32]={0};
    for(unsigned n=0;n<12000;n++){
        if(!(n%400))sd_shader_cache_begin();
        seed=seed*1664525+1013904223;unsigned i=(seed>>16)%32;
        if(p[i]){
            for(size_t k=0;k<sizes[i];k++)assert(p[i][k]==(unsigned char)i);
            if(seed%3){pes13_rust_dealloc(p[i],sizes[i],aligns[i]);p[i]=NULL;}
            else {size_t len=1+(seed>>7)%80000;p[i]=pes13_rust_realloc(p[i],sizes[i],aligns[i],len);assert(p[i]);
                for(size_t k=0;k<len&&k<sizes[i];k++)assert(p[i][k]==(unsigned char)i);
                sizes[i]=len;memset(p[i],i,len);}
        }else{sizes[i]=1+(seed>>8)%80000;aligns[i]=(size_t)16<<((seed>>4)%6);
            p[i]=pes13_rust_alloc(sizes[i],aligns[i]);assert(p[i]&&!((uintptr_t)p[i]&(aligns[i]-1)));memset(p[i],i,sizes[i]);}
        if(n%400==399){bounds();sd_shader_cache_end();assert(!cache.bytes);}
    }
    for(unsigned i=0;i<32;i++)if(p[i])pes13_rust_dealloc(p[i],sizes[i],aligns[i]);return NULL;
}
static pthread_barrier_t barrier;
static unsigned enabled_workers;
static void *worker_limit(void *arg) {
    (void)arg;sd_shader_cache_begin();if(sd_shader_cache_active)__atomic_add_fetch(&enabled_workers,1,__ATOMIC_RELAXED);
    pthread_barrier_wait(&barrier);pthread_barrier_wait(&barrier);sd_shader_cache_end();return NULL;
}
static void *foreign_free(void *p) {sd_shader_cache_begin();pes13_mesa_free(p);assert(cache.bytes);sd_shader_cache_end();return NULL;}
int main(void) {
    basic();pressure();limits();pthread_t threads[16];
    void *p=pes13_mesa_malloc(1024);assert(!pthread_create(&threads[0],NULL,foreign_free,p));assert(!pthread_join(threads[0],NULL));
    for(uintptr_t i=0;i<4;i++)assert(!pthread_create(&threads[i],NULL,stress,(void*)i));
    for(unsigned i=0;i<4;i++)assert(!pthread_join(threads[i],NULL));
    assert(!pthread_barrier_init(&barrier,NULL,17));
    for(unsigned i=0;i<16;i++)assert(!pthread_create(&threads[i],NULL,worker_limit,NULL));
    pthread_barrier_wait(&barrier);assert(enabled_workers==8&&workers==8);pthread_barrier_wait(&barrier);
    for(unsigned i=0;i<16;i++)assert(!pthread_join(threads[i],NULL));
    pthread_barrier_destroy(&barrier);assert(!workers&&!cache.bytes&&!sd_shader_cache_active);
    sd_shader_cache_enabled=0;sd_shader_cache_begin();assert(!sd_shader_cache_active);
    p=pes13_mesa_malloc(256);pes13_mesa_free(p);assert(!cache.bytes);sd_shader_cache_end();sd_shader_cache_report();
    puts("PASS: cache reuse, alignment, zeroing, realloc failure/lifetime, memory pressure, page fallback, 1 MiB/8-worker bounds, cross-thread frees and 48000 concurrent allocation iterations");
}
