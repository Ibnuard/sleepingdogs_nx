"""Adapt Autorun shader improvements to the existing FEXTendo FEX runtime."""
from pathlib import Path
import re
from f1_overlay import exact
from port_common import ROOT

BUILD = 'sleepingdogs-low-window-v9-shader-optimizations'
MARKER = 'sleepingdogs-fextendo-0.1.0-low-window-v9-shader-optimizations'
NATIVE = 'wine-nx-probe/source/'
COPIES = {
    NATIVE+'sd_shader_affinity.h': 'src/low_window/sd_shader_affinity.h',
    NATIVE+'sd_shader_cache.h': 'src/low_window/sd_shader_cache.h',
    NATIVE+'sd_shader_cache.c': 'src/low_window/sd_shader_cache.c',
    NATIVE+'sd_shader_compile.c': 'src/low_window/sd_shader_compile.c',
    NATIVE+'native_heap/fextendo_mesa_heap.h': 'src/low_window/fextendo_mesa_shader_heap.h',
    NATIVE+'native_heap/fextendo_rust_heap.h': 'src/low_window/fextendo_rust_shader_heap.h',
}
FILES = set(COPIES) | {NATIVE+n for n in ('runtime.c','thread_profile.c','thread_profile.h',
    'fex_dxvk_core3.h','sd_perf_summary.h')} | {'wine-nx-probe/CMakeLists.txt',
    'dlls/winevulkan/vulkan_thunks.c','dlls/winevulkan/vulkan_private.h','dlls/winevulkan/make_vulkan'}


