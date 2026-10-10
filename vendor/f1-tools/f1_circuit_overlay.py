"""F1 circuit-loading memory recovery and fatal guest evidence.

The page store is the scoped Wine backing fix from current PES13. Native GPU
buffers retain their existing allocator and lifetime protocol.
"""
from pathlib import Path
from f1_overlay import exact

TOOLS = Path(__file__).resolve().parent

DEVICE_COUNTER = '''#ifdef __SWITCH__
/* F1 creates several D3D devices before the menu. A device that is never
 * destroyed keeps its whole DXVK memory pool; count live host devices. */
static LONG f1_vk_devices_live, f1_vk_devices_created;
#endif

static VkResult win32u_vkCreateDevice('''


def patch_device_lifetime(data: str) -> str:
    """Log every Vulkan device create/destroy with the live count."""
    data = exact(data, 'static VkResult win32u_vkCreateDevice(', DEVICE_COUNTER)
    data = exact(data, '    instance->p_insert_object( instance, &device->obj );\n',
        '    instance->p_insert_object( instance, &device->obj );\n'
        '#ifdef __SWITCH__\n'
        '    nx_vk_trace( "[F1-VKDEVICE] create device=%p host=%p created=%d live=%d",\n'
        '                 device, device->host.device,\n'
        '                 (int)__atomic_add_fetch( &f1_vk_devices_created, 1, __ATOMIC_RELAXED ),\n'
        '                 (int)__atomic_add_fetch( &f1_vk_devices_live, 1, __ATOMIC_RELAXED ) );\n'
        '#endif\n')
    data = exact(data, '    device->p_vkDestroyDevice( device->host.device, NULL /* pAllocator */ );\n',
        '    device->p_vkDestroyDevice( device->host.device, NULL /* pAllocator */ );\n'
        '#ifdef __SWITCH__\n'
        '    nx_vk_trace( "[F1-VKDEVICE] destroy device=%p live=%d", device,\n'
        '                 (int)__atomic_sub_fetch( &f1_vk_devices_live, 1, __ATOMIC_RELAXED ) );\n'
        '#endif\n')
    return data


REPORT_MEMORY_FILE = 'sdmc:/switch/f1-fex/launcher/report-memory-mb.txt'
REPORT_MEMORY_DEFAULT_MB = 1280

MEMFILE_HELPERS = (
    'static inline void *horizon_memfile_pages_alloc(size_t size) { return HORIZON_MEMFILE_ALLOC_PAGES(size); }\n'
    'static inline void horizon_memfile_pages_free(void *ptr, size_t size) { (void)size; HORIZON_MEMFILE_FREE_PAGES(ptr, size); }\n')

MEMFILE_COUNTED = '''/* F1 accounting: live/peak bytes of section pages (anonymous shared memory
 * and image views). Relaxed atomics; observers never take allocator locks. */
static uint64_t f1_section_live __attribute__((unused)), f1_section_peak __attribute__((unused));
static inline void f1_mem_peak(uint64_t *peak, uint64_t now)
{
    uint64_t prev = __atomic_load_n(peak, __ATOMIC_RELAXED);
    while (prev < now && !__atomic_compare_exchange_n(peak, &prev, now, 0, __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {}
}
static inline void *horizon_memfile_pages_alloc(size_t size)
{
    void *ptr = HORIZON_MEMFILE_ALLOC_PAGES(size);
    if (ptr) f1_mem_peak(&f1_section_peak, __atomic_add_fetch(&f1_section_live, size, __ATOMIC_RELAXED));
    return ptr;
}
static inline void horizon_memfile_pages_free(void *ptr, size_t size)
{
    if (ptr) __atomic_sub_fetch(&f1_section_live, size, __ATOMIC_RELAXED);
    HORIZON_MEMFILE_FREE_PAGES(ptr, size);
}
'''

BACKING_HELPERS = '''static void *horizon_backing_pages_alloc(size_t size)
{
    void *ptr = horizon_pages_alloc(&backing_pages, size);
    if (!ptr) { ptr = memalign(0x1000, size); backing_direct_allocs++; }
    return ptr;
}
static void horizon_backing_pages_free(void *ptr, size_t size)
{
    if (!horizon_pages_free(&backing_pages, ptr, size)) free(ptr);
}
'''

