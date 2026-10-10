"""Generic WoW64 x86 execution-breakpoint support for the pinned FEX runtime."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]

def apply(source, adapter):
    changed = {}
    def edit(name, old, new):
        path = source / name
        text = path.read_text(encoding='utf-8')
        if text.count(old) != 1:
            raise ValueError(f'{name}: expected one anchor {old[:100]!r}')
        path.write_text(text.replace(old, new), encoding='utf-8', newline='\n')
        changed[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    for name in ('sd_fex_debug.h', 'sd_fex_debug_emit.inc', 'sd_fex_debug_module.inc'):
        (adapter / name).write_bytes((ROOT / 'src' / name).read_bytes())
    edit('FEXCore/include/FEXCore/Core/CoreState.h', '  JITPointers Pointers;\n', '''  JITPointers Pointers;
  // Appended: existing frame offsets and host ABI remain unchanged.
  struct {
    uint32_t Address[4] {};
    uint32_t Enabled {};
    uint32_t Hit {};
    uint32_t ResumeRIP {};
  } SDDebug;
''')
    edit('FEXCore/Source/Interface/IR/IR.json', '      "GuestOpcode u32:$GuestEntryOffset": {', '''      "SDDebugCheck u32:$GuestEntryOffset": {
        "HasSideEffects": true
      },
      "GuestOpcode u32:$GuestEntryOffset": {''')
    edit('FEXCore/Source/Interface/IR/Passes/RedundantFlagCalculationElimination.cpp',
         'static constexpr FlagInfo ClassifyConst(IROps Op) {\n  switch (Op) {',
         '''static constexpr FlagInfo ClassifyConst(IROps Op) {
  switch (Op) {
  case OP_SDDEBUGCHECK: return FlagInfo::Pack({.Read = FLAG_ALL});''')
    core = 'FEXCore/Source/Interface/Core/Core.cpp'
    edit(core, '#include "horizon_host.h"', '#include "horizon_host.h"\n#include "sd_fex_debug.h"')
    anchor = '        if (ExtendedDebugInfo || Thread->OpDispatcher->CanHaveSideEffects(TableInfo, DecodedInfo)) {'
    edit(core, anchor, '''        if (SDIsDebugTarget(InstAddress)) {
          // Commit all state before a synchronous, pre-instruction #DB fault.
          // The new opcode itself preserves NZCV and all SRA registers.
          Thread->OpDispatcher->FlushRegisterCache();
          Thread->OpDispatcher->_GuestOpcode(InstAddress - GuestRIP);
          Thread->OpDispatcher->_SDDebugCheck(InstAddress - GuestRIP);
        }

''' + anchor)
    edit(core, '    if (DiskCache.IsReadingDiskCache()) {',
         '    if (DiskCache.IsReadingDiskCache() && !SDHasDebugTargets()) {')
    edit(core, '    if (DiskCacheGuestCodeKey) {', '    if (DiskCacheGuestCodeKey && !SDHasDebugTargets()) {')
    edit('FEXCore/Source/Interface/Core/JIT/MiscOps.cpp', 'DEF_OP(GuestOpcode) {', '''DEF_OP(SDDebugCheck) {
  auto Op = IROp->C<IR::IROp_SDDebugCheck>();
  const uint32_t DebugRIP = static_cast<uint32_t>(Entry + Op->GuestEntryOffset);
#include "sd_fex_debug_emit.inc"
}

DEF_OP(GuestOpcode) {''')
    module = 'Source/Windows/WOW64/Module.cpp'
    edit(module, '#include "horizon_host.h"', '#include "horizon_host.h"\n#include "sd_fex_debug.h"')
    edit(module, 'namespace Context {', '#include "sd_fex_debug_module.inc"\n\nnamespace Context {')
    edit(module, '  State.rip = Context->Eip;', '  SDSyncDebugContext(Thread, Context);\n  State.rip = Context->Eip;')
    edit(module, '  if (GuestException.ExceptionCode == EXCEPTION_SINGLE_STEP) {',
         '  if (GuestException.ExceptionCode == EXCEPTION_SINGLE_STEP) {\n    SDApplyDebugException(Thread, WowContext);')
    edit(module, '  PES13FexLog("[FEX3-FP] context v1 MXCSR, x87 TOP/F64, legacy registers");',
         '  PES13FexLog("[SD-DB] execution-breakpoints v1 DR0-DR3 per-thread");\n  PES13FexLog("[FEX3-FP] context v1 MXCSR, x87 TOP/F64, legacy registers");')
    # Same already-approved demand-allocation behavior, expressed in source.
    path = adapter / 'module_host.cpp'
    text = path.read_text(encoding='utf-8')
    start = text.index('extern "C" void PES13FexPrimeCodeCache(uint64_t size) {')
    end = text.index('\nextern "C" void *PES13FexAllocateCode', start)
    text = text[:start] + 'extern "C" void PES13FexPrimeCodeCache(uint64_t) {}\n' + text[end:]
    path.write_text(text, encoding='utf-8', newline='\n')
    return changed
