/* ASan/UBSan ownership test for the exact production arena header. */
#include <assert.h>
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <sched.h>
#include "f1_gpu_arena.h"
static struct f1_gpu_arena arena;
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static void *take(size_t a,size_t n){pthread_mutex_lock(&lock);void *p=f1_gpu_arena_take(&arena,a,n);pthread_mutex_unlock(&lock);return p;}
static int put(void *p){pthread_mutex_lock(&lock);int r=f1_gpu_arena_put(&arena,p);pthread_mutex_unlock(&lock);return r;}
static void *worker(void *arg){
    unsigned char tag=(uintptr_t)arg;
    for(unsigned j=0;j<128;j++){
        size_t n=(1+(j+tag)%8)*F1_GPU_UNIT;
        unsigned char *p=take(1u<<(16+j%4),n);assert(p);
        memset(p,tag,n);sched_yield();
        for(size_t i=0;i<n;i+=4096)assert(p[i]==tag);
        assert(p[n-1]==tag && put(p)==1);
    }
    return NULL;
}
int main(void){
    const size_t size=F1_GPU_ARENA_BYTES;
    void *base=aligned_alloc(F1_GPU_UNIT,size);assert(base);
    assert(!f1_gpu_arena_setup(&arena,(char *)base+1,size));
    assert(f1_gpu_arena_setup(&arena,base,size));assert(!f1_gpu_arena_setup(&arena,base,size));
    assert(!take(3,1)&&!take(65536,SIZE_MAX)&&!take(SIZE_MAX,65536)&&!take(65536,0));
    void *p=take(65536,393216);assert(p);
    memset(p,0xa5,393216);
    assert(put((char *)p+65536)==-1 && put((char *)p+1)==-1);
    assert(arena.used==6 && arena.live==1 && ((unsigned char *)p)[393215]==0xa5);
    assert(put(p)==1 && put(p)==-1);
    int ordinary;assert(put(&ordinary)==0 && put(NULL)==0);
    p=take(2u*1024*1024,393217);assert(p && !((uintptr_t)p%(2u*1024*1024)));
    assert(arena.used==7 && put(p)==1);
    p=take(65536,size);assert(p==base && !take(65536,1));
    assert(put(p)==1 && f1_gpu_arena_largest(&arena)==size);
    pthread_t threads[8];
    for(uintptr_t i=0;i<8;i++)assert(!pthread_create(threads+i,NULL,worker,(void *)(i+1)));
    for(unsigned i=0;i<8;i++)assert(!pthread_join(threads[i],NULL));
    assert(!arena.live && !arena.used && f1_gpu_arena_largest(&arena)==size);
    assert(arena.takes==arena.returned && arena.bad_frees==3);
    free(base);
    puts("PASS: exact GPU arena header: 384-KiB allocation, large alignments, coalescing, exhaustion, invalid free containment and 1024 concurrent lifetime cycles with live contents intact");
}
