// SPDX-License-Identifier: MIT
#include <CodeEmitter/Emitter.h>
// Use the production Windows frame layout without changing host library headers.
#define _WIN32 1
#include <FEXCore/Core/CoreState.h>
#undef _WIN32
#include <FEXCore/Core/SignalDelegator.h>
#include "sd_fex_debug.h"
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <thread>
#include <unordered_map>

// Exercise the production registry/context glue with an invalidation boundary mock.
namespace FEXCore::Core { struct InternalThreadState { CpuStateFrame* CurrentFrame; }; }
struct WOW64_CONTEXT {
  uint32_t ContextFlags {}, Dr0 {}, Dr1 {}, Dr2 {}, Dr3 {}, Dr6 {}, Dr7 {}, Eip {}, EFlags {};
};
constexpr uint32_t WOW64_CONTEXT_DEBUG_REGISTERS = 0x10010;
static std::mutex ThreadCreationMutex;
struct Invalidator {
  std::vector<uint64_t> addresses;
  void InvalidateAlignedInterval(uint64_t address, uint64_t size, bool free) {
    if (size != 1 || free) std::abort();
    addresses.push_back(address);
  }
} invalidator;
static auto InvalidationTracker = &invalidator;
static unsigned GetCurrentThreadId() { return 4; }
extern "C" void PES13FexLog(const char*) {}
extern "C" void* PES13FexWriteAlias(const void* p, uint64_t) { return const_cast<void*>(p); }
namespace fextl::fmt { using ::fmt::format; }
#include "sd_fex_debug_module.inc"

static void CheckRegistry() {
  using namespace FEXCore::Core;
  CpuStateFrame first {}, second {};
  InternalThreadState thread {&first}, other {&second};
  WOW64_CONTEXT c {.Dr0 = 0x401234, .Dr1 = 0x405678, .Dr7 = 5};
  auto require = [](bool ok) { if (!ok) std::abort(); };
  require(!SDHasDebugTargets());
  SDSyncDebugContext(&thread, &c);
  require(invalidator.addresses.size() == 2 && first.SDDebug.Enabled == 3);
  require(SDIsDebugTarget(c.Dr0) && SDIsDebugTarget(c.Dr1) && !SDIsDebugTarget(0x100401234ULL));
  SDSyncDebugContext(&thread, &c);
  require(invalidator.addresses.size() == 2); // No re-invalidation on each syscall.
  c.Dr7 = 0; SDSyncDebugContext(&thread, &c);
  require(first.SDDebug.Enabled == 0 && SDIsDebugTarget(c.Dr0));
  c.Dr0 = 0x409abc; c.Dr7 = 2; SDSyncDebugContext(&other, &c);
  require(second.SDDebug.Enabled == 1 && first.SDDebug.Enabled == 0);
  require(invalidator.addresses.size() == 3 && SDIsDebugTarget(c.Dr0));
  c.EFlags = 1u << 16; c.Eip = 0x500000; SDSyncDebugContext(&other, &c);
  require(second.SDDebug.ResumeRIP == c.Eip && SDIsDebugTarget(c.Eip));
  require(invalidator.addresses.size() == 4);
  c.Dr6 = 0x4000; c.Dr7 |= 1u << 13; second.SDDebug.Hit = 9;
  SDApplyDebugException(&other, &c);
  require(c.Dr6 == 0x4009 && !(c.Dr7 & (1u << 13)) && c.ContextFlags == 0x10010);
  require(second.SDDebug.Hit == 0 && c.Eip == 0x500000 && c.EFlags == (1u << 16));
  auto writer = [] {
    for (unsigned i = 0; i < 200; ++i) {
      std::scoped_lock lock(ThreadCreationMutex);
      SDRegisterDebugTarget(0x600000 + i);
    }
  };
  std::thread a(writer), b(writer);
  for (unsigned i = 0; i < 500; ++i) (void)SDIsDebugTarget(0x600000 + i % 200);
  a.join(); b.join();
  require(invalidator.addresses.size() == 204);
}

