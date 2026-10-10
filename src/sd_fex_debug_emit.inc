// SPDX-License-Identifier: MIT
// Included in the real JIT and the host emitter regression harness.
// Only TMP1/2/3 are clobbered; no instruction changes NZCV or guest registers.
using Frame = FEXCore::Core::CpuStateFrame;
using ARMEmitter::Size;
ARMEmitter::ForwardLabel done, check;
LoadConstant(Size::i32Bit, TMP2, DebugRIP);

// NtContinue/SetThreadContext RF applies to the first resumed instruction.
// That RIP is registered too, even when it is not a breakpoint address.
ldr(TMP1.W(), STATE, offsetof(Frame, SDDebug.ResumeRIP));
eor(Size::i32Bit, TMP1, TMP1, TMP2);
(void)cbnz(Size::i32Bit, TMP1, &check);
ldrb(TMP1, STATE, offsetof(Frame, State.flags[FEXCore::X86State::RFLAG_RF_LOC]));
strb(ARMEmitter::WReg::zr, STATE, offsetof(Frame, State.flags[FEXCore::X86State::RFLAG_RF_LOC]));
(void)cbnz(Size::i32Bit, TMP1, &done);
(void)Bind(&check);

LoadConstant(Size::i32Bit, TMP3, 0);
for (unsigned i = 0; i != 4; ++i) {
  ARMEmitter::ForwardLabel next;
  ldr(TMP1.W(), STATE, offsetof(Frame, SDDebug.Enabled));
  (void)tbz(TMP1, i, &next);
  ldr(TMP1.W(), STATE, offsetof(Frame, SDDebug.Address) + i * sizeof(uint32_t));
  eor(Size::i32Bit, TMP1, TMP1, TMP2);
  (void)cbnz(Size::i32Bit, TMP1, &next);
  orr(Size::i32Bit, TMP3, TMP3, 1u << i);
  (void)Bind(&next);
}
(void)cbz(Size::i32Bit, TMP3, &done);
str(TMP3.W(), STATE, offsetof(Frame, SDDebug.Hit));
str(TMP2, STATE, offsetof(Frame, State.rip));
ResetStack();
Frame::SynchronousFaultDataStruct fault = {
  .FaultToTopAndGeneratedException = true,
  .Signal = FEXCore::Core::FAULT_SIGTRAP,
  .TrapNo = FEXCore::X86State::X86_TRAPNO_DB,
  .si_code = 4,
  .err_code = 0,
};
uint64_t packed = 0;
memcpy(&packed, &fault, sizeof(fault));
LoadConstant(Size::i64Bit, TMP1, packed);
str(TMP1, STATE, offsetof(Frame, SynchronousFaultData));
ldr(TMP1, STATE, offsetof(Frame, Pointers.GuestSignal_SIGTRAP));
br(TMP1);
(void)Bind(&done);
