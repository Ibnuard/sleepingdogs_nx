/* Actual allocateMemory/chunk/page code; Vulkan backing is a bounded model. */
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <vector>
#include "dxvk_allocator.h"
namespace dxvk {
using VkDeviceSize=uint64_t;using VkMemoryPropertyFlags=uint32_t;
using high_resolution_clock=std::chrono::steady_clock;using mutex=std::mutex;
constexpr unsigned VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT=1,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT=2;
struct VkMemoryRequirements{uint64_t size,alignment;unsigned memoryTypeBits;};
enum class DxvkAllocationMode{NoAllocation=1};
struct Modes{unsigned bits=0;bool test(DxvkAllocationMode m)const{return bits&unsigned(m);}};
struct DxvkAllocationInfo{unsigned properties=0;Modes mode;};
struct DxvkDeviceMemory{uint64_t memory=0,size=0;};
struct DxvkMemoryChunk{DxvkDeviceMemory memory;high_resolution_clock::time_point unusedTime;bool canMove=false;};
/* ACTUAL_POOL */
struct DxvkMemoryHeap{unsigned memoryTypes=3;struct{uint64_t size=1536ull<<20;}properties;};
struct DxvkMemoryType{
 unsigned index=0;DxvkMemoryHeap *heap;DxvkMemoryPool mappedPool,devicePool;
 struct{uint64_t memoryAllocated=0;}stats;
};
struct DxvkResourceAllocation{bool dedicated;uint64_t address,size;DxvkMemoryType *type;DxvkMemoryPool *pool;unsigned mapFlags;};
template<class T>using Rc=std::shared_ptr<T>;
namespace str{template<class...T>std::string format(T&&...){return "stream";}}
struct Logger{static void info(const std::string&) {}};
class DxvkMemoryAllocator{
public:
 static constexpr unsigned MinAllocationsPerHeap=8;
 std::mutex m_mutex;DxvkMemoryHeap heap;DxvkMemoryType m_memTypes[2];
 uint64_t budget=128ull<<20,used=0,next=1;unsigned flags=0,maps=0,created=0,freed=0;
 DxvkMemoryAllocator(){for(unsigned i=0;i<2;i++){
   m_memTypes[i].index=i;m_memTypes[i].heap=&heap;
   for(auto p:{&m_memTypes[i].mappedPool,&m_memTypes[i].devicePool})p->maxChunkSize=p->nextChunkSize=2u<<20;
 }}
 unsigned getMemoryTypeMask(unsigned)const{return 3;}
 DxvkDeviceMemory allocateDeviceMemory(DxvkMemoryType&t,uint64_t n,const void*){
   if(n>budget-used)return {};used+=n;t.stats.memoryAllocated+=n;++created;return {next++,n};
 }
 void mapDeviceMemory(DxvkDeviceMemory&m,unsigned f){assert(m.memory);flags=f;++maps;}
 Rc<DxvkResourceAllocation> createAllocation(DxvkMemoryType&t,const DxvkDeviceMemory&m,const DxvkAllocationInfo&i){
   assert(m.memory&&flags==i.properties);
   return Rc<DxvkResourceAllocation>(new DxvkResourceAllocation{true,m.memory,m.size,&t,nullptr,flags},
     [this](auto p){used-=p->size;p->type->stats.memoryAllocated-=p->size;++freed;delete p;});
 }
 Rc<DxvkResourceAllocation> createAllocation(DxvkMemoryType&t,DxvkMemoryPool&p,uint64_t at,uint64_t n,const DxvkAllocationInfo&i){
   return Rc<DxvkResourceAllocation>(new DxvkResourceAllocation{false,at,n,&t,&p,i.properties},
     [](auto q){q->pool->free(q->address,q->size);delete q;});
 }
 bool allocateChunkInPool(DxvkMemoryType&,DxvkMemoryPool&,unsigned,uint64_t,uint64_t);
 Rc<DxvkResourceAllocation> allocateMemory(const VkMemoryRequirements&,const DxvkAllocationInfo&);
};
/* ACTUAL_CHUNK */
/* ACTUAL_ALLOCATE */
}
using namespace dxvk;
constexpr uint64_t M=1048576;
int main(){
 {DxvkMemoryAllocator a;DxvkAllocationInfo i{3,{}};
  auto big=a.allocateMemory({5*M,256,3},i);assert(big&&big->size>=5*M);
#ifdef BASELINE
  assert(!big->dedicated);big.reset();auto small=a.allocateMemory({65536,256,3},i);
  assert(small&&!small->dedicated&&a.used==5*M&&a.created==1);
#else
  assert(big->dedicated);auto command=big;big.reset();assert(a.used==5*M&&!a.freed);
  command.reset();assert(!a.used&&a.freed==1);
  auto small=a.allocateMemory({65536,256,3},i);assert(small&&!small->dedicated&&a.used==2*M);
#endif
 }
 for(uint64_t n:{2*M,2*M+1,5*M,5*M+1,17*M}){
  DxvkMemoryAllocator a;auto p=a.allocateMemory({n,65536,3},{3,{}});assert(p&&p->size>=n);
#ifndef BASELINE
  assert(p->dedicated==(n>2*M));
#endif
 }
 {DxvkMemoryAllocator a;auto p=a.allocateMemory({5*M,256,3},{1,{}});assert(p&&p->mapFlags==1);}
 {DxvkMemoryAllocator a;auto p=a.allocateMemory({5*M,256,3},{3,{1}});assert(!p&&!a.created&&!a.maps);}
 {DxvkMemoryAllocator a;a.budget=5*M-1;auto p=a.allocateMemory({5*M,256,3},{3,{}});assert(!p&&!a.used&&!a.maps);}
#ifndef BASELINE
 {DxvkMemoryAllocator a;a.budget=12*M;auto small=a.allocateMemory({65536,256,3},{3,{}});assert(small);
  for(unsigned k=0;k<256;k++){
   auto first=a.allocateMemory({5*M,256,3},{3,{}}),second=a.allocateMemory({5*M,256,3},{3,{}});
   assert(first&&second&&first->address!=second->address&&a.used==12*M);
   assert(!a.allocateMemory({5*M,256,3},{3,{}}));
  }
  assert(a.used==2*M&&a.freed==512);
 }
#endif
 std::cout<<"PASS: actual DXVK allocation dispatch and page allocator; size floor, failure, NoAllocation, mapping flags and large/small lifetime isolation\n";
}
