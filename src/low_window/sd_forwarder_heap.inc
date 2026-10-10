/* SPDX-License-Identifier: LGPL-2.1-or-later
 * virtmemAddReservation allocates its bookkeeping through __libnx_alloc.
 * The original Sphaira forwarder deliberately aborted on all such allocations.
 * Give libnx/newlib a small private heap in the forwarder's own BSS instead.
 * It remains mapped when the application heap is handed to (and overwritten by)
 * the NRO, so the guest-window reservation also survives NRO return/reload.
 */
void __libnx_initheap(void)
{
    extern char *fake_heap_start;
    extern char *fake_heap_end;
    static char sd_forwarder_private_heap[16 * 1024] __attribute__((aligned(16)));

    fake_heap_start = sd_forwarder_private_heap;
    fake_heap_end = sd_forwarder_private_heap + sizeof(sd_forwarder_private_heap);
}
