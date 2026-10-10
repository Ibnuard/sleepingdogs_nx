// SPDX-License-Identifier: MIT
#include "Interface/Core/JIT/JITClass.h"
using J = FEXCore::CPU::Arm64JITCore;
using F = FEXCore::Core::CpuStateFrame;
using O = FEXCore::IR::IROp_SDDebugCheck;
// Compiled by the production ARM64 compiler, never linked into the shipped DLL.
extern "C" __attribute__((used, section(".sdmeta"))) const uint64_t SDDebugLayout[] = {
  sizeof(J), offsetof(J, BufferBase), offsetof(J, CurrentOffset), offsetof(J, Size),
  offsetof(J, WritableBase), offsetof(J, Entry), offsetof(J, SpillSlots),
  sizeof(O), offsetof(O, GuestEntryOffset), sizeof(F), offsetof(F, SDDebug),
  offsetof(F, SDDebug.Enabled), offsetof(F, SDDebug.Hit), offsetof(F, SDDebug.ResumeRIP),
  offsetof(F, State.rip), offsetof(F, State.flags[FEXCore::X86State::RFLAG_RF_LOC]),
  offsetof(F, SynchronousFaultData), offsetof(F, Pointers.GuestSignal_SIGTRAP),
};
