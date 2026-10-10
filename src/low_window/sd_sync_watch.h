/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef SD_SYNC_WATCH_H
#define SD_SYNC_WATCH_H
#include <stdint.h>
#include <stddef.h>

enum sd_sync_kind { SD_SYNC_CREATE, SD_SYNC_OPEN, SD_SYNC_CLOSE, SD_SYNC_INVALID_WAIT };
struct sd_sync_cpu {
    uint32_t eax, ebx, ecx, edx, esi, edi, ebp, esp, eip;
};
typedef int (*sd_sync_reader)(uint32_t, void *, size_t);
typedef void (*sd_sync_logger)(const char *);
void sd_sync_note(unsigned kind, uint32_t tid, uint64_t handle, uint32_t status,
                  int32_t initial, int32_t maximum, uint64_t tick,
                  const struct sd_sync_cpu *cpu, sd_sync_reader read_memory);
void sd_sync_report(sd_sync_logger log);
void wine_nx_sd_sync_report(void);
void wine_nx_sd_sync_created_handle(uintptr_t handle);
#endif
