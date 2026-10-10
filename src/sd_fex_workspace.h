// SPDX-License-Identifier: MIT
#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <mutex>

// Hold a permit before taking CodeInvalidationMutex or any compiler buffers.
// Each invocation owns one decoder and one IR buffer. Four independent locks
// bound their simultaneous lifetimes even when Horizon preempts a compiler.
// No condition-variable ABI, heap allocation, spin loop or guest-thread cap.
class SDFexCompilerLease {
  static inline std::mutex Slots[4];
  static inline std::atomic<uint32_t> Ticket {};
  static inline std::atomic<uint64_t> Waits {};
  std::unique_lock<std::mutex> Lock;
public:
  SDFexCompilerLease()
    : Lock {Slots[Ticket.fetch_add(1, std::memory_order_relaxed) & 3], std::defer_lock} {
    if (!Lock.try_lock()) {
      Lock.lock();
      const auto Count = Waits.fetch_add(1, std::memory_order_relaxed) + 1;
      if (Count <= 4 || !(Count & (Count - 1))) {
        char Message[112];
        std::snprintf(Message, sizeof(Message), "[SD-COMPILER-WAIT] slots=4 waits=%llu",
                      static_cast<unsigned long long>(Count));
        PES13FexLog(Message);
      }
    }
  }
  SDFexCompilerLease(const SDFexCompilerLease&) = delete;
  SDFexCompilerLease& operator=(const SDFexCompilerLease&) = delete;
};

// The decoder already limits blocks by MaxInst and by 65536 entries. Retain
// that ceiling; allocate only the entries this invocation can actually use.
// Page rounding is required by the native scratch ABI. Config zero still
// needs one entry so that an invalid first instruction can be represented.
constexpr size_t SDFexDecodeCapacity(uint64_t MaxInst) {
  return MaxInst == 0 ? 1 : MaxInst < 65536 ? static_cast<size_t>(MaxInst) : 65536;
}
constexpr size_t SDFexDecodeBytes(uint64_t MaxInst, size_t EntryBytes) {
  return (SDFexDecodeCapacity(MaxInst) * EntryBytes + 4095) & ~size_t(4095);
}
