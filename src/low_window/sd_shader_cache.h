/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Bounded compiler allocation reuse adapted from Autorun e7168c3f438a.
 * FEXTendo uses its existing Mesa/Rust allocation shims, not global malloc hooks.
 */
#ifndef SD_SHADER_CACHE_H
#define SD_SHADER_CACHE_H
#include <stddef.h>
extern int sd_shader_cache_enabled;
extern __thread unsigned sd_shader_cache_active;
void sd_shader_cache_begin(void);
void sd_shader_cache_end(void);
void *sd_shader_cache_take(size_t size, size_t alignment);
int sd_shader_cache_put(void *pointer, size_t usable);
int sd_shader_cache_trim(void);
void sd_shader_cache_report(void);
#endif
