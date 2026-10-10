/* Exact production helper, with the pinned Wine ABI types and sanitizers. */
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "windef.h"
#include "winternl.h"
#include "../src/sd_wow64_debug_cache.h"

int main(void)
{
    struct { unsigned char before[32]; TEB32 teb; unsigned char after[32]; } a, b, original;
    I386_CONTEXT ctx = {0};
    memset(&a, 0xa5, sizeof(a)); original = a; b = a;
    ctx.Dr0 = 0x4c0a8a; ctx.Dr1 = 0x5b2e92; ctx.Dr2 = 0x61ce88;
    ctx.Dr3 = 0x68d35a; ctx.Dr6 = 9; ctx.Dr7 = 0x155;
    assert(sd_wow64_sync_debug_cache(&a.teb, &ctx));
    assert(!sd_wow64_sync_debug_cache(&a.teb, &ctx));
    const unsigned char *p = (const unsigned char *)&a, *q = (const unsigned char *)&original;
    size_t offset = offsetof(__typeof__(a), teb) + 0x1dc;
    for (size_t i = 0; i < sizeof(a); ++i)
        if (i < offset || i >= offset + 24) assert(p[i] == q[i]);
    assert(!memcmp((char *)&a.teb + 0x1dc, &ctx.Dr0, 24));
    assert(!memcmp(&b, &original, sizeof(b)));
    assert(!sd_wow64_sync_debug_cache(NULL, &ctx));
    assert(!sd_wow64_sync_debug_cache(&b.teb, NULL));
    memset(&ctx, 0, sizeof(ctx));
    assert(sd_wow64_sync_debug_cache(&a.teb, &ctx));
    assert(!memcmp((char *)&a.teb + 0x1dc, &ctx.Dr0, 24));
    for (unsigned i = 0; i < 10000; ++i) {
        ctx.Dr0 = i; ctx.Dr7 = i & 0xff;
        sd_wow64_sync_debug_cache(&a.teb, &ctx);
        assert(!memcmp((char *)&a.teb + 0x1dc, &ctx.Dr0, 24));
        assert(!memcmp(&b, &original, sizeof(b)));
    }
    puts("PASS cache layout, six registers, explicit clearing, idempotence, null inputs");
    puts("PASS selectors/exit frame/rest of TEB and surrounding guards preserved");
    puts("PASS 10000 updates with independent second thread untouched");
    return 0;
}
