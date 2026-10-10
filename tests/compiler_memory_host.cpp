// SPDX-License-Identifier: MIT
// Real FEX pool/client code and production compiler permits. Only host heap
// and diagnostics are substituted; this is not a Horizon scheduler test.
#include <FEXCore/Utils/ThreadPoolAllocator.h>
#include "sd_fex_workspace.h"
#include <cassert>
#include <cstring>
#include <future>
#include <memory>
#include <thread>
#include <vector>

struct OOM {};
extern "C" void PES13FexLog(const char*) {}
extern "C" void PES13FexHeapFailure(const char*, uint64_t) { throw OOM {}; }
namespace LogMan::Throw {
[[noreturn]] void MFmt(const char* message, const fmt::format_args& args) {
  std::fprintf(stderr, "%s\n", fmt::vformat(message, args).c_str()); std::abort();
}
}
namespace FEXCore::Allocator {
void* malloc(size_t n) { return std::malloc(n); }
void free(void* p) { std::free(p); }
void* aligned_alloc(size_t a, size_t n) {
  void* p {}; assert(!::posix_memalign(&p, std::max(a, sizeof(void*)), n)); return p;
}
void aligned_free(void* p) { std::free(p); }
}
using Client = FEXCore::Utils::PoolBufferWithTimedRetirement<uint8_t*, 5000, 500>;
class Pool : public FEXCore::Utils::IntrusivePooledAllocator {
  void* Alloc(size_t n) override {
    if (Live == 4) { ++Refused; return nullptr; }
    ++Live; Peak = std::max(Peak, Live); ++Allocations;
    return std::malloc(n);
  }
  void Free(void* p, size_t) override { --Live; std::free(p); }
public:
  unsigned Live {}, Peak {}, Allocations {}, Refused {};
  void RetirementRace() {
    BufferOwnedFlag flags[5] {};
    ContainerType::iterator buffers[5];
    for (unsigned i=0;i<4;++i) buffers[i]=ClaimBuffer(16*1024*1024,&flags[i]);
    DisownBuffer(buffers[3]);
    std::unique_lock lock {AllocationMutex};
    std::promise<void> started;
    std::thread retiring([&] { started.set_value(); UnclaimBuffer(buffers[3],&flags[3]); });
    started.get_future().wait();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    // The retiring thread must leave the buffer available to the reclaimer
    // until it can atomically move it under AllocationMutex.
    assert(flags[3].load()==ClientFlags::FLAG_DISOWNED);
    buffers[4]=ClaimBufferImpl(16*1024*1024);
    (*buffers[4])->CurrentClientOwnedFlag=&flags[4];
    flags[4].store(ClientFlags::FLAG_OWNED);
    lock.unlock(); retiring.join();
    assert(flags[3].load()==ClientFlags::FLAG_FREE && flags[4].load()==ClientFlags::FLAG_OWNED);
    assert(Live==4 && Refused==0);
    for (unsigned i : {0u,1u,2u,4u}) UnclaimBuffer(buffers[i],&flags[i]);
  }
  ~Pool() { FreeAllBuffers(); assert(!Live); }
};
constexpr size_t IR = 16 * 1024 * 1024;
int main() {
  { Pool pool; pool.RetirementRace(); }
  // Reproduce the old failure: a fifth simultaneously owned IR buffer cannot
  // use any of four live owners, even though all four are perfectly reusable.
  {
    Pool pool; std::vector<std::unique_ptr<Client>> clients;
    for (unsigned i = 0; i < 4; ++i) {
      clients.emplace_back(std::make_unique<Client>(pool, IR));
      assert(clients.back()->ReownOrClaimBuffer());
    }
    Client fifth {pool, IR}; bool refused = false;
    try { fifth.ReownOrClaimBuffer(); } catch (OOM) { refused = true; }
    assert(refused && pool.Refused == 1 && pool.Live == 4);
  }
  // A fifth compiler blocks before taking any buffer; release wakes progress.
  {
    std::unique_ptr<SDFexCompilerLease> held[4];
    for (auto& p : held) p = std::make_unique<SDFexCompilerLease>();
    std::promise<void> started, done; auto finished = done.get_future();
    std::thread waiter([&] { started.set_value(); SDFexCompilerLease lease; done.set_value(); });
    started.get_future().wait();
    assert(finished.wait_for(std::chrono::milliseconds(100)) == std::future_status::timeout);
    held[0].reset();
    assert(finished.wait_for(std::chrono::seconds(5)) == std::future_status::ready);
    waiter.join();
  }
  {
    Pool pool; std::vector<std::thread> threads;
    std::atomic<unsigned> active {}, peak {}, completed {};
    for (unsigned id = 0; id < 32; ++id) threads.emplace_back([&, id] {
      Client client {pool, IR};
      for (unsigned round = 0; round < 250; ++round) {
        SDFexCompilerLease lease;
        unsigned count = ++active, previous = peak.load();
        while (previous < count && !peak.compare_exchange_weak(previous, count)) {}
        assert(count <= 4);
        auto* p = client.ReownOrClaimBuffer();
        const auto tag = uint8_t(id + round); p[0] = tag; p[IR - 1] = tag ^ 0xff;
        std::this_thread::yield();
        assert(p[0] == tag && p[IR - 1] == uint8_t(tag ^ 0xff));
        client.DelayedDisownBuffer(); --active; ++completed;
      }
    });
    for (auto& t : threads) t.join();
    assert(completed == 8000 && !active && pool.Peak <= 4 && pool.Refused == 0);
    std::printf("32 threads / 8000 compiler lifetimes: peak=%u, IR allocations=%u, OOM=%u\n",
                peak.load(), pool.Allocations, pool.Refused);
  }
  // An exceptional or early exit destroys the permit; a later burst proceeds.
  for (unsigned i = 0; i < 20; ++i) {
    try { SDFexCompilerLease lease; throw 42; } catch (int) {}
  }
  // Every supported decoder size fits its page-rounded allocation. Oversized
  // requests saturate at the original limit instead of overflowing arithmetic.
  for (uint64_t n = 0; n <= 70000; ++n) {
    const auto capacity = SDFexDecodeCapacity(n), bytes = SDFexDecodeBytes(n, 128);
    assert(capacity >= 1 && capacity <= 65536 && bytes >= capacity * 128 && !(bytes & 4095));
  }
  assert(SDFexDecodeBytes(500, 128) == 65536);
  assert(SDFexDecodeBytes(UINT64_MAX, 128) == 8388608);
  std::puts("PASS: old fifth-owner failure; retirement/reclaim race; queued progress; ownership; early exits; 70002 decoder sizes");
}
