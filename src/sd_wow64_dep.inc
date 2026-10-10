/* LGPL-2.1-or-later. Keep the CPU backend's guest execute policy in sync
 * with the policy accepted by Wine. No policy is forced by this bridge. */
static RTL_SRWLOCK sd_dep_lock = RTL_SRWLOCK_INIT;
static unsigned sd_dep_lines;

static void sd_wow64_notify_execute_flags(const char *reason)
{
    ULONG flags;
    NTSTATUS status;
    if (!pBTCpuNotifyProcessExecuteFlagsChange) return;
    status = NtQueryInformationProcess(GetCurrentProcess(), ProcessExecuteFlags,
                                      &flags, sizeof(flags), NULL);
    if (status) return;
    pBTCpuNotifyProcessExecuteFlagsChange(flags);
    if (sd_dep_lines < 16) {
        ++sd_dep_lines;
        WARN("[SD-DEP] %s flags=%08lx backend notified\n", reason, flags);
    }
}

void sd_wow64_sync_execute_flags(void)
{
    RtlAcquireSRWLockExclusive(&sd_dep_lock);
    sd_wow64_notify_execute_flags("initial");
    RtlReleaseSRWLockExclusive(&sd_dep_lock);
}

static NTSTATUS sd_wow64_set_execute_flags(HANDLE handle, void *info, ULONG size)
{
    PROCESS_BASIC_INFORMATION basic;
    NTSTATUS status;
    BOOL self = handle == GetCurrentProcess();

    /* Serialize guest policy changes through notification so two callers
     * cannot leave the backend with an older policy than Wine. */
    RtlAcquireSRWLockExclusive(&sd_dep_lock);
    status = NtSetInformationProcess(handle, ProcessExecuteFlags, info, size);
    if (!status && pBTCpuNotifyProcessExecuteFlagsChange) {
        if (!self && !NtQueryInformationProcess(handle, ProcessBasicInformation,
                                                &basic, sizeof(basic), NULL))
            self = basic.UniqueProcessId == (ULONG_PTR)NtCurrentTeb()->ClientId.UniqueProcess;
        if (self) sd_wow64_notify_execute_flags("change");
    }
    RtlReleaseSRWLockExclusive(&sd_dep_lock);
    return status;
}