namespace FEXCore::Allocator {
void* aligned_alloc(size_t a, size_t s) {
  void* p = nullptr;
  if (::posix_memalign(&p, std::max(a, sizeof(void*)), s)) std::abort();
  return p;
}
void aligned_free(void* p) { std::free(p); }
}
namespace LogMan::Throw {
[[noreturn]] void MFmt(const char* f, const fmt::format_args& a) {
  std::fprintf(stderr, "%s\n", fmt::vformat(f, a).c_str()); std::abort();
}
}
namespace LogMan::Msg {
void MFmtImpl(DebugLevels, const char* f, const fmt::format_args& a) {
  std::fprintf(stderr, "%s\n", fmt::vformat(f, a).c_str());
}
}
namespace FEXCore::Assert { [[noreturn]] void ForcedAssert() { std::abort(); } }

struct Probe : ARMEmitter::Emitter {
  using Emitter::Emitter;
  static constexpr auto STATE = ARMEmitter::XReg::x28;
  static constexpr auto TMP1 = ARMEmitter::XReg::x0;
  static constexpr auto TMP2 = ARMEmitter::XReg::x1;
  static constexpr auto TMP3 = ARMEmitter::XReg::x2;
  void LoadConstant(ARMEmitter::Size size, ARMEmitter::Register reg, uint64_t value) {
    movz(size, reg, value & 0xffff, 0);
    for (unsigned shift = 16; shift < (size == ARMEmitter::Size::i32Bit ? 32 : 64); shift += 16)
      if ((value >> shift) & 0xffff) movk(size, reg, (value >> shift) & 0xffff, shift);
  }
  // Exercise a real spill-stack unwind on the trap path, none on the fallthrough.
  void ResetStack() { add(ARMEmitter::Size::i64Bit, ARMEmitter::Reg::rsp, ARMEmitter::Reg::rsp, 32); }
  void Emit(uint32_t DebugRIP) {
#include "sd_fex_debug_emit.inc"
    ret();
  }
};

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  CheckRegistry();
  uint8_t bytes[4096] {};
  Probe probe(bytes, sizeof(bytes)); probe.Emit(0x4c0a8a);
  auto f = std::fopen(argv[1], "wb"); if (!f) return 3;
  std::fwrite(bytes, 1, probe.GetCursorOffset(), f); std::fclose(f);
  using Frame = FEXCore::Core::CpuStateFrame;
  std::printf("{\"frame_size\":%zu,\"address\":%zu,\"enabled\":%zu,\"hit\":%zu,\"resume_rip\":%zu,"
              "\"rf\":%zu,\"rip\":%zu,\"fault\":%zu,\"signal\":%zu,\"bytes\":%zu}\n",
    sizeof(Frame), offsetof(Frame, SDDebug.Address), offsetof(Frame, SDDebug.Enabled),
    offsetof(Frame, SDDebug.Hit), offsetof(Frame, SDDebug.ResumeRIP),
    offsetof(Frame, State.flags[FEXCore::X86State::RFLAG_RF_LOC]), offsetof(Frame, State.rip),
    offsetof(Frame, SynchronousFaultData), offsetof(Frame, Pointers.GuestSignal_SIGTRAP), probe.GetCursorOffset());
  // Decode every slot, local/global enables and condition/length encodings.
  for (unsigned slot = 0; slot < 4; ++slot)
    for (unsigned enable = 0; enable < 4; ++enable)
      for (unsigned mode = 0; mode < 16; ++mode) {
        const auto dr7 = (enable << (slot * 2)) | (mode << (16 + slot * 4));
        const auto expected = enable && !mode ? 1u << slot : 0;
        if (SDExecDebugMask(dr7) != expected) return 4;
      }
  if (SDExecDebugMask(0x155) != 15) return 5;
}
