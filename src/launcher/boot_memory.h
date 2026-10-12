/* SPDX-License-Identifier: LGPL-2.1-or-later. Kernel data, never a file marker. */
#ifndef SD_BOOT_MEMORY_H
#define SD_BOOT_MEMORY_H
#include <stdint.h>
struct sd_boot_memory {uint64_t base,size,total,title;uint32_t rc[4];};
static struct sd_boot_memory sd_boot;
static int sd_boot_profile_valid(const struct sd_boot_memory *m){
    return !(m->rc[0]|m->rc[1]|m->rc[2]|m->rc[3])&&m->base==UINT64_C(0x200000)&&
        m->size==UINT64_C(0x8000000000)-UINT64_C(0x200000)&&m->total>UINT64_C(0x80000000)&&
        m->title==UINT64_C(0x059a3db219b42000);
}
#ifdef __SWITCH__
static int sd_boot_memory_compatible(void){
    sd_boot.rc[0]=svcGetInfo(&sd_boot.base,InfoType_AslrRegionAddress,CUR_PROCESS_HANDLE,0);
    sd_boot.rc[1]=svcGetInfo(&sd_boot.size,InfoType_AslrRegionSize,CUR_PROCESS_HANDLE,0);
    sd_boot.rc[2]=svcGetInfo(&sd_boot.total,InfoType_TotalMemorySize,CUR_PROCESS_HANDLE,0);
    sd_boot.rc[3]=svcGetInfo(&sd_boot.title,InfoType_ProgramId,CUR_PROCESS_HANDLE,0);
    return sd_boot_profile_valid(&sd_boot);
}
#endif
#endif
