/* Production MapBuffer / UpdateMappedBuffer bodies. The resource allocator,
 * command queue, and logging are controlled boundary objects. */
#include <cassert>
#include <cstdint>
#include <cstring>
#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <utility>
#include <vector>
#define unlikely(x) (x)
#define likely(x) (x)
#define FAILED(x) ((x)<0)
using HRESULT=int32_t;
using UINT=uint32_t;
constexpr HRESULT S_OK=0, E_INVALIDARG=int32_t(0x80070057), E_OUTOFMEMORY=int32_t(0x8007000e);
constexpr UINT D3D11_COMMON_BUFFER_MAP_MODE_NONE=0, D3D11_COPY_NO_OVERWRITE=1;
struct D3D11_MAPPED_SUBRESOURCE { void* pData; UINT RowPitch, DepthPitch; };
struct ID3D11Resource {};
namespace dxvk {
template<class T>using Rc=std::shared_ptr<T>;
struct DxvkResourceAllocation { uint8_t data[512]={}; void* mapPtr(){return data;} };
struct Buffer { Rc<DxvkResourceAllocation> storage; };
struct DxvkContext {
  unsigned invalidations=0;
  void invalidateBuffer(const Rc<Buffer>& buffer,Rc<DxvkResourceAllocation> allocation) {
    buffer->storage=std::move(allocation);++invalidations;
  }
};
struct Logger { static inline unsigned errors=0; static void err(const std::string&){++errors;} };
namespace str { template<class... T>std::string format(T&&...){return "log";} }
struct D3D11Buffer:ID3D11Resource {
  struct Description { UINT ByteWidth=512; } desc;
  UINT mode=1,allocations=0;
  bool fail=false;
  Rc<Buffer> buffer=std::make_shared<Buffer>();
  std::weak_ptr<DxvkResourceAllocation> last;
  UINT GetMapMode(){return mode;}
  Description* Desc(){return &desc;}
  uint64_t GetCookie(){return 123;}
  Rc<Buffer> GetBuffer(){return buffer;}
  Rc<DxvkResourceAllocation> AllocSlice(void*) {
    ++allocations;
    if(fail)return {};
    auto result=std::make_shared<DxvkResourceAllocation>();last=result;return result;
  }
};
struct D3D11DeferredContext {
  int m_allocationCache=0;
  std::vector<std::function<void(DxvkContext*)>> commands;
  std::vector<D3D11_MAPPED_SUBRESOURCE> maps;
  template<class T>void EmitCs(T&& callback){commands.emplace_back(std::move(callback));}
  void AddMapEntry(uint64_t,D3D11_MAPPED_SUBRESOURCE sr){maps.push_back(sr);}
  D3D11_MAPPED_SUBRESOURCE FindMapEntry(uint64_t){return maps.empty()?D3D11_MAPPED_SUBRESOURCE{}:maps.back();}
  HRESULT MapBuffer(ID3D11Resource*,D3D11_MAPPED_SUBRESOURCE*);
  void UpdateMappedBuffer(D3D11Buffer*,UINT,UINT,const void*,UINT);
};
/* ACTUAL_MAP_BUFFER */
/* ACTUAL_UPDATE_BUFFER */
}
using namespace dxvk;
int main() {
  D3D11DeferredContext context;D3D11Buffer buffer;
  // Match the faulting path: valid map mode, failed 5 MiB allocation.
  buffer.fail=true;buffer.desc.ByteWidth=5*1024*1024;
  D3D11_MAPPED_SUBRESOURCE sr{reinterpret_cast<void*>(0x1234),1,2};
  assert(context.MapBuffer(&buffer,&sr)==E_OUTOFMEMORY);
  assert(!sr.pData&&!sr.RowPitch&&!sr.DepthPitch);
  assert(context.commands.empty()&&context.maps.empty()&&Logger::errors==1);
  const uint8_t data[8]={1,2,3,4,5,6,7,8};
  context.UpdateMappedBuffer(&buffer,16,sizeof(data),data,0);
  assert(context.commands.empty()&&context.maps.empty()&&Logger::errors==2);
  // Successful maps retain allocation ownership in the queued command.
  buffer.fail=false;buffer.desc.ByteWidth=512;
  assert(context.MapBuffer(&buffer,&sr)==S_OK&&sr.pData&&sr.RowPitch==512&&sr.DepthPitch==512);
  assert(context.commands.size()==1&&context.maps.size()==1&&!buffer.last.expired());
  assert(!buffer.buffer->storage);
  std::memcpy(sr.pData,data,sizeof(data));
  DxvkContext execute;context.commands[0](&execute);context.commands.clear();
  assert(execute.invalidations==1&&!buffer.last.expired());
  assert(!std::memcmp(buffer.buffer->storage->data,data,sizeof(data)));
  auto allocations=buffer.allocations;
  context.UpdateMappedBuffer(&buffer,16,sizeof(data),data,D3D11_COPY_NO_OVERWRITE);
  assert(buffer.allocations==allocations&&context.commands.empty());
  assert(!std::memcmp(buffer.buffer->storage->data+16,data,sizeof(data)));
  context.UpdateMappedBuffer(&buffer,32,sizeof(data),data,0);
  assert(buffer.allocations==allocations+1&&context.commands.size()==1);
  assert(!std::memcmp(buffer.last.lock()->data+32,data,sizeof(data)));
  buffer.mode=0;sr.pData=reinterpret_cast<void*>(0x1234);
  assert(context.MapBuffer(&buffer,&sr)==E_INVALIDARG&&!sr.pData);
  std::cout<<"PASS: deferred Map OOM HRESULT/zero output/no commands; failed update; map success/queued ownership; NO_OVERWRITE; invalid mode\n";
}
