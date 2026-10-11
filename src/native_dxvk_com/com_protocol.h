/* SPDX-License-Identifier: MIT; fixed-width PE32/native COM transport. */
#pragma once
#include <stdint.h>
#include "com_interfaces.h"
#define SD_COM_ABI 4u
#define SD_COM_MAX_ARRAY 16384u
#define SD_COM_PRIVATE_INTERFACE 1u
enum sd_com_global {
    SD_COM_CREATE_DEVICE = 1, SD_COM_CREATE_FACTORY, SD_COM_BIND_MAP,
    SD_COM_ABORT_MAP, SD_COM_STATS, SD_COM_SHUTDOWN
};
struct sd_com_packet {
    uint32_t abi, object, interface_id, method;
    uint32_t ret, fault, aux, reserved;
    uint32_t args[16], high[16];
};
struct sd_com_subresource32 { uint32_t data, row_pitch, slice_pitch; };
struct sd_com_mapped32 { uint32_t data, row_pitch, depth_pitch; };
struct sd_com_input32 {
    uint32_t semantic, index, format, slot, offset, slot_class, step;
};
struct sd_com_so32 {
    uint32_t stream, semantic, index;
    uint8_t start, count, slot, pad;
};
struct sd_com_swapchain32 {
    uint32_t mode[7], sample[2], usage, count, window, windowed, effect, flags;
};
#ifdef __cplusplus
static_assert(sizeof(sd_com_packet)==160 && sizeof(sd_com_swapchain32)==60, "COM transport ABI");
extern "C" {
#else
_Static_assert(sizeof(struct sd_com_packet)==160 && sizeof(struct sd_com_swapchain32)==60, "COM transport ABI");
#endif
typedef int32_t (*sd_com_unix_entry)(void*);
extern const sd_com_unix_entry wine_nx_sd_com_wow64_unix_funcs[];
extern const unsigned int wine_nx_sd_com_wow64_unix_count;
void sd_com_shutdown(void);
void* sd_com_native_window(void);
uint64_t sd_com_clock_ns(void);
uint64_t sd_com_thread_id(void);
void sd_com_presented(uint32_t token, int32_t result);
#ifdef __cplusplus
}
#endif
