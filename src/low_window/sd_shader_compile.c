/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Scoped NAK allocation reuse adapted from Autorun e7168c3f438a.
 * Signature checked against the pinned Mesa 26.2.2 nak.h.
 */
#include <stdbool.h>
#include <stdint.h>
#include "sd_shader_cache.h"
struct nir_shader;
struct nak_compiler;
struct nak_fs_key;
struct nak_shader_bin;
struct nak_shader_bin *__real_nak_compile_shader(struct nir_shader *, bool, const struct nak_compiler *,
                                               uint32_t, const struct nak_fs_key *, bool);
struct nak_shader_bin *__wrap_nak_compile_shader(struct nir_shader *nir, bool dump,
        const struct nak_compiler *nak, uint32_t robust, const struct nak_fs_key *fs, bool task)
{
    if (!sd_shader_cache_enabled) return __real_nak_compile_shader(nir, dump, nak, robust, fs, task);
    sd_shader_cache_begin();
    struct nak_shader_bin *result = __real_nak_compile_shader(nir, dump, nak, robust, fs, task);
    sd_shader_cache_end();
    return result;
}
