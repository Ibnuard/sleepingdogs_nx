/* LGPL-2.1-or-later. Bounded evidence from the exiting thread's saved WOW64
 * context. Reads are validated by the caller. Never resume a fatal exception
 * or treat raw stack words as proven return addresses. No heap allocations. */
#ifndef F1_GUEST_FAILURE_H
#define F1_GUEST_FAILURE_H
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

typedef int (*f1_guest_read_fn)(uint64_t, void *, size_t);
typedef void (*f1_guest_log_fn)(const char *);

static void f1_guest_failure_capture(uint64_t context, unsigned tid, unsigned code,
                                     f1_guest_read_fn read, f1_guest_log_fn log)
{
    uint32_t eip = 0, esp = 0, ebp = 0;
    char line[240];
    /* WOW64_CONTEXT offsets, validated against the built Wine headers. */
    int valid = context && context <= UINT64_MAX - 0xcc &&
        read(context + 0xb8, &eip, 4) && read(context + 0xc4, &esp, 4) &&
        read(context + 0xb4, &ebp, 4);
    snprintf(line, sizeof(line), "[F1-GUEST] tid=%u exit=%08x saved_context=%d eip=%08x esp=%08x ebp=%08x",
             tid, code, valid, eip, esp, ebp);
    log(line);
    if (!valid) return;
    uint32_t frame = ebp;
    for (unsigned i = 0; i < 16; ++i) {
        uint32_t words[6];
        if (frame < esp || (uint64_t)frame - esp > 16u * 1024 * 1024 ||
            (uint64_t)frame + sizeof(words) > UINT64_C(0x100000000) ||
            !read(frame, words, sizeof(words))) break;
        snprintf(line, sizeof(line), "[F1-GUEST-FRAME] tid=%u index=%u fp=%08x next=%08x return=%08x args=%08x %08x %08x %08x",
            tid, i, frame, words[0], words[1], words[2], words[3], words[4], words[5]);
        log(line);
        if (words[0] <= frame) break;
        frame = words[0];
    }
    for (unsigned i = 0; i < 16; ++i) {
        uint32_t words[8];
        uint64_t at = (uint64_t)esp + i * sizeof(words);
        if (at + sizeof(words) > UINT64_C(0x100000000) || !read(at, words, sizeof(words))) break;
        snprintf(line, sizeof(line), "[F1-GUEST-STACK] tid=%u at=%08x raw=%08x %08x %08x %08x %08x %08x %08x %08x",
            tid, (unsigned)at, words[0], words[1], words[2], words[3], words[4], words[5], words[6], words[7]);
        log(line);
    }
}
#endif
