/* SPDX-License-Identifier: MIT
 * Exact last-call keys for bindings without resource read/write hazards.
 * The caller supplies checked, copied wire tokens, never COM pointer identity.
 * This is a binding cache, not a buffer-content cache. Map/Unmap still execute.
 */
#pragma once
#include <stdint.h>
#include <string.h>
#include "com_protocol.h"
#define SD_STATE_SLOTS 25u
#define SD_STATE_WORDS 98u
#define SD_COM_STATE_REPORT 7u
struct sd_state_key { uint32_t count,words[SD_STATE_WORDS]; };
struct sd_state_cache {
    uint32_t owner,disabled,valid,busy,epoch;
    uint32_t attempts[SD_STATE_SLOTS],hits[SD_STATE_SLOTS];
    struct sd_state_key keys[SD_STATE_SLOTS];
};
/* No SRV/UAV/RTV, IA buffers, stream output, predication, draw or dispatch.
 * Those calls can have hazards, counter side effects or execute GPU work. */
static inline int sd_state_slot(uint32_t method) {
    switch(method) {
    case 7:return 0; case 16:return 1; case 22:return 2;
    case 62:return 3; case 66:return 4; case 71:return 5; /* CB: VS PS GS HS DS CS */
    case 26:return 6; case 10:return 7; case 32:return 8;
    case 61:return 9; case 65:return 10; case 70:return 11; /* samplers */
    case 11:return 12; case 9:return 13; case 23:return 14;
    case 60:return 15; case 64:return 16; case 69:return 17; /* shaders */
    case 17:return 18; case 24:return 19; case 43:return 20;
    case 36:return 21; case 35:return 22; case 44:return 23;
    case 45:return 24;
    default:return -1;
    }
}
static inline int sd_state_make_key(const struct sd_com_packet *p,struct sd_state_key *key) {
    int slot=sd_state_slot(p->method);if(slot<0)return -1;
    const uint32_t *a=p->args;uint32_t n=0;
    if(slot<12) {
        uint32_t limit=slot<6?14u:16u,start=a[0],count=a[1];
        if(start>=limit||count>limit-start||!count||!a[2])return -1;
        key->words[n++]=start;key->words[n++]=count;
        memcpy(key->words+n,(const void*)(uintptr_t)a[2],count*4);n+=count;
    } else if(slot<18) {
        /* Dynamic class instances use the baseline path. Their call also
         * invalidates this shader key so a later no-class call cannot hit. */
        if(a[2])return -1;
        key->words[n++]=a[0];
    } else if(slot<=20) key->words[n++]=a[0];
    else if(slot==21) {key->words[n++]=a[0];key->words[n++]=a[1];}
    else if(slot==22) {
        key->words[n++]=a[0];key->words[n++]=a[2];
        if(a[1])memcpy(key->words+n,(const void*)(uintptr_t)a[1],16);
        else for(unsigned i=0;i<4;++i)key->words[n+i]=0x3f800000u;
        n+=4;
    } else {
        uint32_t count=a[0],stride=slot==23?6u:4u;
        if(count>16u||(count&&!a[1]))return -1;
        key->words[n++]=count;
        if(count)memcpy(key->words+n,(const void*)(uintptr_t)a[1],count*stride*4);
        n+=count*stride;
    }
    key->count=n;return slot;
}
static inline int sd_state_equal(const struct sd_state_key *a,const struct sd_state_key *b) {
    return a->count==b->count&&!memcmp(a->words,b->words,a->count*4);
}