BACKING_COUNTED = '''/* F1 accounting: bytes Wine committed for anonymous/file backing. "pooled" is
 * the part served from page-pool arenas, which page_arenas already contains. */
static uint64_t f1_backing_live, f1_backing_peak, f1_backing_pooled;
static void *horizon_backing_pages_alloc(size_t size)
{
    void *ptr = horizon_pages_alloc(&backing_pages, size);
    if (ptr) __atomic_add_fetch(&f1_backing_pooled, size, __ATOMIC_RELAXED);
    else { ptr = memalign(0x1000, size); backing_direct_allocs++; }
    if (ptr) f1_mem_peak(&f1_backing_peak, __atomic_add_fetch(&f1_backing_live, size, __ATOMIC_RELAXED));
    return ptr;
}
static void horizon_backing_pages_free(void *ptr, size_t size)
{
    __atomic_sub_fetch(&f1_backing_live, size, __ATOMIC_RELAXED);
    if (horizon_pages_free(&backing_pages, ptr, size))
        __atomic_sub_fetch(&f1_backing_pooled, size, __ATOMIC_RELAXED);
    else free(ptr);
}
/* Lock-free diagnostic view: backing live/peak/pooled, section live/peak,
 * and bytes held by page-pool arenas (retained 2 MiB blocks). */
void wine_nx_f1_guest_memory_snapshot(uint64_t out[6])
{
    uint64_t arenas = 0;
    for (unsigned i = 0; i < HORIZON_POOL_ARENAS; ++i)
        if (__atomic_load_n(&backing_pages.arenas[i].memory, __ATOMIC_RELAXED)) ++arenas;
    out[0] = __atomic_load_n(&f1_backing_live, __ATOMIC_RELAXED);
    out[1] = __atomic_load_n(&f1_backing_peak, __ATOMIC_RELAXED);
    out[2] = __atomic_load_n(&f1_backing_pooled, __ATOMIC_RELAXED);
    out[3] = __atomic_load_n(&f1_section_live, __ATOMIC_RELAXED);
    out[4] = __atomic_load_n(&f1_section_peak, __ATOMIC_RELAXED);
    out[5] = arenas * HORIZON_POOL_PAGES * HORIZON_POOL_PAGE;
}
'''

MEMORY_INFO = '''void horizon_get_memory_info( unsigned long long *total, unsigned long long *used )
{
    u64 value;

    *total = R_SUCCEEDED( svcGetInfo( &value, InfoType_TotalMemorySize, CUR_PROCESS_HANDLE, 0 ) ) ? value : 0;
    *used = R_SUCCEEDED( svcGetInfo( &value, InfoType_UsedMemorySize, CUR_PROCESS_HANDLE, 0 ) ) ? value : 0;
    if (*used > *total) *used = *total;
}
'''

MEMORY_INFO_CAPPED = '''static void horizon_get_real_memory_info( unsigned long long *total, unsigned long long *used )
{
    u64 value;

    *total = R_SUCCEEDED( svcGetInfo( &value, InfoType_TotalMemorySize, CUR_PROCESS_HANDLE, 0 ) ) ? value : 0;
    *used = R_SUCCEEDED( svcGetInfo( &value, InfoType_UsedMemorySize, CUR_PROCESS_HANDLE, 0 ) ) ? value : 0;
    if (*used > *total) *used = *total;
}

/* F1: Windows programs size caches from total physical memory. Report a
 * smaller total while keeping the real available amount, which the game
 * already tolerates. The MB value comes from REPORT_FILE once; 0 = real. */
static unsigned long long f1_reported_memory_cap( void )
{
    static long long cached = -1;
    long long cap = __atomic_load_n( &cached, __ATOMIC_ACQUIRE );

    if (cap < 0)
    {
        FILE *file = fopen( "REPORT_FILE", "rb" );
        cap = REPORT_DEFAULT;
        if (file)
        {
            char text[32] = {0}, *end;
            size_t n = fread( text, 1, sizeof(text) - 1, file );
            unsigned long mb;

            fclose( file );
            text[n] = 0;
            mb = strtoul( text, &end, 10 );
            if (end != text && mb <= 65536) cap = (long long)mb;
        }
        cap = (long long)((unsigned long long)cap << 20);
        __atomic_store_n( &cached, cap, __ATOMIC_RELEASE );
    }
    return (unsigned long long)cap;
}

void horizon_get_memory_info( unsigned long long *total, unsigned long long *used )
{
    unsigned long long cap = f1_reported_memory_cap(), avail;

    horizon_get_real_memory_info( total, used );
    if (!cap || cap >= *total) return;
    avail = *total - *used;
    if (avail > cap) avail = cap;
    *total = cap;
    *used = cap - avail;
}
'''.replace('REPORT_FILE', REPORT_MEMORY_FILE).replace('REPORT_DEFAULT', str(REPORT_MEMORY_DEFAULT_MB))

