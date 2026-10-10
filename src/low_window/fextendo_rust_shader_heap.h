/* SPDX-License-Identifier: MIT
 * FEXTendo Rust CPU allocator: preserve page recovery and add scoped NAK
 * allocation reuse. The pinned system allocator's malloc/free ABI is checked
 * before building; large page-store allocations never enter the cache.
 */
#ifndef FEXTENDO_RUST_HEAP_H
#define FEXTENDO_RUST_HEAP_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <malloc.h>
#include "fextendo_rust_symbols.h"
#include "../sd_shader_cache.h"
extern void *pes13_cpu_pages_allocate(size_t,size_t);
extern int pes13_cpu_pages_owned(void *);
extern int pes13_cpu_pages_release(void *);
extern void wine_nx_crash_rust_allocation(unsigned,size_t,size_t,size_t,uintptr_t);
static uint64_t fx_rust_heap_stats[7];
static void fx_rust_heap_add(unsigned n,uint64_t v){__atomic_fetch_add(&fx_rust_heap_stats[n],v,__ATOMIC_RELAXED);}
static void *fx_rust_heap_fallback(unsigned kind,size_t n,size_t a,size_t old,uintptr_t caller)
{
    fx_rust_heap_add(0,1);
    __atomic_store_n(&fx_rust_heap_stats[5],n,__ATOMIC_RELAXED);
    __atomic_store_n(&fx_rust_heap_stats[6],a,__ATOMIC_RELAXED);
    void *p=pes13_cpu_pages_allocate(n,a);
    fx_rust_heap_add(p?1:2,1);
    if(!p)wine_nx_crash_rust_allocation(kind,n,a,old,caller);
    return p;
}
void *pes13_rust_alloc(size_t n,size_t a)
{
    void *p;
    if (sd_shader_cache_active && (p=sd_shader_cache_take(n,a))) return p;
    p=fx_rust_real_alloc(n,a);
    if (!p && sd_shader_cache_trim()) p=fx_rust_real_alloc(n,a);
    return p?p:fx_rust_heap_fallback(1,n,a,0,(uintptr_t)__builtin_return_address(0));
}
void *pes13_rust_alloc_zeroed(size_t n,size_t a)
{
    void *p;
    if (sd_shader_cache_active && (p=sd_shader_cache_take(n,a))) { memset(p,0,n); return p; }
    p=fx_rust_real_alloc_zeroed(n,a);
    if (!p && sd_shader_cache_trim()) p=fx_rust_real_alloc_zeroed(n,a);
    if(p)return p;
    p=fx_rust_heap_fallback(2,n,a,0,(uintptr_t)__builtin_return_address(0));
    if(p)memset(p,0,n);
    return p;
}
void pes13_rust_dealloc(void *p,size_t n,size_t a)
{
    if(pes13_cpu_pages_release(p)){fx_rust_heap_add(3,1);return;}
    if(p && sd_shader_cache_active && sd_shader_cache_put(p,malloc_usable_size(p))) return;
    fx_rust_real_dealloc(p,n,a);
}
void *pes13_rust_realloc(void *old,size_t old_n,size_t a,size_t n)
{
    int aliased=pes13_cpu_pages_owned(old);
    void *p;
    if (!aliased && old && n && sd_shader_cache_active) {
        size_t available=malloc_usable_size(old);
        if(n<=available && available<=65536 && n>available/2) return old;
        if((p=sd_shader_cache_take(n,a))) {
            memcpy(p,old,n<old_n?n:old_n);
            pes13_rust_dealloc(old,old_n,a);
            return p;
        }
    }
    p=aliased?fx_rust_real_alloc(n,a):fx_rust_real_realloc(old,old_n,a,n);
    if(p&&!aliased)return p;
    if(!p && sd_shader_cache_trim()) {
        p=aliased?fx_rust_real_alloc(n,a):fx_rust_real_realloc(old,old_n,a,n);
        if(p&&!aliased)return p;
    }
    if(!p)p=fx_rust_heap_fallback(3,n,a,old_n,(uintptr_t)__builtin_return_address(0));
    if(!p)return NULL;
    memcpy(p,old,n<old_n?n:old_n);
    pes13_rust_dealloc(old,old_n,a);
    fx_rust_heap_add(4,1);return p;
}
#endif
