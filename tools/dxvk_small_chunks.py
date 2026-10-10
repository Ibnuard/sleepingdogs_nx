"""Scoped recovery for the pinned DXVK 3.1.1 allocator used by F1.

Normal pool sizes are unchanged. Only an unsuccessful pool growth may descend
below the ordinary chunk floor, down to the real aligned resource/page size.
Every returned chunk remains an ordinary Vulkan allocation with its true size.
"""
from pathlib import Path

COMMIT = 'b1a1c99ab52b687cf950d62c88bc2fa316b41663'
OLD_ALLOC = '''    if (!chunk.memory)
      return false;

    mapDeviceMemory(chunk, properties);

    // If we expect the application to require more memory in the
    // future, increase the chunk size for subsequent allocations.
    if (pool.nextChunkSize < pool.maxChunkSize
     && pool.nextChunkSize <= type.stats.memoryAllocated / 2u)
      pool.nextChunkSize *= 2u;'''
NEW_ALLOC = '''    // F1/NVK: a fragmented host heap can reject every chunk down to
    // several MiB even when the requested resource is only 64 KiB. Keep normal
    // growth first, then try smaller *real* Vulkan allocations. The page
    // allocator supports one-page chunks; never go below the aligned request.
    bool smallChunk = false;
    VkDeviceSize recoveryFloor = std::max(requiredSize, VkDeviceSize(DxvkPageAllocator::PageSize));
    while (!chunk.memory && desiredSize >= recoveryFloor) {
      chunk = allocateDeviceMemory(type, desiredSize, nullptr);
      desiredSize /= 2u;
      smallChunk = !!chunk.memory;
    }

    if (!chunk.memory)
      return false;

    if (smallChunk) {
      static std::atomic<uint32_t> reports { 0u };
      if (reports.fetch_add(1u, std::memory_order_relaxed) < 16u)
        Logger::info(str::format("[F1-DXVK-MEM] small chunk recovered: required=",
          requiredSize, " allocated=", chunk.size, " type=", type.index));
    }

    mapDeviceMemory(chunk, properties);

    // Keep subsequent growth modest after recovery instead of retrying all
    // failed large sizes for every resource. Normal successful growth is intact.
    if (smallChunk)
      pool.nextChunkSize = chunk.size;
    else if (pool.nextChunkSize < pool.maxChunkSize
          && pool.nextChunkSize <= type.stats.memoryAllocated / 2u)
      pool.nextChunkSize *= 2u;'''


def apply(source: Path):
    path = source / 'src/dxvk/dxvk_memory.cpp'
    text = path.read_text()
    assert text.count(OLD_ALLOC) == 1, 'Unexpected DXVK memory allocator source'
    assert text.count('#include <algorithm>') == 1
    text = text.replace('#include <algorithm>', '#include <algorithm>\n#include <atomic>')
    path.write_text(text.replace(OLD_ALLOC, NEW_ALLOC))
    # This makes the runtime version self-identifying in the Wine log.
    version = source / 'version.h.in'
    original = version.read_text()
    assert '@VCS_TAG@' in original
    version.write_text(original.replace('@VCS_TAG@', '@VCS_TAG@-f1mem1'))

