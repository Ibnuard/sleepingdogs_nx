/* Exercise the exact generated loader calculation and shared native policy. */
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "sd_gpu_budget.h"
typedef uint64_t u64;
#define InfoType_TotalMemorySize 6
#define InfoType_UsedMemorySize 7
#define CUR_PROCESS_HANDLE 0xffff8001u
static u64 total, used;
static unsigned svcGetInfo(u64 *out, unsigned type, unsigned handle, u64 subtype)
{
    assert(handle == CUR_PROCESS_HANDLE && subtype == 0);
    assert(type == InfoType_TotalMemorySize || type == InfoType_UsedMemorySize);
    *out = type == InfoType_TotalMemorySize ? total : used;
    return 0;
}
#include "loader_calculations.h"

int main(void)
{
    const u64 MiB = 1048576;
    for (unsigned n = 0; n < 512; n++) {
        total = 2048 * MiB; used = (4 + n) * MiB + n * 4096;
        u64 old = baselineMaxHeapSize(), now = calculateMaxHeapSize();
        assert(now - old == 64 * MiB);
        assert(now % (2 * MiB) == 0 && total - used - now >= 34 * MiB);
    }
    for (unsigned n = 128; n < 2048; n += 16) {
        total = n * MiB; used = 8 * MiB;
        assert(baselineMaxHeapSize() == calculateMaxHeapSize());
    }
    size_t cap = 2002944000u;
    const char info[] = SD_GPU_LOADER_INFO;
    assert(sd_gpu_budget_bytes(cap, info, sizeof(info)) == 128 * MiB);
    assert(sd_gpu_budget_bytes(cap + 64 * MiB, info, sizeof(info)) == 256 * MiB);
    assert(sd_gpu_budget_bytes(cap + 64 * MiB, NULL, 0) == 128 * MiB);
    const char old[] = "sphaira 3.0.0";
    assert(sd_gpu_budget_bytes(cap + 64 * MiB, old, sizeof(old)) == 128 * MiB);
    for (size_t n = 0; n < sizeof(info); n++) {
        char short_info[sizeof(info)]; memcpy(short_info, info, sizeof(info));
        assert(sd_gpu_budget_bytes(cap + 64 * MiB, short_info, n) == 128 * MiB);
        short_info[n] ^= 1;
        assert(sd_gpu_budget_bytes(cap + 64 * MiB, short_info, sizeof(info)) == 128 * MiB);
    }
    assert(sd_gpu_budget_bytes(cap + 64 * MiB, info, SIZE_MAX) == 128 * MiB);
    puts("PASS: 512 full-quota loader cases add exactly 64 MiB and retain >=34 MiB outside heap; smaller quotas unchanged");
    puts("PASS: old/absent/malformed loader and short heap retain 128 MiB; verified pair selects 256 MiB");
}
