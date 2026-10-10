// Production allocation dispatch, retirement, trim and cache helpers.
// Vulkan device allocation/destruction and diagnostics are controlled boundaries.
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstring>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>
#include "dxvk_allocator.h"
#include "util_flags.h"
namespace dxvk {
using VkDeviceSize=uint64_t;using VkMemoryPropertyFlags=uint32_t;
using high_resolution_clock=std::chrono::steady_clock;using mutex=std::mutex;
constexpr unsigned VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT=1,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT=2;
constexpr unsigned VK_EXTERNAL_MEMORY_HANDLE_TYPE_FLAG_BITS_MAX_ENUM=0x7fffffff;
struct VkMemoryRequirements{uint64_t size,alignment;unsigned memoryTypeBits;};
enum class DxvkAllocationMode{NoAllocation=0};
struct DxvkAllocationInfo{uint64_t resourceCookie=0;unsigned properties=3;Flags<DxvkAllocationMode> mode={};unsigned handleType=VK_EXTERNAL_MEMORY_HANDLE_TYPE_FLAG_BITS_MAX_ENUM;};
struct DxvkDeviceMemory{uint64_t memory=0,size=0,buffer=0,gpuVa=0;void* mapPtr=nullptr;};
struct DxvkMemoryChunk{
 DxvkDeviceMemory memory;high_resolution_clock::time_point unusedTime;bool canMove=false;
 template<class T>void addAllocation(T*){} template<class T>void removeAllocation(T*){}
};
/* ACTUAL_POOL */
struct DxvkMemoryHeap{unsigned index=0,memoryTypes=3;struct{uint64_t size=1536ull<<20;}properties;};
struct SharedCache{template<class T>T* freeAllocation(T*p){return p;}};
struct DxvkMemoryType{
 unsigned index=0;DxvkMemoryHeap *heap;DxvkMemoryPool mappedPool,devicePool;unsigned bufferUsage=1;
 struct{uint64_t memoryAllocated=0,memoryUsed=0;}stats;SharedCache* sharedCache=nullptr;
 struct{unsigned heapIndex=0;}properties;
};
/* ACTUAL_FLAGS */
using DxvkAllocationFlags=Flags<DxvkAllocationFlag>;
class DxvkMemoryAllocator;
struct DxvkResourceAllocation{
 std::atomic<unsigned> m_useCount{0};DxvkAllocationFlags m_flags={};
 uint64_t m_resourceCookie=0,m_memory=0,m_address=0,m_size=0;void* m_mapPtr=nullptr;
 uint64_t m_buffer=0,m_bufferOffset=0,m_bufferAddress=0,m_image=0;
 unsigned m_kmtLocal=0,m_kmtGlobal=0;void* m_sparsePageTable=nullptr;
 DxvkMemoryAllocator* m_allocator;DxvkMemoryType* m_type;bool views=false;
 DxvkResourceAllocation(DxvkMemoryAllocator*a,DxvkMemoryType*t):m_allocator(a),m_type(t){}
 ~DxvkResourceAllocation();
 void destroyBufferViews(){views=false;}
 void incRef(){++m_useCount;}
 void decRef();
};
template<class T>struct Rc{
 T*p=nullptr;Rc()=default;Rc(std::nullptr_t){}Rc(T*q):p(q){if(p)p->incRef();}
 Rc(const Rc&r):Rc(r.p){}Rc(Rc&&r):p(std::exchange(r.p,nullptr)){}
 ~Rc(){if(p)p->decRef();}
 T*operator->()const{return p;}explicit operator bool()const{return p;}
 void reset(){auto*q=std::exchange(p,nullptr);if(q)q->decRef();}
};
namespace str{template<class...T>std::string format(T&&...){return "recycle";}}
struct Logger{static void info(const std::string&) {}};
struct Device{struct Config{bool zeroMappedMemory=false;}cfg;Config& config(){return cfg;}};
class DxvkMemoryAllocator{
public:
 static constexpr unsigned MinAllocationsPerHeap=8;static constexpr uint64_t GlobalBufferAlignment=256,DedicatedChunkAddress=~uint64_t(0);
 std::mutex m_mutex;DxvkMemoryHeap heap;DxvkMemoryType m_memTypes[2];Device device;Device*m_device=&device;
 uint64_t budget=128ull<<20,used=0;unsigned created=0,freed=0,trims=0;bool failFresh=false;
 struct Pool{DxvkResourceAllocation*create(DxvkMemoryAllocator*a,DxvkMemoryType*t){return new DxvkResourceAllocation(a,t);}void free(DxvkResourceAllocation*p){delete p;}}m_allocationPool;
 /* ACTUAL_CACHE_MEMBERS */
 DxvkMemoryAllocator(){for(unsigned i=0;i<2;i++){
   m_memTypes[i].index=i;m_memTypes[i].heap=&heap;
   for(auto p:{&m_memTypes[i].mappedPool,&m_memTypes[i].devicePool})p->maxChunkSize=p->nextChunkSize=2u<<20;
 }}
 ~DxvkMemoryAllocator(){drainStreamAllocations(heap);for(auto&t:m_memTypes)for(auto*p:{&t.mappedPool,&t.devicePool})for(auto&c:p->chunks)if(c.memory.memory)freeMemory(t,c.memory.size,c.memory.memory);assert(!used);}
 unsigned getMemoryTypeMask(unsigned)const{return 3;}
 DxvkDeviceMemory allocateDeviceMemory(DxvkMemoryType&t,uint64_t n,const void*){
   n=align(n,GlobalBufferAlignment);
   if(failFresh)return {};
   if(n>budget-used){freeEmptyChunksInHeap(*t.heap,~uint64_t(0),{});++trims;}
   if(n>budget-used)return {};
   auto*p=std::malloc(n);assert(p);used+=n;t.stats.memoryAllocated+=n;++created;
   auto address=reinterpret_cast<uintptr_t>(p);return {address,n,address,address,nullptr};
 }
 void freeMemory(DxvkMemoryType&,uint64_t n,uint64_t memory){assert(used>=n);used-=n;++freed;std::free(reinterpret_cast<void*>(memory));}
 void mapDeviceMemory(DxvkDeviceMemory&m,unsigned f){assert(m.memory);if(f&2)m.mapPtr=reinterpret_cast<void*>(m.memory);}
 DxvkResourceAllocation* createAllocation(DxvkMemoryType&,const DxvkDeviceMemory&,const DxvkAllocationInfo&);
 DxvkResourceAllocation* createAllocation(DxvkMemoryType&,DxvkMemoryPool&,uint64_t,uint64_t,const DxvkAllocationInfo&);
 bool allocateChunkInPool(DxvkMemoryType&,DxvkMemoryPool&,unsigned,uint64_t,uint64_t);
 Rc<DxvkResourceAllocation> allocateMemory(const VkMemoryRequirements&,const DxvkAllocationInfo&);
 void freeAllocation(DxvkResourceAllocation*);
 void freeEmptyChunksInHeap(const DxvkMemoryHeap&,VkDeviceSize,high_resolution_clock::time_point);
 bool freeEmptyChunksInPool(DxvkMemoryType&,DxvkMemoryPool&,VkDeviceSize,high_resolution_clock::time_point){return false;}
 void updateMemoryHeapStats(unsigned){}
 void freeCachedAllocations(DxvkResourceAllocation*){assert(false);}
};
DxvkResourceAllocation::~DxvkResourceAllocation(){if(m_flags.test(DxvkAllocationFlag::OwnsMemory))m_allocator->freeMemory(*m_type,m_size,m_memory);}
void DxvkResourceAllocation::decRef(){if(m_useCount.fetch_sub(1)==1)m_allocator->freeAllocation(this);}
/* ACTUAL_CACHE */
/* ACTUAL_CREATE_DEDICATED */
/* ACTUAL_CREATE_POOLED */
/* ACTUAL_CHUNK */
/* ACTUAL_ALLOCATE */
/* ACTUAL_FREE */
/* ACTUAL_TRIM */
}
using namespace dxvk;constexpr uint64_t M=1048576;
static Rc<DxvkResourceAllocation> take(DxvkMemoryAllocator&a,uint64_t bytes,unsigned mask=1){return a.allocateMemory({bytes,256,mask},{});}
int main(){
 // Reproduce fragmentation after retirement: fresh backing is unavailable.
 {DxvkMemoryAllocator a;auto p=take(a,5*M);assert(p);auto address=p->m_memory;
  auto pendingCommand=p;p.reset();a.failFresh=true;
  assert(!take(a,5*M)); // A still-live command can NEVER lend its backing.
  pendingCommand.reset();auto retry=take(a,5*M);
#ifdef BASELINE
  assert(!retry&&a.used==0);std::cout<<"PASS baseline: retired buffer lost; fragmented backing fails 5 MiB\n";return 0;
#else
  assert(retry&&retry->m_memory==address&&a.created==1&&a.freed==0);
#endif
 }
 {DxvkMemoryAllocator a;auto p=take(a,4*M),q=take(a,5*M);auto p4=p->m_memory,p5=q->m_memory;p.reset();q.reset();a.failFresh=true;
  for(unsigned i=0;i<2000;i++){auto x=take(a,(i&1?5:4)*M);assert(x&&x->m_memory==(i&1?p5:p4));auto*bytes=static_cast<unsigned char*>(x->m_mapPtr);bytes[0]=i%251;bytes[x->m_size-1]=i%251;}
  assert(a.created==2&&a.freed==0&&a.used==9*M&&a.m_streamCacheBytes==9*M&&!a.m_memTypes[0].stats.memoryUsed);
  assert(!take(a,6*M)&&!take(a,5*M,2));
  DxvkAllocationInfo external;external.handleType=1;assert(!a.allocateMemory({5*M,256,1},external));
  DxvkAllocationInfo no;no.mode.set(DxvkAllocationMode::NoAllocation);assert(!a.allocateMemory({5*M,256,1},no));
 }
 // Identical live resource versions stay separate. Retire only one idle copy.
 {DxvkMemoryAllocator a;auto first=take(a,5*M),second=take(a,5*M);assert(first->m_memory!=second->m_memory);
  std::memset(first->m_mapPtr,11,64);std::memset(second->m_mapPtr,22,64);
  first.reset();a.failFresh=true;auto third=take(a,5*M);assert(third&&third->m_memory!=second->m_memory);
  assert(static_cast<unsigned char*>(second->m_mapPtr)[0]==22);third.reset();second.reset();
  assert(a.used==5*M&&a.m_streamCacheBytes==5*M&&a.freed==1);
 }
 // Global byte cap, slot cap, and duplicate key cap are enforced independently.
 {DxvkMemoryAllocator a;std::vector<Rc<DxvkResourceAllocation>> live;for(unsigned n:{4,5,6,7,8,9})live.push_back(take(a,n*M));
  for(auto& p:live){p.reset();assert(a.m_streamCacheBytes<=16*M);}
  assert(a.m_streamCacheBytes==15*M);}
 {DxvkMemoryAllocator a;std::vector<Rc<DxvkResourceAllocation>> live;for(unsigned n=0;n<6;n++)live.push_back(take(a,3*M+n*65536));
  for(auto& p:live)p.reset();unsigned entries=0;for(auto p:a.m_streamCache)entries+=!!p;assert(entries==4);}
 // Cache trimming makes room for a different size; a live buffer survives.
 {DxvkMemoryAllocator a;a.budget=12*M;auto live=take(a,5*M),idle=take(a,4*M);idle.reset();
  auto next=take(a,6*M);assert(next&&a.trims==1&&!a.m_streamCacheBytes&&a.used==11*M);
  assert(live->m_useCount.load()==1&&live->m_memory!=next->m_memory);}
 // Preserve zeroMappedMemory for reused allocations.
 {DxvkMemoryAllocator a;a.device.cfg.zeroMappedMemory=true;auto p=take(a,5*M);std::memset(p->m_mapPtr,0xab,p->m_size);p.reset();
  auto q=take(a,5*M);auto*bytes=static_cast<unsigned char*>(q->m_mapPtr);for(unsigned i=0;i<q->m_size;i++)assert(!bytes[i]);}
 // Imported/image/shared/sparse resources must never enter this buffer cache.
 for(unsigned which=0;which<5;which++){DxvkMemoryAllocator a;auto p=take(a,5*M);
  if(which==0)p->m_flags.set(DxvkAllocationFlag::Imported);if(which==1)p->m_image=1;
  if(which==2)p->m_kmtLocal=1;if(which==3)p->m_kmtGlobal=1;if(which==4)p->m_sparsePageTable=reinterpret_cast<void*>(1);
  p.reset();assert(!a.used&&!a.m_streamCacheBytes);}
 // Production allocator lock serializes cache mutation, while users write live data.
 {DxvkMemoryAllocator a;std::vector<std::thread> threads;for(unsigned id=1;id<=8;id++)threads.emplace_back([&,id]{for(unsigned r=0;r<1000;r++){
   auto p=take(a,(r&1?4:5)*M);assert(p);auto*bytes=static_cast<unsigned char*>(p->m_mapPtr);bytes[0]=id;bytes[p->m_size-1]=id;
   std::this_thread::yield();assert(bytes[0]==id&&bytes[p->m_size-1]==id);
  }});for(auto& t:threads)t.join();assert(a.used==a.m_streamCacheBytes&&a.m_streamCacheBytes<=9*M);}
 std::cout<<"PASS: retired-only reuse, 2000 fragmented-backing cycles, exact type/size, distinct live versions, 16 MiB/4-slot bounds, trim, zeroing, exclusions, 8 threads/8000 lifetimes\n";
}
