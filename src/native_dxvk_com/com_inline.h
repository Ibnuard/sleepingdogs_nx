/* SPDX-License-Identifier: MIT; synchronous input payloads in the v4 packet. */
#pragma once
#include "com_protocol.h"
#include <stddef.h>
#define SD_COM_INLINE_MAGIC 0x53490000u

/* Only these input-only methods have an inline guest encoder. All other
 * compact/legacy packets retain their original wire format and probes. */
static inline int sd_com_inline_count(uint32_t interface_id,uint32_t method) {
    if(interface_id!=SD_COM_IF_ID3D11DeviceContext)return -1;
    switch(method) {
    case 7: case 8: case 9: case 10: case 11: case 16:
    case 22: case 23: case 25: case 26: case 31: case 32:
    case 33: case 35: case 37: case 59: case 60: case 61:
    case 62: case 63: case 64: case 65: case 66: case 67:
    case 69: case 70: case 71:return 3;
    case 18:return 5;
    case 34:return 7;
    case 44: case 45:return 2;
    case 68:return 4;
    default:return -1;
    }
}

#ifdef __cplusplus
namespace sd_com {
struct InlineRange {
    uint64_t begin=0,end=0;
    bool covers(uint32_t address,uint64_t bytes)const {
        return bytes && begin && uint64_t(address)>=begin &&
            uint64_t(address)<=end && bytes<=end-uint64_t(address);
    }
};
/* A Present may release the bridge gate while another host thread enters.
 * Thread-local state also lets a nested dispatcher restore its caller's span.
 * No range survives the synchronous call and no permission is cached. */
inline InlineRange& current_inline_range() {
    static thread_local InlineRange value;
    return value;
}
class InlineScope {
    InlineRange previous;
    bool restore;
public:
    InlineScope():previous(current_inline_range()),restore(previous.begin!=0) {
        if(restore)current_inline_range()={};
    }
    ~InlineScope(){if(restore)current_inline_range()=previous;}
    InlineScope(const InlineScope&)=delete;
    InlineScope& operator=(const InlineScope&)=delete;
    void allow(uint32_t packet,const sd_com_packet& decoded) {
        if((decoded.reserved&0xffff0000u)!=SD_COM_INLINE_MAGIC)return;
        int n=sd_com_inline_count(decoded.interface_id,decoded.method);
        if(n>=0 && decoded.reserved==(SD_COM_INLINE_MAGIC|uint32_t(n))) {
            restore=true;
            current_inline_range()={uint64_t(packet)+offsetof(sd_com_packet,words)+4u*uint32_t(n),
                                    uint64_t(packet)+sizeof(sd_com_packet)};
        }
    }
};
}
#endif
