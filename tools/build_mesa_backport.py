"""Build four pinned Horizon Mesa fixes without writing to the shared SDK.

The original NAK/NIR, WSI, allocator and utility objects are retained byte for
byte. All NVK translation units are rebuilt because internal layouts change.
"""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/home/blekjek/pes13-build')
WORK = Path('/home/blekjek/sleepingdogs-mesa-v13')
COMMIT = 'b297e230ef88c6c88df2561becf864f979f494a6'
LIB_SHA = 'ca9c82e03b04fb385004d6f7d47bd8357e107f7a35481f08e06f7b870f941315'
VERSION = '26.2.2-sdv13-zcull-ubo'
PATCHES = {
    'ed2b4dd00d06a60b233a6fb3b1397689eb4e80a3': '33b7529d639cc6baff051d70bca458e483ea44d492d7f024fecd45ba9550d842',
    '1b03eff0ad5c882b392abbf2b9ac7142295d32bc': 'cea4adf4e600b3d82d66c345c99a60271b9cfac5e72424724b4802fbc069473f',
    'f68a41350dbc0b380dcb1462898d8bed48dfdb5e': 'a39d061f43f0e3d467b5c5a19665f6e2e645bb43d2c5ba533ede6a591f61ff25',
    'a72f9551e79e7881ba67940f41df2b115d360600': '556597bde1b44a9d30c0394d5331f33a02a88ddb72fb55ae02c153678154d26e',
}
INTEGRATION = 'gpu-private-type-v1-zcull-once-v1'
BUILD_ID = hashlib.sha1(json.dumps([COMMIT, PATCHES, VERSION, INTEGRATION], sort_keys=True).encode()).hexdigest()
AR = '/opt/devkitpro/devkitA64/bin/aarch64-none-elf-ar'


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def manifest(source):
    return {p.relative_to(source).as_posix(): sha(p)
            for p in sorted(source.rglob('*')) if p.is_file()}


def verify_changed(source, prepared):
    # Initial preparation records the entire pinned tree. On reuse, unrelated
    # Intel/AMD files are not build inputs and need not be reread. The compiler
    # preflight below checks every actual owned source/header dependency.
    for name, digest in prepared['changed'].items():
        assert sha(source/name) == digest, 'Candidate source changed: '+name


def apply_integration(source):
    """Expose private GPU backing; never bypass imported-memory exclusions."""
    path = source/'src/nouveau/vulkan/nvk_physical_device.c'
    text = path.read_text()
    needle = '      pdev->mem_heaps[sysmem_heap_idx].flags |= VK_MEMORY_HEAP_DEVICE_LOCAL_BIT;\n'
    assert text.count(needle) == 1
    insert = '''
#ifdef HAVE_SWITCH_PLATFORM
      /* A GPU-only type keeps optimal images in driver-owned backing. Wine
       * imports HOST_VISIBLE allocations into its 32-bit address window;
       * those imports cannot preserve NVK's private ZCULL hierarchy. This
       * type is never advertised as mappable or usable for host imports.
       * The existing cached/coherent types remain available for staging.
       */
      pdev->mem_types[pdev->mem_type_count++] = (VkMemoryType) {
         .propertyFlags = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
         .heapIndex = sysmem_heap_idx,
      };
      _debug_printf("[SD-NVK-V13] private_gpu_type=0 host_cached_type=1 "
                    "host_coherent_type=2 heap=%u; ZCULL import guards retained\\n",
                    sysmem_heap_idx);
#endif
'''
    text = text.replace(needle, needle+insert)
    text = text.replace('#include "util/os_misc.h"', '#include "util/os_misc.h"\n#include "util/u_debug.h"')
    path.write_text(text)
    path = source/'src/nouveau/vulkan/nvk_cmd_draw.c'
    text = path.read_text()
    needle = '   render->zcull_enabled = use_zcull;\n'
    assert text.count(needle) == 1
    insert = '''
#ifdef HAVE_SWITCH_PLATFORM
   if (use_zcull)
      nvk_sd_v13_report_zcull(zcull_plane != NULL);
#endif
'''
    text = text.replace(needle, needle+insert)
    helper = '''
#ifdef HAVE_SWITCH_PLATFORM
/* At most one marker for each actually recorded ZCULL mode, process-wide. */
static void
nvk_sd_v13_report_zcull(bool persistent)
{
   static int persistent_seen;
   static int transient_seen;
   int *seen = persistent ? &persistent_seen : &transient_seen;
   if (p_atomic_read_relaxed(seen) == 0 && p_atomic_cmpxchg(seen, 0, 1) == 0)
      _debug_printf("[SD-NVK-V13] ZCULL active mode=%s\\n",
                    persistent ? "persistent" : "transient");
}
#endif

'''
    needle = 'static inline uint16_t\nnvk_cmd_buffer_3d_cls'
    assert text.count(needle) == 1
    text = text.replace(needle,helper+needle)
    text = text.replace('#include "util/compiler.h"', '#include "util/compiler.h"\n#include "util/u_atomic.h"\n#include "util/u_debug.h"')
    path.write_text(text)


