#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include "sd_gpu_pressure.h"
#define M (1024u*1024u)
#define U 65536u
static struct f1_gpu_arena a;
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static void *take(size_t align,size_t n,int *emergency) {
    pthread_mutex_lock(&lock);void *p=sd_gpu_pressure_take(&a,align,n,emergency);
    pthread_mutex_unlock(&lock);return p;
}
static void put(void *p){pthread_mutex_lock(&lock);assert(f1_gpu_arena_put(&a,p)==1);pthread_mutex_unlock(&lock);}
static void *worker(void *arg){
    unsigned char tag=(uintptr_t)arg;
    for(unsigned i=0;i<128;i++){
        int emergency;size_t size=(i&1)?196608:U;
        unsigned char *p=take(U,size,&emergency);assert(p);
        memset(p,tag,size);sched_yield();
        for(size_t j=0;j<size;j+=4096)assert(p[j]==tag);
        assert(p[size-1]==tag);put(p);
    }
    return NULL;
}
int main(void){
    void *base=aligned_alloc(U,256*M);assert(base&&f1_gpu_arena_setup(&a,base,256*M));
    void *general[96],*large[6];
    for(unsigned i=0;i<96;i++){
        general[i]=sd_gpu_stream_take(&a,U,2*M,0);assert(general[i]);
        memset(general[i],i+1,2*M);
    }
    size_t sizes[]={9*M,16*M,5*M,16*M,50*U,238*U};
    for(unsigned i=0;i<6;i++){
        large[i]=sd_gpu_stream_take(&a,U,sizes[i],0);assert(large[i]);
        memset(large[i],i+101,sizes[i]);
    }
    assert(a.used*U==256*M);
    for(unsigned i=0;i<6;i+=2)put(large[i]);
    assert(a.used*U==250478592&&f1_gpu_arena_largest(&a)==9*M);
    /* Same occupancy/free/largest values as the failing hardware snapshot.
     * The exact hardware arrangement of holes is unknown. */
    for(size_t size=U;size<=2*M;size*=2)assert(!sd_gpu_stream_take(&a,U,size,1));
    assert(!sd_gpu_stream_take(&a,U,196608,1));
    for(unsigned i=0;i<128;i++){
        int emergency=0;void *p=take(U,196608,&emergency);assert(p&&emergency);
        assert(f1_gpu_arena_largest(&a)==9*M); /* use a smaller hole first */
        memset(p,0xa5,196608);put(p);
    }
    pthread_t threads[8];
    for(uintptr_t i=0;i<8;i++)assert(!pthread_create(threads+i,NULL,worker,(void *)(i+1)));
    for(unsigned i=0;i<8;i++)assert(!pthread_join(threads[i],NULL));
    /* Real exhaustion: consume every free unit, without touching live data. */
    void *loans[274];int emergency;
    for(unsigned i=0;i<274;i++){loans[i]=take(U,U,&emergency);assert(loans[i]);}
    assert(!take(U,U,&emergency)&&!emergency&&a.used*U==256*M);
    assert(!take(0,1,&emergency)&&!take(3,1,&emergency)&&!take(U,SIZE_MAX,&emergency));
    for(unsigned i=0;i<274;i++)put(loans[i]);
    for(unsigned i=1;i<6;i+=2){assert(((unsigned char*)large[i])[sizes[i]-1]==i+101);put(large[i]);}
    for(unsigned i=0;i<96;i++){assert(((unsigned char*)general[i])[2*M-1]==i+1);put(general[i]);}
    assert(!a.used&&!a.live);
    /* A request crossing the preferred 192/64 boundary can use free memory. */
    void *p=take(U,256*M,&emergency);assert(p==base&&emergency);put(p);
    for(size_t align=U;align<=16*M;align*=2){p=take(align,5*M,&emergency);assert(p&&!((uintptr_t)p%align));put(p);}
    /* Under less pressure the original guarded preference remains active. */
    p=take(U,2*M,&emergency);assert(p&&!emergency);put(p);
    struct f1_gpu_arena legacy={0};assert(f1_gpu_arena_setup(&legacy,base,128*M));
    assert(!sd_gpu_pressure_take(&legacy,U,U,&emergency)&&!emergency);
    free(base);puts("PASS: old guard starvation reproduced; 192 KiB recovered, smallest-hole reuse, full exhaustion, 1024 concurrent lifetimes, alignment and legacy fallback");
}
