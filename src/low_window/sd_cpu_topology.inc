/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Horizon has no sysfs/hwloc backend. Publish the same processor count that
 * init_cpu_info exposes through the PEB/GetSystemInfo, with one hardware
 * thread per core, one package, one NUMA node and one processor group.
 * Included by ntdll/unix/system.c for __SWITCH__ only.
 */
static NTSTATUS create_logical_proc_info(void)
{
    extern void wine_nx_runtime_trace( const char * ) __attribute__((weak));
    const unsigned int count = peb->NumberOfProcessors;
    ULONG_PTR mask = 0;
    unsigned int i;
    char line[160];

    if (!count || count > 8 * sizeof(ULONG_PTR)) return STATUS_INVALID_PARAMETER;

    for (i = 0; i < count; ++i)
    {
        const ULONG_PTR bit = (ULONG_PTR)1 << i;
        mask |= bit;
        if (!logical_proc_info_add_by_id( RelationProcessorPackage, 0, bit ) ||
            !logical_proc_info_add_by_id( RelationProcessorCore, i, bit ))
            return STATUS_NO_MEMORY;
    }
    if (!logical_proc_info_add_numa_node( mask, 0 ) ||
        !logical_proc_info_add_group( count, mask ))
        return STATUS_NO_MEMORY;

    snprintf( line, sizeof(line),
              "[SD-CPU-TOPOLOGY] v1 logical=%u cores=%u mask=%llx legacy_records=%u ex_bytes=%u",
              count, count, (unsigned long long)mask,
              (unsigned int)logical_proc_info_len, (unsigned int)logical_proc_info_ex_size );
    if (wine_nx_runtime_trace) wine_nx_runtime_trace( line );
    return STATUS_SUCCESS;
}
