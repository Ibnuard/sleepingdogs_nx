/* SPDX-License-Identifier: MIT
 * CPU-only Mesa ralloc/linear/GC storage. The build redirects the three
 * imports of the pinned ralloc object, including calls inlined by Mesa's
 * compiler. GPU backing, executable memory and unrelated malloc users are
 * deliberately not interposed. Normal allocations keep their libc ABI.
 */
#ifndef FEXTENDO_MESA_HEAP_H
#define FEXTENDO_MESA_HEAP_H
#include <malloc.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
extern void *pes13_cpu_pages_allocate(size_t,size_t);
extern int pes13_cpu_pages_owned(void *);
extern size_t pes13_cpu_pages_size(void *);
extern int pes13_cpu_pages_release(void *);
extern size_t wine_nx_release_idle_backing_pages(void);

void *pes13_mesa_malloc(size_t size){
    void *p=malloc(size);
    if(p)return p;
    if(wine_nx_release_idle_backing_pages())p=malloc(size);
    return p?p:pes13_cpu_pages_allocate(size?size:1,16);
}
void pes13_mesa_free(void *p){
    if(p&&pes13_cpu_pages_release(p))return;
    free(p);
}
void *pes13_mesa_realloc(void *old,size_t size){
    if(!old)return pes13_mesa_malloc(size);
    if(!size){pes13_mesa_free(old);return NULL;}
    int owned=pes13_cpu_pages_owned(old);
    void *p=owned?malloc(size):realloc(old,size);
    if(p&&!owned)return p;
    if(!p&&wine_nx_release_idle_backing_pages()){
        p=owned?malloc(size):realloc(old,size);
        if(p&&!owned)return p;
    }
    if(!p)p=pes13_cpu_pages_allocate(size,16);
    if(!p)return NULL; /* The original allocation and its tree still live. */
    size_t available=owned?pes13_cpu_pages_size(old):malloc_usable_size(old);
    memcpy(p,old,size<available?size:available);
    pes13_mesa_free(old);
    return p;
}
#endif
