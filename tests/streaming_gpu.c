#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include "sd_gpu_stream.h"
#define M (1024u*1024u)
static struct f1_gpu_arena arena;
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static void *take(size_t a,size_t n,int pressure){pthread_mutex_lock(&lock);void *p=sd_gpu_stream_take(&arena,a,n,pressure);pthread_mutex_unlock(&lock);return p;}
static void put(void *p){pthread_mutex_lock(&lock);assert(f1_gpu_arena_put(&arena,p)==1);pthread_mutex_unlock(&lock);}
static void *worker(void *arg){
    unsigned char tag=(uintptr_t)arg;
    for(unsigned i=0;i<128;i++){
        size_t bytes=(i&1)?5*M:65536;
        unsigned char *p=take(65536,bytes,0);assert(p);
        memset(p,tag,bytes);sched_yield();
        for(size_t j=0;j<bytes;j+=4096)assert(p[j]==tag);
        assert(p[bytes-1]==tag);put(p);
    }
    return NULL;
}
int main(void){
    void *base=aligned_alloc(65536,256*M);assert(base);
    assert(f1_gpu_arena_setup(&arena,base,256*M));
    void *small[96],*large[12],*loans[24];
    for(unsigned i=0;i<96;i++){
        small[i]=take(65536,2*M,0);assert(small[i]);
        assert((char *)small[i]+2*M<=(char *)base+192*M);
        memset(small[i],i,2*M);
    }
    assert(!take(65536,1,0));
    for(unsigned i=0;i<12;i++){
        large[i]=take(65536,5*M,0);assert(large[i]);
        assert((char *)large[i]>=(char *)base+192*M);
    }
    assert(!take(65536,5*M,0));
    assert(!take(65536,2*M,1)); /* live large buffers cannot be displaced */
    for(unsigned i=0;i<12;i++)put(large[i]);
    for(unsigned i=0;i<24;i++){loans[i]=take(65536,2*M,1);assert(loans[i]);}
    assert(!take(65536,65536,1)); /* keep the final contiguous 16 MiB */
    for(unsigned i=0;i<3;i++){large[i]=take(65536,5*M,0);assert(large[i]);}
    assert(!take(65536,5*M,0));
    for(unsigned i=0;i<3;i++)put(large[i]);
    for(unsigned i=0;i<24;i++)put(loans[i]);
    for(unsigned i=0;i<96;i++){
        assert(((unsigned char *)small[i])[2*M-1]==i);put(small[i]);
    }
    assert(!arena.live&&!arena.used&&f1_gpu_arena_largest(&arena)==256*M);
    for(size_t a=65536;a<=16*M;a*=2){
        void *p=take(a,5*M,0);assert(p&&!((uintptr_t)p%a));
        assert(f1_gpu_arena_put(&arena,(char *)p+65536)==-1);put(p);
    }
    assert(!take(0,1,0)&&!take(3,1,0)&&!take(65536,SIZE_MAX,0));
    pthread_t t[8];for(uintptr_t i=0;i<8;i++)assert(!pthread_create(t+i,NULL,worker,(void *)(i+1)));
    for(unsigned i=0;i<8;i++)assert(!pthread_join(t[i],NULL));
    assert(!arena.live&&!arena.used);
    struct f1_gpu_arena legacy={0};assert(f1_gpu_arena_setup(&legacy,base,128*M));
    assert(sd_gpu_stream_take(&legacy,65536,128*M,0)==base);
    assert(f1_gpu_arena_put(&legacy,base)==1&&!sd_gpu_stream_take(&legacy,65536,1,1));
    free(base);puts("PASS: size segregation, bounded borrowing, full-size 5 MiB slices, alignment, invalid frees, old pool fallback and 1024 concurrent lifetimes");
}
