"""Bound concurrent compiler lifetimes and right-size the x86 decoder buffer."""
from pathlib import Path
from port_common import ROOT, sha
from f1_overlay import exact


def apply_fex(source, adapter):
    source, adapter = Path(source), Path(adapter)
    changed = {}
    def edit(name, old, new):
        p = source / name
        p.write_text(exact(p.read_text(), old, new), encoding='utf-8', newline='\n')
        changed[name] = sha(p)
    (adapter / 'sd_fex_workspace.h').write_bytes((ROOT / 'src/sd_fex_workspace.h').read_bytes())
    edit('FEXCore/include/FEXCore/Utils/ThreadPoolAllocator.h', '''    // Transition the buffer to free, unclaiming if it wasn't free prior.
    if (ClientFlag->exchange(ClientFlags::FLAG_FREE) != ClientFlags::FLAG_FREE) {
      std::unique_lock lk {AllocationMutex};
      UnclaimBufferImpl(Buffer);
    }''', '''    // Publish FREE only while holding the allocator lock. Otherwise a
    // retiring client can expose a buffer that is neither reclaimable nor in
    // UnclaimedBuffers, forcing an unnecessary fifth allocation at pressure.
    // A competing reclaimer may win while we wait; recheck under the lock so
    // a stale iterator can never unclaim the buffer from its new owner.
    std::unique_lock lk {AllocationMutex};
    if (ClientFlag->exchange(ClientFlags::FLAG_FREE) != ClientFlags::FLAG_FREE) {
      UnclaimBufferImpl(Buffer);
    }''')
    core = 'FEXCore/Source/Interface/Core/Core.cpp'
    edit(core, '#include "sd_fex_debug.h"', '#include "sd_fex_debug.h"\n#include "sd_fex_workspace.h"')
    anchor = '  // Invalidate might take a unique lock on this, to guarantee that during invalidation no code gets compiled'
    # Both normal compilation and single-step must enter before decoder setup
    # and before the shared invalidation lock. Their RAII unlock order is then
    # invalidation -> permit, including cache hits and compilation failures.
    p = source / core; s = p.read_text(); assert s.count(anchor) == 2
    p.write_text(s.replace(anchor, '  SDFexCompilerLease HorizonCompilerLease;\n\n' + anchor), newline='\n')
    changed[core] = sha(p)
    edit(core, '''          Thread->OpDispatcher->DelayedDisownBuffer();
          return {std::nullopt, 0, 0, 0, 0};''', '''          Thread->OpDispatcher->DelayedDisownBuffer();
          Thread->FrontendDecoder->DelayedDisownBuffer();
          return {std::nullopt, 0, 0, 0, 0};''')
    front = 'FEXCore/Source/Interface/Core/Frontend.cpp'
    edit(front, '#include "Interface/Core/Frontend.h"',
         '#include "Interface/Core/Frontend.h"\n#include "sd_fex_workspace.h"')
    edit(front, 'PoolObject {CTX->FrontendAllocator, sizeof(FEXCore::X86Tables::DecodedInst) * DefaultDecodedBufferSize}',
         'PoolObject {CTX->FrontendAllocator, 0}')
    edit(front, '  DecodedBuffer = PoolObject.ReownOrClaimBuffer();', '''  DecodedCapacity = SDFexDecodeCapacity(MaxInst);
  DecodedBuffer = PoolObject.ReownOrClaimBuffer(SDFexDecodeBytes(MaxInst, sizeof(FEXCore::X86Tables::DecodedInst)));''')
    edit(front, '''    while (1) {
      InstructionSize = 0;''', '''    while (1) {
      // Invalid instructions and overlapping branches may leave the loop
      // before its usual FinalInstruction update. Check before every write,
      // including a resumed decode, so a compact buffer cannot overflow.
      if (DecodedSize >= DecodedCapacity) {
        FinalInstruction = true;
        break;
      }
      InstructionSize = 0;''')
    edit(front, 'DecodedSize >= DefaultDecodedBufferSize', 'DecodedSize >= DecodedCapacity')
    edit('FEXCore/Source/Interface/Core/Frontend.h',
         '  static constexpr size_t DefaultDecodedBufferSize = 0x10000;', '  size_t DecodedCapacity {};')
    module = 'Source/Windows/WOW64/Module.cpp'
    anchor = '  PES13FexLog("[SD-DB] execution-breakpoints v1 DR0-DR3 per-thread");'
    edit(module, anchor, anchor + '\n  PES13FexLog("[SD-COMPILER-MEM] fex=v1 compile_slots=4 decoder=instruction-limit ir_mib=16");')
    return changed


def apply_native(source, adapter):
    p = Path(adapter) / 'f1_scratch.h'
    s = exact(p.read_text(), 'size_t size = (i < 4 ? 8u : 16u) * 1024 * 1024;',
              'size_t size = i < 4 ? 64u * 1024u : 16u * 1024u * 1024u;')
    s = s.replace('Same sizes/ABI as FEX;', 'Compact decoder / original IR sizes;')
    p.write_text(s, newline='\n')
    p = Path(source) / 'wine-nx-probe/source/runtime.c'
    anchor = 'log_line("[SD-MEMORY-BUDGET] build=v1 gpu_reserve_mib=128 stack_reserve_max_kib=1024");'
    p.write_text(exact(p.read_text(), anchor, anchor + '\n'
        '                        log_line("[SD-COMPILER-MEM] native=v1 decoder_reserve_kib=64 ir_reserve_mib=16 pairs=4");'), newline='\n')
