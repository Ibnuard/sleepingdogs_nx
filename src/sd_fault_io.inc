/* LGPL-2.1-or-later. Included by f1_crash.c after the existing crash writer.
 * The final 4 KiB of crash.log is unused by its event/fatal/native/Rust records.
 * Keep the first guest snapshot there even if later recursive faults fill logs. */
#define SD_FAULT_BASE (28u * 1024u)
#define SD_FAULT_BYTES 4096u
_Static_assert(SD_FAULT_BASE >= F1_RUST_BASE + 512, "crash region overlap");
_Static_assert(SD_FAULT_BASE + SD_FAULT_BYTES <= F1_CRASH_BYTES, "crash region overflow");
static unsigned sd_fault_used, sd_fault_busy;

int wine_nx_sd_fault_read(uintptr_t address, void *out, size_t bytes)
{
    MemoryInfo info;
    u32 page;
    if (!address || !out || !bytes || bytes > UINTPTR_MAX - address ||
        R_FAILED(svcQueryMemory(&info, &page, address)) || !(info.perm & Perm_R) ||
        address < info.addr || bytes > info.size || address - info.addr > info.size - bytes)
        return 0;
    /* Only owner-thread context, TIB and bounded stack reads are requested.
     * Refuse cross-region reads instead of touching a guard/no-access page. */
    const volatile unsigned char *src = (const volatile unsigned char *)address;
    unsigned char *dst = out;
    for (size_t i = 0; i < bytes; ++i) dst[i] = src[i];
    return 1;
}

extern void wine_nx_runtime_trace(const char *);
void wine_nx_sd_fault_line(unsigned ticket, const char *line)
{
    int saved_errno = errno;
    if (ticket == 1 && __atomic_load_n(&f1_crash_ready, __ATOMIC_ACQUIRE) &&
        !__atomic_exchange_n(&sd_fault_busy, 1, __ATOMIC_ACQUIRE)) {
        char text[240];
        size_t n = 0;
        while (line[n] && n < sizeof(text) - 1) { text[n] = line[n]; ++n; }
        text[n++] = '\n';
        if (n <= SD_FAULT_BYTES - sd_fault_used) {
            Result rc = fsFileWrite(&f1_crash_fatal, SD_FAULT_BASE + sd_fault_used,
                                    text, n, FsWriteOption_Flush);
            if (R_SUCCEEDED(rc)) sd_fault_used += n;
        }
        __atomic_store_n(&sd_fault_busy, 0, __ATOMIC_RELEASE);
    }
    wine_nx_runtime_trace(line);
    errno = saved_errno;
}
