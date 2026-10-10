/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Based on AutorunHQ's low_window.c at cbb0e4e6e7fa7f47f328d92441f51bfb507f266f.
 * Our single libnx virtmem manager excludes the low window at virtmemSetup,
 * including allocations that precede appletInitialize; no second lock/list.
 */
#include <malloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <switch.h>
#include "sd_low_window.h"
extern void wine_nx_runtime_trace(const char *);
static int sd_low_checked, sd_low_ready;
int sd_low_window_ready(void) { return sd_low_ready; }

static int sd_native_layout(void)
{
    static const InfoType regions[] = {InfoType_HeapRegionAddress,
        InfoType_AliasRegionAddress, InfoType_StackRegionAddress};
    u64 base;
    if ((uintptr_t)sd_native_layout < SD_NATIVE_BASE || (uintptr_t)&base < SD_NATIVE_BASE ||
        (uintptr_t)armGetTls() < SD_NATIVE_BASE) return 0;
    for (unsigned i=0; i<sizeof(regions)/sizeof(regions[0]); ++i)
        if (R_FAILED(svcGetInfo(&base,regions[i],CUR_PROCESS_HANDLE,0)) || base<SD_NATIVE_BASE)
            return 0;
    return 1;
}

static int sd_guest_window_free(void)
{
    uintptr_t address=SD_GUEST_BASE;
    while (address<SD_NATIVE_BASE) {
        MemoryInfo info; u32 page;
        if (R_FAILED(svcQueryMemory(&info,&page,address)) || info.type!=MemType_Unmapped ||
            info.addr>address || !info.size || info.size>UINT64_MAX-info.addr ||
            info.addr+info.size<=address) return 0;
        address=info.addr+info.size;
    }
    return 1;
}

static int sd_probe_page(uintptr_t address,int executable,char *line,size_t line_size)
{
    const size_t size=4096;
    Handle process=envGetOwnProcessHandle();
    u32 *backing=memalign(size,size),page;
    MemoryInfo info;
    Result rc=0,unmap_rc=0;
    int passed=0;
    if (!backing || (uintptr_t)backing<SD_NATIVE_BASE) {
        free(backing); snprintf(line,line_size,"[SD-LOWVA] FAIL high probe backing"); return 0;
    }
    backing[0]=0x528009a0; /* mov w0, #77 */
    backing[1]=0xd65f03c0; /* ret */
    armDCacheFlush(backing,size);
    rc=svcMapProcessCodeMemory(process,address,(u64)backing,size);
    if (R_SUCCEEDED(rc)) {
        rc=svcSetProcessMemoryPermission(process,address,size,executable?Perm_Rx:Perm_Rw);
        if (R_SUCCEEDED(rc)) rc=svcQueryMemory(&info,&page,address);
        if (R_SUCCEEDED(rc) && info.perm==(u32)(executable?Perm_Rx:Perm_Rw)) {
            if (executable) {
                armICacheInvalidate((void *)address,size);
                passed=((unsigned (*)(void))address)()==77;
            } else {
                *(volatile u32 *)address=0x12345678;
                /* RW converts AliasCode to AliasCodeData. Further data-only
                 * protection must use SetMemoryPermission, not SetProcess*. */
                rc=svcSetMemoryPermission((void *)address,size,Perm_None);
                if (R_SUCCEEDED(rc)) rc=svcQueryMemory(&info,&page,address);
                if (R_SUCCEEDED(rc) && info.perm==Perm_None) {
                    rc=svcSetMemoryPermission((void *)address,size,Perm_Rw);
                    if (R_SUCCEEDED(rc)) passed=*(volatile u32 *)address==0x12345678;
                }
            }
        }
        unmap_rc=svcUnmapProcessCodeMemory(process,address,(u64)backing,size);
        if (R_FAILED(unmap_rc)) {
            /* Kernel may still own these pages. Keep them allocated and refuse
             * launch; freeing them could corrupt an unrelated native user. */
            snprintf(line,line_size,"[SD-LOWVA] FAIL unmap=%08x low=%llx; backing retained",unmap_rc,(unsigned long long)address);
            return 0;
        }
        if (!executable && passed) passed=backing[0]==0x12345678;
    }
    free(backing);
    snprintf(line,line_size,"[SD-LOWVA] %s low=%llx %s rc=%08x",
        executable?"RX execute":"RW/NONE/RW alias",(unsigned long long)address,passed?"PASS":"FAIL",rc);
    return passed;
}

void sd_low_window_init(void)
{
    u64 base=0,size=0,total=0,id=0; char line[224],rx[224]="",rw[224]="";
    if (sd_low_checked) return;
    sd_low_checked=1;
    Result a=svcGetInfo(&base,InfoType_AslrRegionAddress,CUR_PROCESS_HANDLE,0);
    Result b=svcGetInfo(&size,InfoType_AslrRegionSize,CUR_PROCESS_HANDLE,0);
    Result c=svcGetInfo(&total,InfoType_TotalMemorySize,CUR_PROCESS_HANDLE,0);
    Result d=svcGetInfo(&id,InfoType_ProgramId,CUR_PROCESS_HANDLE,0);
    snprintf(line,sizeof(line),"[SD-LOWVA] v1 host=%llx+%llx quota=%llu title=%016llx query=%08x/%08x/%08x/%08x",
        (unsigned long long)base,(unsigned long long)size,(unsigned long long)total,
        (unsigned long long)id,a,b,c,d); wine_nx_runtime_trace(line);
    if (R_FAILED(a)||R_FAILED(b)||R_FAILED(c)||R_FAILED(d)||!sd_is_low_window(base,size)||
        id!=UINT64_C(0x059a3db219b42000)||total<=UINT64_C(0x80000000)||
        envGetOwnProcessHandle()==INVALID_HANDLE) {
        wine_nx_runtime_trace("[SD-LOWVA] FAIL profile: use SD low-window Hekate entry and 39-bit HOME forwarder"); return;
    }
    virtmemLock();
    if (sd_native_layout() && sd_guest_window_free())
        sd_low_ready=sd_probe_page(0x00400000,1,rx,sizeof(rx)) &&
                     sd_probe_page(0xffff0000,0,rw,sizeof(rw)) && sd_guest_window_free();
    virtmemUnlock();
    if (rx[0]) wine_nx_runtime_trace(rx);
    if (rw[0]) wine_nx_runtime_trace(rw);
    wine_nx_runtime_trace(sd_low_ready?
        "[SD-LOWVA] PASS: native above 4 GiB; guest low window available":
        "[SD-LOWVA] FAIL layout or mapping probe; game disabled");
}
