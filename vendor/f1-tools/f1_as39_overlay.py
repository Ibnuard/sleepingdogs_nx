"""Experimental F1 wide-address-space bootstrap, applied to a private source copy.

The packaged game, Wine PE DLLs, SDK and approved PES source are never edited.
Keep this separate from the production overlay until hardware has exercised it.
"""
from pathlib import Path
from f1_overlay import exact

VERSION = "0.1.28-as39t1"
BUILD = "f1-fextendo-0.1.28-as39-test1"

VM_GLOBALS = r'''
#ifdef __SWITCH__
/* Immutable host floor for wide layouts. WINEPRELOADRESERVE and Windows'
 * low-address conventions cannot make the kernel's null guard mappable.
 * Zero on the already-working 32-bit layout preserves its allocation policy. */
static void *f1_host_address_floor;
static LONG f1_bootstrap_heap_trace_active, f1_bootstrap_heap_trace_count;
void wine_nx_f1_bootstrap_heap_trace(int enabled)
{
    if (enabled) __atomic_store_n(&f1_bootstrap_heap_trace_count, 0, __ATOMIC_RELAXED);
    __atomic_store_n(&f1_bootstrap_heap_trace_active, enabled, __ATOMIC_RELEASE);
}
#endif
'''

VM_FLOOR = r'''
#ifdef __SWITCH__
    /* Also covers explicit addresses and placeholder reservations. Otherwise
     * PROT_NONE can succeed below the host floor and fail only at commit. */
    if (f1_host_address_floor)
    {
        if (base && (ULONG_PTR)base < (ULONG_PTR)f1_host_address_floor)
            return STATUS_CONFLICTING_ADDRESSES;
        limit_low = max(limit_low, (ULONG_PTR)f1_host_address_floor);
    }
#endif
'''

VM_PRELOAD = r'''            if (preload_reserve_start)
            {
#ifdef __SWITCH__
                if (f1_host_address_floor && preload_reserve_start < f1_host_address_floor)
                {
                    char msg[224];
                    snprintf(msg, sizeof(msg), "[F1-AS39] preload %p-%p below host floor %p; use PE relocation",
                             preload_reserve_start, preload_reserve_end, f1_host_address_floor);
                    wine_nx_runtime_trace(msg);
                    preload_reserve_start = preload_reserve_end = NULL;
                }
                else
#endif
                    address_space_start = min(address_space_start, preload_reserve_start);
            }'''

VM_ALLOC_TRACE = r'''
        if (__atomic_load_n(&f1_bootstrap_heap_trace_active, __ATOMIC_ACQUIRE) &&
            __atomic_add_fetch(&f1_bootstrap_heap_trace_count, 1, __ATOMIC_RELAXED) <= 32)
        {
            char msg[320];
            snprintf(msg, sizeof(msg), "[F1-BOOT-ALLOC] base=%p bytes=0x%lx type=%x protect=%x zero_bits=%lx status=%08x out=%p/0x%lx floor=%p",
                     requested_base, (unsigned long)requested_size, type, protect,
                     (unsigned long)zero_bits, status, *ret, (unsigned long)*size_ptr,
                     f1_host_address_floor);
            wine_nx_runtime_trace(msg);
        }
'''


def patch_virtual(s: str) -> str:
    marker = "static NTSTATUS map_view( struct file_view **view_ret, void *base, size_t size,"
    s = exact(s, marker, VM_GLOBALS + "\n" + marker)
    marker = "    fixup_effective_user_space_limit( &effective_user_space_limit );"
    s = exact(s, marker, VM_FLOOR + "\n" + marker)
    marker = "    horizon_get_address_space_limits( &address_space_start, &host_addr_space_limit );"
    s = exact(s, marker, marker + r'''
    f1_host_address_floor = (ULONG_PTR)host_addr_space_limit > limit_4g ? address_space_start : NULL;
    {
        char msg[192];
        snprintf(msg, sizeof(msg), "[F1-AS39] host_start=%p host_limit=%p allocation_floor=%p",
                 address_space_start, host_addr_space_limit, f1_host_address_floor);
        wine_nx_runtime_trace(msg);
    }''')
    s = exact(s, "            if (preload_reserve_start)\n                address_space_start = min( address_space_start, preload_reserve_start );", VM_PRELOAD)
    s = exact(s, "            address_space_start = (void *)0x10000;", r'''#ifdef __SWITCH__
            address_space_start = max((void *)0x10000, f1_host_address_floor);
#else
            address_space_start = (void *)0x10000;
#endif''')
    marker = '''        NTSTATUS status = allocate_virtual_memory( ret, size_ptr, type, protect, 0, limit, 0, 0 );
#ifdef __SWITCH__'''
    s = exact(s, marker, marker + VM_ALLOC_TRACE)
    return s


