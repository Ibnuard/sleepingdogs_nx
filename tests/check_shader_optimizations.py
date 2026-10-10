"""Execute v9 allocator/affinity integration and preserve a verified v8 control."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from port_common import ROOT, APPROVED, sha, write_json
from sleepingdogs_shader_optimizations import apply, FILES, COPIES
from check_perf_counters import HARNESS as PERF_HARNESS

WRAPPER = r'''
#include <assert.h>
#include <stdlib.h>
#include <malloc.h>
#include <string.h>
#include "sd_shader_cache.c"
#include "sd_shader_compile.c"
void wine_nx_runtime_trace(const char *s) {(void)s;}
static unsigned calls, failure;
struct nak_shader_bin *__real_nak_compile_shader(struct nir_shader *nir, bool dump,
    const struct nak_compiler *nak, uint32_t robust, const struct nak_fs_key *fs, bool task) {
    assert(nir==(void*)1&&dump&&nak==(void*)2&&robust==123&&fs==(void*)3&&task);
    ++calls;assert(!!sd_shader_cache_active==!!sd_shader_cache_enabled);
    void *p=malloc(128);assert(p);
    if(!sd_shader_cache_put(p,malloc_usable_size(p)))free(p);
    return failure?NULL:(void*)4;
}
int main(void) {
    assert(__wrap_nak_compile_shader((void*)1,1,(void*)2,123,(void*)3,1)==(void*)4);
    assert(!workers&&!cache.bytes&&!cache.depth);
    sd_shader_cache_enabled=1;
    assert(__wrap_nak_compile_shader((void*)1,1,(void*)2,123,(void*)3,1)==(void*)4);
    assert(!workers&&!cache.bytes&&!cache.depth&&totals[0]==1);
    failure=1;assert(!__wrap_nak_compile_shader((void*)1,1,(void*)2,123,(void*)3,1));
    assert(calls==3&&!workers&&!cache.bytes&&!cache.depth&&totals[0]==2);
    puts("PASS: NAK wrapper forwards all ABI arguments/results and drains cache on success/failure; OFF bypasses scope");
}
'''


def function(s, signature):
    start = s.index(signature)
    end = s.index('\n}\n', start) + 3
    return s[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1/native-source'))
    parser.add_argument('--before-build', action='store_true')
    args = parser.parse_args()
    receipt = json.loads((ROOT/'dist/low-window-perf-counters/native.json').read_text())
    original = ROOT/'local/shader-v9-v8-source'
    out = ROOT/'local/shader-v9-check'
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    with tempfile.TemporaryDirectory(dir=out, prefix='source-') as tmp:
        source = Path(tmp)
        for name in FILES:
            if name not in receipt['source_files']:
                continue
            assert sha(original/name) == receipt['source_files'][name], name
            dest = source/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original/name, dest)
        apply(source)
        native = source/'wine-nx-probe/source'
        shutil.copy2(original/'wine-nx-probe/source/native_heap/fextendo_rust_symbols.h', native/'native_heap')
        for name in ('fex_balance_stable.h','fex_worker_cores.h'):
            shutil.copy2(APPROVED/'source/src/runtime'/name, native/name)
        profile = (native/'thread_profile.c').read_text()
        glue = '\n'.join(function(profile, sig) for sig in
            ('void wine_nx_thread_register(', 'void wine_nx_thread_balance('))
        (native/'shader_registry_glue.inc').write_text(glue)
        if not args.before_build:
            for name in FILES:
                assert (source/name).read_bytes() == (args.source/name).read_bytes(), name
        vulkan = (source/'dlls/winevulkan/vulkan_thunks.c').read_text()
        for architecture in ('32','64'):
            for kind in ('Compute','Graphics'):
                f = function(vulkan, f'static NTSTATUS thunk{architecture}_vkCreate{kind}Pipelines(')
                assert f.index('wine_nx_thread_pipeline_begin()') < f.index(f'->p_vkCreate{kind}Pipelines(') < f.index('wine_nx_thread_pipeline_end(')
                assert f.count('wine_nx_thread_pipeline_begin()') == f.count('wine_nx_thread_pipeline_end(') == 1
        # Parse the generator; retain its generation hook for both thunk ABIs.
        compile((source/'dlls/winevulkan/make_vulkan').read_text(), 'make_vulkan', 'exec')
        runtime = (native/'runtime.c').read_text()
        for config in ('shader-affinity.txt','shader-cache.txt'):
            assert f'"/{config}", 0)' in runtime
        assert '!guest_tests && wine_nx_config_file_bool(RUNTIME_DIR "/shader-cache.txt", 0)' in runtime
        programs = {'affinity': (ROOT/'tests/shader_affinity.c').read_text(),
                    'cache': (ROOT/'tests/shader_cache.c').read_text(), 'wrapper': WRAPPER}
        programs['interval'] = PERF_HARNESS.replace('#include "sd_perf_summary.h"',
            'static unsigned shader_reports;\nstatic void sd_shader_cache_report(void) { ++shader_reports; }\n#include "sd_perf_summary.h"').replace(
            '    puts("PASS:', '    assert(shader_reports==5);\n    puts("PASS:')
        compiler = shutil.which('clang') or shutil.which('cc')
        assert compiler
        for name, code in programs.items():
            src, binary = out/(name+'.c'), out/name
            src.write_text(code)
            subprocess.run([compiler, '-std=gnu11', '-O1', '-g', '-pthread', '-Wall', '-Wextra', '-Werror',
                '-Wno-address', '-Wno-unused-function', '-Wno-misleading-indentation',
                '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                '-I', str(native), str(src), '-o', str(binary)], check=True)
            p = subprocess.run([str(binary)], capture_output=True, text=True)
            assert p.returncode == 0, p.stdout+p.stderr
            results[name] = p.stdout.strip()
            print(p.stdout, end='', flush=True)
        report = dict(status='PASS', hardware_tested=False, all_native_changes_match_overlay=not args.before_build,
            sanitizers=['address','undefined'], results=results, vulkan_thunks_checked=4,
            source_files={n:sha(source/n) for n in sorted(FILES)},
            sources={n:sha(ROOT/n) for n in sorted(set(COPIES.values()) | {
                'tools/sleepingdogs_shader_optimizations.py','tests/check_shader_optimizations.py',
                'tests/shader_affinity.c','tests/shader_cache.c','tests/check_perf_counters.py'})})
        path = ROOT/'reports'/('low-window-v9-shaders-prebuild.json' if args.before_build else 'low-window-v9-shaders.json')
        write_json(path, report)
        print('Report:', path, flush=True)


if __name__ == '__main__':
    main()
