/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Included in the ARM64 syscall dispatcher, after Wine and watch declarations.
 * Read guest pages after the syscall releases its locks. No pause or mutation.
 */
#include "sd_sync_watch.inc"
static __thread uintptr_t sd_sync_last_created;
static __thread uint64_t sd_sync_create_serial;
static __thread uint64_t sd_sync_last_invalid;
static __thread unsigned sd_sync_invalid_taken;

void wine_nx_sd_sync_created_handle(uintptr_t handle)
{
    /* Called at the ordinary Create/OpenSemaphore return: capture a scalar,
     * not a pointer into a WoW64 stack that will subsequently unwind. */
    if (!__atomic_load_n(&f1_startup_watch_enabled,__ATOMIC_RELAXED)) return;
    sd_sync_last_created=handle;sd_sync_create_serial++;
}

static int sd_sync_guest_read(uint32_t address, void *out, size_t size)
{
    return virtual_uninterrupted_read_memory((const void *)(uintptr_t)address,out,size)==size;
}

static void sd_sync_after_syscall(void *handler, uintptr_t a0, uintptr_t a3, uintptr_t a4,
                                  uint32_t status, uint64_t creation_before)
{
    unsigned kind;
    uint64_t handle=a0;
    if (!__atomic_load_n(&f1_startup_watch_enabled,__ATOMIC_RELAXED)) return;
    if (handler==(void *)NtCreateSemaphore || handler==(void *)NtOpenSemaphore) {
        kind=handler==(void *)NtCreateSemaphore ? SD_SYNC_CREATE : SD_SYNC_OPEN;
        handle=sd_sync_create_serial!=creation_before ? sd_sync_last_created : 0;
    } else if (handler==(void *)NtClose) kind=SD_SYNC_CLOSE;
    else if (handler==(void *)NtWaitForSingleObject && status==0xc0000008u && a0>=0x10000 && a0<=UINT32_MAX) {
        /* A retry loop must not take a diagnostic mutex or reread memory on
         * every iteration. Capture at most two distinct values per thread. */
        if (sd_sync_invalid_taken>=2 || (sd_sync_invalid_taken && sd_sync_last_invalid==a0)) return;
        kind=SD_SYNC_INVALID_WAIT;
    } else return;
    /* Early loader syscalls and native threads can run before WoW64 assigns
     * a per-thread CPU area. get_cpu_area checks the global wow_peb, but then
     * dereferences this TLS slot without checking it. */
    TEB *teb=NtCurrentTeb();
    if (!teb || !teb->TlsSlots[WOW64_TLS_CPURESERVED]) return;
    const I386_CONTEXT *saved=get_cpu_area(IMAGE_FILE_MACHINE_I386);
    if (!saved) return;
    if (kind==SD_SYNC_INVALID_WAIT) {
        sd_sync_last_invalid=a0;sd_sync_invalid_taken++;
    }
    struct sd_sync_cpu cpu={saved->Eax,saved->Ebx,saved->Ecx,saved->Edx,saved->Esi,
                            saved->Edi,saved->Ebp,saved->Esp,saved->Eip};
    sd_sync_note(kind,HandleToULong(teb->ClientId.UniqueThread),handle,status,
                 kind==SD_SYNC_CREATE ? (int32_t)a3 : 0,kind==SD_SYNC_CREATE ? (int32_t)a4 : 0,
                 armGetSystemTick(),&cpu,sd_sync_guest_read);
}

void wine_nx_sd_sync_report(void) { sd_sync_report(wine_nx_runtime_trace); }
