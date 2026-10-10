// SPDX-License-Identifier: MIT
// Production FEX pools and permits; native allocation and logging substituted.
#include <FEXCore/Utils/ThreadPoolAllocator.h>
#include "sd_fex_workspace.h"
#include <cassert>
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
    if (Live == 2) { ++Refused; return nullptr; }
    ++Live; Peak = std::max(Peak, Live); ++Allocations; return std::malloc(n);
  }
  void Free(void* p, size_t) override { --Live; std::free(p); }
public:
  unsigned Live {}, Peak {}, Allocations {}, Refused {};
  ~Pool() { FreeAllBuffers(); assert(!Live); }
};
constexpr size_t IR = 16 * 1024 * 1024, Decode = 65536;
int main() {
  // A third compiler cannot claim either protected workspace until one exits.
  {
    std::unique_ptr<SDFexCompilerLease> held[2];
    for (auto& p : held) p = std::make_unique<SDFexCompilerLease>();
    std::promise<void> started, done; auto finished = done.get_future();
    std::thread waiter([&] { started.set_value(); SDFexCompilerLease lease; done.set_value(); });
    started.get_future().wait();
    assert(finished.wait_for(std::chrono::milliseconds(100)) == std::future_status::timeout);
    held[0].reset();
    assert(finished.wait_for(std::chrono::seconds(5)) == std::future_status::ready);
    waiter.join();
  }
  // Exception paths must return permits before another burst begins.
  for (unsigned i = 0; i < 20; ++i) {
    try { SDFexCompilerLease lease; throw 42; } catch (int) {}
  }
  Pool ir, decode; std::vector<std::thread> threads;
  std::atomic<unsigned> active {}, peak {}, completed {};
  for (unsigned id = 0; id < 32; ++id) threads.emplace_back([&, id] {
    Client a {ir, IR}, b {decode, Decode};
    for (unsigned round = 0; round < 250; ++round) {
      SDFexCompilerLease lease;
      unsigned count = ++active, previous = peak.load();
      while (previous < count && !peak.compare_exchange_weak(previous, count)) {}
      assert(count <= 2);
      auto* p = a.ReownOrClaimBuffer(); auto* q = b.ReownOrClaimBuffer();
      const auto tag = uint8_t(id + round);
      p[0] = q[0] = tag; p[IR-1] = q[Decode-1] = tag ^ 0xff;
      std::this_thread::yield();
      assert(p[0] == tag && q[0] == tag);
      assert(p[IR-1] == uint8_t(tag ^ 0xff) && q[Decode-1] == uint8_t(tag ^ 0xff));
      a.DelayedDisownBuffer(); b.DelayedDisownBuffer(); --active; ++completed;
    }
  });
  for (auto& t : threads) t.join();
  assert(completed == 8000 && !active && ir.Peak <= 2 && decode.Peak <= 2);
  assert(!ir.Refused && !decode.Refused);
  assert(SDFexDecodeBytes(500,128) == Decode);
  std::printf("PASS: 32 threads, 8000 paired lifetimes; peak=%u, IR=%u, decoder=%u, refusals=0; waiting and exception release\n",
              peak.load(), ir.Peak, decode.Peak);
}
