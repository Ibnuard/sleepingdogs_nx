"""Bounded reuse of fully retired large mapped DXVK allocations."""
from pathlib import Path
from port_common import ROOT
from f1_overlay import exact
FILES=('src/dxvk/dxvk_memory.cpp','src/dxvk/dxvk_memory.h','src/dxvk/sd_dxvk_recycle.inc','version.h.in')
MARKER='[SD-DXVK-RECYCLE] v1 retired-only exact-size-type max_idle_mib=16'

def apply(source):
    source=Path(source);p=source/'src/dxvk/dxvk_memory.h';s=p.read_text()
    s=exact(s,'    ClearOnFree = 6,','    ClearOnFree = 6,\n    /// Dedicated mapped backing may be reused after its final reference.\n    StreamCache = 7,')
    anchor='    void freeDeviceMemory(\n'
    members='''    // Global bound, not per memory type. Only zero-reference entries live here.
    constexpr static VkDeviceSize StreamCacheBudget = 16u << 20;
    std::array<DxvkResourceAllocation*, 4> m_streamCache = { };
    VkDeviceSize m_streamCacheBytes = 0u;
    uint64_t m_streamCacheHits = 0u;

    DxvkResourceAllocation* takeStreamAllocation(
            DxvkMemoryType& type, VkDeviceSize size, const DxvkAllocationInfo& info);
    bool cacheStreamAllocation(DxvkResourceAllocation* allocation);
    void drainStreamAllocations(const DxvkMemoryHeap& heap);
    void logStreamCache(const char* event, VkDeviceSize size);

'''
    s=exact(s,anchor,members+anchor);p.write_text(s,newline='\n')
    p=source/'src/dxvk/dxvk_memory.cpp';s=p.read_text()
    s=exact(s,'namespace dxvk {','namespace dxvk {\n\n#include "sd_dxvk_recycle.inc"')
    anchor='      if (!i) Logger::info("[SD-DXVK-STREAM] v1 mapped > 2 MiB dedicated; no small suballocations");'
    s=exact(s,anchor,anchor+'\n      if (!i) Logger::info("'+MARKER+'");')
    old='''        DxvkDeviceMemory memory = allocateDeviceMemory(type, size, nullptr);
        if (!memory.memory)
          continue;
        mapDeviceMemory(memory, allocationInfo.properties);
        return createAllocation(type, memory, allocationInfo);'''
    new='''        // Reuse only a full dedicated buffer whose last command/resource
        // reference has retired. Type/size matching preserves mapping and usage.
        VkDeviceSize backingSize = type.bufferUsage ? align(size, GlobalBufferAlignment) : size;
        if (auto allocation = takeStreamAllocation(type, backingSize, allocationInfo))
          return allocation;
        DxvkDeviceMemory memory = allocateDeviceMemory(type, size, nullptr);
        if (!memory.memory)
          continue;
        mapDeviceMemory(memory, allocationInfo.properties);
        auto allocation = createAllocation(type, memory, allocationInfo);
        if (memory.buffer && memory.mapPtr && memory.size <= (8u << 20)
         && allocationInfo.handleType == VK_EXTERNAL_MEMORY_HANDLE_TYPE_FLAG_BITS_MAX_ENUM) {
          allocation->m_flags.set(DxvkAllocationFlag::StreamCache);
          if (m_device->config().zeroMappedMemory)
            allocation->m_flags.set(DxvkAllocationFlag::ClearOnFree);
        }
        return allocation;'''
    s=exact(s,old,new)
    anchor='''        if (unlikely(allocation->m_flags.test(DxvkAllocationFlag::OwnsMemory))) {
          // We free the actual allocation later, just update stats here.'''
    s=exact(s,anchor,'''        if (unlikely(allocation->m_flags.test(DxvkAllocationFlag::OwnsMemory))) {
          if (cacheStreamAllocation(allocation))
            return;
          // We free the actual allocation later, just update stats here.''')
    anchor='''    bool freed = false;

    for (auto typeIndex : bit::BitMask(heap.memoryTypes)) {'''
    s=exact(s,anchor,'''    // Both real allocation-failure retries and teardown request a full trim.
    // Drop only idle entries; live allocations remain owned by normal Rc refs.
    if (allocationSize == VkDeviceSize(-1))
      drainStreamAllocations(heap);
    bool freed = false;

    for (auto typeIndex : bit::BitMask(heap.memoryTypes)) {''')
    p.write_text(s,newline='\n')
    (source/'src/dxvk/sd_dxvk_recycle.inc').write_bytes((ROOT/'src/sd_dxvk_recycle.inc').read_bytes())
    p=source/'version.h.in';p.write_text(exact(p.read_text(),'-sdstream1','-sdrecycle1'),newline='\n')
