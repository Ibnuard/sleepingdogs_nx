"""Pair the full-application loader reserve with native GPU segregation."""
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT


def apply_forwarder(source):
    source = Path(source)
    p = source / 'main.c'; s = p.read_text()
    s = exact(s, '#include <string.h>', '#include <string.h>\n#include "sd_gpu_budget.h"')
    s = exact(s, 'static const char g_noticeText[] = { "sphaira " VERSION };',
        'static const char g_noticeText[] = SD_GPU_LOADER_INFO;')
    s = exact(s, '    if (size > 0x6000000)\n        size -= 0x6000000;',
        '''    const u64 reserve = sd_loader_reserve_bytes(mem_available);
    if (size > reserve)
        size -= reserve;''')
    p.write_text(s)
    (source / 'sd_gpu_budget.h').write_bytes((ROOT / 'src/sd_gpu_budget.h').read_bytes())


def apply_native(source):
    native = Path(source) / 'wine-nx-probe/source'
    (native / 'sd_gpu_budget.h').write_bytes((ROOT / 'src/sd_gpu_budget.h').read_bytes())
    p = native / 'f1_gpu_arena.h'
    p.write_text(exact(p.read_text(), '#define F1_GPU_ARENA_BYTES (128u * 1024u * 1024u)',
        '#define F1_GPU_ARENA_BYTES (256u * 1024u * 1024u)'))
    p = native / 'f1_gpu_heap.c'; s = p.read_text()
    s = exact(s, '#include "f1_gpu_arena.h"', '#include "f1_gpu_arena.h"\n#include "sd_gpu_budget.h"')
    start = s.index('/* Before Wine/FEX/scene allocations fragment the heap.')
    end = s.index('void wine_nx_f1_gpu_heap_init(void)', start)
    s = s[:start] + '''/* Keep GPU backing separate from long-lived CPU fragments. The updated
 * loader adds 64 MiB to the ordinary heap. Enable the larger pool only when
 * its contract and actual capacity agree; older loaders keep 128 MiB. */
''' + s[end:]
    s = exact(s, '''    size_t wanted=capacity>=1792u*1024u*1024u?F1_GPU_ARENA_BYTES:capacity/3;
    if(wanted>F1_GPU_ARENA_BYTES)wanted=F1_GPU_ARENA_BYTES;''',
        '''    size_t budget=sd_gpu_budget_bytes(capacity,envGetLoaderInfo(),envGetLoaderInfoSize());
    size_t wanted=capacity>=1792u*1024u*1024u?budget:capacity/3;
    if(wanted>budget)wanted=budget;''')
    s = exact(s, '    wine_nx_runtime_trace(line);errno=saved_errno;',
        '''    wine_nx_runtime_trace(line);
    snprintf(line,sizeof(line),"[SD-GPU-BUDGET] v1 paired_loader=%u heap=%llu target_mib=%llu reserved_mib=%llu",
        budget==SD_GPU_PAIRED_BYTES,(unsigned long long)capacity,
        (unsigned long long)(budget/SD_GPU_MIB),(unsigned long long)(base?reserved/SD_GPU_MIB:0));
    wine_nx_runtime_trace(line);errno=saved_errno;''')
    p.write_text(s)
    p = native / 'runtime.c'
    p.write_text(exact(p.read_text(), '[SD-MEMORY-BUDGET] build=v1 gpu_reserve_mib=128',
        '[SD-MEMORY-BUDGET] build=v2 gpu_reserve_max_mib=256'))
