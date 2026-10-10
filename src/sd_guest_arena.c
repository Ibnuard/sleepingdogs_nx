/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Sleeping Dogs requests 1000 MiB of contiguous PAGE_READWRITE memory before
 * graphics starts. In a 32-bit no-alias process, duplicating that range outside
 * the 2 GiB kernel heap cannot reliably fit. Give it owned heap pages directly.
 * This saves virtual addresses, not physical RAM; the entire arena is charged
 * to the same fixed process heap. */
#include "sd_guest_arena.h"
#include <errno.h>
#include <malloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef SD_ARENA_HOST_TEST
#include "horizon_mman.h"
#include <switch.h>
#else
#include <sys/mman.h>
#endif

extern void wine_nx_runtime_trace(const char *);
static void *sd_arena_base;
static unsigned sd_arena_started;
/* Low two bits are kernel access; bit 2 means zero before the next commit.
 * Deferred zeroing keeps a failed decommit from changing live guest data. */
static unsigned char sd_arena_pages[SD_GUEST_ARENA_BYTES / 4096];

void *sd_guest_arena_base(void) { return sd_arena_base; }
size_t sd_guest_arena_size(void) { return sd_arena_base ? SD_GUEST_ARENA_BYTES : 0; }

int sd_guest_arena_contains(const void *base, size_t size)
{
    uintptr_t at = (uintptr_t)base, first = (uintptr_t)sd_arena_base;
    return first && size && at >= first && at - first < SD_GUEST_ARENA_BYTES &&
           size <= SD_GUEST_ARENA_BYTES - (at - first);
}

int sd_guest_arena_overlaps(const void *base, size_t size)
{
    uintptr_t at = (uintptr_t)base, first = (uintptr_t)sd_arena_base;
    if (!first || !size) return 0;
    if (at >= first) return at - first < SD_GUEST_ARENA_BYTES;
    return size > first - at;
}

static int sd_arena_permission(void *base, size_t size, int prot)
{
    unsigned permission;
    Result rc;
    if (prot == PROT_NONE) permission = Perm_None;
    else if (prot == PROT_READ) permission = Perm_R;
    else if (prot == (PROT_READ | PROT_WRITE)) permission = Perm_Rw;
    else { errno = EACCES; return -1; }
    rc = svcSetMemoryPermission(base, size, permission);
    if (R_FAILED(rc))
    {
        char message[192];
        snprintf(message, sizeof(message), "[SD-DIRECT] permission failed base=%p bytes=%zu prot=%d rc=%08x",
                 base, size, prot, rc);
        wine_nx_runtime_trace(message);
        errno = EACCES;
        return -1;
    }
    return 0;
}

int sd_guest_arena_protect(void *base, size_t size, int prot)
{
    size_t first, count, i;
    int clear = 0;
    if (!sd_guest_arena_contains(base, size) || ((uintptr_t)base & 4095) || (size & 4095))
    { errno = EINVAL; return -1; }
    if (prot != PROT_NONE && prot != PROT_READ && prot != (PROT_READ | PROT_WRITE))
    { errno = EACCES; return -1; }
    first = ((uintptr_t)base - (uintptr_t)sd_arena_base) / 4096;
    count = size / 4096;
    for (i = first; i < first + count; ++i) clear |= sd_arena_pages[i] & 4;
    if (prot != PROT_NONE && clear)
    {
        if (sd_arena_permission(base, size, PROT_READ | PROT_WRITE)) return -1;
        for (i = first; i < first + count;)
        {
            size_t begin = i;
            while (i < first + count && (sd_arena_pages[i] & 4)) ++i;
            if (i > begin) memset((char *)sd_arena_base + begin * 4096, 0, (i - begin) * 4096);
            else ++i;
        }
        if (prot != (PROT_READ | PROT_WRITE) && sd_arena_permission(base, size, prot))
        {
            /* Restore exactly the old access groups. A failed rollback must
             * stop rather than leave supposedly inaccessible pages writable. */
            for (i = first; i < first + count;)
            {
                size_t begin = i;
                int old = sd_arena_pages[i] & 3;
                while (i < first + count && (sd_arena_pages[i] & 3) == old) ++i;
                if (sd_arena_permission((char *)sd_arena_base + begin * 4096, (i - begin) * 4096, old))
                { wine_nx_runtime_trace("[SD-DIRECT] protection rollback failed; stopping"); abort(); }
            }
            return -1;
        }
    }
    else if (sd_arena_permission(base, size, prot)) return -1;
    for (i = first; i < first + count; ++i)
        sd_arena_pages[i] = prot | (prot == PROT_NONE ? sd_arena_pages[i] & 4 : 0);
    return 0;
}

int sd_guest_arena_reset(void *base, size_t size, int prot)
{
    size_t first, count;
    if (prot != PROT_NONE && prot != (PROT_READ | PROT_WRITE)) { errno = EACCES; return -1; }
    if (sd_guest_arena_protect(base, size, prot)) return -1;
    if (prot == PROT_NONE)
    {
        first = ((uintptr_t)base - (uintptr_t)sd_arena_base) / 4096;
        count = size / 4096;
        memset(sd_arena_pages + first, 4, count);
    }
    return 0;
}

void sd_guest_arena_init(void)
{
    void *base;
    char message[224];
    int saved_errno = errno;
    if (__atomic_exchange_n(&sd_arena_started, 1, __ATOMIC_ACQ_REL)) return;
    base = memalign(65536, SD_GUEST_ARENA_BYTES);
    if (base && ((uintptr_t)base >= UINT64_C(0x100000000) ||
                 SD_GUEST_ARENA_BYTES > UINT64_C(0x100000000) - (uintptr_t)base))
    { free(base); base = NULL; }
    if (base && sd_arena_permission(base, SD_GUEST_ARENA_BYTES, PROT_NONE))
    {
        /* A failed SVC leaves permissions unchanged. Do not publish an arena
         * unless the kernel enforces its idle/decommitted page protections. */
        free(base);
        base = NULL;
    }
    sd_arena_base = base;
    if (base) memset(sd_arena_pages, 4, sizeof(sd_arena_pages));
    snprintf(message, sizeof(message), "[SD-DIRECT] init requested=%zu reserved=%zu base=%p alias_bytes=0 source=ordinary-heap",
             SD_GUEST_ARENA_BYTES, sd_guest_arena_size(), base);
    wine_nx_runtime_trace(message);
    errno = saved_errno;
}
