/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Called with the forwarder's libnx virtmem lock held. Reserve the guest span
 * before placing the NRO: the runtime's own allocator starts only afterwards.
 * Reservation belongs to the forwarder and survives NRO return/reload.
 */
static VirtmemReservation *sd_forwarder_guest_reservation;
static void *sd_forwarder_find_native(size_t size)
{
    if (!sd_forwarder_guest_reservation)
        sd_forwarder_guest_reservation=virtmemAddReservation((void *)UINT64_C(0x200000),UINT64_C(0xffe00000));
    if (!sd_forwarder_guest_reservation) return NULL;
    void *address=virtmemFindCodeMemory(size,0);
    uintptr_t at=(uintptr_t)address;
    if (at<UINT64_C(0x100000000) || at>=UINT64_C(0x8000000000) ||
        size>UINT64_C(0x8000000000)-at) return NULL;
    return address;
}
