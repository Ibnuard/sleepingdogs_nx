/* SPDX-License-Identifier: MIT; fixed guest/native diagnostic ABI. */
#include <stddef.h>
#include "bridge_protocol.h"
_Static_assert(sizeof(void*)==SD_NDX_EXPECT_POINTER_BYTES,"target pointer width");
_Static_assert(offsetof(struct sd_ndx_bridge_init,session)==12,"init session");
_Static_assert(offsetof(struct sd_ndx_bridge_dispatch,packet)==8,"dispatch packet");
_Static_assert(offsetof(struct sd_ndx_bridge_dispatch,hresult)==12,"dispatch result");
_Static_assert(sizeof(struct sd_ndx_packet)==64,"renderer packet");
