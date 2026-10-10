"""Separate large mapped DXVK resources and contiguous native GPU backing."""
from pathlib import Path
from port_common import ROOT
from f1_overlay import exact

DXVK_FILES = ('src/dxvk/dxvk_memory.cpp', 'version.h.in')
MARKER = '[SD-DXVK-STREAM] v1 mapped > 2 MiB dedicated; no small suballocations'


def apply_dxvk(source):
    source = Path(source); p = source / DXVK_FILES[0]; s = p.read_text()
    anchor = '''      // Always try to suballocate first, even if the allocation is
      // very large. We will decide what to do if this fails.'''
    s = exact(s, anchor, '''      // On Switch, large dynamic DISCARD buffers must not become pools
      // for unrelated small allocations when their command lists retire.
      // A dedicated allocation returns its entire contiguous native backing
      // after the final reference; live commands retain normal Rc ownership.
      // Preserve NoAllocation: it may only reuse existing suballocations.
      if ((allocationInfo.properties & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)
       && size > VkDeviceSize(2u << 20)
       && !allocationInfo.mode.test(DxvkAllocationMode::NoAllocation)) {
        DxvkDeviceMemory memory = allocateDeviceMemory(type, size, nullptr);
        if (!memory.memory)
          continue;
        mapDeviceMemory(memory, allocationInfo.properties);
        return createAllocation(type, memory, allocationInfo);
      }

''' + anchor)
    anchor = '      if (!i) Logger::info("[SD-DXVK-MEM] v1 pool cap=2 MiB; large chunks=aligned resource");'
    s = exact(s, anchor, anchor + '\n      if (!i) Logger::info("' + MARKER + '");')
    p.write_text(s, newline='\n')
    p = source / 'version.h.in'
    p.write_text(exact(p.read_text(), '-sdmem1', '-sdstream1'), newline='\n')


def apply_native(source):
    native = Path(source) / 'wine-nx-probe/source'
    (native / 'sd_gpu_stream.h').write_bytes((ROOT / 'src/sd_gpu_stream.h').read_bytes())
    p = native / 'f1_gpu_heap.c'; s = p.read_text()
    s = exact(s, '#include "sd_gpu_budget.h"', '#include "sd_gpu_budget.h"\n#include "sd_gpu_stream.h"')
    s = exact(s, '        void *pooled=f1_gpu_arena_take(&f1_gpu_pool,alignment,bytes);',
        '        void *pooled=sd_gpu_stream_take(&f1_gpu_pool,alignment,bytes,0);')
    s = exact(s, '    p = f1_gpu_find_chunk(alignment, bytes, &largest, &scanned);',
        '''    p = f1_gpu_find_chunk(alignment, bytes, &largest, &scanned);
    if(!p && __atomic_load_n(&f1_gpu_arena_ready,__ATOMIC_ACQUIRE)) {
        mutexLock(&f1_gpu_arena_lock);
        p=sd_gpu_stream_take(&f1_gpu_pool,alignment,bytes,1);
        mutexUnlock(&f1_gpu_arena_lock);
    }''')
    anchor = '    wine_nx_runtime_trace(line);errno=saved_errno;'
    s = exact(s, anchor, '''    wine_nx_runtime_trace(line);
    snprintf(line,sizeof(line),"[SD-GPU-STREAM] v1 total_mib=%llu large_mib=%u threshold_mib=2 borrow_guard_mib=16",
        (unsigned long long)(base?reserved/SD_GPU_MIB:0),
        base && reserved>=256u*SD_GPU_MIB?64u:0u);
    wine_nx_runtime_trace(line);errno=saved_errno;''')
    # This diagnostic reads only arena metadata, under the existing lock.
    anchor = '    uint64_t live=f1_gpu_pool.live, invalid=f1_gpu_pool.bad_frees;'
    s = exact(s, anchor, anchor + '''
    uint32_t split=f1_gpu_pool.units>=4096?f1_gpu_pool.units-1024:f1_gpu_pool.units;
    uint64_t general_largest=(uint64_t)sd_gpu_stream_largest(&f1_gpu_pool,0,split,0,0)*F1_GPU_UNIT;
    uint64_t large_largest=(uint64_t)sd_gpu_stream_largest(&f1_gpu_pool,split,f1_gpu_pool.units,0,0)*F1_GPU_UNIT;''')
    anchor = '''    wine_nx_runtime_trace(line);
}

void wine_nx_f1_gpu_heap_snapshot(void)'''
    s = exact(s, anchor, '''    wine_nx_runtime_trace(line);
    struct mallinfo heap=mallinfo();
    snprintf(line,sizeof(line),"[SD-GPU-STREAM-STATS] general_largest=%llu large_largest=%llu heap_free=%llu heap_unclaimed=%llu",
        (unsigned long long)general_largest,(unsigned long long)large_largest,
        (unsigned long long)heap.fordblks,
        (unsigned long long)((uintptr_t)fake_heap_end-(uintptr_t)fake_heap_start>(size_t)heap.arena?
         (uintptr_t)fake_heap_end-(uintptr_t)fake_heap_start-(size_t)heap.arena:0));
    wine_nx_runtime_trace(line);
}

void wine_nx_f1_gpu_heap_snapshot(void)''')
    p.write_text(s, newline='\n')
