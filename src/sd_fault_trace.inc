/* LGPL-2.1-or-later. Included by the Horizon ARM64 exception dispatcher.
 * Observe the first guest exceptions before Wine constructs another frame.
 * Never write the guest context, change a result, or consume an exception. */
#include <errno.h>
#include <stdint.h>

extern int wine_nx_sd_fault_read(uintptr_t address, void *out, size_t bytes);
extern void wine_nx_sd_fault_line(unsigned ticket, const char *line);

static void sd_guest_fault_trace(const EXCEPTION_RECORD *rec, const CONTEXT *native)
{
    static unsigned count;
    unsigned ticket = __atomic_load_n(&count, __ATOMIC_RELAXED);
    I386_CONTEXT ctx;
    WOW64_CPURESERVED cpu_header;
    TEB *teb;
    TEB32 *teb32;
    uint32_t tib[7], words[4], chain;
    char line[240];
    int saved_errno = errno;

    if (!rec || !native) return;
    /* The game uses execution breakpoints during normal startup. They must
     * not consume the persistent snapshot or hide a later access violation. */
    if (rec->ExceptionCode == 0x80000003u || rec->ExceptionCode == 0x80000004u ||
        rec->ExceptionCode == 0x406d1388u) return; /* Conventional thread naming. */
    do {
        if (ticket >= 4) return;
    } while (!__atomic_compare_exchange_n(&count, &ticket, ticket + 1, 1,
                                           __ATOMIC_RELAXED, __ATOMIC_RELAXED));
    ++ticket;
    teb = NtCurrentTeb();
    teb32 = teb ? get_wow_teb(teb) : NULL;
    snprintf(line, sizeof(line),
             "[SD-FIRSTFAULT] ticket=%u tid=%llu code=%08x address=%llx native_pc=%llx native_sp=%llx",
             ticket, teb ? (unsigned long long)(uintptr_t)teb->ClientId.UniqueThread : 0,
             (unsigned)rec->ExceptionCode, (unsigned long long)(uintptr_t)rec->ExceptionAddress,
             (unsigned long long)native->Pc, (unsigned long long)native->Sp);
    wine_nx_sd_fault_line(ticket, line);
    if (rec->NumberParameters >= 2) {
        snprintf(line, sizeof(line), "[SD-FIRSTFAULT] access=%llu target=%llx flags=%08x",
                 (unsigned long long)rec->ExceptionInformation[0],
                 (unsigned long long)rec->ExceptionInformation[1], (unsigned)rec->ExceptionFlags);
        wine_nx_sd_fault_line(ticket, line);
    }
    if (!teb32 || !wine_nx_sd_fault_read((uintptr_t)teb->TlsSlots[WOW64_TLS_CPURESERVED],
                                        &cpu_header, sizeof(cpu_header)) ||
        cpu_header.Machine != IMAGE_FILE_MACHINE_I386 ||
        !wine_nx_sd_fault_read((uintptr_t)get_cpu_area(IMAGE_FILE_MACHINE_I386), &ctx, sizeof(ctx))) {
        wine_nx_sd_fault_line(ticket, "[SD-FIRSTFAULT] guest-context=unavailable");
        goto done;
    }
    snprintf(line, sizeof(line),
             "[SD-FIRSTFAULT] eip=%08x esp=%08x ebp=%08x eflags=%08x context_flags=%08x",
             (unsigned)ctx.Eip, (unsigned)ctx.Esp, (unsigned)ctx.Ebp,
             (unsigned)ctx.EFlags, (unsigned)ctx.ContextFlags);
    wine_nx_sd_fault_line(ticket, line);
    snprintf(line, sizeof(line), "[SD-FIRSTFAULT] eax=%08x ebx=%08x ecx=%08x edx=%08x esi=%08x edi=%08x",
             (unsigned)ctx.Eax, (unsigned)ctx.Ebx, (unsigned)ctx.Ecx,
             (unsigned)ctx.Edx, (unsigned)ctx.Esi, (unsigned)ctx.Edi);
    wine_nx_sd_fault_line(ticket, line);
    snprintf(line, sizeof(line), "[SD-FIRSTFAULT] dr0=%08x dr1=%08x dr2=%08x dr3=%08x dr6=%08x dr7=%08x",
             (unsigned)ctx.Dr0, (unsigned)ctx.Dr1, (unsigned)ctx.Dr2,
             (unsigned)ctx.Dr3, (unsigned)ctx.Dr6, (unsigned)ctx.Dr7);
    wine_nx_sd_fault_line(ticket, line);
    if (pLdrSystemDllInitBlock) {
        snprintf(line, sizeof(line), "[SD-FIRSTFAULT] guest_dispatcher=%llx guest_ntdll=%llx",
                 (unsigned long long)pLdrSystemDllInitBlock->pKiUserExceptionDispatcher,
                 (unsigned long long)pLdrSystemDllInitBlock->ntdll_handle);
        wine_nx_sd_fault_line(ticket, line);
    }
    for (unsigned i = 0; i < 4; ++i) {
        uint64_t address = (uint64_t)ctx.Eip + i * 16;
        if (address + 16 > (uint64_t)UINT32_MAX + 1 ||
            !wine_nx_sd_fault_read((uintptr_t)address, words, sizeof(words))) break;
        snprintf(line, sizeof(line), "[SD-FIRSTFAULT] code@%08x=%08x %08x %08x %08x",
                 (unsigned)address, words[0], words[1], words[2], words[3]);
        wine_nx_sd_fault_line(ticket, line);
    }
    if (!wine_nx_sd_fault_read((uintptr_t)teb32, tib, sizeof(tib))) {
        wine_nx_sd_fault_line(ticket, "[SD-FIRSTFAULT] guest-tib=unavailable");
        goto done;
    }
    snprintf(line, sizeof(line), "[SD-FIRSTFAULT] teb32=%llx seh=%08x stack_limit=%08x stack_base=%08x",
             (unsigned long long)(uintptr_t)teb32, tib[0], tib[2], tib[1]);
    wine_nx_sd_fault_line(ticket, line);
    /* Include the recently popped return/argument slots as well as live stack.
     * Bound every read to this thread's stack and query its current permissions. */
    for (unsigned i = 0; i < 14; ++i) {
        uint64_t address = (uint64_t)ctx.Esp + i * 16;
        if (address < 32) continue;
        address -= 32;
        if (address < tib[2] || address > tib[1] || 16 > tib[1] - address ||
            !wine_nx_sd_fault_read((uintptr_t)address, words, sizeof(words))) continue;
        snprintf(line, sizeof(line), "[SD-FIRSTFAULT] stack@%08x=%08x %08x %08x %08x",
                 (unsigned)address, words[0], words[1], words[2], words[3]);
        wine_nx_sd_fault_line(ticket, line);
    }
    chain = ctx.Ebp;
    for (unsigned i = 0; i < 8; ++i) {
        if ((chain & 3) || chain < tib[2] || chain > tib[1] || 8 > tib[1] - chain ||
            !wine_nx_sd_fault_read(chain, words, 8)) break;
        snprintf(line, sizeof(line), "[SD-FIRSTFAULT] frame@%08x next=%08x return=%08x", chain, words[0], words[1]);
        wine_nx_sd_fault_line(ticket, line);
        if (words[0] <= chain) break;
        chain = words[0];
    }
    chain = tib[0];
    for (unsigned i = 0; i < 8; ++i) {
        if (chain == UINT32_MAX || (chain & 3) || chain < tib[2] || chain > tib[1] ||
            8 > tib[1] - chain || !wine_nx_sd_fault_read(chain, words, 8)) break;
        snprintf(line, sizeof(line), "[SD-FIRSTFAULT] seh@%08x next=%08x handler=%08x", chain, words[0], words[1]);
        wine_nx_sd_fault_line(ticket, line);
        if (words[0] <= chain) break;
        chain = words[0];
    }
done:
    wine_nx_sd_fault_line(ticket, "[SD-FIRSTFAULT] end");
    errno = saved_errno;
}
