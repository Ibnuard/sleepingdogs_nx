"""Native direct data arena for the original game's fixed 1000 MiB pool."""
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT


def apply(source: Path):
    native = source / 'wine-nx-probe/source'
    unix = source / 'dlls/ntdll/unix'
    for directory in (native, unix):
        (directory / 'sd_guest_arena.h').write_bytes((ROOT / 'src/sd_guest_arena.h').read_bytes())
    (native / 'sd_guest_arena.c').write_bytes((ROOT / 'src/sd_guest_arena.c').read_bytes())
    (unix / 'sd_guest_view.inc').write_bytes((ROOT / 'src/sd_guest_view.inc').read_bytes())
    cmake = source / 'wine-nx-probe/CMakeLists.txt'
    with cmake.open('a') as f:
        f.write('\ntarget_sources(wine-nx-runtime PRIVATE source/sd_guest_arena.c)\n')
    p = native / 'runtime.c'
    s = exact(p.read_text(), '    wine_nx_f1_native_stacks_init();\n    wine_nx_f1_gpu_heap_init();',
              '    wine_nx_f1_native_stacks_init();\n    sd_guest_arena_init();\n    wine_nx_f1_gpu_heap_init();')
    s = exact(s, '#include "f1_native_stacks.h"', '#include "f1_native_stacks.h"\n#include "sd_guest_arena.h"')
    p.write_text(s)
    # F1's 640 MiB pool + 1000 MiB guest data leaves too little for FEX/Wine.
    # This is a reservation, not a GPU limit; the normal allocator still serves
    # additional GPU requests if physical memory permits.
    p = native / 'f1_gpu_arena.h'
    p.write_text(exact(p.read_text(), '#define F1_GPU_ARENA_BYTES (640u * 1024u * 1024u)',
                      '#define F1_GPU_ARENA_BYTES (256u * 1024u * 1024u)'))
    p = unix / 'virtual.c'
    s = p.read_text()
    s = exact(s, '#define mmap    horizon_mmap', '#include "sd_guest_arena.h"\n#define mmap    horizon_mmap')
    # Helpers are inserted after the complete create_view definition, before
    # protection/decommit/allocation callers. All share virtual_mutex.
    marker = 'static NTSTATUS get_vprot_flags( DWORD protect, unsigned int *vprot, BOOL image )'
    s = exact(s, marker, '#ifdef __SWITCH__\n#include "sd_guest_view.inc"\n#endif\n\n' + marker)
    s = exact(s, 'static inline int mprotect_exec( void *base, size_t size, int unix_prot )\n{',
              'static inline int mprotect_exec( void *base, size_t size, int unix_prot )\n{\n'
              '#ifdef __SWITCH__\n    if (sd_guest_arena_overlaps(base, size))\n'
              '        return sd_guest_arena_protect(base, size, unix_prot);\n#endif')
    marker = '    if ((status = get_vprot_flags( protect, &vprot, view->protect & SEC_IMAGE ))) return status;'
    s = exact(s, marker, marker + '\n#ifdef __SWITCH__\n    if (view == sd_direct_view)\n'
              '        return sd_direct_protection(view, base, size, vprot);\n#endif')
    marker = '    if (limit_high && limit_low >= limit_high) return STATUS_INVALID_PARAMETER;'
    s = exact(s, marker, marker + '''
#ifdef __SWITCH__
    status = sd_map_direct_view(view_ret, base, size, alloc_type, vprot, limit_low,
                               limit_high, align_mask, (uintptr_t)effective_user_space_limit);
    if (status != STATUS_NOT_SUPPORTED) return status;
#endif''')
    marker = '    char *host_end, *host_start = (char *)ROUND_SIZE( 0, base, host_page_mask );'
    s = exact(s, marker, marker + '\n#ifdef __SWITCH__\n    if (view == sd_direct_view)\n'
              '        return sd_direct_decommit(view, base, size);\n#endif')
    marker = '''static NTSTATUS free_pages( struct file_view *view, char *base, size_t size )
{
    char *host_base = (char *)ROUND_SIZE( 0, base, host_page_mask );
    char *host_end = base + size;
    NTSTATUS status;'''
    s = exact(s, marker, marker + '\n#ifdef __SWITCH__\n    if (view == sd_direct_view)\n'
              '        return sd_direct_release(view, base, size);\n#endif')
    s = exact(s, '            if (create_view( &view, start, end - start, VPROT_SYSTEM ))',
              '            if (sd_register_kernel_range(start, end - start))')
    p.write_text(s)

