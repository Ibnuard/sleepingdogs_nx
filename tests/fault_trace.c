/* Host regression tests for the exact diagnostic capture/read/write code. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>

typedef unsigned u32, Result;
typedef struct { uintptr_t addr; size_t size; unsigned perm; } MemoryInfo;
#define Perm_R 1
#define R_FAILED(x) ((x) != 0)
#define R_SUCCEEDED(x) ((x) == 0)
#define FsWriteOption_Flush 1
#define F1_RUST_BASE 25600
#define F1_CRASH_BYTES 32768
static unsigned f1_crash_ready = 1, f1_crash_fatal;
static unsigned char crash_file[F1_CRASH_BYTES];
static char output[65536];
static size_t used, writes, reads;
static int query_failed, write_failed;
static MemoryInfo regions[4];
static Result svcQueryMemory(MemoryInfo *info, u32 *page, uintptr_t address)
{
    ++reads; *page = 0;
    if (query_failed) return 1;
    for (unsigned i = 0; i < 4; ++i)
        if (address >= regions[i].addr && address - regions[i].addr < regions[i].size) {
            *info = regions[i]; return 0;
        }
    return 1;
}
static Result fsFileWrite(unsigned *file, size_t offset, const void *data, size_t bytes, unsigned flags)
{
    (void)file; assert(flags == FsWriteOption_Flush);
    assert(offset >= 28672 && offset + bytes <= sizeof(crash_file));
    ++writes; errno = EIO;
    if (write_failed) return 1;
    memcpy(crash_file + offset, data, bytes); return 0;
}
void wine_nx_runtime_trace(const char *s)
{
    size_t n = strlen(s); assert(used + n + 2 < sizeof(output));
    memcpy(output + used, s, n); used += n; output[used++] = '\n'; output[used] = 0;
    errno = EBUSY;
}
#include "../src/sd_fault_io.inc"

typedef struct {
    uint32_t ContextFlags, Eip, Esp, Ebp, EFlags, Eax, Ebx, Ecx, Edx, Esi, Edi;
    uint32_t Dr0, Dr1, Dr2, Dr3, Dr6, Dr7;
} I386_CONTEXT;
typedef struct { uint32_t words[7]; } TEB32;
typedef struct { struct { void *UniqueThread; } ClientId; void *TlsSlots[1]; } TEB;
typedef struct { uint16_t Flags, Machine; } WOW64_CPURESERVED;
#define WOW64_TLS_CPURESERVED 0
typedef struct { uint64_t Pc, Sp; } CONTEXT;
typedef struct { unsigned ExceptionCode, ExceptionFlags, NumberParameters;
    void *ExceptionAddress; uint64_t ExceptionInformation[2]; } EXCEPTION_RECORD;
static struct { I386_CONTEXT ctx; TEB32 teb32; TEB teb; WOW64_CPURESERVED cpu; } fixtures;
static TEB *NtCurrentTeb(void) { return &fixtures.teb; }
static TEB32 *get_wow_teb(TEB *teb) { assert(teb == &fixtures.teb); return &fixtures.teb32; }
#define IMAGE_FILE_MACHINE_I386 0x14c
static void *get_cpu_area(unsigned machine) {
    assert(machine == 0x14c && fixtures.teb.TlsSlots[0] && fixtures.cpu.Machine == 0x14c);
    return &fixtures.ctx;
}
static struct { uint64_t pKiUserExceptionDispatcher, ntdll_handle; } init_block = {0x70102030, 0x70000000};
static __typeof__(init_block) *pLdrSystemDllInitBlock = &init_block;
#include "../src/sd_fault_trace.inc"
#include "../src/sd_fault_wine_log.h"

int main(void)
{
    unsigned char *stack = mmap(NULL, 8192, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_32BIT, -1, 0);
    assert(stack != MAP_FAILED && (uintptr_t)stack + 8192 <= UINT32_MAX);
    assert(!mprotect(stack + 4096, 4096, PROT_NONE));
    regions[0] = (MemoryInfo){(uintptr_t)stack, 4096, Perm_R};
    regions[1] = (MemoryInfo){(uintptr_t)stack + 4096, 4096, 0};
    regions[2] = (MemoryInfo){(uintptr_t)&fixtures, sizeof(fixtures), Perm_R};
    uint32_t value = 123;
    assert(!wine_nx_sd_fault_read(0, &value, 4));
    assert(!wine_nx_sd_fault_read(UINTPTR_MAX - 1, &value, 4));
    assert(!wine_nx_sd_fault_read((uintptr_t)stack + 4094, &value, 4));
    assert(!wine_nx_sd_fault_read((uintptr_t)stack + 4096, &value, 4));
    query_failed = 1;
    assert(!wine_nx_sd_fault_read((uintptr_t)stack, &value, 4));
    query_failed = 0;
    assert(value == 123);
    puts("PASS guarded reads: null, overflow, cross-region, no-access, query failure");

    uint32_t start = (uint32_t)(uintptr_t)stack;
    for (unsigned i = 0; i < 4096 / 4; ++i) ((uint32_t *)stack)[i] = 0x11220000 + i;
    fixtures.ctx = (I386_CONTEXT){.ContextFlags=0x1003f, .Eip=0xfffffffe, .Esp=start+128,
        .Ebp=start+512, .Eax=0x68d50000, .Dr7=0x55};
    fixtures.teb.ClientId.UniqueThread = (void *)4;
    fixtures.teb.TlsSlots[0] = &fixtures.cpu; fixtures.cpu.Machine = 0x14c;
    fixtures.teb32.words[0] = start+768;
    fixtures.teb32.words[1] = start+4096;
    fixtures.teb32.words[2] = start;
    ((uint32_t *)(stack+512))[0] = start+512; /* self-cycle terminates */
    ((uint32_t *)(stack+512))[1] = 0x008b500b;
    ((uint32_t *)(stack+768))[0] = UINT32_MAX;
    ((uint32_t *)(stack+768))[1] = 0x00b74470;
    __typeof__(fixtures) original = fixtures;
    EXCEPTION_RECORD rec = {.ExceptionCode=0xc0000005, .ExceptionAddress=(void *)0xfffffffe,
                             .NumberParameters=2, .ExceptionInformation={8,0xfffffffe}};
    CONTEXT native = {0xff68498c,0x1c2739c0};
    sd_guest_fault_trace(NULL, &native); sd_guest_fault_trace(&rec, NULL);
    assert(!used && !writes);
    for (unsigned i = 0; i < 2000; ++i) {
        EXCEPTION_RECORD debug = rec;
        const unsigned benign[] = {0x80000003, 0x80000004, 0x406d1388};
        debug.ExceptionCode = benign[i % 3];
        sd_guest_fault_trace(&debug, &native);
    }
    assert(!used && !writes);
    puts("PASS 2000 normal debug/thread-name exceptions do not consume the fault snapshot quota");
    errno = ENOENT;
    sd_guest_fault_trace(&rec, &native);
    assert(errno == ENOENT && !memcmp(&fixtures, &original, sizeof(fixtures)));
    assert(strstr(output,"ticket=1 tid=4") && strstr(output,"eip=fffffffe"));
    assert(strstr(output,"eax=68d50000") && strstr(output,"dr7=00000055"));
    assert(strstr(output,"guest_dispatcher=70102030") && strstr(output,"return=008b500b"));
    assert(strstr(output,"handler=00b74470") && strstr(output,"[SD-FIRSTFAULT] end"));
    assert(sd_fault_used < 4096 && writes > 10);
    for (unsigned i = 0; i < SD_FAULT_BASE; ++i) assert(!crash_file[i]);
    unsigned char saved[SD_FAULT_BYTES]; memcpy(saved, crash_file+SD_FAULT_BASE, sizeof(saved));
    puts("PASS first snapshot: registers, dispatcher, stack, frame chain, SEH; context and errno preserved");

    fixtures.ctx.Eip = start + 4096 - 32; /* two readable chunks before guard */
    fixtures.ctx.Esp = UINT32_MAX - 8; fixtures.ctx.Ebp = UINT32_MAX;
    fixtures.teb32.words[0] = 0;
    sd_guest_fault_trace(&rec, &native);
    assert(strstr(output,"code@") && strstr(output,"112203f8 112203f9 112203fa 112203fb"));
    query_failed = 1; sd_guest_fault_trace(&rec, &native); query_failed = 0;
    assert(strstr(output,"guest-context=unavailable"));
    pLdrSystemDllInitBlock = NULL; fixtures.teb.TlsSlots[0] = NULL;
    sd_guest_fault_trace(&rec, &native);
    size_t count = used, old_reads = reads;
    for (unsigned i = 0; i < 100; ++i) sd_guest_fault_trace(&rec, &native);
    assert(used == count && reads == old_reads);
    assert(!memcmp(saved, crash_file+SD_FAULT_BASE, sizeof(saved)));
    puts("PASS bad guest pointers and repeated faults bounded; first persistent snapshot retained");

    used = 0; sd_fault_used = SD_FAULT_BYTES - 1;
    size_t old_writes = writes;
    wine_nx_sd_fault_line(1,"record-too-large"); assert(writes == old_writes);
    sd_fault_used = 0; write_failed = 1; errno = EINVAL;
    wine_nx_sd_fault_line(1,"write-failure"); assert(!sd_fault_used && errno == EINVAL);
    puts("PASS full record and storage failure leave runtime status intact");

    for (unsigned i = 0; i < 1000; ++i) {
        assert(sd_fault_wine_line("0004:trace:seh:dispatch_exception fault") == (i < 256));
        assert(sd_fault_wine_line("0004:trace:wow:call_user_exception_dispatcher target") == (i < 32));
        assert(!sd_fault_wine_line("0004:trace:wow:Wow64SystemServiceEx syscall"));
        assert(sd_fault_wine_line("0004:err:module:important_loader_error"));
        assert(sd_fault_wine_line("0004:err:seh:real_failure"));
        assert(sd_fault_wine_line("0004:warn:wow:sd_wow64_notify_execute_flags [SD-DEP] change"));
        assert(sd_fault_wine_line("0004:warn:seh:dump_backtrace: frame") == (i < 128));
        assert(sd_fault_wine_line("0004:err:seh:dump_backtrace: error"));
        assert(sd_fault_wine_line("0004:warn:seh:other_warning detail"));
    }
    puts("PASS SEH/WoW/backtrace limits; other Wine warnings and all errors remain visible");
    assert(!munmap(stack,8192));
    return 0;
}
