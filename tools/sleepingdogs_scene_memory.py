"""Pair two FEX compiler permits with two protected native workspace pairs."""
from pathlib import Path
from f1_overlay import exact

FEX_MARKER='[SD-COMPILER-MEM] fex=v2 compile_slots=2 decoder=instruction-limit ir_mib=16'
NATIVE_MARKER='[SD-COMPILER-MEM] native=v2 decoder_reserve_kib=64 ir_reserve_mib=16 pairs=2'
RESERVE_BYTES=2*(16777216+65536)


def apply_fex(source,adapter):
    p=Path(adapter)/'sd_fex_workspace.h';s=p.read_text()
    s=exact(s,'Four independent locks','Two independent locks')
    s=exact(s,'std::mutex Slots[4]','std::mutex Slots[2]')
    s=exact(s,'std::memory_order_relaxed) & 3]','std::memory_order_relaxed) & 1]')
    s=exact(s,'[SD-COMPILER-WAIT] slots=4','[SD-COMPILER-WAIT] slots=2')
    p.write_text(s,newline='\n')
    p=Path(source)/'Source/Windows/WOW64/Module.cpp'
    p.write_text(exact(p.read_text(),
        '[SD-COMPILER-MEM] fex=v1 compile_slots=4 decoder=instruction-limit ir_mib=16',FEX_MARKER),newline='\n')


def apply_native(source,adapter):
    p=Path(adapter)/'f1_scratch.h';s=p.read_text()
    s=exact(s,'usual four simultaneous compiler workspaces','two simultaneous compiler workspaces')
    s=exact(s,'Keep the four pairs dedicated','Keep the two pairs dedicated')
    s=exact(s,'the eight reserve owners','the four reserve owners')
    s=exact(s,'#define F1_SCRATCH_SLOTS 8','#define F1_SCRATCH_SLOTS 4')
    s=exact(s,'size_t size = i < 4 ? 64u * 1024u : 16u * 1024u * 1024u;',
        'size_t size = i < 2 ? 64u * 1024u : 16u * 1024u * 1024u;')
    p.write_text(s,newline='\n')
    p=Path(source)/'wine-nx-probe/source/runtime.c'
    p.write_text(exact(p.read_text(),
        '[SD-COMPILER-MEM] native=v1 decoder_reserve_kib=64 ir_reserve_mib=16 pairs=4',NATIVE_MARKER),newline='\n')
