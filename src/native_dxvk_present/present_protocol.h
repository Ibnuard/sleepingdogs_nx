/* SPDX-License-Identifier: MIT; bounded H3 diagnostic, not a game COM ABI. */
#pragma once
#include "../native_dxvk_bridge/bridge_protocol.h"

/* DISPATCH packet extension. args[0]=0 returns presents, elapsed microseconds,
 * full arena scans and dispatch count. args[0]=1 returns accumulated bridge
 * validation/copy microseconds and native-dispatch microseconds. */
#define SD_NDX_H3_STATS 17u
#define SD_NDX_H3_FRAMES 300u

#ifdef __cplusplus
extern "C" {
#endif
int sd_ndx_h3_window_prepare(void);
void* sd_ndx_h3_native_window(void);
uint64_t sd_ndx_h3_clock_ns(void);
void sd_ndx_h3_shutdown(void);
#ifdef __cplusplus
}
#endif
