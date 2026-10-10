"""Correct v14's retained v13 disk-cache identity; preserve all shader code."""
from pathlib import Path
import hashlib
import json
import os
import shlex
import shutil
import struct
import subprocess
import zipfile
from port_common import ROOT,sha,write_json
from build_mesa_backport import BASE,AR,archive_members,dependency_paths
from build_mesa_shader_v14 import PREVIOUS as V13,WORK as V14

WORK=Path('/home/blekjek/sleepingdogs-mesa-v141')
DEST=ROOT/'dist/low-window-gm20b-cache-fix'
BUILD='sleepingdogs-low-window-v14.1-gm20b-cache-fix'
OLD_LIB='0467beaa7fc8a0c9a256a666521bb074dd0707e118d47281f468daaced7dad2b'
OLD_ELF='1b919a9c90291ec3054a716b1400bd080259e29451c60539217d36e27d916f5d'
OLD_NRO='e35c1a35e170b8e532895f5fee8daadc78d281e7cca3ab84123c1768160324c5'
OLD_ZIP='e9c51827334ba1d1fdbac0aed9bba61a30fea5c258eb78037b76e77329e8a11e'
FILE='src/nouveau/vulkan/nvk_instance.c'
PHYSICAL='src/nouveau/vulkan/nvk_physical_device.c'
VERSION='26.2.2-sdv14.1-cache'
BUILD_ID=hashlib.sha1((OLD_LIB+VERSION+'uniform-pipeline-and-disk-cache-v1').encode()).hexdigest()


