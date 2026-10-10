"""F1's shared native/GPU heap: smaller pools from startup and exact-size retry.

Apply to the pinned, unmodified upstream tree. No resource eviction, synthetic
allocation or change to Vulkan mapping/ownership; use the real page allocator.
"""
from pathlib import Path
from dxvk_small_chunks import apply as small_chunks, COMMIT

def replace(text, old, new):
    assert text.count(old)==1, old
    return text.replace(old,new)

def apply(source: Path):
    small_chunks(source)
    path=source/'src/dxvk/dxvk_memory.cpp'
    s=path.read_text()
    # This cap limits growth before the host heap is fragmented, including the
    # HVV path which otherwise requests up to 128 MiB on 32-bit UMA drivers.
    s=replace(s, '    DxvkDeviceMemory chunk = { };\n\n    while (!chunk.memory',
        '''    DxvkDeviceMemory chunk = { };
    constexpr VkDeviceSize f1ChunkCap = 8u << 20;
    VkDeviceSize recoveryFloor = align(std::max(requiredSize,
      VkDeviceSize(DxvkPageAllocator::PageSize)), VkDeviceSize(DxvkPageAllocator::PageSize));
    desiredSize = std::min(desiredSize, std::max(recoveryFloor, f1ChunkCap));
    VkDeviceSize lastAttempt = 0;

    while (!chunk.memory''')
    old='      chunk = allocateDeviceMemory(type, desiredSize, nullptr);\n      desiredSize /= 2u;'
    assert s.count(old)==2
    s=s.replace(old,'      lastAttempt = desiredSize;\n'+old)
    s=replace(s, '    VkDeviceSize recoveryFloor = std::max(requiredSize, VkDeviceSize(DxvkPageAllocator::PageSize));\n','')
    s=replace(s, '    if (!chunk.memory)\n      return false;\n\n    if (smallChunk)',
        '''    // Halving skips a non-power-of-two resource floor (the GP log
    // needs 1,661,632 bytes, between 1 and 2 MiB). Try its aligned size once.
    if (!chunk.memory && lastAttempt != recoveryFloor) {
      chunk = allocateDeviceMemory(type, recoveryFloor, nullptr);
      smallChunk = !!chunk.memory;
    }
    if (!chunk.memory)
      return false;

    if (smallChunk)''')
    s=replace(s, '''    if (smallChunk)
      pool.nextChunkSize = chunk.size;
    else if (pool.nextChunkSize < pool.maxChunkSize
          && pool.nextChunkSize <= type.stats.memoryAllocated / 2u)
      pool.nextChunkSize *= 2u;''', '''    if (smallChunk) {
      // nextChunkSize retains its documented power-of-two invariant even
      // when the recovered backing contains an arbitrary number of pages.
      VkDeviceSize next = DxvkPageAllocator::PageSize;
      while (next < chunk.size) next *= 2u;
      pool.nextChunkSize = std::min(next, f1ChunkCap);
    } else if (pool.nextChunkSize < pool.maxChunkSize
            && pool.nextChunkSize <= type.stats.memoryAllocated / 2u) {
      pool.nextChunkSize = std::min(pool.nextChunkSize * 2u, f1ChunkCap);
    }''')
    s=replace(s, '    return std::max(size, DxvkMemoryPool::MinChunkSize);',
        '    return std::min(VkDeviceSize(8u << 20), std::max(size, DxvkMemoryPool::MinChunkSize));')
    s=replace(s, '      type.devicePool.maxChunkSize = determineMaxChunkSize(type, false);',
        '''      if (!i) Logger::info("[F1-DXVK-MEM] pool cap=8 MiB; exact aligned floor retry enabled");
      type.devicePool.maxChunkSize = determineMaxChunkSize(type, false);''')
    path.write_text(s)
    version=source/'version.h.in'
    version.write_text(replace(version.read_text(),'-f1mem1','-f1mem2'))
