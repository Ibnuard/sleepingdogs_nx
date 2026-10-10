#include <cstddef>
#include <cstdint>
#include "dxvk_device.h"
#include "dxvk_memory.h"
using namespace dxvk;
#define O(T,F) uint32_t(offsetof(T,F))
extern "C" __attribute__((used,section(".sdmeta"))) const uint32_t sd_layout[]={
 sizeof(DxvkMemoryAllocator),O(DxvkMemoryAllocator,m_streamCache),O(DxvkMemoryAllocator,m_streamCacheBytes),
 O(DxvkMemoryAllocator,m_streamCacheHits),O(DxvkMemoryAllocator,m_memTypes),O(DxvkMemoryAllocator,m_memTypesByPropertyFlags),
 sizeof(DxvkMemoryType),O(DxvkMemoryType,heap),O(DxvkMemoryType,stats),O(DxvkMemoryType,bufferUsage),
 sizeof(DxvkMemoryHeap),O(DxvkMemoryHeap,memoryTypes),O(DxvkMemoryHeap,index),
 O(DxvkMemoryStats,memoryAllocated),O(DxvkMemoryStats,memoryUsed),
 sizeof(DxvkResourceAllocation),O(DxvkResourceAllocation,m_useCount),O(DxvkResourceAllocation,m_flags),
 O(DxvkResourceAllocation,m_resourceCookie),O(DxvkResourceAllocation,m_memory),O(DxvkResourceAllocation,m_size),
 O(DxvkResourceAllocation,m_mapPtr),O(DxvkResourceAllocation,m_buffer),O(DxvkResourceAllocation,m_image),
 O(DxvkResourceAllocation,m_kmtLocal),O(DxvkResourceAllocation,m_kmtGlobal),O(DxvkResourceAllocation,m_sparsePageTable),
 O(DxvkResourceAllocation,m_type),O(DxvkResourceAllocation,m_allocator),O(DxvkResourceAllocation,m_bufferViews),
 sizeof(DxvkAllocationInfo),O(DxvkAllocationInfo,resourceCookie),O(DxvkAllocationInfo,properties),O(DxvkAllocationInfo,mode),
 sizeof(VkMemoryRequirements),O(VkMemoryRequirements,size),O(VkMemoryRequirements,alignment),O(VkMemoryRequirements,memoryTypeBits),
 sizeof(DxvkDeviceMemory),O(DxvkAllocationInfo,handleType)
};