def main():
    assert sha(V14/'library/libvulkan.a')==OLD_LIB
    WORK.mkdir(exist_ok=True);(WORK/'objects').mkdir(exist_ok=True)
    prepared=json.loads((V13/'prepared.json').read_text())
    baseline=V13/'source'/FILE;assert sha(baseline)==prepared['source_files'][FILE]
    text=baseline.read_text()
    needle='   *pInstance = nvk_instance_to_handle(instance);'
    assert text.count(needle)==1
    # Both identity-bearing units must use one NEW ID. A fresh pipeline ID also
    # rejects any v14 pipeline binaries populated with the old disk-cache shaders.
    text=text.replace(needle,'''#if defined(HAVE_SWITCH_PLATFORM) && defined(NVK_BUILD_ID_OVERRIDE)
   extern void wine_nx_runtime_trace(const char *) __attribute__((weak));
   if (wine_nx_runtime_trace)
      wine_nx_runtime_trace("[SD-NVK-V14.1] instance/disk cache_id="
                            NVK_BUILD_ID_OVERRIDE "; matches v14.1 pipeline identity");
#endif

'''+needle)
    source=WORK/'source'/FILE;source.parent.mkdir(parents=True,exist_ok=True)
    source.write_text(text)
    physical_source=WORK/'source'/PHYSICAL
    v14_prepared=json.loads((V14/'prepared.json').read_text())
    assert sha(V14/'source'/PHYSICAL)==v14_prepared['source_files'][PHYSICAL]
    shutil.copy2(V14/'source'/PHYSICAL,physical_source)
    cross=BASE/'mesa-vulkan/cross'
    entries=json.loads((cross/'compile_commands.json').read_text())
    def redirect(x):
        p=(cross/x).resolve()
        return str(V13/'source'/p.relative_to(BASE/'mesa-switch')) if p.is_relative_to(BASE/'mesa-switch') else str(p)
    old_deps=json.loads((V13/'dependencies.json').read_text())
    deps={};objects=[];recipes={}
    for unit in (source,physical_source):
        recipe=next(e for e in entries if e['file'].endswith('/'+unit.name))
        raw=shlex.split(recipe['command']);obj=WORK/'objects'/(unit.name+'.o');dep=obj.with_suffix('.d')
        args=[];i=0
        while i<len(raw):
            x=raw[i]
            if x in ('-c','-o','-MF','-MQ'):
                args += [x,str(unit if x=='-c' else dep if x=='-MF' else obj)];i+=2;continue
            if x.startswith('-I'):x='-I'+redirect(x[2:])
            if x.startswith('-DNVK_BUILD_ID_OVERRIDE='):x='-DNVK_BUILD_ID_OVERRIDE="'+BUILD_ID+'"'
            if x.startswith('-DPACKAGE_VERSION='):x='-DPACKAGE_VERSION="'+VERSION+'"'
            args.append(x);i+=1
        assert args.count('-DNVK_BUILD_ID_OVERRIDE="'+BUILD_ID+'"')==1
        with (WORK/(unit.name+'.compile.log')).open('w') as log:
            subprocess.run(args,cwd=cross,stdout=log,stderr=subprocess.STDOUT,check=True)
        unit_deps={str(p):sha(p) for p in dependency_paths(dep)}
        for n,h in unit_deps.items():
            p=Path(n)
            if p==unit:assert h==sha(unit)
            elif p.is_relative_to(V13/'source'):assert h==prepared['source_files'][p.relative_to(V13/'source').as_posix()],n
            else:assert h==old_deps[n],('shared generated/header dependency changed',n)
        deps.update(unit_deps);objects.append(obj)
        recipes[unit.name]=dict(command=args,source_sha256=sha(unit),object_sha256=sha(obj))
    (WORK/'library').mkdir(exist_ok=True);library=WORK/'library/libvulkan.a'
    shutil.copy2(V14/'library/libvulkan.a',library)
    before=archive_members(library)
    names={obj.name for obj in objects}
    assert all(sum(m['name']==obj.name for m in before)==1 for obj in objects)
    subprocess.run([AR,'rD',str(library),*[str(obj) for obj in objects]],check=True)
    subprocess.run([AR,'sD',str(library)],check=True)
    after=archive_members(library)
    keep=lambda rows:[(m['name'],m['sha256']) for m in rows if m['name'] not in names]
    assert keep(before)==keep(after),'Compiler or unrelated driver member changed'
    assert all(next(m['sha256'] for m in after if m['name']==obj.name)==sha(obj) for obj in objects)
    write_json(WORK/'dependencies.json',deps)
    write_json(WORK/'compile.json',dict(recipes=recipes,baseline_source_sha256=sha(baseline),
        build_id=BUILD_ID,version=VERSION,dependency_count=len(deps)))
    # Record target layouts using the same preprocessor/ABI as the driver,
    # for executable regression tests of the shipped ARM64 entry points.
    layout=WORK/'layout.c'
    layout.write_text('''#include <stddef.h>
#include "nvk_instance.h"
#include "nvk_physical_device.h"
const unsigned long long sd_cache_layout[] = {
 sizeof(struct nvk_instance), offsetof(struct nvk_instance,driver_build_sha),
 sizeof(struct nvk_physical_device), offsetof(struct nvk_physical_device,vk.instance),
 offsetof(struct nvk_physical_device,info.chipset),
 offsetof(struct nvk_physical_device,vk.properties.pipelineCacheUUID),
 offsetof(struct nvk_physical_device,vk.disk_cache),
};
''')
    flags=[];i=0
    while i<len(args):
        if args[i] in ('-o','-MF','-MQ','-c'):i+=2;continue
        if args[i]=='-MD':i+=1;continue
        flags.append(args[i]);i+=1
    layout_obj=WORK/'layout.o'
    subprocess.run(flags+['-c',str(layout),'-o',str(layout_obj)],cwd=cross,check=True)
    layout_bin=WORK/'layout.bin'
    subprocess.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objcopy','-O','binary','-j','.rodata.sd_cache_layout',str(layout_obj),str(layout_bin)],check=True)
    assert layout_bin.stat().st_size==56
    write_json(DEST/'layout.json',dict(zip(('instance_size','build_sha_offset','pdev_size','pdev_instance_offset',
        'chipset_offset','pipeline_uuid_offset','disk_cache_offset'),struct.unpack('<7Q',layout_bin.read_bytes()))))
    previous=json.loads((ROOT/'dist/low-window-gm20b-shaders/native.json').read_text())
    driver=json.loads((ROOT/'dist/low-window-gm20b-shaders/driver.json').read_text())
    for n,h in previous['inputs'].items():assert sha(Path(n))==h,n
    for e in driver['explicit_link_objects'].values():assert sha(Path(e['path']))==e['sha256']
    original=previous['link_argv'];out=WORK/'runtime';out.mkdir(exist_ok=True)
    env=dict(os.environ,DEVKITPRO='/opt/devkitpro',DEVKITA64='/opt/devkitpro/devkitA64')
    cwd=previous['working_directory'];idx=original.index('-o')+1
    baseline_elf=out/'baseline/wine-nx-runtime.elf';baseline_elf.parent.mkdir(exist_ok=True)
    cmd=['-Wl,-Map='+str(out/'baseline.map') if x.startswith('-Wl,-Map=') else x for x in original];cmd[idx]=str(baseline_elf)
    with (out/'baseline.log').open('w') as log:subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    assert sha(baseline_elf)==OLD_ELF,'v14 baseline differs'
    candidate=out/'candidate/wine-nx-runtime.elf';candidate.parent.mkdir(exist_ok=True)
    cmd=[str(library) if x==str(V14/'library/libvulkan.a') else '-Wl,-Map='+str(out/'candidate.map') if x.startswith('-Wl,-Map=') else x for x in original]
    cmd[idx]=str(candidate);cmd[1:1]=[str(obj) for obj in objects]
    with (out/'candidate.log').open('w') as log:subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    mapping=(out/'candidate.map').read_text()
    for obj in objects:assert 'LOAD '+str(obj) in mapping and '.a('+obj.name+')' not in mapping
    for e in driver['explicit_link_objects'].values():assert 'LOAD '+e['path'] in mapping
    for n,h in previous['inputs'].items():assert sha(Path(n))==h,n
    package=ROOT/'dist/sleepingdogs-fex-low-window-gm20b-shaders.zip';assert sha(package)==OLD_ZIP
    with zipfile.ZipFile(package) as z:old=z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    assert hashlib.sha256(old).hexdigest()==OLD_NRO
    size=struct.unpack_from('<I',old,0x18)[0];assert old[size:size+4]==b'ASET'
    io,il,no,nl,ro,rl=struct.unpack_from('<6Q',old,size+8);assert rl==0
    (out/'icon.jpg').write_bytes(old[size+io:size+io+il]);(out/'app.nacp').write_bytes(old[size+no:size+no+nl])
    nro=out/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro',str(candidate),str(nro),'--icon='+str(out/'icon.jpg'),'--nacp='+str(out/'app.nacp')],check=True)
    data=nro.read_bytes();assert data[struct.unpack_from('<I',data,0x18)[0]:]==old[size:]
    DEST.mkdir(parents=True,exist_ok=True);(DEST/nro.name).write_bytes(data)
    (ROOT/'local/symbols/sleepingdogs-low-window-v141.elf').write_bytes(candidate.read_bytes())
    result=dict(status='BUILT',build=BUILD,nro_sha256=sha(nro),elf_sha256=sha(candidate),
        library_sha256=sha(library),baseline_library_sha256=OLD_LIB,baseline_zip_sha256=OLD_ZIP,
        baseline_elf_sha256=OLD_ELF,baseline_reproduced=True,cache_id=BUILD_ID,version=VERSION,
        changed_source=FILE,source_sha256=sha(source),baseline_source_sha256=sha(baseline),
        replaced_objects={str(obj):sha(obj) for obj in objects},preserved_driver_member_count=len(keep(before)),
        preserved_driver_members_sha256=hashlib.sha256(json.dumps(keep(before)).encode()).hexdigest(),
        shaders_unchanged=True,wine_objects_unchanged=True,fex_adapter_unchanged=True,dxvk_unchanged=True,
        dependencies_sha256=sha(WORK/'dependencies.json'),compile_sha256=sha(WORK/'compile.json'),
        inputs=previous['inputs'],link_argv=cmd,working_directory=cwd,explicit_identity_objects=[str(obj) for obj in objects],
        script_sha256=sha(Path(__file__)),hardware_tested=False,fps_gain_measured=False)
    write_json(DEST/'native.json',result)
    print('BUILT v14.1 cache identity fix',result['nro_sha256'],flush=True)


if __name__=='__main__':main()
