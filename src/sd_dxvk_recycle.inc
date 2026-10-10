// SPDX-License-Identifier: MIT
// Included inside namespace dxvk. All calls hold DxvkMemoryAllocator::m_mutex.
// Retain only fully retired, dedicated mapped buffers, never live command data.

  DxvkResourceAllocation* DxvkMemoryAllocator::takeStreamAllocation(
          DxvkMemoryType& type, VkDeviceSize size,
    const DxvkAllocationInfo& info) {
    if (info.handleType != VK_EXTERNAL_MEMORY_HANDLE_TYPE_FLAG_BITS_MAX_ENUM)
      return nullptr;
    for (auto& entry : m_streamCache) {
      if (!entry || entry->m_type != &type || entry->m_size != size)
        continue;
      auto allocation = std::exchange(entry, nullptr);
      m_streamCacheBytes -= allocation->m_size;
      type.stats.memoryUsed += allocation->m_size;
      allocation->m_resourceCookie = info.resourceCookie;
      ++m_streamCacheHits;
      if (m_streamCacheHits <= 4 || !(m_streamCacheHits & (m_streamCacheHits - 1)))
        logStreamCache("reuse", size);
      return allocation;
    }
    return nullptr;
  }

  bool DxvkMemoryAllocator::cacheStreamAllocation(DxvkResourceAllocation* allocation) {
    if (!allocation->m_flags.test(DxvkAllocationFlag::StreamCache)
     || !allocation->m_flags.test(DxvkAllocationFlag::OwnsMemory)
     || !allocation->m_flags.test(DxvkAllocationFlag::OwnsBuffer)
     || allocation->m_flags.test(DxvkAllocationFlag::Imported)
     || allocation->m_flags.test(DxvkAllocationFlag::CanCache)
     || !allocation->m_mapPtr || !allocation->m_buffer || !allocation->m_type
     || allocation->m_image || allocation->m_sparsePageTable
     || allocation->m_kmtLocal || allocation->m_kmtGlobal
     || allocation->m_useCount.load() != 0u
     || allocation->m_size <= (2u << 20) || allocation->m_size > (8u << 20)
     || allocation->m_size > StreamCacheBudget - m_streamCacheBytes)
      return false;

    // One idle allocation per exact size/type; do not accumulate renamed copies.
    DxvkResourceAllocation** vacant = nullptr;
    for (auto& entry : m_streamCache) {
      if (entry && entry->m_type == allocation->m_type && entry->m_size == allocation->m_size)
        return false;
      if (!entry && !vacant)
        vacant = &entry;
    }
    if (!vacant)
      return false;

    allocation->destroyBufferViews();
    allocation->m_resourceCookie = 0u;
    *vacant = allocation;
    m_streamCacheBytes += allocation->m_size;
    return true;
  }

  void DxvkMemoryAllocator::drainStreamAllocations(const DxvkMemoryHeap& heap) {
    for (auto& entry : m_streamCache) {
      if (!entry || entry->m_type->heap != &heap)
        continue;
      auto allocation = std::exchange(entry, nullptr);
      m_streamCacheBytes -= allocation->m_size;
      allocation->m_type->stats.memoryAllocated -= allocation->m_size;
      // memoryUsed was subtracted when the last command/resource retired.
      // Normal destruction frees both VkBuffer and its full VkDeviceMemory.
      m_allocationPool.free(allocation);
    }
  }

  [[gnu::noinline]] void DxvkMemoryAllocator::logStreamCache(const char* event, VkDeviceSize size) {
    Logger::info(str::format("[SD-DXVK-RECYCLE] event=", event, " bytes=", size,
      " idle_bytes=", m_streamCacheBytes, " hits=", m_streamCacheHits));
  }
