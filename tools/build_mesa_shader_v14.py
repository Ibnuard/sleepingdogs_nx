"""Build an isolated GM20B shader-compiler overlay on the tested v13 driver."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
from collections import Counter

from port_common import ROOT, sha, write_json
from build_mesa_backport import archive_members, dependency_paths, AR, BASE

PREVIOUS = Path('/home/blekjek/sleepingdogs-mesa-v13')
WORK = Path('/home/blekjek/sleepingdogs-mesa-v14')
OLD_LIB = 'f596961d96bcea37bdb36423cdfde99261838ba1e06b16d1f36c66ddbc71fd6c'
OLD_NAK = 'f56fc46711c90330a9d68ff78cf00fd31a2525f922b6a90b77366d044542381f'
VERSION = '26.2.2-sdv14-shader'
POLICY = 'sm53-texture-global-read-latency200-select8-sm50-fadd-sat-v1'
BUILD_ID = hashlib.sha1((OLD_LIB + VERSION + POLICY).encode()).hexdigest()
RUSTC = BASE/'toolchains/rust/rustup/toolchains/1.93.1-x86_64-unknown-linux-gnu/bin/rustc'
FILES = ('src/nouveau/compiler/nak/opt_instr_sched_common.rs',
         'src/nouveau/compiler/nak/sm50.rs',
         'src/nouveau/compiler/nak_nir.c',
         'src/nouveau/vulkan/nvk_physical_device.c',
         'src/nouveau/vulkan/nvk_cmd_draw.c',
         'src/nouveau/vulkan/nvk_shader.c')
REFERENCE_COMMIT = '4e3ffc24fe80285189f2cea601606c529d5f1b97'
REFERENCE_SHA = 'b19a2010d1bb070b99f7c87b6da7ab61a267f40e8c4bee2c00d73b7189271d24'


def replace_once(text, before, after):
    assert text.count(before) == 1, before[:100]
    return text.replace(before, after)


def apply(source):
    p = source/FILES[0]
    s = p.read_text()
    # This is a priority estimate, NOT the hardware dependency/barrier delay.
    # Keep shared, attribute, interpolation, stores and barriers unchanged.
    s = replace_once(s, '    match op {\n        // Multi-function unit', '''    if sm.sm() == 53 {
        match op {
            Op::Tex(_) | Op::Tld(_) | Op::Tld4(_) | Op::Tmml(_)
            | Op::Txd(_) | Op::Txq(_) => return 200,
            Op::Ld(ld) if matches!(ld.access.space, MemSpace::Global(_)) => return 200,
            _ => {},
        }
    }

    match op {
        // Multi-function unit''')
    p.write_text(s)
    p = source/FILES[1]; s = p.read_text()
    start, end = s.index('impl SM50Op for OpFAdd'), s.index('impl SM50Op for OpFFma')
    part = s[start:end]
    part = replace_once(part,'&& self.rnd_mode != FRndMode::NearestEven',
                        '&& (self.rnd_mode != FRndMode::NearestEven || self.saturate)')
    part = replace_once(part,'// Hardware cannot encode long-immediate + rounding mode',
                        '// FADD32I cannot encode non-default rounding or saturation.')
    part = replace_once(part,'assert!(self.rnd_mode == FRndMode::NearestEven);',
                        'assert!(self.rnd_mode == FRndMode::NearestEven && !self.saturate);')
    p.write_text(s[:start]+part+s[end:])
    p = source/FILES[2]; s = p.read_text()
    s = replace_once(s,'''nir_opt_peephole_select_options peephole_select_options = {
         .limit = 0,''','''nir_opt_peephole_select_options peephole_select_options = {
         /* Flatten only small, safe branches on the Switch's SM53. The NIR
          * pass retains side-effecting / unsafe speculation and large ifs. */
         .limit = nak->sm == 53 ? 8 : 0,''')
    p.write_text(s)
    # Route a bounded number of diagnostics to the existing, mutex-protected
    # FEXTendo trace, since Mesa's stderr isn't in fex-runtime.log.
    declaration = '\nextern void wine_nx_runtime_trace(const char *msg) __attribute__((weak));\n'
    p = source/FILES[3]; s = p.read_text()
    s = replace_once(s, '#include "util/u_debug.h"', '#include "util/u_debug.h"'+declaration)
    old = '''      _debug_printf("[SD-NVK-V13] private_gpu_type=0 host_cached_type=1 "
                    "host_coherent_type=2 heap=%u; ZCULL import guards retained\\n",
                    sysmem_heap_idx);'''
    new = '''      if (wine_nx_runtime_trace)
         wine_nx_runtime_trace("[SD-NVK-V14] shader compiler SM53: texture/global-load "
                               "priority=200 select_limit=8 FADD.SAT=correct; "
                               "v13 private GPU memory and ZCULL guards retained");'''
    s = replace_once(s, old, new); p.write_text(s)
    p = source/FILES[4]; s = p.read_text()
    s = replace_once(s, '#include "util/u_debug.h"', '#include "util/u_debug.h"'+declaration)
    s = replace_once(s,'''      _debug_printf("[SD-NVK-V13] ZCULL active mode=%s\\n",
                    persistent ? "persistent" : "transient");''',
                    '''      if (wine_nx_runtime_trace)
         wine_nx_runtime_trace(persistent ? "[SD-NVK-V14] ZCULL active=persistent" :
                                           "[SD-NVK-V14] ZCULL active=transient");''')
    p.write_text(s)
    p = source/FILES[5]; s = p.read_text()
    s = replace_once(s, '#include "nak.h"', '#include "nak.h"\n#include "util/u_atomic.h"\n#include <stdio.h>'+declaration)
    s = replace_once(s,'   shader->info = shader->nak->info;', '''   shader->info = shader->nak->info;
#ifdef HAVE_SWITCH_PLATFORM
   /* At most 16 records, only on shader compilation, never on a draw. */
   static int sd_shader_count;
   unsigned sd_n = p_atomic_inc_return(&sd_shader_count);
   if (wine_nx_runtime_trace && (sd_n == 1 || (sd_n <= 960 && sd_n % 64 == 0))) {
      char message[192];
      snprintf(message, sizeof(message),
               "[SD-NVK-V14] shader=%u stage=%u gprs=%u slm_bytes=%u code_bytes=%u",
               sd_n, (unsigned)shader->info.stage, (unsigned)shader->info.num_gprs,
               shader->info.slm_size, shader->nak->code_size);
      wine_nx_runtime_trace(message);
   }
#endif''')
    p.write_text(s)


def prepare(work=WORK):
    assert work.resolve() not in (BASE.resolve(), PREVIOUS.resolve())
    assert sha(PREVIOUS/'library/libvulkan.a') == OLD_LIB
    prepared = json.loads((PREVIOUS/'prepared.json').read_text())
    reference = ROOT/'local/research-v14/mesa-switch-nfsmw.patch'
    assert sha(reference) == REFERENCE_SHA
    work.mkdir(parents=True,exist_ok=True)
    source=work/'source'
    # A sparse, fully pinned source overlay: the Rust crate's modules plus
    # the changed C translation units. Unchanged includes are read-only v13.
    names = set(FILES) | {p.relative_to(PREVIOUS/'source').as_posix()
        for p in (PREVIOUS/'source/src/nouveau/compiler/nak').glob('*.rs')}
    baseline = {n:prepared['source_files'][n] for n in sorted(names)}
    for n,h in baseline.items(): assert sha(PREVIOUS/'source'/n)==h,n
    stamp=work/'prepared.json'
    if not stamp.exists():
        assert not source.exists(), 'Interrupted preparation: use another owned directory'
        for n in names:
            p=source/n;p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PREVIOUS/'source'/n,p)
        apply(source)
        candidate={n:sha(source/n) for n in sorted(names)}
        changed={n:h for n,h in candidate.items() if baseline[n]!=h}
        assert set(changed)==set(FILES)
        write_json(stamp,dict(baseline_files=baseline,source_files=candidate,changed=changed,
            baseline_library_sha256=OLD_LIB,version=VERSION,build_id=BUILD_ID,policy=POLICY,
            reference_commit=REFERENCE_COMMIT,reference_sha256=REFERENCE_SHA))
    saved=json.loads(stamp.read_text())
    assert saved['baseline_files']==baseline and saved['build_id']==BUILD_ID
    for n,h in saved['source_files'].items(): assert sha(source/n)==h,n
    return saved


def compile_c(work, prepared):
    cross=BASE/'mesa-vulkan/cross'
    v13=json.loads((PREVIOUS/'prepared.json').read_text())
    commands=json.loads((cross/'compile_commands.json').read_text())
    recipes=[]; deps={}
    for item in commands:
        raw=shlex.split(item['command'])
        if '-c' not in raw: continue
        path=(cross/raw[raw.index('-c')+1]).resolve()
        if not path.is_relative_to(BASE/'mesa-switch'): continue
        rel=path.relative_to(BASE/'mesa-switch').as_posix()
        if rel not in FILES or not rel.endswith('.c'): continue
        output=work/'objects'/Path(raw[raw.index('-o')+1]).name
        output.parent.mkdir(exist_ok=True)
        dep=output.with_suffix('.d')
        def redirect(x):
            p=(cross/x).resolve()
            return str(PREVIOUS/'source'/p.relative_to(BASE/'mesa-switch')) if p.is_relative_to(BASE/'mesa-switch') else str(p)
        args=[];i=0
        while i<len(raw):
            x=raw[i]
            if x in ('-o','-MF','-MQ','-c'):
                args += [x,str(work/'source'/rel if x=='-c' else dep if x=='-MF' else output)]
                i+=2;continue
            if x.startswith('-I'): x='-I'+redirect(x[2:])
            if x.startswith('-DNVK_BUILD_ID_OVERRIDE='): x='-DNVK_BUILD_ID_OVERRIDE="'+BUILD_ID+'"'
            if x.startswith('-DPACKAGE_VERSION='): x='-DPACKAGE_VERSION="'+VERSION+'"'
            args.append(x);i+=1
        with output.with_suffix('.log').open('w') as log:
            subprocess.run(args,cwd=cross,stdout=log,stderr=subprocess.STDOUT,check=True)
        actual=dependency_paths(dep)
        for p in actual:
            h=sha(p);deps[str(p)]=h
            if p.is_relative_to(work/'source'):
                assert h==prepared['source_files'][p.relative_to(work/'source').as_posix()]
            elif p.is_relative_to(PREVIOUS/'source'):
                assert h==v13['source_files'][p.relative_to(PREVIOUS/'source').as_posix()]
        recipes.append(dict(name=output.name,source=rel,path=str(output),sha256=sha(output),command=args))
        print('Compiled',rel,flush=True)
    assert len(recipes)==4
    write_json(work/'c-dependencies.json',deps)
    write_json(work/'c-recipes.json',recipes)
    return recipes


def compile_rust(work, prepared):
    cross=BASE/'mesa-vulkan/cross'
    old=BASE/'mesa-vulkan/install/opt/devkitpro/portlibs/switch/lib/libnak_rs.a'
    assert sha(old)==OLD_NAK
    cmd=subprocess.check_output(['ninja','-C',str(cross),'-t','commands','src/nouveau/compiler/libnak_rs.a'],text=True).splitlines()[-1]
    args=shlex.split(cmd)
    args[0]=str(RUSTC)
    args[1:1]=['--target=aarch64-unknown-linux-gnu']
    out=work/'library/libnak_rs.a';out.parent.mkdir(exist_ok=True)
    for i,x in enumerate(args):
        if x.startswith('dep-info='): args[i]='dep-info='+str(work/'nak.d')
        if x.startswith('link='): args[i]='link='+str(out)
        if x.endswith('/nak/lib.rs'): args[i]=str(work/'source/src/nouveau/compiler/nak/lib.rs')
    externs={}
    for i,x in enumerate(args):
        if x=='--extern':
            path=(cross/args[i+1].split('=',1)[1]).resolve();externs[str(path)]=sha(path)
    with (work/'rust-build.log').open('w') as log:
        subprocess.run(args,cwd=cross,stdout=log,stderr=subprocess.STDOUT,check=True)
    before=archive_members(old);after=archive_members(out)
    is_nak=lambda m:m['name'].startswith('nak_rs.') and m['name'].endswith('.rcgu.o')
    # All std, ABI, bindings, allocator and other Rust crates must be exact.
    # rustc preserves one thin-archive directory prefix before installation;
    # GNU ar's installed archive strips it. Compare basenames AND bytes. None
    # of these dependency members is replaced in the shipped Vulkan archive.
    unchanged=lambda rows:[(Path(m['name']).name,m['sha256']) for m in rows if not is_nak(m)]
    assert unchanged(before)==unchanged(after),'Rust dependency or allocator ABI changed'
    previous=[m for m in before if is_nak(m)];candidate=[m for m in after if is_nak(m)]
    assert len(previous)>1 and len(candidate)>1
    # The generated allocator-shim object has a unique non-CGU name. Keep it
    # byte identical; the runtime's existing --wrap Rust symbols stay valid.
    shims=[m for m in previous if '.nak_rs.' not in m['name']]
    assert len(shims)==1
    assert shims[0] in after,'Allocation shim changed'
    for n,h in externs.items(): assert sha(Path(n))==h,n
    for n,h in prepared['source_files'].items(): assert sha(work/'source'/n)==h,n
    write_json(work/'rust.json',dict(status='PASS',library_sha256=sha(out),baseline_sha256=OLD_NAK,
        command=args,externs=externs,rustc_sha256=sha(RUSTC),unchanged_dependencies=True,
        allocator_shim=shims[0],old_members=previous,new_members=candidate))
    print('PASS Rust dependencies and allocation shims unchanged',flush=True)
    return candidate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=WORK)
    p.add_argument('--prepare-only',action='store_true')
    a=p.parse_args();work=a.work
    prepared=prepare(work)
    if a.prepare_only:
        print('Prepared v14',BUILD_ID,flush=True);return
    recipes=compile_c(work,prepared)
    nak=compile_rust(work,prepared)
    old=PREVIOUS/'library/libvulkan.a'
    before=archive_members(old)
    target=work/'library/libvulkan.a';shutil.copy2(old,target)
    # Explicit objects also prevent an earlier libEGL archive from selecting
    # the old NAK compiler. Every new compiler object participates in linking.
    explicit={r['name']:dict(path=r['path'],sha256=r['sha256']) for r in recipes if r['source'].endswith('nak_nir.c')}
    old_nak=[m['name'] for m in before if m['name'].startswith('nak_rs.') and m['name'].endswith('.rcgu.o')]
    assert len(old_nak)==len(set(old_nak))
    subprocess.run([AR,'d',str(target),*old_nak],check=True)
    for m in nak:
        obj=work/'objects'/m['name']
        obj.write_bytes(subprocess.check_output([AR,'p',str(work/'library/libnak_rs.a'),m['name']]))
        assert sha(obj)==m['sha256']
        explicit[m['name']]=dict(path=str(obj),sha256=sha(obj))
    subprocess.run([AR,'rD',str(target),*[r['path'] for r in recipes],*[v['path'] for k,v in explicit.items() if k.startswith('nak_rs.')]],check=True)
    subprocess.run([AR,'sD',str(target)],check=True)
    changed=set(old_nak)|{r['name'] for r in recipes}|set(explicit)
    after=archive_members(target)
    keep=lambda rows:[(m['name'],m['sha256']) for m in rows if m['name'] not in changed]
    assert keep(before)==keep(after),'Unrelated driver objects changed'
    retained=Counter(m['name'] for m in after)
    for n in changed:
        if n in retained: assert retained[n]==1,n
    v13=json.loads((PREVIOUS/'build.json').read_text())
    explicit.update(v13['explicit_link_objects'])
    write_json(work/'build.json',dict(status='PASS',version=VERSION,build_id=BUILD_ID,policy=POLICY,
        library=str(target),library_sha256=sha(target),baseline_library_sha256=OLD_LIB,
        changed_sources=prepared['changed'],prepared_sha256=sha(work/'prepared.json'),
        c_dependencies_sha256=sha(work/'c-dependencies.json'),c_recipes_sha256=sha(work/'c-recipes.json'),
        rust_report_sha256=sha(work/'rust.json'),explicit_link_objects=explicit,
        preserved_member_count=len(keep(before)),preserved_members_sha256=hashlib.sha256(json.dumps(keep(before)).encode()).hexdigest(),
        memory_object_unchanged=True,compiler_c_abi_unchanged=True,rust_allocator_abi_unchanged=True,
        builder_sha256=sha(Path(__file__)),hardware_tested=False,fps_gain_measured=False))
    print('BUILT v14',sha(target),flush=True)


if __name__=='__main__':main()
