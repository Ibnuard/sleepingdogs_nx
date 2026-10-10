/* SPDX-License-Identifier: MIT. Paired loader/native GPU backing budget. */
#ifndef SD_GPU_BUDGET_H
#define SD_GPU_BUDGET_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define SD_GPU_LOADER_INFO "sphaira 3.0.0; sleepingdogs-gpu-budget-v1 reserve=32MiB"
#define SD_GPU_MIB ((size_t)1024 * 1024)
#define SD_GPU_LEGACY_BYTES (128 * SD_GPU_MIB)
#define SD_GPU_PAIRED_BYTES (256 * SD_GPU_MIB)
#define SD_GPU_MIN_HEAP_BYTES (1952 * SD_GPU_MIB)

/* The pinned forwarder supplies the extra 64 MiB only in a full application
 * with at least 2 GiB quota. Smaller/unknown environments retain its 96 MiB
 * reserve. Keep at least 32 MiB outside the heap, plus its existing rounding
 * and 2 MiB allowance. No memory limit, NRO mapping or guest alias is changed. */
static inline uint64_t sd_loader_reserve_bytes(uint64_t total)
{
    return total >= UINT64_C(2147483648) ? 32 * SD_GPU_MIB : 96 * SD_GPU_MIB;
}

/* Check both the loader's exact versioned contract and the actual heap. A
 * partial update must never take the larger pool from the old CPU budget. */
static inline size_t sd_gpu_budget_bytes(size_t heap, const char *info, size_t length)
{
    if (heap >= SD_GPU_MIN_HEAP_BYTES && info &&
        length == sizeof(SD_GPU_LOADER_INFO) &&
        !memcmp(info, SD_GPU_LOADER_INFO, sizeof(SD_GPU_LOADER_INFO)))
        return SD_GPU_PAIRED_BYTES;
    return SD_GPU_LEGACY_BYTES;
}
#endif
