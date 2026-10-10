/* SPDX-License-Identifier: MIT. GPU backing suballocation in an ordinary
 * heap allocation. Caller holds the arena lock. No aliases or mapped pages.
 * Metadata is outside the backing: NvMap can change page cache attributes. */
#ifndef F1_GPU_ARENA_H
#define F1_GPU_ARENA_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define F1_GPU_UNIT (64u * 1024u)
#define F1_GPU_ARENA_BYTES (640u * 1024u * 1024u)
#define F1_GPU_UNITS (F1_GPU_ARENA_BYTES / F1_GPU_UNIT)
struct f1_gpu_arena {
    uintptr_t base;
    uint32_t units, used, peak, live;
    uint64_t takes, misses, returned, bad_frees;
    /* 0 = free, UINT16_MAX = interior, otherwise allocation length in units. */
    uint16_t run[F1_GPU_UNITS];
};
static int f1_gpu_arena_setup(struct f1_gpu_arena *a, void *base, size_t bytes)
{
    if (a->base || !base || (uintptr_t)base % F1_GPU_UNIT || !bytes ||
        bytes % F1_GPU_UNIT || bytes > F1_GPU_ARENA_BYTES ||
        (uintptr_t)base > UINTPTR_MAX - bytes) return 0;
    a->base=(uintptr_t)base; a->units=bytes/F1_GPU_UNIT;
    return 1;
}
static void *f1_gpu_arena_take(struct f1_gpu_arena *a, size_t alignment, size_t bytes)
{
    if (!a->base || !bytes || !alignment || (alignment & (alignment-1)) ||
        bytes > F1_GPU_ARENA_BYTES || alignment > F1_GPU_ARENA_BYTES) return NULL;
    uint32_t need=(bytes+F1_GPU_UNIT-1)/F1_GPU_UNIT;
    if (alignment<F1_GPU_UNIT) alignment=F1_GPU_UNIT;
    uint32_t best=UINT32_MAX, best_span=UINT32_MAX;
    for (uint32_t i=0;i<a->units;) {
        if (a->run[i]) { i+=a->run[i]==UINT16_MAX?1:a->run[i]; continue; }
        uint32_t start=i;
        while(i<a->units && !a->run[i]) ++i;
        uintptr_t address=a->base+(size_t)start*F1_GPU_UNIT;
        if(address>UINTPTR_MAX-(alignment-1))continue;
        uintptr_t aligned=(address+alignment-1)&~(uintptr_t)(alignment-1);
        size_t first=(aligned-a->base)/F1_GPU_UNIT;
        if(first<=i && need<=i-first && i-start<best_span) {
            best=(uint32_t)first; best_span=i-start;
            if(best_span==need)break;
        }
    }
    if(best==UINT32_MAX){++a->misses;return NULL;}
    a->run[best]=(uint16_t)need;
    for(uint32_t i=1;i<need;i++)a->run[best+i]=UINT16_MAX;
    a->used+=need;if(a->used>a->peak)a->peak=a->used;
    ++a->live;++a->takes;
    return (void *)(a->base+(size_t)best*F1_GPU_UNIT);
}
/* 0 = ordinary heap pointer; 1 = returned to arena; -1 = invalid arena free. */
static int f1_gpu_arena_put(struct f1_gpu_arena *a, void *p)
{
    uintptr_t address=(uintptr_t)p;
    if(!a->base || address<a->base || address-a->base>=(size_t)a->units*F1_GPU_UNIT)return 0;
    size_t offset=address-a->base;
    uint32_t at=offset/F1_GPU_UNIT, length=a->run[at];
    if(offset%F1_GPU_UNIT || !length || length==UINT16_MAX || length>a->units-at){++a->bad_frees;return -1;}
    memset(a->run+at,0,length*sizeof(a->run[0]));
    a->used-=length;--a->live;++a->returned;
    return 1;
}
static size_t f1_gpu_arena_largest(const struct f1_gpu_arena *a)
{
    uint32_t run=0,best=0;
    for(uint32_t i=0;i<a->units;i++) {
        if(a->run[i])run=0;
        else if(++run>best)best=run;
    }
    return (size_t)best*F1_GPU_UNIT;
}
#endif
