"""Report the actual loaded FEX spare policy, without changing PE code at runtime."""
from pathlib import Path
from f1_overlay import exact


def apply(adapter: Path):
    path=adapter/'wine_bridge.c'
    text=path.read_text()
    helper='''
/* The private F1 PE patch preserves this reviewed function's location and
 * following bytes. Check the mapped image before reporting its memory policy. */
static void f1_fex_memory_policy(HMODULE module)
{
    static const unsigned char demand_entry[32] = {
        0xc0,0x03,0x5f,0xd6,0xf5,0x5b,0x01,0xa9,0xfe,0x13,0x00,0xf9,0x95,0x15,0x00,0xd0,
        0xa8,0x42,0x5f,0x39,0x1f,0x05,0x00,0x71,0xe1,0x05,0x00,0x54,0x88,0x15,0x00,0xd0
    };
    const IMAGE_NT_HEADERS *nt = RtlImageNtHeader(module);
    int demand = nt && nt->FileHeader.Machine == IMAGE_FILE_MACHINE_ARM64 &&
        nt->OptionalHeader.SizeOfImage >= 1355080 + sizeof(demand_entry) &&
        !memcmp((const unsigned char *)module + 1355080, demand_entry, sizeof(demand_entry));
    wine_nx_runtime_trace(demand ?
        "[F1-CODE-MEM] eager_spare=off saved_idle_bytes=134217728; active cache and growth unchanged" :
        "[F1-CODE-MEM] eager_spare=unverified; install the matching libwow64fex.dll from the full update");
}

'''
    text=exact(text,'NTSTATUS pes13_fex_install_module(HMODULE module)',helper+'NTSTATUS pes13_fex_install_module(HMODULE module)')
    text=exact(text,'    pes13_fex_set_logger(wine_nx_runtime_trace);',
        '    f1_fex_memory_policy(module);\n    pes13_fex_set_logger(wine_nx_runtime_trace);')
    path.write_text(text)
