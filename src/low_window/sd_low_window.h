/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef SD_LOW_WINDOW_H
#define SD_LOW_WINDOW_H
#include <stdint.h>
#include <stddef.h>
#define SD_GUEST_BASE UINT64_C(0x200000)
#define SD_NATIVE_BASE UINT64_C(0x100000000)
#define SD_HOST_LIMIT UINT64_C(0x8000000000)
#define SD_LOW_ARENA_BASE UINT64_C(0x30000000)
static inline int sd_is_low_window(uint64_t base, uint64_t size)
{
    return base == SD_GUEST_BASE && size == SD_HOST_LIMIT - base;
}
/* Run once, on the main thread before any guest view or arena is mapped. */
void sd_low_window_init(void);
int sd_low_window_ready(void);
int sd_launch_memory_prepare(char *error, size_t error_size);
#endif