def archive_members(path):
    """Read GNU ar members without extracting or assuming unique basenames."""
    result = []
    strings = b''
    with Path(path).open('rb') as f:
        assert f.read(8) == b'!<arch>\n', 'Expected a real, non-thin archive'
        while header := f.read(60):
            assert len(header) == 60 and header[58:] == b'`\n'
            size = int(header[48:58])
            raw_name = header[:16].decode().strip()
            data = f.read(size)
            assert len(data) == size
            if size & 1:
                assert f.read(1) == b'\n'
            if raw_name == '//':
                strings = data
                continue
            if raw_name in ('/', '/SYM64/'):
                continue
            if re.fullmatch(r'/\d+', raw_name):
                start = int(raw_name[1:])
                name = strings[start:strings.index(b'/\n', start)].decode()
            else:
                name = raw_name.removesuffix('/')
            result.append(dict(name=name, bytes=size, sha256=hashlib.sha256(data).hexdigest()))
    return result


def prepare(work=WORK, refresh_builder_receipt=False):
    work = work.resolve()
    assert work != BASE and BASE not in work.parents
    source = work/'source'
    shared_source = BASE/'mesa-switch'
    cross = BASE/'mesa-vulkan/cross'
    library = BASE/'mesa-vulkan/install/opt/devkitpro/portlibs/switch/lib/libvulkan.a'
    assert sha(library) == LIB_SHA, 'Shared Mesa archive changed'
    patches = ROOT/'vendor/mesa/v13'
    for commit, digest in PATCHES.items():
        assert sha(patches/(commit+'.patch')) == digest, commit
    inputs = dict(commit=COMMIT, baseline_library_sha256=LIB_SHA,
                  patches=PATCHES, version=VERSION, build_id=BUILD_ID, integration=INTEGRATION,
                  builder_sha256=sha(Path(__file__)),
                  compile_commands_sha256=sha(cross/'compile_commands.json'))
    work.mkdir(parents=True, exist_ok=True)
    stamp = work/'prepared.json'
    if not stamp.exists():
        assert not source.exists(), 'Use a fresh work directory after interrupted preparation'
        source.mkdir()
        archive = work/'baseline-source.tar'
        with archive.open('wb') as out:
            subprocess.run(['git', '-C', str(shared_source), 'archive', COMMIT], stdout=out, check=True)
        with tarfile.open(archive) as tar:
            tar.extractall(source, filter='data')
        baseline = manifest(source)
        for commit in PATCHES:
            patch = patches/(commit+'.patch')
            subprocess.run(['git', 'apply', '--check', str(patch)], cwd=source, check=True)
            subprocess.run(['git', 'apply', '--whitespace=nowarn', str(patch)], cwd=source, check=True)
        apply_integration(source)
        candidate = manifest(source)
        changed = {n:h for n,h in candidate.items() if baseline.get(n) != h}
        expected = set().union(*(set(p['files']) for p in json.loads((patches/'patches.json').read_text())))
        expected.add('src/nouveau/vulkan/nvk_physical_device.c')
        assert set(changed) == expected and len(changed) == 17
        assert set(baseline) <= set(candidate)
        # No compiler or allocator ABI changes are part of this backport.
        assert not any(n.startswith(('src/compiler/', 'src/nouveau/compiler/', 'src/util/')) for n in changed)
        assert candidate['src/nouveau/horizon/nouveau_horizon_memory.c'] == baseline['src/nouveau/horizon/nouveau_horizon_memory.c']
        write_json(stamp, dict(inputs=inputs, baseline_files=baseline,
                              source_files=candidate, changed=changed))
    prepared = json.loads(stamp.read_text())
    if refresh_builder_receipt and prepared['inputs'] != inputs:
        previous = dict(prepared['inputs'])
        previous['builder_sha256'] = inputs['builder_sha256']
        assert previous == inputs, 'Only a builder implementation change may be refreshed'
        verify_changed(source, prepared)
        # Reconstruct every changed source from the pinned Git commit and
        # patches, including the local integration, before refreshing a build-
        # tooling-only receipt. Never trust a same-size or same-name source.
        with tempfile.TemporaryDirectory(prefix='verify-source-', dir=work) as tmp:
            proof = Path(tmp)
            for name in prepared['changed']:
                if name not in prepared['baseline_files']:
                    continue
                data = subprocess.check_output(['git', '-C', str(shared_source), 'show', COMMIT+':'+name])
                assert hashlib.sha256(data).hexdigest() == prepared['baseline_files'][name]
                path = proof/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            for commit in PATCHES:
                subprocess.run(['git', 'apply', '--check', str(patches/(commit+'.patch'))], cwd=proof, check=True)
                subprocess.run(['git', 'apply', '--whitespace=nowarn', str(patches/(commit+'.patch'))], cwd=proof, check=True)
            apply_integration(proof)
            assert manifest(proof) == prepared['changed'], 'Reconstructed candidate differs'
        prepared['inputs'] = inputs
        write_json(stamp, prepared)
    assert prepared['inputs'] == inputs
    verify_changed(source, prepared)
    return prepared


