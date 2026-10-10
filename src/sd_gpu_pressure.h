/* SPDX-License-Identifier: MIT. Last-resort reuse of idle GPU pool backing.
 * Caller holds f1_gpu_arena_lock and has exhausted ordinary newlib paths. */
#ifndef SD_GPU_PRESSURE_H
#define SD_GPU_PRESSURE_H
#include "sd_gpu_stream.h"

static void *sd_gpu_pressure_take(struct f1_gpu_arena *a, size_t alignment,
                                  size_t bytes, int *emergency)
{
    *emergency=0;
    void *p=sd_gpu_stream_take(a,alignment,bytes,1);
    if(p || (size_t)a->units*F1_GPU_UNIT<256u*1024u*1024u)return p;
    /* The preferred reserve must not turn an available allocation into OOM.
     * Search all free runs only after guarded borrowing and normal heap fail.
     * Best fit consumes the smallest fitting hole, including a free run that
     * crosses the preferred region boundary. Live metadata is never moved. */
    p=sd_gpu_stream_region(a,alignment,bytes,0,a->units,1,0);
    if(p)*emergency=1;
    return p;
}
#endif
