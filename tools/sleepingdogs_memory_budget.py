"""Keep native headroom and use idle stack reserves for smaller SDK threads."""
from pathlib import Path
from f1_overlay import exact

GPU_BYTES = 128 * 1024 * 1024


def apply(source, adapter):
    native = Path(source) / 'wine-nx-probe/source'
    p = native / 'f1_gpu_arena.h'
    p.write_text(exact(p.read_text(), '#define F1_GPU_ARENA_BYTES (256u * 1024u * 1024u)',
                      '#define F1_GPU_ARENA_BYTES (128u * 1024u * 1024u)'))
    p = native / 'f1_native_stacks.c'
    p.write_text(exact(p.read_text(),
        '        stack || size != F1_STACK_BYTES) return previous;',
        '''        stack || !size || size > F1_STACK_BYTES || size % F1_STACK_PAGE) return previous;
    /* Sleeping Dogs also creates 128 KiB Wine server/audio workers. They may
     * use an idle full-size slot: libnx receives the same padded allocation,
     * so TLS/reent and usable stack capacity are never reduced. Caller-owned
     * stacks, oversize requests and mapping/quota failures still pass through. */'''))
    # Snapshot the actual failure point; the previous 5s sample can predate
    # both new thread creation and the fifth compiler workspace request.
    p = Path(adapter) / 'f1_scratch.h'; s = p.read_text()
    s = exact(s, 'extern void pes13_virtmem_snapshot(uint64_t out[4]);',
        '''extern void pes13_virtmem_snapshot(uint64_t out[4]);
extern void wine_nx_f1_resource_snapshot(const char *reason);
extern void wine_nx_f1_gpu_heap_snapshot(void);
extern void wine_nx_f1_native_stacks_snapshot(void);''')
    s = exact(s, '    if (!ptr) ptr = fx_scratch_pages_take_report(size, &failure);',
        '''    if (!ptr) ptr = fx_scratch_pages_take_report(size, &failure);
    if (!ptr) {
        wine_nx_f1_resource_snapshot("compiler-scratch-failed");
        wine_nx_f1_gpu_heap_snapshot();
        wine_nx_f1_native_stacks_snapshot();
    }''')
    p.write_text(s)
    p = native / 'runtime.c'; s = p.read_text()
    marker = 'log_line("[SD-THREAD-DEBUG] build=v1 suspended thread debug context");'
    p.write_text(exact(s, marker, marker + '\n'
        '                        log_line("[SD-MEMORY-BUDGET] build=v1 gpu_reserve_mib=128 stack_reserve_max_kib=1024");'))
