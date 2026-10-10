/* CPU allocation recovery shared with the existing bounded FEX page store. */
#include <stdio.h>
#include "native_heap/fextendo_rust_heap.h"
#include "native_heap/fextendo_mesa_heap.h"
extern void wine_nx_runtime_trace(const char *);

void wine_nx_f1_native_heap_counters(uint64_t out[7])
{
    for (unsigned i=0;i<7;i++) out[i]=__atomic_load_n(&fx_rust_heap_stats[i],__ATOMIC_RELAXED);
}
void wine_nx_f1_native_heap_snapshot(void)
{
    uint64_t v[7];char line[224];
    wine_nx_f1_native_heap_counters(v);
    snprintf(line,sizeof(line),
        "[F1-RUST-HEAP] attempts=%llu recovered=%llu failed=%llu returned=%llu realloc=%llu last_bytes=%llu last_align=%llu",
        (unsigned long long)v[0],(unsigned long long)v[1],(unsigned long long)v[2],
        (unsigned long long)v[3],(unsigned long long)v[4],(unsigned long long)v[5],(unsigned long long)v[6]);
    wine_nx_runtime_trace(line);
}