def apply(source: Path):
    def edit(name, change):
        path = source/name
        path.write_text(change(path.read_text()))

    def runtime(s):
        s = exact(s, 'sleepingdogs-fextendo-0.1.0-low-window-v8-perf-counters', MARKER)
        s = exact(s, '#define FX_APP_VERSION "0.1.0-v8"', '#define FX_APP_VERSION "0.1.0-v9"')
        s = exact(s, '#include "sd_perf_summary.h"',
                  '#include "sd_shader_cache.h"\n#include "sd_perf_summary.h"')
        return exact(s, '    sd_perf_counters = wine_nx_config_file_bool(RUNTIME_DIR "/performance-counters.txt", 0);',
            '    extern int wine_nx_sd_shader_configure(int requested);\n'
            '    const int sd_shader_affinity = wine_nx_sd_shader_configure(!guest_tests &&\n'
            '        wine_nx_config_file_bool(RUNTIME_DIR "/shader-affinity.txt", 0));\n'
            '    sd_shader_cache_enabled = !guest_tests && wine_nx_config_file_bool(RUNTIME_DIR "/shader-cache.txt", 0);\n'
            '    log_line("[SD-SHADER] v1 affinity=%d cache=%d; application cores 0-2, priority unchanged, scoped NAK allocation reuse",\n'
            '             sd_shader_affinity, sd_shader_cache_enabled);\n'
            '    sd_perf_counters = wine_nx_config_file_bool(RUNTIME_DIR "/performance-counters.txt", 0);')
    edit(NATIVE+'runtime.c', runtime)

    def profile(s):
        # The v8 tree already carries the byte-identical helper header locally.
        s, n = re.subn(r'#include "[^"\n]+/fex_dxvk_core3.h"', '#include "fex_dxvk_core3.h"', s)
        assert n == 1
        s = exact(s, '        memset(&fex_dxvk_slots[slot],0,sizeof(fex_dxvk_slots[slot]));',
            '        memset(&fex_dxvk_slots[slot],0,sizeof(fex_dxvk_slots[slot]));\n'
            '        memset(&sd_shader_slots[slot],0,sizeof(sd_shader_slots[slot]));')
        s = exact(s, "        if (!thread->handle || thread->kind != 'w' || fex_dxvk_slots[i].active) continue;",
            '        if (thread->handle) sd_shader_retry_locked(i);\n'
            "        if (!thread->handle || thread->kind != 'w' || fex_dxvk_slots[i].active || sd_shader_slots[i].mode) continue;")
        return s
    edit(NATIVE+'thread_profile.c', profile)
    edit(NATIVE+'thread_profile.h', lambda s: exact(s, '#include <stdint.h>', '#include <stdint.h>\n'
        'unsigned int wine_nx_thread_pipeline_begin(void);\nvoid wine_nx_thread_pipeline_end(unsigned int token);'))

    def core3(s):
        s = exact(s, 'static int fex_dxvk_enabled;', 'static int fex_dxvk_enabled;\n#include "sd_shader_affinity.h"')
        s = exact(s, '        snprintf(s->name,sizeof(s->name),"%s",name);',
            '        if (!sd_shader_before_name_locked(i,name)) break;\n'
            '        snprintf(s->name,sizeof(s->name),"%s",name);')
        s = exact(s, '        s32 actual_core=-1,priority=-1;u64 actual_mask=0;',
            '        sd_shader_after_name_locked(i,name);\n'
            '        s32 actual_core=-1,priority=-1;u64 actual_mask=0;')
        s = exact(s, 'read_priority_rc=%x tick=%llu",', 'read_priority_rc=%x tick=%llu shader_mode=%u",')
        s = exact(s, '(unsigned)cm,(unsigned)pr,(unsigned long long)armGetSystemTick());',
            '(unsigned)cm,(unsigned)pr,(unsigned long long)armGetSystemTick(),sd_shader_slots[i].mode);')
        s = exact(s, '        if(fex_dxvk_slots[i].active){',
            '        if (sd_shader_explicit_locked(i,mask)) {\n'
            '            handled=1;\n'
            '            snprintf(line,sizeof(line),"[SD-SHADER-AFFINITY] explicit tid=%u mask=%llx pending=%u",\n'
            '                     tid,(unsigned long long)mask,sd_shader_slots[i].mode);\n'
            '            break;\n'
            '        }\n'
            '        if(fex_dxvk_slots[i].active){')
        return s
    edit(NATIVE+'fex_dxvk_core3.h', core3)
    edit(NATIVE+'sd_perf_summary.h', lambda s: exact(s, '    fex_sync_report();',
        '    fex_sync_report();\n    sd_shader_cache_report();'))

    def vulkan(s):
        pattern = r'^(    params->result = [^\n]+->p_vkCreate(?:Compute|Graphics)Pipelines\([^\n]+\);)$'
        s, n = re.subn(pattern, '#ifdef __SWITCH__\n'
            '    unsigned int nx_pipeline_affinity = wine_nx_thread_pipeline_begin();\n'
            '#endif\n\\1\n#ifdef __SWITCH__\n'
            '    wine_nx_thread_pipeline_end(nx_pipeline_affinity);\n#endif', s, flags=re.M)
        assert n == 4, n
        return s
    edit('dlls/winevulkan/vulkan_thunks.c', vulkan)
    edit('dlls/winevulkan/vulkan_private.h', lambda s: exact(s, '#include "wine/rbtree.h"',
        '#include "wine/rbtree.h"\n#ifdef __SWITCH__\n'
        'extern unsigned int wine_nx_thread_pipeline_begin(void);\n'
        'extern void wine_nx_thread_pipeline_end(unsigned int token);\n#endif'))
    def generator(s):
        s = exact(s, '        # Call the host Vulkan function.\n',
            '        # Call the host Vulkan function.\n'
            '        pipeline_affinity = self.name in ("vkCreateGraphicsPipelines", "vkCreateComputePipelines")\n'
            '        if pipeline_affinity:\n'
            '            body += "#ifdef __SWITCH__\\n    unsigned int nx_pipeline_affinity = wine_nx_thread_pipeline_begin();\\n#endif\\n"\n')
        return exact(s, '        # Call any host_to_win conversion calls.\n',
            '        if pipeline_affinity:\n'
            '            body += "#ifdef __SWITCH__\\n    wine_nx_thread_pipeline_end(nx_pipeline_affinity);\\n#endif\\n"\n\n'
            '        # Call any host_to_win conversion calls.\n')
    edit('dlls/winevulkan/make_vulkan', generator)
    edit('wine-nx-probe/CMakeLists.txt', lambda s: s + '\n# FEXTendo v9: scoped shader optimizations (Autorun backport).\n'
         'target_sources(wine-nx-runtime PRIVATE source/sd_shader_cache.c source/sd_shader_compile.c)\n'
         'target_link_options(wine-nx-runtime PRIVATE -Wl,--wrap=nak_compile_shader)\n'
         'set_property(SOURCE source/sd_shader_cache.c source/sd_shader_compile.c APPEND PROPERTY COMPILE_OPTIONS -O2)\n')
    for name, original in COPIES.items():
        (source/name).write_bytes((ROOT/original).read_bytes())
