/* SPDX-License-Identifier: MIT
 * FEXTendo Mesa CPU allocator with scoped shader-cache reuse. Outside NAK,
 * preserve the existing libc/idle-backing/page recovery policy. GPU backing,
 * executable memory and unrelated malloc users are not interposed.
 */
#ifndef FEXTENDO_MESA_HEAP_H
#define FEXTENDO_MESA_HEAP_H
#include <malloc.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "../sd_shader_cache.h"
extern void *pes13_cpu_pages_allocate(size_t,size_t);
extern int pes13_cpu_pages_owned(void *);
extern size_t pes13_cpu_pages_size(void *);
extern int pes13_cpu_pages_release(void *);
extern size_t wine_nx_release_idle_backing_pages(void);

void *pes13_mesa_malloc(size_t size)
{
    void *p;
    if (sd_shader_cache_active && (p = sd_shader_cache_take(size, 16))) return p;
    p = malloc(size);
    if (p) return p;
    if (sd_shader_cache_trim()) p = malloc(size);
    if (!p && wine_nx_release_idle_backing_pages()) p = malloc(size);
    return p ? p : pes13_cpu_pages_allocate(size ? size : 1, 16);
}

void pes13_mesa_free(void *p)
{
    if (p && pes13_cpu_pages_release(p)) return;
    if (p && sd_shader_cache_active && sd_shader_cache_put(p, malloc_usable_size(p))) return;
    free(p);
}

void *pes13_mesa_realloc(void *old, size_t size)
{
    if (!old) return pes13_mesa_malloc(size);
    if (!size) { pes13_mesa_free(old); return NULL; }
    int owned = pes13_cpu_pages_owned(old);
    void *p;
    if (!owned && sd_shader_cache_active) {
        size_t available = malloc_usable_size(old);
        if (size <= available && available <= 65536 && size > available / 2) return old;
        if ((p = sd_shader_cache_take(size, 16))) {
            memcpy(p, old, size < available ? size : available);
            pes13_mesa_free(old);
            return p;
        }
    }
    p = owned ? malloc(size) : realloc(old, size);
    if (p && !owned) return p;
    if (!p && sd_shader_cache_trim()) {
        p = owned ? malloc(size) : realloc(old, size);
        if (p && !owned) return p;
    }
    if (!p && wine_nx_release_idle_backing_pages()) {
        p = owned ? malloc(size) : realloc(old, size);
        if (p && !owned) return p;
    }
    if (!p) p = pes13_cpu_pages_allocate(size, 16);
    if (!p) return NULL;
    size_t available = owned ? pes13_cpu_pages_size(old) : malloc_usable_size(old);
    memcpy(p, old, size < available ? size : available);
    pes13_mesa_free(old);
    return p;
}
#endif
