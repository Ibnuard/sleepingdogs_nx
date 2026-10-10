// SPDX-License-Identifier: MIT
#include "Interface/Context/Context.h"
#include "Interface/Core/Frontend.h"
#include <FEXCore/Debug/InternalThreadState.h>
#include <cstddef>
using D = FEXCore::Frontend::Decoder;
using C = FEXCore::Context::ContextImpl;
using T = FEXCore::Core::InternalThreadState;
using F = FEXCore::Core::CpuStateFrame;
using S = FEXCore::Core::CPUState;
using P = FEXCore::Utils::PooledAllocatorVirtual;
using B = D::DecodedBlocks;
using I = D::DecodedBlockInformation;
extern "C" __attribute__((used,section(".sdmeta"))) const uint64_t sd_compiler_layout[] = {
 sizeof(D), sizeof(C), sizeof(T), sizeof(F), sizeof(P), sizeof(FEXCore::X86Tables::DecodedInst),
 offsetof(D, CTX), offsetof(D, PoolObject), offsetof(D, DecodedCapacity), offsetof(D, DecodedBuffer),
 offsetof(D, DecodedSize), offsetof(D, MaxInst), offsetof(D, FinalInstruction), offsetof(D, Paused),
 offsetof(D, BlockInfo), offsetof(D, ExecutableRangeBase), offsetof(D, ExecutableRangeEnd),
 offsetof(C, FrontendAllocator), offsetof(C, Config.MaxInstPerBlock), offsetof(C, Config.Multiblock),
 offsetof(T, CTX), offsetof(T, CurrentFrame), offsetof(F, State.segment_arrays),
 offsetof(I, Blocks), sizeof(B), offsetof(B, Entry), offsetof(B, Size), offsetof(B, NumInstructions),
 offsetof(B, DecodedInstructions), offsetof(B, BlockStatus), offsetof(D, BlocksToDecode),
 offsetof(D, BlockStartOffset), offsetof(D, EntryBlock), offsetof(D, EraseBlock),
 offsetof(F, Thread), offsetof(C, SyscallHandler)
};
