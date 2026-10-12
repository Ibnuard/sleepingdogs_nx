/* SPDX-License-Identifier: MIT; original FEXTendo x86/native probe ABI. */
#pragma once
#include <stdint.h>
#define SD_NDX_ABI 1u
enum sd_ndx_op {
    SD_NDX_CREATE_DEVICE = 1, SD_NDX_CREATE_BUFFER, SD_NDX_MAP, SD_NDX_UNMAP,
    SD_NDX_CREATE_TEXTURE, SD_NDX_CREATE_RTV, SD_NDX_CREATE_VS, SD_NDX_CREATE_PS,
    SD_NDX_SET_PIPELINE, SD_NDX_DRAW, SD_NDX_COPY, SD_NDX_RELEASE,
    SD_NDX_CREATE_SWAPCHAIN, SD_NDX_GET_BACKBUFFER, SD_NDX_PRESENT,
    SD_NDX_CLEAR_STATE
};
/* No native pointers, size_t, bool or compiler-dependent bitfields cross ABI. */
struct sd_ndx_packet {
    uint32_t abi, op, object, flags;
    uint32_t args[8];
    uint32_t result[4];
};
/* Guest addresses are checked against this explicitly supplied arena. */
#ifdef __cplusplus
extern "C" {
#endif
void* sd_ndx_session_create(void* arena, uint32_t guest_base, uint32_t size, void* native_window);
void sd_ndx_session_destroy(void* session);
int32_t sd_ndx_dispatch(void* session, struct sd_ndx_packet* packet);
#ifdef __cplusplus
}
static_assert(sizeof(sd_ndx_packet) == 64, "x86/native packet layout changed");
#else
_Static_assert(sizeof(struct sd_ndx_packet) == 64, "x86/native packet layout changed");
#endif