def compile_recipes(work):
    cross = BASE/'mesa-vulkan/cross'
    shared = BASE/'mesa-switch'
    commands = json.loads((cross/'compile_commands.json').read_text())
    result = []
    for item in commands:
        args = shlex.split(item['command'])
        if '-o' not in args:
            continue
        output = args[args.index('-o')+1]
        nvk = output.startswith('src/nouveau/vulkan/libnvk.a.p/')
        horizon = output.endswith(('/nouveau_horizon_channel.c.o', '/nouveau_horizon_device.c.o'))
        if not (nvk or horizon):
            continue
        obj = work/'objects'/Path(output).name
        dep = obj.with_suffix(obj.suffix+'.d')

        def redirect(raw):
            p = (cross/raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
            return str(work/'source'/p.relative_to(shared)) if p.is_relative_to(shared) else str(p)

        rewritten = []
        i = 0
        while i < len(args):
            a = args[i]
            if a in ('-o', '-MF', '-MQ'):
                rewritten.extend([a, str(dep if a == '-MF' else obj)])
                i += 2
                continue
            if a == '-c':
                rewritten.extend([a, redirect(args[i+1])])
                i += 2
                continue
            if a.startswith('-I') and len(a) > 2:
                a = '-I'+redirect(a[2:])
            if nvk and a.startswith('-DNVK_BUILD_ID_OVERRIDE='):
                a = '-DNVK_BUILD_ID_OVERRIDE="'+BUILD_ID+'"'
            if nvk and a.startswith('-DPACKAGE_VERSION='):
                a = '-DPACKAGE_VERSION="'+VERSION+'"'
            rewritten.append(a)
            i += 1
        assert not any(str(shared) in a or '../../mesa-switch' in a for a in rewritten)
        result.append(dict(name=obj.name, command=rewritten, output=str(obj), dependency=str(dep)))
    assert len(result) == 114, len(result)
    assert len({r['name'] for r in result}) == len(result)
    return result


def dependency_paths(dep):
    text = dep.read_text().replace('\\\n', ' ')
    return [Path(p).resolve() for p in shlex.split(text.split(':', 1)[1])]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=WORK)
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--prepare-only', action='store_true')
    p.add_argument('--refresh-builder-receipt', action='store_true')
    a = p.parse_args()
    prepared = prepare(a.work, a.refresh_builder_receipt)
    if a.prepare_only:
        print('Prepared', a.work, BUILD_ID, flush=True)
        return
    report = json.loads((ROOT/'reports/mesa-v13-host.json').read_text())
    assert report['status'] == 'PASS' and report['changed_sources'] == prepared['changed']
    for n,h in report['test_sources'].items():
        assert sha(ROOT/n) == h, n
    recipes = compile_recipes(a.work)
    (a.work/'objects').mkdir(exist_ok=True)
    cross = BASE/'mesa-vulkan/cross'
    oldlib = BASE/'mesa-vulkan/install/opt/devkitpro/portlibs/switch/lib/libvulkan.a'
    before = archive_members(oldlib)
    counts = Counter(m['name'] for m in before)
    retained_common = {}
    for recipe in recipes:
        name = recipe['name']
        recipe['retain_common'] = counts[name] != 1
        if recipe['retain_common']:
            assert re.fullmatch(r'meson-generated_\.\._\.\._headers_nv_push_cl[0-9a-f]+\.c\.o', name) or name == '.._headers_nv_push.c.o', name
            copies = [m for m in before if m['name'] == name]
            assert len(copies) == 5 and len({m['sha256'] for m in copies}) == 1, name
            retained_common[name] = dict(copies=len(copies), sha256=copies[0]['sha256'])
    assert len(retained_common) == 66
    write_json(a.work/'compile-recipes.json', recipes)

    # Discover and hash every header/input before compiling. This includes
    # generated headers and the SDK; there is no mixed old/new NVK struct ABI.
    dependencies = set()
    changed_paths = {(a.work/'source'/name).resolve() for name in prepared['changed']}
    for recipe in recipes:
        args = recipe['command']
        scan = []
        i = 0
        while i < len(args):
            if args[i] in ('-o', '-MF', '-MQ'):
                i += 2
            elif args[i] in ('-MD', '-c'):
                i += 1
            else:
                scan.append(args[i]); i += 1
        scan += ['-M', '-MF', recipe['dependency'], '-MT', '__sd_v13__']
        subprocess.run(scan, cwd=cross, check=True, stdout=subprocess.DEVNULL)
        actual_dependencies = set(dependency_paths(Path(recipe['dependency'])))
        if recipe['retain_common']:
            assert not (actual_dependencies & changed_paths), \
                'A retained helper depends on a changed NVK/Horizon header: '+recipe['name']
        dependencies.update(actual_dependencies)
    dependency_hashes = {str(path):sha(path) for path in sorted(dependencies)}
    owned_source = (a.work/'source').resolve()
    owned_dependency_count = 0
    for path in dependencies:
        if path.is_relative_to(owned_source):
            name = path.relative_to(owned_source).as_posix()
            assert prepared['source_files'].get(name) == dependency_hashes[str(path)], \
                'Unpinned or changed source/header dependency: '+name
            owned_dependency_count += 1
    assert owned_dependency_count > 100, 'Missing source/header dependency coverage'
    write_json(a.work/'dependencies.json', dependency_hashes)
    recipes = [r for r in recipes if not r['retain_common']]
    assert len(recipes) == 48
    print('Checked', len(dependencies), 'source/header dependencies; compiling', len(recipes),
          'objects; preserving 66 common header helpers after dependency audit', flush=True)

    def compile_one(recipe):
        log = Path(recipe['output']+'.log')
        with log.open('w') as output:
            subprocess.run(recipe['command'], cwd=cross, stdout=output,
                           stderr=subprocess.STDOUT, check=True)
        actual = set(dependency_paths(Path(recipe['dependency'])))
        assert actual <= dependencies, 'Compiler discovered an unpinned dependency'
        return recipe['name']

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        for index, future in enumerate(concurrent.futures.as_completed([pool.submit(compile_one,r) for r in recipes]), 1):
            name = future.result()
            if index % 8 == 0 or index == len(recipes):
                print('Compiled', index, '/', len(recipes), name, flush=True)
    for name,digest in dependency_hashes.items():
        assert sha(name) == digest, 'Dependency changed during compile: '+name
    verify_changed(a.work/'source', prepared)
    assert sha(oldlib) == LIB_SHA

    out = a.work/'library/libvulkan.a'
    out.parent.mkdir(exist_ok=True)
    shutil.copy2(oldlib, out)
    subprocess.run([AR, 'rD', str(out), *[r['output'] for r in recipes]], check=True)
    subprocess.run([AR, 'sD', str(out)], check=True)
    after = archive_members(out)
    names = {r['name'] for r in recipes}
    assert Counter(m['name'] for m in before) == Counter(m['name'] for m in after)
    preserved = lambda rows: [(m['name'],m['bytes'],m['sha256']) for m in rows if m['name'] not in names]
    assert preserved(before) == preserved(after), 'Unrelated archive members changed'
    replaced = {m['name']:m['sha256'] for m in after if m['name'] in names}
    for recipe in recipes:
        assert replaced[recipe['name']] == sha(recipe['output'])
    assert VERSION.encode() in out.read_bytes(), 'Missing driver marker'
    write_json(a.work/'build.json', dict(status='PASS', version=VERSION, build_id=BUILD_ID,
        library=str(out), library_sha256=sha(out), baseline_library_sha256=LIB_SHA,
        baseline_commit=COMMIT, patches=PATCHES, changed_sources=prepared['changed'],
        source_manifest=str(a.work/'prepared.json'), source_manifest_sha256=sha(a.work/'prepared.json'),
        dependencies_sha256=sha(a.work/'dependencies.json'), dependency_count=len(dependencies),
        owned_source_dependency_count=owned_dependency_count,
        all_compiled_dependencies_verified=True, full_tree_revalidated=False,
        replaced_members=replaced, preserved_member_count=len(before)-len(replaced),
        retained_common_helpers=retained_common,
        explicit_link_objects={r['name']:dict(path=r['output'],sha256=sha(r['output'])) for r in recipes if r['name'].startswith('nouveau_horizon_')},
        preserved_members_digest=hashlib.sha256(json.dumps(preserved(before)).encode()).hexdigest(),
        memory_object_unchanged=True, nak_nir_unchanged=True,
        hardware_tested=False, fps_gain_measured=False,
        builder_sha256=sha(Path(__file__)), tests_sha256=sha(ROOT/'reports/mesa-v13-host.json')))
    print('PASS candidate library:', out, sha(out), flush=True)


if __name__ == '__main__':
    main()
