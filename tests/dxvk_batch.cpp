#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <random>
#include "baseline.h"
#include "candidate.h"

using Type = dxvk::GpuFlushType;
using OldType = baseline::GpuFlushType;
using Tracker = dxvk::GpuFlushTracker;
using OldTracker = baseline::GpuFlushTracker;

int main() {
  uint64_t grid = 0;
  // The original and candidate production bodies are compiled separately.
  // With the option disabled every public decision must be identical.
  for (uint32_t maxType = 0; maxType < 4; maxType++) {
    for (uint32_t type = 0; type < 4; type++) {
      for (uint32_t pending = 0; pending < 12; pending++) {
        for (uint32_t chunks = 0; chunks <= 40; chunks++) {
          for (uint64_t cost : {0ull, 1499ull, 1500ull, 1501ull}) {
            OldTracker old{OldType(maxType)};
            Tracker off(Type(maxType), false), on(Type(maxType), true);
            old.notifyFlush(100, 30);
            off.notifyFlush(100, 30);
            on.notifyFlush(100, 30);
            bool expected = old.considerFlush(OldType(type), 100+chunks, 30-pending, cost);
            bool actual = off.considerFlush(Type(type), 100+chunks, 30-pending, cost);
            bool batched = on.considerFlush(Type(type), 100+chunks, 30-pending, cost);
            assert(actual == expected);
            assert(uint32_t(off.getPendingType()) == uint32_t(old.getPendingType()));
            assert(off.sdDeferredHints() == 0);
            // Only hints may change, and only by postponing a small batch.
            assert(!batched || expected);
            if (type < 2 || chunks >= 12 || pending < 2 || cost >= 1500 || type > maxType)
              assert(batched == expected);
            grid++;
          }
        }
      }
    }
  }

  // Stateful disabled-mode differential regression, including wraparound
  // of the submission ID exposed by the existing uint32_t API.
  std::mt19937 rng(732540);
  OldTracker original{OldType::ImplicitWeakHint};
  Tracker disabled{Type::ImplicitWeakHint, false};
  uint64_t chunk = 0, submitted = 0xffffffffull - 1000;
  uint32_t completed = uint32_t(submitted);
  for (unsigned i = 0; i < 200000; i++) {
    chunk += rng() % 3;
    uint32_t type = rng() % 4;
    uint64_t cost = rng() % 2000;
    bool a = original.considerFlush(OldType(type), chunk, completed, cost);
    bool b = disabled.considerFlush(Type(type), chunk, completed, cost);
    assert(a == b);
    assert(uint32_t(original.getPendingType()) == uint32_t(disabled.getPendingType()));
    if (a) {
      original.notifyFlush(chunk, ++submitted);
      disabled.notifyFlush(chunk, submitted);
    }
    if (rng() % 3 == 0) completed = uint32_t(submitted);
  }

  // A readback must eventually progress as earlier GPU work completes,
  // even if its command list is smaller than the hint batch threshold.
  Tracker readback{Type::ImplicitWeakHint, true};
  readback.notifyFlush(20, 10);
  assert(!readback.considerFlush(Type::ImplicitStrongHint, 23, 8, 10));
  assert(readback.getPendingType() == Type::ImplicitStrongHint);
  assert(!readback.considerFlush(Type::ImplicitSynchronization, 23, 8, 10));
  assert(readback.considerFlush(Type::ImplicitSynchronization, 23, 9, 10));
  readback.notifyFlush(23, 11);
  assert(readback.getPendingType() == Type::None);
  assert(!readback.considerFlush(Type::ExplicitFlush, 23, 9, 10)); // no commands
  assert(readback.considerFlush(Type::ExplicitFlush, 24, 9, 10));

  // Deferred hints are bounded by 12 chunks and the existing cost gate.
  Tracker bounded{Type::ImplicitWeakHint, true};
  bounded.notifyFlush(0, 10);
  for (unsigned i = 1; i < 12; i++)
    assert(!bounded.considerFlush(Type::ImplicitStrongHint, i, 8, 10));
  assert(bounded.sdDeferredHints() == 11);
  assert(bounded.considerFlush(Type::ImplicitStrongHint, 12, 8, 10));
  bounded.notifyFlush(12, 11);
  assert(bounded.considerFlush(Type::ImplicitStrongHint, 15, 9, 1500));

  // Default-constructed policy remains off (other DXVK users/D3D9).
  Tracker defaultPolicy{Type::ImplicitWeakHint};
  assert(!defaultPolicy.sdBatchingEnabled());
  assert(bounded.sdBatchingEnabled());
  std::printf("PASS grid=%llu stateful=200000 readback=progress explicit=preserved bound=12 defaults=off\n",
              (unsigned long long)grid);
}
