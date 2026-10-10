/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef SD_GUEST_ARENA_H
#define SD_GUEST_ARENA_H
#include <stddef.h>
#include <stdint.h>

#ifndef SD_GUEST_ARENA_BYTES
#define SD_GUEST_ARENA_BYTES ((size_t)1000 * 1024 * 1024)
#endif

/* One ordinary-heap allocation, retained until process exit. Wine owns its
 * view and serializes all access changes with virtual_mutex. It is never a
 * source for svcMapProcessCodeMemory, FEX scratch, or GPU allocations. */
void sd_guest_arena_init(void);
void *sd_guest_arena_base(void);
size_t sd_guest_arena_size(void);
int sd_guest_arena_overlaps(const void *base, size_t size);
int sd_guest_arena_contains(const void *base, size_t size);
int sd_guest_arena_protect(void *base, size_t size, int prot);
int sd_guest_arena_reset(void *base, size_t size, int prot);
#endif