def patch_preload(s: str) -> str:
    s = exact(s, "static unsigned int hook_calls;", r'''static unsigned int hook_calls;
static int f1_preload_relocate;
static u64 f1_preload_floor, f1_preload_limit;''')
    s = exact(s, "        if (image_range_is_free())", r'''        u64 host_start = 0, host_size = 0;
        if (R_SUCCEEDED(svcGetInfo(&host_start, InfoType_AslrRegionAddress, CUR_PROCESS_HANDLE, 0)) &&
            R_SUCCEEDED(svcGetInfo(&host_size, InfoType_AslrRegionSize, CUR_PROCESS_HANDLE, 0)) &&
            host_size && host_start + host_size > host_start &&
            host_start + host_size > 0x100000000ULL && PES_IMAGE_BASE < host_start)
        {
            f1_preload_relocate = 1;
            f1_preload_floor = host_start;
            f1_preload_limit = host_start + host_size;
        }
        if (!f1_preload_relocate && image_range_is_free())''')
    s = exact(s, "    if (pes_reservation)\n    {", r'''    if (f1_preload_relocate)
    {
        snprintf(message, sizeof(message), "[F1-AS39] fixed image %p below host range %llx-%llx; relocatable PE required",
                 (void *)PES_IMAGE_BASE, (unsigned long long)f1_preload_floor,
                 (unsigned long long)f1_preload_limit);
        wine_nx_runtime_trace(message);
        return 1; /* Wine applies the existing PE relocation table to a valid view. */
    }
    if (pes_reservation)
    {''')
    return s


def patch_loader(s: str) -> str:
    s = exact(s, "            HANDLE real_heap = NULL;", r'''            extern void wine_nx_f1_bootstrap_heap_trace(int);
            extern void wine_nx_f1_bootstrap_stopped(unsigned);
            HANDLE real_heap = NULL;''')
    marker = "            uintptr_t teb_val = (uintptr_t)NtCurrentTeb();\n\n            __asm__ volatile("
    # There is another TEB wrapper for version_init; only this one has real_heap.
    pos = s.index("            HANDLE real_heap = NULL;")
    prefix, tail = s[:pos], s[pos:]
    heap_end = tail.index("            if (real_heap)")
    heap, rest = tail[:heap_end], tail[heap_end:]
    heap = exact(heap, marker, r'''            uintptr_t teb_val = (uintptr_t)NtCurrentTeb();
            wine_nx_trace("[F1-BOOT-HEAP] begin ntdll=%p function=%p peb=%p teb=%p",
                          ntdll->ldr.DllBase, real_create_heap, peb, NtCurrentTeb());
            wine_nx_f1_bootstrap_heap_trace(1);

            __asm__ volatile(''', count=1)
    s = prefix + heap + rest
    s = exact(s, "            if (real_heap)\n            {", r'''            wine_nx_f1_bootstrap_heap_trace(0);
            wine_nx_trace("[F1-BOOT-HEAP] end heap=%p", real_heap);
            if (real_heap)
            {''')
    s = exact(s, '''                wine_nx_trace( "[LDR] real RtlCreateHeap returned NULL; keeping shim heap %p",
                               peb->ProcessHeap );''', r'''                wine_nx_trace("[F1-BOOT-HEAP] failed; refusing to publish sentinel heap %p", peb->ProcessHeap);
                wine_nx_f1_bootstrap_stopped(0xf1390001u);
                NtTerminateProcess(NtCurrentProcess(), STATUS_NO_MEMORY);
                return;''')
    return s


def apply(source: Path) -> list[str]:
    changed = []
    for relative, patch in (
        ("dlls/ntdll/unix/virtual.c", patch_virtual),
        ("dlls/ntdll/loader.c", patch_loader),
        ("wine-nx-probe/source/pes13_preload.c", patch_preload),
    ):
        p = source / relative
        p.write_text(patch(p.read_text()))
        changed.append(relative)
    native = source / "wine-nx-probe/source"
    p = native / "runtime.c"
    s = exact(p.read_text(), '#define FX_APP_VERSION "0.1.27"', f'#define FX_APP_VERSION "{VERSION}"')
    s = exact(s, '"f1-fextendo-0.1.27-memory-budget"', f'"{BUILD}"')
    p.write_text(s)
    changed.append(str(p.relative_to(source)))
    p = native / "f1_crash.c"
    s = p.read_text().replace("/ crash.log / 0.1.27", f"/ crash.log / {VERSION}")
    s = exact(s, "f1-fextendo-0.1.27-memory-budget", BUILD)
    p.write_text(s)
    changed.append(str(p.relative_to(source)))
    p = native / "f1_relaunch.h"
    s = exact(p.read_text(), "F1_RETURN_COMPILER };", "F1_RETURN_COMPILER, F1_RETURN_BOOTSTRAP };")
    s = exact(s, "r.words[4] = 127;", "r.words[4] = 128;")
    s = exact(s, "r->words[2] <= F1_RETURN_COMPILER", "r->words[2] <= F1_RETURN_BOOTSTRAP")
    p.write_text(s)
    changed.append(str(p.relative_to(source)))
    p = native / "f1_relaunch.c"
    s = exact(p.read_text(), "    else if (record.words[2] == F1_RETURN_COMPILER)", r'''    else if (record.words[2] == F1_RETURN_BOOTSTRAP)
        snprintf(message, capacity, "Wine startup heap failed (0x%08x). Runtime restarted. Save fex-runtime.log before retrying.", code);
    else if (record.words[2] == F1_RETURN_COMPILER)''')
    s = exact(s, "kind > F1_RETURN_COMPILER", "kind > F1_RETURN_BOOTSTRAP")
    s += r'''
void wine_nx_f1_bootstrap_stopped(unsigned code)
{
    wine_nx_f1_relaunch_fatal(F1_RETURN_BOOTSTRAP, code);
}
'''
    p.write_text(s)
    changed.append(str(p.relative_to(source)))
    return changed
