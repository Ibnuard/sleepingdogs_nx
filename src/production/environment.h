/* SPDX-License-Identifier: LGPL-2.1-or-later. One logging policy in guest env. */
#pragma once
#include <stddef.h>
#include <string.h>

static size_t sd_production_environment(char *out,size_t capacity,
                                        const char *input,size_t bytes,int debug) {
    static const char quiet[]="FEXTENDO_TRACE=0\0DXVK_LOG_LEVEL=none\0DXVK_LOG_PATH=none\0WINEDEBUG=-all\0";
    static const char capture[]="FEXTENDO_TRACE=0\0DXVK_LOG_LEVEL=info\0DXVK_LOG_PATH=C:\\SleepingDogs\0WINEDEBUG=-all\0";
    size_t used=0,at=0;
    if(!out||!input||!bytes)return 0;
    while(at<bytes&&input[at]) {
        const char *end=(const char*)memchr(input+at,0,bytes-at);
        if(!end)return 0;
        size_t n=(size_t)(end-input-at)+1;
        if(strncmp(input+at,"FEXTENDO_TRACE=",15)&&strncmp(input+at,"DXVK_LOG_LEVEL=",15)&&
           strncmp(input+at,"DXVK_LOG_PATH=",14)&&strncmp(input+at,"WINEDEBUG=",10)) {
            if(n>capacity-used)return 0;
            memcpy(out+used,input+at,n);used+=n;
        }
        at+=n;
    }
    const char *policy=debug?capture:quiet;
    size_t n=debug?sizeof(capture):sizeof(quiet);
    if(n>capacity-used)return 0;
    memcpy(out+used,policy,n);return used+n;
}
