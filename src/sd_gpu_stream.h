/* SPDX-License-Identifier: MIT. Size-segregated ordinary GPU heap backing.
 * Caller holds f1_gpu_arena_lock. Allocation heads retain the original arena
 * metadata/free ABI. No live object, NvMap or guest pointer is ever moved. */
#ifndef SD_GPU_STREAM_H
#define SD_GPU_STREAM_H
#include "f1_gpu_arena.h"
#define SD_GPU_STREAM_THRESHOLD (2u * 1024u * 1024u)
#define SD_GPU_STREAM_RESERVE (64u * 1024u * 1024u)
#define SD_GPU_STREAM_GUARD (16u * 1024u * 1024u)

static uint32_t sd_gpu_stream_largest(const struct f1_gpu_arena *a,
                                    uint32_t first, uint32_t end,
                                    uint32_t exclude, uint32_t count)
{
    uint32_t run=0, best=0;
    for(uint32_t i=first;i<end;++i) {
        if(a->run[i] || (i>=exclude && i-exclude<count))run=0;
        else if(++run>best)best=run;
    }
    return best;
}

static void *sd_gpu_stream_region(struct f1_gpu_arena *a, size_t alignment,
                                 size_t bytes, uint32_t first, uint32_t end,
                                 int reverse, uint32_t guard)
{
    if(!a->base || !bytes || !alignment || (alignment&(alignment-1)) ||
       bytes>F1_GPU_ARENA_BYTES || alignment>F1_GPU_ARENA_BYTES ||
       first>=end || end>a->units)return NULL;
    uint32_t need=(bytes+F1_GPU_UNIT-1)/F1_GPU_UNIT;
    if(alignment<F1_GPU_UNIT)alignment=F1_GPU_UNIT;
    uint32_t best=UINT32_MAX,best_span=UINT32_MAX;
    for(uint32_t i=first;i<end;) {
        if(a->run[i]){++i;continue;}
        uint32_t start=i;
        while(i<end && !a->run[i])++i;
        uint32_t span=i-start;
        if(need>span)continue;
        uintptr_t address=a->base+(size_t)start*F1_GPU_UNIT,aligned;
        if(reverse) {
            uintptr_t last=a->base+(size_t)(i-need)*F1_GPU_UNIT;
            aligned=last&~(uintptr_t)(alignment-1);
        } else {
            if(address>UINTPTR_MAX-(alignment-1))continue;
            aligned=(address+alignment-1)&~(uintptr_t)(alignment-1);
        }
        if(aligned<address)continue;
        size_t at=(aligned-a->base)/F1_GPU_UNIT;
        if(at>i || need>i-at)continue;
        if(guard && sd_gpu_stream_largest(a,first,end,(uint32_t)at,need)<guard)continue;
        if(span<best_span || (reverse && span==best_span && at>best)) {
            best=(uint32_t)at;best_span=span;
        }
    }
    if(best==UINT32_MAX)return NULL;
    a->run[best]=(uint16_t)need;
    for(uint32_t i=1;i<need;++i)a->run[best+i]=UINT16_MAX;
    a->used+=need;if(a->used>a->peak)a->peak=a->used;
    ++a->live;++a->takes;
    return (void *)(a->base+(size_t)best*F1_GPU_UNIT);
}

/* Full paired pool: 192 MiB general + 64 MiB for >2 MiB resources.
 * Small requests first use general GPU backing and ordinary newlib. Only
 * after BOTH fail may they borrow the upper area, retaining a contiguous
 * 16 MiB run. Large requests may also overflow into the general area. */
static void *sd_gpu_stream_take(struct f1_gpu_arena *a, size_t alignment,
                               size_t bytes, int pressure)
{
    if((size_t)a->units*F1_GPU_UNIT<256u*1024u*1024u)
        return pressure?NULL:f1_gpu_arena_take(a,alignment,bytes);
    uint32_t split=a->units-SD_GPU_STREAM_RESERVE/F1_GPU_UNIT;
    void *result=NULL;
    if(pressure) {
        if(bytes && bytes<=SD_GPU_STREAM_THRESHOLD)
            result=sd_gpu_stream_region(a,alignment,bytes,split,a->units,1,
                                       SD_GPU_STREAM_GUARD/F1_GPU_UNIT);
        return result;
    }
    if(bytes>SD_GPU_STREAM_THRESHOLD)
        result=sd_gpu_stream_region(a,alignment,bytes,split,a->units,1,0);
    if(!result)result=sd_gpu_stream_region(a,alignment,bytes,0,split,0,0);
    if(!result)++a->misses;
    return result;
}
#endif
