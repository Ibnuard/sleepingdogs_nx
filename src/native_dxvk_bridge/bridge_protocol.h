/* SPDX-License-Identifier: MIT; original FEXTendo diagnostic WOW64 protocol. */
#pragma once
#include <stdint.h>
#include "../native_dxvk/probe_protocol.h"

#define SD_NDX_BRIDGE_ABI 1u
#define SD_NDX_BRIDGE_ARENA_BYTES (8u * 1024u * 1024u)
#define SD_NDX_BRIDGE_METADATA_BYTES 4096u
enum sd_ndx_bridge_op { SD_NDX_BRIDGE_INIT, SD_NDX_BRIDGE_DISPATCH, SD_NDX_BRIDGE_CLOSE };
struct sd_ndx_bridge_init { uint32_t abi, arena, bytes, session; };
struct sd_ndx_bridge_dispatch { uint32_t abi, session, packet; int32_t hresult; };
struct sd_ndx_bridge_close { uint32_t abi, session, flags; };

#ifdef __cplusplus
static_assert(sizeof(sd_ndx_bridge_init)==16 && sizeof(sd_ndx_bridge_dispatch)==16 && sizeof(sd_ndx_bridge_close)==12, "bridge layout");
extern "C" {
#else
_Static_assert(sizeof(struct sd_ndx_bridge_init)==16 && sizeof(struct sd_ndx_bridge_dispatch)==16 && sizeof(struct sd_ndx_bridge_close)==12, "bridge layout");
#endif
typedef int32_t (*sd_ndx_unix_entry)(void*);
extern const sd_ndx_unix_entry wine_nx_sd_ndx_wow64_unix_funcs[];
extern const unsigned int wine_nx_sd_ndx_wow64_unix_count;
#ifdef __cplusplus
}
#endif
