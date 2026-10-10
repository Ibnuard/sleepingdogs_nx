/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Included by virtual.c after create_view/get_unix_prot. virtual_mutex owns
 * every transition after virtual_init. Idle arena and neighbouring heap ranges
 * remain system views: arbitrary guest allocations must not enter libc's heap.
 */
extern void wine_nx_runtime_trace(const char *);
static struct file_view *sd_direct_view;

static NTSTATUS sd_register_kernel_range(void *start, size_t size)
{
    struct file_view *view, *guard = NULL;
    uintptr_t first = (uintptr_t)start, arena = (uintptr_t)sd_guest_arena_base();
    size_t bytes = sd_guest_arena_size();
    NTSTATUS status;
    if (!arena || arena < first || arena - first > size || bytes > size - (arena - first))
        return create_view(&view, start, size, VPROT_SYSTEM);
    if (arena > first && (status = create_view(&view, start, arena - first, VPROT_SYSTEM)))
        return status;
    if ((status = create_view(&guard, (void *)arena, bytes, VPROT_SYSTEM))) return status;
    if (size > arena - first + bytes &&
        (status = create_view(&view, (void *)(arena + bytes), size - (arena - first) - bytes, VPROT_SYSTEM)))
        return status;
    sd_direct_view = guard;
    wine_nx_runtime_trace("[SD-DIRECT] Wine guards registered; native heap neighbours excluded");
    return STATUS_SUCCESS;
}

static NTSTATUS sd_map_direct_view(struct file_view **result, void *base, size_t size,
                                  unsigned type, unsigned vprot, uintptr_t low,
                                  uintptr_t high, size_t align_mask, uintptr_t end)
{
    uintptr_t arena = (uintptr_t)sd_guest_arena_base();
    size_t bytes = sd_guest_arena_size();
    if (!sd_direct_view || sd_direct_view->protect != VPROT_SYSTEM || base || !bytes || size != bytes ||
        (type & ~MEM_TOP_DOWN) != (MEM_RESERVE | MEM_COMMIT) ||
        vprot != (VPROT_READ | VPROT_WRITE | VPROT_COMMITTED) ||
        (arena & align_mask) || arena < low || (high && (arena > high || bytes - 1 > high - arena)) ||
        arena >= end || bytes > end - arena)
        return STATUS_NOT_SUPPORTED; /* Let the ordinary allocator handle other requests. */
    if (sd_guest_arena_reset((void *)arena, bytes, PROT_READ | PROT_WRITE))
        return STATUS_ACCESS_DENIED;
    sd_direct_view->protect = vprot;
    set_page_vprot((void *)arena, bytes, vprot);
    *result = sd_direct_view;
    wine_nx_runtime_trace("[SD-DIRECT] allocated 1000 MiB RW; guest and backing share one address range");
    return STATUS_SUCCESS;
}

static NTSTATUS sd_direct_protection(struct file_view *view, void *base, size_t size, unsigned vprot)
{
    if (view->protect & VPROT_SYSTEM) return STATUS_ACCESS_DENIED;
    /* Native executable/WRITECOPY allocations keep using the existing mapping
     * backend. This arena serves the game's data pool only. */
    if (vprot & (VPROT_EXEC | VPROT_WRITECOPY | VPROT_WRITEWATCH)) return STATUS_INVALID_PAGE_PROTECTION;
    vprot |= VPROT_COMMITTED;
    if (sd_guest_arena_protect(base, size, get_unix_prot(vprot))) return STATUS_ACCESS_DENIED;
    set_page_vprot(base, size, vprot);
    return STATUS_SUCCESS;
}

static NTSTATUS sd_direct_decommit(struct file_view *view, void *base, size_t size)
{
    if (view->protect & VPROT_SYSTEM) return STATUS_ACCESS_DENIED;
    if (!size) size = view->size;
    if (sd_guest_arena_reset(base, size, PROT_NONE)) return STATUS_ACCESS_DENIED;
    set_page_vprot_bits(base, size, 0, VPROT_COMMITTED);
    return STATUS_SUCCESS;
}

static NTSTATUS sd_direct_release(struct file_view *view, void *base, size_t size)
{
    if (view->protect & VPROT_SYSTEM) return STATUS_MEMORY_NOT_ALLOCATED;
    /* This dedicated allocation can be decommitted/recommitted by page. A
     * release must cover it completely; never let generic splitting/unmapping
     * discard the guard or return protected pages to libc. */
    if (base != view->base || size != view->size) return STATUS_UNABLE_TO_FREE_VM;
    if (sd_guest_arena_reset(base, size, PROT_NONE)) return STATUS_ACCESS_DENIED;
    set_page_vprot(base, size, 0);
    view->protect = VPROT_SYSTEM;
    wine_nx_runtime_trace("[SD-DIRECT] released guest view; backing retained for safe reuse");
    return STATUS_SUCCESS;
}
