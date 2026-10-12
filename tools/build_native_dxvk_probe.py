"""Build an isolated real DXVK Native D3D11 probe for Linux and Horizon.

This does not install a renderer into the game prefix. Source is the pinned
3.1.1-sdbatch2 input used by v18; only the task-owned copy is adapted.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / 'vendor/dxvk/native-probe-v1-inputs.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_changed(path, text):
    if not path.exists() or path.read_text() != text:
        path.write_text(text, newline='\n')


def run(argv, log):
    with log.open('w') as output:
        result = subprocess.run(list(map(str, argv)), stdout=output,
                                stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text()[-14000:], flush=True)
        raise RuntimeError(f'Build failed: {log}')


def replace(path, before, after):
    text = path.read_text()
    if text.count(before) != 1:
        raise RuntimeError(f'Expected one source anchor in {path}: {before[:70]}')
    path.write_text(text.replace(before, after), newline='\n')


def pinned_manifest(baseline):
    receipt = json.loads(INPUTS.read_text())
    if sha(baseline.parent / 'prepared.json') != receipt['prepared_receipt_sha256']:
        raise RuntimeError('Baseline preparation receipt differs from the pinned input')
    return receipt['source_files']


def prepare(work, baseline):
    source = work / 'source'
    pinned = pinned_manifest(baseline)
    for name, digest in pinned.items():
        if sha(baseline / name) != digest:
            raise RuntimeError(f'Pinned DXVK input changed: {name}')
    if not source.exists():
        shutil.copytree(baseline, source, symlinks=True)
    # Recreate adapted inputs from the baseline, allowing repeatable rebuilding.
    patched = ('src/wsi/wsi_platform.cpp', 'src/wsi/wsi_platform.h',
               'src/vulkan/vulkan_loader.cpp', 'src/util/util_env.cpp',
               'src/util/util_win32_compat.h', 'src/util/thread.h', 'src/dxgi/dxgi_main.cpp')
    for name in patched:
        shutil.copy2(baseline / name, source / name)
    for name, digest in pinned.items():
        if name not in patched and sha(source / name) != digest:
            raise RuntimeError(f'Unexpected change in isolated DXVK source: {name}')
    replace(source / patched[0], '  static const WsiBootstrap *wsiBootstrap[] = {',
            '  static const WsiBootstrap *wsiBootstrap[] = {\n    &ProbeWSI,')
    replace(source / patched[1], '  void init();',
            '  extern WsiBootstrap ProbeWSI;\n\n  void init();')
    replace(source / patched[2], '#include "vulkan_loader.h"',
            '#include "vulkan_loader.h"\n#ifdef SD_NATIVE_STATIC_VULKAN\n'
            'extern "C" PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance, const char*);\n#endif')
    replace(source / patched[2], '  static std::pair<HMODULE, PFN_vkGetInstanceProcAddr> loadVulkanLibrary() {',
            '  static std::pair<HMODULE, PFN_vkGetInstanceProcAddr> loadVulkanLibrary() {\n'
            '#ifdef SD_NATIVE_STATIC_VULKAN\n'
            '    return {nullptr, &vkGetInstanceProcAddr};\n'
            '#else')
    replace(source / patched[2], '    return { };\n  }',
            '    return { };\n#endif\n  }')
    replace(source / patched[4], '#include <dlfcn.h>',
            '#ifndef __SWITCH__\n#include <dlfcn.h>\n#endif')
    replace(source / patched[4], '  return dlopen(lpLibFileName, RTLD_NOW);',
            '#ifdef __SWITCH__\n  (void)lpLibFileName; return nullptr;\n#else\n'
            '  return dlopen(lpLibFileName, RTLD_NOW);\n#endif')
    replace(source / patched[4], '  dlclose(module);',
            '#ifndef __SWITCH__\n  dlclose(module);\n#else\n  (void)module;\n#endif')
    replace(source / patched[4], '  return dlsym(module, lpProcName);',
            '#ifdef __SWITCH__\n  (void)lpProcName; return nullptr;\n#else\n'
            '  return dlsym(module, lpProcName);\n#endif')
    replace(source / patched[3], '#elif defined(__FreeBSD__)\n    int mib[4]',
            '#elif defined(__SWITCH__)\n    return "sd-dxvk-native-probe";\n'
            '#elif defined(__FreeBSD__)\n    int mib[4]')
    replace(source / patched[3],
            '    ::pthread_setname_np(pthread_self(), posixName.data());',
            '#ifndef __SWITCH__\n    ::pthread_setname_np(pthread_self(), posixName.data());\n'
            '#else\n    (void)posixName; // libnx has no optional POSIX thread-name API.\n#endif')
    replace(source / 'src/util/thread.h',
            '      ::pthread_setschedparam(this->native_handle(), policy, &param);',
            '#ifndef __SWITCH__\n      ::pthread_setschedparam(this->native_handle(), policy, &param);\n'
            '#else\n      (void)policy; (void)param; // Probe retains default Horizon priority.\n#endif')
    replace(source / 'src/dxgi/dxgi_main.cpp', '  Logger Logger::s_instance("dxgi.log");',
            '  // Unified static probe uses the D3D11 logger singleton.')
    # No game renderer defaults are used; this probe has a distinct cache/config.
    hashes = {name: sha(source / name) for name in patched}
    (work / 'adapted-source.json').write_text(json.dumps(hashes, indent=2)+'\n')
    return source, hashes


def list_assignment(path, name):
    text = path.read_text()
    pattern = rf'\b{re.escape(name)}\s*=\s*(?:files\()?\[(.*?)\]'
    match = re.search(pattern, text, re.S)
    if not match:
        raise RuntimeError(f'Missing source list {name} in {path}')
    return [path.parent / p for p in re.findall(r"'([^']+)'", match[1])]


def configure(work, source, target, jobs):
    recipe = work / f'recipe-{target}'
    recipe.mkdir(exist_ok=True)
    generated = work / ('generated' if target == 'horizon' else 'generated-host')
    generated.mkdir(exist_ok=True)
    shader_tool = Path('/home/blekjek/f1-dxvk-small-chunks/shader-tools/usr/bin/glslangValidator')
    for component, variable in (('dxvk', 'dxvk_shaders'), ('d3d11', 'd3d11_shaders')):
        for shader in list_assignment(source / 'src' / component / 'meson.build', variable):
            output = generated / (shader.stem + '.h')
            if not output.exists():
                subprocess.run([str(shader_tool), '--quiet', '--target-env', 'vulkan1.3',
                                '--vn', shader.stem, str(shader), '-o', str(output)], check=True)
    write_changed(generated / 'version.h', '#define DXVK_VERSION "3.1.1-sdbatch2-native-probe-v1"\n')
    write_changed(generated / 'buildenv.h',
        f'#define DXVK_TARGET "{target}"\n#define DXVK_COMPILER "GCC"\n'
        '#define DXVK_COMPILER_VERSION "recorded in receipt"\n')
    files = []
    for component, variable in [('util', 'util_src'), ('spirv', 'spirv_src'),
                               ('vulkan', 'vkcommon_src'), ('dxvk', 'dxvk_src'),
                               ('dxgi', 'dxgi_src'), ('d3d11', 'd3d11_src'),
                               ('d3d11', 'd3d10_src')]:
        files += list_assignment(source / 'src' / component / 'meson.build', variable)
    files += [source / 'src/wsi/wsi_edid.cpp', source / 'src/wsi/wsi_platform.cpp',
              ROOT / 'src/native_dxvk/probe_wsi.cpp', ROOT / 'src/native_dxvk/probe_backend.cpp']
    dxbc = source / 'subprojects/dxbc-spirv'
    for variable in ('sm5_files', 'spv_files', 'dxbc_spv_files'):
        files += list_assignment(dxbc / 'meson.build', variable)
    display = source / 'subprojects/libdisplay-info'
    if not (generated / 'pnp-id-table.c').exists():
        subprocess.run(['python3', str(display / 'tool/gen-search-table.py'), str(display / 'pnp.ids'),
                        str(generated / 'pnp-id-table.c'), 'pnp_id_table'], check=True)
    match = re.search(r"di_lib\s*=\s*static_library\(\s*'display-info',\s*\[(.*?)\]", (display/'meson.build').read_text(), re.S)
    display_files = [display / p for p in re.findall(r"'([^']+\.c)'", match[1])]
    files += display_files + [generated / 'pnp-id-table.c']
    includes = [source / 'include', source / 'include/native', source / 'include/native/windows',
                source / 'include/native/directx', source / 'include/vulkan/include',
                source / 'include/spirv/include', dxbc, display / 'include', display, generated,
                ROOT / 'src/native_dxvk', source / 'src/wsi']
    def quoted(paths):
        return '\n'.join('  "' + str(p) + '"' for p in paths)
    cmake = f'''cmake_minimum_required(VERSION 3.18)
project(sd_native_dxvk_probe LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
add_library(sd_native_dxvk STATIC
{quoted(files)}
)
target_include_directories(sd_native_dxvk PUBLIC
{quoted(includes)}
)
target_compile_definitions(sd_native_dxvk PRIVATE DXBC_SPV_ENABLE_SM5 DXBC_SPV_ENABLE_SPIRV _GNU_SOURCE _POSIX_C_SOURCE=200809L static_array=static)
target_compile_options(sd_native_dxvk PRIVATE -Wno-unknown-pragmas -Wno-missing-field-initializers)
'''
    if target == 'horizon':
        cmake += '''target_compile_definitions(sd_native_dxvk PUBLIC __unix__ SD_NATIVE_STATIC_VULKAN VK_USE_PLATFORM_VI_NN)
'''
    else:
        cmake += '''target_compile_definitions(sd_native_dxvk PUBLIC VK_USE_PLATFORM_XCB_KHR)
target_include_directories(sd_native_dxvk PUBLIC "''' + str(work / 'host-deps/usr/include') + '''")
target_link_libraries(sd_native_dxvk PUBLIC /usr/lib/x86_64-linux-gnu/libxcb.so.1 dl pthread)
add_executable(sd_native_dxvk_host_probe "''' + str(ROOT / 'src/native_dxvk/probe_host_main.cpp') + '''")
target_link_libraries(sd_native_dxvk_host_probe PRIVATE sd_native_dxvk)
'''
    write_changed(recipe / 'CMakeLists.txt', cmake)
    build = work / f'build-{target}'
    command = ['cmake', '-S', recipe, '-B', build, '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release',
               '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
    if target == 'horizon':
        toolchain = recipe / 'horizon.cmake'
        toolchain.write_text('''set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_C_COMPILER /opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc)
set(CMAKE_CXX_COMPILER /opt/devkitpro/devkitA64/bin/aarch64-none-elf-g++)
set(CMAKE_AR /opt/devkitpro/devkitA64/bin/aarch64-none-elf-ar)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
set(CMAKE_C_FLAGS_INIT "-march=armv8-a+crc+crypto -mtune=cortex-a57 -mtp=soft -ffixed-x18 -ftls-model=local-exec -ffunction-sections -fdata-sections -D__SWITCH__ -DNX -isystem /opt/devkitpro/libnx/include -isystem /opt/devkitpro/portlibs/switch/include")
set(CMAKE_CXX_FLAGS_INIT "${CMAKE_C_FLAGS_INIT}")
''')
        command += ['-DCMAKE_TOOLCHAIN_FILE=' + str(toolchain)]
    run(command, work / f'configure-{target}.log')
    run(['ninja', '-C', build, '-j' + str(jobs)], work / f'build-{target}.log')
    return build, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1'))
    parser.add_argument('--source', type=Path, default=Path('/home/blekjek/sleepingdogs-dxvk-native-v15/source'))
    parser.add_argument('--target', choices=('host', 'horizon'), required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--reuse-prepared', action='store_true', help='Verify and reuse the adapted source without rewriting it')
    args = parser.parse_args()
    if os.name != 'posix':
        parser.error('Run under WSL/Linux')
    args.work.mkdir(parents=True, exist_ok=True)
    if args.reuse_prepared:
        source = args.work / 'source'
        patches = json.loads((args.work / 'adapted-source.json').read_text())
        for name, digest in patches.items():
            if sha(source / name) != digest:
                raise RuntimeError(f'Adapted input changed: {name}')
        pinned = pinned_manifest(args.source)
        for name, digest in pinned.items():
            if name not in patches and sha(source / name) != digest:
                raise RuntimeError(f'Unexpected change in isolated DXVK source: {name}')
    else:
        source, patches = prepare(args.work, args.source)
    build, files = configure(args.work, source, args.target, args.jobs)
    library = build / 'libsd_native_dxvk.a'
    output = ROOT / 'local/native-dxvk-probe-v1'
    output.mkdir(parents=True, exist_ok=True)
    receipt = dict(status='BUILT', target=args.target, library=str(library), sha256=sha(library),
                   bytes=library.stat().st_size, source_base='DXVK 3.1.1-sdbatch2',
                   adapted_files=patches, compiled_sources=len(files),
                   compile_commands_sha256=sha(build / 'compile_commands.json'),
                   fex_bypassed_for_renderer=True, game_integration=False,
                   hardware_tested=False, fps_gain_measured=False,
                   baseline_receipt_sha256=sha(args.source.parent / 'prepared.json'),
                   input_manifest_sha256=sha(INPUTS),
                   probe_sources={str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT/'src/native_dxvk').glob('*'))},
                   builder_sha256=sha(__file__))
    compiler = '/opt/devkitpro/devkitA64/bin/aarch64-none-elf-g++' if args.target == 'horizon' else 'g++'
    receipt['compiler'] = subprocess.check_output([compiler, '--version'], text=True).splitlines()[0]
    reader = '/opt/devkitpro/devkitA64/bin/aarch64-none-elf-readelf' if args.target == 'horizon' else 'readelf'
    audit = subprocess.check_output([reader, '-h', str(library)], text=True)
    machines = re.findall(r'Machine:\s*(.*)', audit)
    expected = 'AArch64' if args.target == 'horizon' else 'Advanced Micro Devices X86-64'
    if len(machines) != len(files) or set(machines) != {expected}:
        raise RuntimeError(f'Archive architecture mismatch: {len(machines)} members, {set(machines)}')
    receipt['elf_members'] = len(machines)
    receipt['elf_machine'] = expected
    undefined = subprocess.check_output([reader, '-Ws', str(library)], text=True)
    receipt['static_vulkan_import'] = bool(re.search(r'UND\s+vkGetInstanceProcAddr\b', undefined))
    if args.target == 'horizon' and not receipt['static_vulkan_import']:
        raise RuntimeError('Horizon static Vulkan loader import missing')
    guest_cc = Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/i686-w64-mingw32-gcc')
    host_cc = Path('/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc') if args.target == 'horizon' else Path('/usr/bin/gcc')
    for label, cc, width in [('guest32', guest_cc, 4), (args.target, host_cc, 8)]:
        obj = build / (label+'-abi.o')
        subprocess.run([str(cc), '-std=c11', '-c', str(ROOT/'tests/native_dxvk_abi.c'),
                        '-I'+str(ROOT/'src/native_dxvk'), '-DSD_NDX_EXPECT_POINTER_BYTES='+str(width),
                        '-o', str(obj)], check=True)
        receipt[label+'_wire_layout'] = dict(status='PASS', pointer_bytes=width, packet_bytes=64, object_sha256=sha(obj))
    (output / f'build-{args.target}.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == '__main__':
    main()
