/* Real DXVK chunk function and page/pool allocator, with Vulkan allocation and
 * mapping as controlled boundaries. Pressure cases are synthetic, not a replay
 * of the unrecorded full Switch allocation history. */
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
#include "dxvk_allocator.h"
namespace dxvk {
using VkDeviceSize=uint64_t;
using VkMemoryPropertyFlags=uint32_t;
using high_resolution_clock=std::chrono::steady_clock;
struct DxvkDeviceMemory { uint64_t memory=0, size=0; };
struct DxvkMemoryChunk {
  DxvkDeviceMemory memory;
  high_resolution_clock::time_point unusedTime;
  bool canMove=false;
};
/* ACTUAL_DXVK_MEMORY_POOL */
struct DxvkMemoryType {
  unsigned index=0;
  struct { uint64_t memoryAllocated=0; } stats;
};
namespace str { template<class... T> std::string format(T&&...) {return "chunk";} }
struct Logger { static void info(const std::string&){} };
class DxvkMemoryAllocator {
public:
  uint64_t maxContiguous=256u<<20, budget=1024u<<20, nextHandle=0;
  unsigned maps=0;
  VkMemoryPropertyFlags mappedFlags=0;
  std::vector<uint64_t> attempts;
  DxvkDeviceMemory allocateDeviceMemory(DxvkMemoryType& type,uint64_t bytes,const void *next) {
    assert(!next); assert(bytes); attempts.push_back(bytes);
    if(bytes>maxContiguous || bytes>budget-type.stats.memoryAllocated) return {};
    type.stats.memoryAllocated+=bytes;
    return {++nextHandle,bytes};
  }
  void mapDeviceMemory(DxvkDeviceMemory& memory,VkMemoryPropertyFlags flags) {
    assert(memory.memory); ++maps; mappedFlags=flags;
  }
  bool allocateChunkInPool(DxvkMemoryType&,DxvkMemoryPool&,VkMemoryPropertyFlags,VkDeviceSize,VkDeviceSize);
};
/* ACTUAL_ALLOCATE_CHUNK */
}
using namespace dxvk;
static constexpr uint64_t K=1024, M=1024*K;
#ifdef BASELINE
static constexpr uint64_t Cap=8*M;
#else
static constexpr uint64_t Cap=2*M;
#endif
static int64_t take(DxvkMemoryAllocator& a,DxvkMemoryType& t,DxvkMemoryPool& p,uint64_t size) {
  auto at=p.alloc(size,256);
  if(at>=0) return at;
  if(!a.allocateChunkInPool(t,p,7,size,128*M)) return -1;
  at=p.alloc(size,256);assert(at>=0);
  auto idx=uint64_t(at)>>DxvkPageAllocator::ChunkAddressBits;
  assert((uint64_t(at)&DxvkPageAllocator::ChunkAddressMask)+size<=p.chunks[idx].memory.size);
  return at;
}
static void release(DxvkMemoryPool& p,uint64_t at,uint64_t size) {
  assert(p.free(at,size));
  auto idx=at>>DxvkPageAllocator::ChunkAddressBits;
  assert(!p.pageAllocator.pagesUsed(idx));
  p.pageAllocator.removeChunk(idx);
}
int main() {
  static_assert(DxvkPageAllocator::PageSize==64*K);
  // Healthy backing allocator: exactly the failing resource size from hardware.
  {
    DxvkMemoryAllocator a;DxvkMemoryType t;DxvkMemoryPool p;
    p.maxChunkSize=p.nextChunkSize=Cap;
    auto at=take(a,t,p,5*M);assert(at>=0&&a.maps==1&&a.mappedFlags==7);
#ifdef BASELINE
    assert(t.stats.memoryAllocated==8*M);
#else
    assert(t.stats.memoryAllocated==5*M);
#endif
    release(p,at,5*M);
  }
  // Repeated discard buffers, with a bounded shared backing budget.
  {
    DxvkMemoryAllocator a;DxvkMemoryType t;DxvkMemoryPool p;
    p.maxChunkSize=p.nextChunkSize=Cap; a.budget=80*M;
    std::vector<uint64_t> live;
    for(unsigned i=0;i<16;i++) {
      auto at=take(a,t,p,5*M);
      if(at<0) break;
      for(auto prev:live)assert(at!=int64_t(prev));
      live.push_back(at);
    }
#ifdef BASELINE
    assert(live.size()==10 && t.stats.memoryAllocated==80*M);
#else
    assert(live.size()==16 && t.stats.memoryAllocated==80*M);
#endif
    for(auto at:live)release(p,at,5*M);
  }
  // No under-allocation, even above the ordinary cap; non-power-of-two floors.
  for(uint64_t need:{uint64_t(1),64*K,64*K+1,uint64_t(1661632),2*M,3*M,5*M,5*M+1,8*M+64*K,32*M}) {
    uint64_t floor=(need+64*K-1)/(64*K)*(64*K);
    DxvkMemoryAllocator a;DxvkMemoryType t;DxvkMemoryPool p;
    p.maxChunkSize=p.nextChunkSize=Cap;a.maxContiguous=floor;
    auto at=take(a,t,p,need);assert(at>=0&&t.stats.memoryAllocated==floor);
    for(auto n:a.attempts)assert(n>=need&&n%(64*K)==0);
    assert(!(p.nextChunkSize&(p.nextChunkSize-1))&&p.nextChunkSize<=Cap);
    release(p,at,need);
  }
  for(uint64_t need:{64*K,uint64_t(1661632),3*M,5*M,12*M+64*K}) {
    DxvkMemoryAllocator a;DxvkMemoryType t;DxvkMemoryPool p;
    p.maxChunkSize=p.nextChunkSize=Cap;a.maxContiguous=need-1;
    assert(take(a,t,p,need)<0&&!a.maps&&p.chunks.empty()&&!t.stats.memoryAllocated);
    assert(a.attempts.size()<=9);
  }
  // Small resources still share real pages, and freed space can be reused.
  {
    DxvkMemoryAllocator a;DxvkMemoryType t;DxvkMemoryPool p;
    p.maxChunkSize=p.nextChunkSize=Cap;
    std::vector<int64_t> live;
    for(unsigned i=0;i<600;i++)live.push_back(take(a,t,p,768));
    assert(std::all_of(live.begin(),live.end(),[](auto p){return p>=0;}));
    assert(t.stats.memoryAllocated==Cap);
    for(auto at:live)p.free(at,768);
    auto maps=a.maps;
    for(unsigned i=0;i<600;i++)assert(take(a,t,p,768)>=0);
    assert(a.maps==maps);
  }
  std::cout<<"PASS: cap="<<Cap<<"; 5 MiB backing; bounded pressure; aligned floors; failure cleanup; small-resource reuse\n";
}