SD_ACCESSOR = '''
/* F1 diagnostics: bytes currently held by cached chunks. */
unsigned long long wine_nx_sd_cache_bytes(void)
{
    return (unsigned long long)__atomic_load_n( &sd_cache_pool.used, __ATOMIC_RELAXED ) * SD_CACHE_CHUNK;
}
'''


def patch_memory_reporting(source: Path) -> None:
    """Guest memory accounting, smaller SD cache, capped reported RAM."""
    unix = source / 'dlls/ntdll/unix'
    memfile = unix / 'horizon_memfile.h'
    memfile.write_text(exact(memfile.read_text(), MEMFILE_HELPERS, MEMFILE_COUNTED))
    backing = unix / 'horizon_store_backing.h'
    backing.write_text(exact(backing.read_text(), BACKING_HELPERS, BACKING_COUNTED))
    horizon = unix / 'horizon.c'
    horizon.write_text(exact(horizon.read_text(), MEMORY_INFO, MEMORY_INFO_CAPPED))
    sd = source / 'wine-nx-probe/source/sd_cache.c'
    data = exact(sd.read_text(), 'static struct sd_cache_pool sd_cache_pool = { 0, 256 };  /* 32 MB */',
                 'static struct sd_cache_pool sd_cache_pool = { 0, 64 };  /* 8 MB: F1 needs the heap at circuit load */')
    sd.write_text(data + SD_ACCESSOR)
    runtime = source / 'wine-nx-probe/source/runtime.c'
    data = exact(runtime.read_text(), 'sdmc reads cached: 128 KB chunks, 8 per file, 32 MB in all',
                 'sdmc reads cached: 128 KB chunks, 8 per file, 8 MB in all')
    data = exact(data, '"[INIT] processors=%u memory=%llu MB used=%llu MB"',
                 '"[INIT] processors=%u reported_memory=%llu MB reported_used=%llu MB '
                 '(launcher/report-memory-mb.txt, default ' + str(REPORT_MEMORY_DEFAULT_MB) +
                 ', 0=real; real totals in [F1-MEMBUDGET])"')
    runtime.write_text(data)


def apply(source: Path):
    from page_store.patches import apply as pages_apply
    pages_apply(source, TOOLS / 'page_store')
    profile = source / 'wine-nx-probe/source/thread_profile.c'
    profile.write_text(profile.read_text() + '''
#include "f1_guest_failure.h"
void wine_nx_f1_guest_exit_snapshot(uint64_t teb, unsigned tid, unsigned code)
{
    static unsigned captured;
    if (!code || __atomic_exchange_n(&captured, 1, __ATOMIC_RELAXED)) return;
    uint64_t area = 0, context = 0;
    if (teb && teb <= UINT64_MAX - NX_PROF_TEB_CPU_AREA &&
        fex_stall_read(teb + NX_PROF_TEB_CPU_AREA, &area, sizeof(area)) &&
        area && area <= UINT64_MAX - NX_PROF_CPU_CONTEXT)
        context = area + NX_PROF_CPU_CONTEXT;
    f1_guest_failure_capture(context, tid, code, fex_stall_read, wine_nx_runtime_trace);
}
''')
    (profile.parent / 'f1_guest_failure.h').write_bytes((TOOLS / 'f1_guest_failure.h').read_bytes())
    process = source / 'dlls/ntdll/unix/process.c'
    process.write_text(exact(process.read_text(), '        horizon_registry_flush();', '''        /* Capture this thread before lifecycle reporting or any exit cleanup. */
        extern void wine_nx_f1_guest_exit_snapshot(uint64_t, unsigned, unsigned);
        wine_nx_f1_guest_exit_snapshot((uintptr_t)NtCurrentTeb(),
            HandleToULong(NtCurrentTeb()->ClientId.UniqueThread), (unsigned)exit_code);
        horizon_registry_flush();'''))
    vulkan = source / 'dlls/win32u/vulkan.c'
    data = exact(vulkan.read_text(), 'static VkResult win32u_vkAllocateMemory(',
                 '#include "f1_vk_recovery.h"\n\nstatic VkResult win32u_vkAllocateMemory(')
    data = exact(data, 'device->p_vkAllocateMemory( device->host.device, alloc_info, NULL, &host_device_memory )',
                 'f1_vk_allocate_recover( device->p_vkAllocateMemory, device->host.device, alloc_info, &host_device_memory )')
    data = patch_device_lifetime(data)
    vulkan.write_text(data)
    patch_memory_reporting(source)
    (vulkan.parent / 'f1_vk_recovery.h').write_bytes((TOOLS / 'f1_vk_recovery.h').read_bytes())
