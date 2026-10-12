/* SPDX-License-Identifier: MIT; wire layout must match the guest and host. */
#include "probe_protocol.h"
#include <stddef.h>

_Static_assert(sizeof(void*) == SD_NDX_EXPECT_POINTER_BYTES, "wrong compiler target");
_Static_assert(sizeof(uint32_t) == 4, "wire word size");
_Static_assert(offsetof(struct sd_ndx_packet, abi) == 0, "abi offset");
_Static_assert(offsetof(struct sd_ndx_packet, op) == 4, "operation offset");
_Static_assert(offsetof(struct sd_ndx_packet, object) == 8, "object offset");
_Static_assert(offsetof(struct sd_ndx_packet, flags) == 12, "flags offset");
_Static_assert(offsetof(struct sd_ndx_packet, args) == 16, "argument offset");
_Static_assert(offsetof(struct sd_ndx_packet, result) == 48, "result offset");
_Static_assert(sizeof(struct sd_ndx_packet) == 64, "wire packet size");
