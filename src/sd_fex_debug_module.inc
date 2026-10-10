// SPDX-License-Identifier: MIT
// Registry is process-wide because compiled code is shared; checks use thread-local state.
static std::mutex SDDebugTargetsMutex;
static std::unordered_map<uint32_t, bool> SDDebugTargets;
static std::atomic<bool> SDDebugTargetsPresent {false};

bool SDHasDebugTargets() {
  return SDDebugTargetsPresent.load(std::memory_order_acquire);
}

bool SDIsDebugTarget(uint64_t address) {
  if (address > UINT32_MAX || !SDHasDebugTargets()) return false;
  std::scoped_lock lock(SDDebugTargetsMutex);
  return SDDebugTargets.contains(static_cast<uint32_t>(address));
}

// Caller holds ThreadCreationMutex, just like BTCpuFlushInstructionCache2.
static void SDRegisterDebugTarget(uint32_t address) {
  bool added;
  {
    std::scoped_lock lock(SDDebugTargetsMutex);
    added = SDDebugTargets.emplace(address, true).second;
    SDDebugTargetsPresent.store(true, std::memory_order_release);
  }
  // Never hold the registry lock while waiting for the compilation lock.
  if (added) InvalidationTracker->InvalidateAlignedInterval(address, 1, false);
}

static void SDSyncDebugContext(FEXCore::Core::InternalThreadState* thread, const WOW64_CONTEXT* context) {
  auto& debug = thread->CurrentFrame->SDDebug;
  const uint32_t addresses[] = {context->Dr0, context->Dr1, context->Dr2, context->Dr3};
  const auto mask = SDExecDebugMask(context->Dr7);
  const bool changed = debug.Enabled != mask || memcmp(debug.Address, addresses, sizeof(addresses));
  memcpy(debug.Address, addresses, sizeof(addresses));
  debug.Enabled = mask;
  debug.Hit = 0;
  const bool resume = context->EFlags & (1u << FEXCore::X86State::RFLAG_RF_LOC);
  if (changed || resume) {
    std::scoped_lock lock(ThreadCreationMutex);
    if (changed) {
      for (unsigned i = 0; i != 4; ++i)
        if (mask & (1u << i)) SDRegisterDebugTarget(addresses[i]);
    }
    if (resume) {
      debug.ResumeRIP = context->Eip;
      SDRegisterDebugTarget(context->Eip);
    }
  }
  if (changed && mask) {
    static std::atomic<unsigned> logged {0};
    if (logged.fetch_add(1, std::memory_order_relaxed) < 16)
      PES13FexLog(fextl::fmt::format("[SD-DB] arm tid={} mask={:x} dr0={:08x} dr1={:08x} dr2={:08x} dr3={:08x}",
        GetCurrentThreadId(), mask, addresses[0], addresses[1], addresses[2], addresses[3]).c_str());
  }
}

static void SDApplyDebugException(FEXCore::Core::InternalThreadState* thread, WOW64_CONTEXT* context) {
  auto& debug = thread->CurrentFrame->SDDebug;
  const auto hit = debug.Hit;
  debug.Hit = 0;
  if (!hit) return;
  context->Dr6 |= hit;
  context->Dr7 &= ~(1u << 13); // GD is cleared on entry to the debug handler.
  context->ContextFlags |= WOW64_CONTEXT_DEBUG_REGISTERS;
  static std::atomic<unsigned> logged {0};
  if (logged.fetch_add(1, std::memory_order_relaxed) < 16)
    PES13FexLog(fextl::fmt::format("[SD-DB] hit tid={} eip={:08x} mask={:x} dr6={:08x}",
      GetCurrentThreadId(), context->Eip, hit, context->Dr6).c_str());
}
