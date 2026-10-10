/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Allocation reuse adapted from Autorun/Wine-NX e7168c3f438a (2026).
 * FEXTendo changes: libc-compatible Mesa/Rust CPU allocations only, explicit
 * runtime switch, bounded thread-local counters, and drain via ordinary free.
 * The pinned Rust system allocator's malloc/free ABI is verified at build.
 */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sd_shader_cache.h"

enum { CACHE_LIMIT = 1048576, BLOCK_LIMIT = 65536, BIN_COUNT = 13,
       SMALL_BIN_COUNT = 6, SMALL_BIN_LIMIT = 1024, BIN_LIMIT = 64,
       LARGE_LIMIT = CACHE_LIMIT / 4, CLASS_COUNT = 61, SEARCH_LIMIT = 8,
       CLASS_SEARCH_LIMIT = 4, WORKER_LIMIT = 8 };
_Static_assert(CLASS_COUNT < 64, "cache class bitmap");
struct cached_block { struct cached_block *next; size_t usable; };
static __thread struct {
    struct cached_block *bins[CLASS_COUNT];
    uint64_t nonempty, hits, misses, puts;
    unsigned counts[BIN_COUNT], depth;
    size_t bytes, large_bytes, peak;
} cache;
int sd_shader_cache_enabled;
__thread unsigned sd_shader_cache_active;
static unsigned workers;
static uint64_t totals[5]; /* completed scopes, hits, misses, puts, peak bytes/worker */

static unsigned size_bin(size_t size)
{
    return size < 32 ? 0 : (unsigned)(8 * sizeof(unsigned long long) - 1 -
                                     __builtin_clzll(size)) - 4;
}
static unsigned size_class(size_t size)
{
    if (size < 512) return size >> 4;
    unsigned shift = size_bin(size) + 4;
    return 32 + (shift - 9) * 4 + ((size >> (shift - 2)) & 3);
}

void sd_shader_cache_begin(void)
{
    if (cache.depth++) return;
    if (!sd_shader_cache_enabled) return;
    unsigned count = __atomic_load_n(&workers, __ATOMIC_RELAXED);
    while (count < WORKER_LIMIT) {
        if (!__atomic_compare_exchange_n(&workers, &count, count + 1, 0,
                                         __ATOMIC_RELAXED, __ATOMIC_RELAXED)) continue;
        cache.hits = cache.misses = cache.puts = cache.peak = 0;
        sd_shader_cache_active = 1;
        return;
    }
}

void *sd_shader_cache_take(size_t size, size_t alignment)
{
    if (!sd_shader_cache_active || !size || size > BLOCK_LIMIT || !alignment ||
        (alignment & (alignment - 1)) || alignment > 256) return NULL;
    unsigned first = size_class(size), examined = 0;
    size_t limit = size < 64 ? size + 64 : size * 2;
    if (limit > BLOCK_LIMIT) limit = BLOCK_LIMIT;
    uint64_t candidates = cache.nonempty & (UINT64_MAX << first) &
                          ((UINT64_C(1) << (size_class(limit) + 1)) - 1);
    while (candidates && examined < SEARCH_LIMIT) {
        unsigned bin = __builtin_ctzll(candidates);
        candidates &= candidates - 1;
        struct cached_block **link = &cache.bins[bin];
        for (unsigned i = 0; *link && i < CLASS_SEARCH_LIMIT && examined < SEARCH_LIMIT;
             ++i, link = &(*link)->next) {
            struct cached_block *block = *link;
            ++examined;
            if (block->usable < size || block->usable > limit || ((uintptr_t)block & (alignment - 1))) continue;
            *link = block->next;
            if (!cache.bins[bin]) cache.nonempty &= ~(UINT64_C(1) << bin);
            unsigned group = size_bin(block->usable);
            --cache.counts[group];
            cache.bytes -= block->usable + sizeof(size_t);
            if (group >= SMALL_BIN_COUNT) cache.large_bytes -= block->usable + sizeof(size_t);
            ++cache.hits;
            return block;
        }
    }
    ++cache.misses;
    return NULL;
}

int sd_shader_cache_put(void *pointer, size_t usable)
{
    if (!sd_shader_cache_active || !pointer || usable < sizeof(struct cached_block) || usable > BLOCK_LIMIT)
        return 0;
    unsigned bin = size_bin(usable);
    if (bin >= SMALL_BIN_COUNT && cache.large_bytes > LARGE_LIMIT - usable - sizeof(size_t)) return 0;
    if (cache.bytes > CACHE_LIMIT - usable - sizeof(size_t)) return 0;
    if (cache.counts[bin] == (bin < SMALL_BIN_COUNT ? SMALL_BIN_LIMIT : BIN_LIMIT)) return 0;
    struct cached_block *block = pointer;
    unsigned index = size_class(usable);
    block->usable = usable;
    block->next = cache.bins[index];
    cache.bins[index] = block;
    cache.nonempty |= UINT64_C(1) << index;
    ++cache.counts[bin];
    cache.bytes += usable + sizeof(size_t);
    if (bin >= SMALL_BIN_COUNT) cache.large_bytes += usable + sizeof(size_t);
    if (cache.peak < cache.bytes) cache.peak = cache.bytes;
    ++cache.puts;
    return 1;
}

int sd_shader_cache_trim(void)
{
    if (!sd_shader_cache_active || !cache.bytes) return 0;
    int saved_errno = errno;
    for (uint64_t mask = cache.nonempty; mask; mask &= mask - 1) {
        unsigned bin = __builtin_ctzll(mask);
        struct cached_block *block = cache.bins[bin];
        cache.bins[bin] = NULL;
        while (block) {
            struct cached_block *next = block->next;
            free(block);
            block = next;
        }
    }
    memset(cache.counts, 0, sizeof(cache.counts));
    cache.nonempty = 0;
    cache.bytes = cache.large_bytes = 0;
    errno = saved_errno;
    return 1;
}

void sd_shader_cache_end(void)
{
    if (!cache.depth || --cache.depth || !sd_shader_cache_active) return;
    sd_shader_cache_trim();
    sd_shader_cache_active = 0;
    __atomic_fetch_add(&totals[0], 1, __ATOMIC_RELAXED);
    __atomic_fetch_add(&totals[1], cache.hits, __ATOMIC_RELAXED);
    __atomic_fetch_add(&totals[2], cache.misses, __ATOMIC_RELAXED);
    __atomic_fetch_add(&totals[3], cache.puts, __ATOMIC_RELAXED);
    uint64_t peak = __atomic_load_n(&totals[4], __ATOMIC_RELAXED);
    while (peak < cache.peak && !__atomic_compare_exchange_n(&totals[4], &peak, cache.peak, 0,
                                                            __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {}
    __atomic_sub_fetch(&workers, 1, __ATOMIC_RELAXED);
}

extern void wine_nx_runtime_trace(const char *);
void sd_shader_cache_report(void)
{
    uint64_t v[5];
    char line[224];
    for (unsigned i = 0; i < 5; ++i) v[i] = __atomic_load_n(&totals[i], __ATOMIC_RELAXED);
    snprintf(line, sizeof(line), "[SD-SHADER-CACHE] completed=%llu hits=%llu misses=%llu puts=%llu peak_worker_bytes=%llu; cumulative completed scopes",
             (unsigned long long)v[0], (unsigned long long)v[1], (unsigned long long)v[2],
             (unsigned long long)v[3], (unsigned long long)v[4]);
    wine_nx_runtime_trace(line);
}
