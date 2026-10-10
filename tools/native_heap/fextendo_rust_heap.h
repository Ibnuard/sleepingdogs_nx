/* SPDX-License-Identifier: MIT
 * Native Rust CPU allocations keep the original fast path. Only a failed
 * request borrows the shared, bounded fragmented-page store. GPU buffers,
 * mappings and executable code do not pass through this allocator.
 * Rust symbols/ABI are checked against a hash-pinned libnak_rs.a at build.
 */
#ifndef FEXTENDO_RUST_HEAP_H
#define FEXTENDO_RUST_HEAP_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "fextendo_rust_symbols.h"
extern void *pes13_cpu_pages_allocate(size_t,size_t);
extern int pes13_cpu_pages_owned(void *);
extern int pes13_cpu_pages_release(void *);
extern void wine_nx_crash_rust_allocation(unsigned,size_t,size_t,size_t,uintptr_t);
/* fallback attempts, recovered, failed, returned, realloc recovered,
 * last size, last alignment. No per-allocation counters on the normal path. */
static uint64_t fx_rust_heap_stats[7];
static void fx_rust_heap_add(unsigned n,uint64_t v){__atomic_fetch_add(&fx_rust_heap_stats[n],v,__ATOMIC_RELAXED);}
static void *fx_rust_heap_fallback(unsigned kind,size_t n,size_t a,size_t old,uintptr_t caller){
    fx_rust_heap_add(0,1);
    __atomic_store_n(&fx_rust_heap_stats[5],n,__ATOMIC_RELAXED);
    __atomic_store_n(&fx_rust_heap_stats[6],a,__ATOMIC_RELAXED);
    void *p=pes13_cpu_pages_allocate(n,a);
    fx_rust_heap_add(p?1:2,1);
    if(!p)wine_nx_crash_rust_allocation(kind,n,a,old,caller);
    return p;
}
void *pes13_rust_alloc(size_t n,size_t a){
    void *p=fx_rust_real_alloc(n,a);
    return p?p:fx_rust_heap_fallback(1,n,a,0,(uintptr_t)__builtin_return_address(0));
}
void *pes13_rust_alloc_zeroed(size_t n,size_t a){
    void *p=fx_rust_real_alloc_zeroed(n,a);
    if(p)return p;
    p=fx_rust_heap_fallback(2,n,a,0,(uintptr_t)__builtin_return_address(0));
    if(p)memset(p,0,n);
    return p;
}
void pes13_rust_dealloc(void *p,size_t n,size_t a){
    if(pes13_cpu_pages_release(p)){fx_rust_heap_add(3,1);return;}
    fx_rust_real_dealloc(p,n,a);
}
void *pes13_rust_realloc(void *old,size_t old_n,size_t a,size_t n){
    int aliased=pes13_cpu_pages_owned(old);
    void *p=aliased?fx_rust_real_alloc(n,a):fx_rust_real_realloc(old,old_n,a,n);
    if(p&&!aliased)return p;
    if(!p)p=fx_rust_heap_fallback(3,n,a,old_n,(uintptr_t)__builtin_return_address(0));
    if(!p)return NULL; /* Caller still owns the unchanged old allocation. */
    memcpy(p,old,n<old_n?n:old_n);
    pes13_rust_dealloc(old,old_n,a);
    fx_rust_heap_add(4,1);return p;
}
#endif
