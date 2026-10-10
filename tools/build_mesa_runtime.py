"""Relink the proven v11 runtime against an isolated, reviewed NVK backport.

The baseline link must reproduce the shipped ELF exactly before replacing
the Vulkan archive. No native source, existing object or shared SDK is edited.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shlex
import struct
import subprocess
import zipfile
from port_common import ROOT, sha, write_json

OLD_ELF = 'e8cf0e365a75716d179bcc8e55f41317b87bee3fe7928ca92a50f7339ed70f1e'
OLD_NRO = '91cce20983b88834d9652deb9f5225ec431c300a0440e34370766f9372ecd7d8'
OLD_LIB = 'ca9c82e03b04fb385004d6f7d47bd8357e107f7a35481f08e06f7b870f941315'
OLD_ZIP = '108f8a78872b31fba566cf1df70ebb100856f67480818ae2af66ffa70e5f7232'
SDK_LIB = Path('/home/blekjek/pes13-build/mesa-vulkan/install/opt/devkitpro/portlibs/switch/lib/libvulkan.a')
NATIVE = Path('/home/blekjek/sleepingdogs-low-window-v1')
BUILD = 'sleepingdogs-low-window-v13-mesa-backport'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-mesa-v13'))
    p.add_argument('--library', type=Path)
    p.add_argument('--baseline-only', action='store_true')
    a = p.parse_args()
    env = dict(os.environ,DEVKITPRO='/opt/devkitpro',DEVKITA64='/opt/devkitpro/devkitA64')
    out = a.work/'runtime'; out.mkdir(parents=True, exist_ok=True)
    cwd = NATIVE/'native-build'
    assert sha(SDK_LIB) == OLD_LIB
    assert sha(ROOT/'local/symbols/sleepingdogs-low-window-v11.elf') == OLD_ELF
    line = subprocess.check_output(['ninja','-C',str(cwd),'-t','commands','wine-nx-runtime.elf'], text=True).splitlines()[-1]
    assert line.startswith(': && ') and line.endswith(' && :')
    command = shlex.split(line[5:-5])
    assert not any(x in ('&&',';', '|') for x in command)
    index = command.index('-o') + 1
    assert command[index] == 'wine-nx-runtime.elf'
    assert command.count(str(SDK_LIB)) == 2
    inputs = {}
    for item in command:
        if item.endswith(('.obj','.o','.a')):
            path = (cwd/item).resolve()
            inputs[str(path)] = sha(path)
    # switch.specs embeds the output stem in .nx-module-name; keep it exact.
    baseline = out/'baseline/wine-nx-runtime.elf'
    baseline.parent.mkdir(exist_ok=True)
    replay = command.copy(); replay[index] = str(baseline)
    with (out/'baseline-link.log').open('w') as log:
        subprocess.run(replay,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    assert sha(baseline) == OLD_ELF, 'Baseline relink differs: native or SDK state is not the tested v11'
    write_json(out/'baseline.json',dict(status='PASS',elf_sha256=sha(baseline),inputs=inputs,
        link_argv=command,working_directory=str(cwd),script_sha256=sha(Path(__file__))))
    print('PASS baseline replay: identical v11 ELF',flush=True)
    if a.baseline_only: return
    assert a.library and a.library.is_file()
    candidate_hash=sha(a.library)
    assert candidate_hash != OLD_LIB
    driver_path=a.work/'build.json'
    driver=json.loads(driver_path.read_text())
    assert driver['status']=='PASS' and driver['library_sha256']==candidate_hash
    assert driver['baseline_library_sha256']==OLD_LIB
    assert driver['memory_object_unchanged'] and driver['nak_nir_unchanged']
    explicit=driver['explicit_link_objects']
    assert set(explicit)=={'nouveau_horizon_device.c.o','nouveau_horizon_channel.c.o'}
    for entry in explicit.values(): assert sha(Path(entry['path']))==entry['sha256']
    elf = out/'candidate/wine-nx-runtime.elf'
    elf.parent.mkdir(exist_ok=True)
    linked = [str(a.library) if x == str(SDK_LIB) else x for x in command]
    linked[index] = str(elf)
    # libEGL also bundles Horizon objects and appears earlier in the group.
    # Explicit objects ensure all changed definitions come from this backport.
    linked[1:1]=[entry['path'] for _,entry in sorted(explicit.items())]
    linked.insert(1,'-Wl,-Map='+str(out/'sleepingdogs-v13.map'))
    with (out/'candidate-link.log').open('w') as log:
        subprocess.run(linked,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    for path,digest in inputs.items(): assert sha(Path(path)) == digest,path
    assert sha(a.library) == candidate_hash
    for entry in explicit.values(): assert sha(Path(entry['path']))==entry['sha256']
    map_text=(out/'sleepingdogs-v13.map').read_text()
    for name,entry in explicit.items():
        assert 'LOAD '+entry['path'] in map_text
        for archive in ('libEGL.a','libGL.a','libvulkan.a'):
            assert archive+'('+name+')' not in map_text, 'Archive overrode explicit Horizon object'
    assert driver['version'].encode() in elf.read_bytes()
    base_zip = ROOT/'dist/sleepingdogs-fex-low-window-submit-batching.zip'
    assert sha(base_zip) == OLD_ZIP
    with zipfile.ZipFile(base_zip) as z: old = z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    assert hashlib.sha256(old).hexdigest() == OLD_NRO
    size=struct.unpack_from('<I',old,0x18)[0]
    assert old[size:size+4] == b'ASET'
    io,il,no,nl=struct.unpack_from('<4Q',old,size+8)
    icon,nacp=out/'icon.jpg',out/'runtime.nacp'
    icon.write_bytes(old[size+io:size+io+il]); nacp.write_bytes(old[size+no:size+no+nl])
    nro=out/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro',str(elf),str(nro),
        '--nacp='+str(nacp),'--icon='+str(icon)],check=True)
    data=nro.read_bytes()
    for marker in (b'[SD-DIAG-WAIT]',b'[SD-DIRECT-SYNC]',b'[SD-LOWVA] v1',b'[SD-CPU-TOPOLOGY] v1'):
        assert marker in data,marker
    dest=ROOT/'dist/low-window-mesa-backport'; dest.mkdir(parents=True,exist_ok=True)
    (dest/nro.name).write_bytes(data)
    symbol=ROOT/'local/symbols/sleepingdogs-low-window-v13.elf'
    symbol.write_bytes(elf.read_bytes())
    receipt=dict(status='BUILT',build=BUILD,nro_sha256=sha(nro),elf_sha256=sha(elf),
        base_zip_sha256=OLD_ZIP,baseline_reproduced=True,baseline_elf_sha256=OLD_ELF,
        base_vulkan_sha256=OLD_LIB,candidate_vulkan_sha256=candidate_hash,
        driver_build_sha256=sha(driver_path),driver_version=driver['version'],
        driver_build_id=driver['build_id'],explicit_link_objects=explicit,
        changed_horizon_objects_explicit=True,link_map_sha256=sha(out/'sleepingdogs-v13.map'),
        inputs=inputs,link_argv=linked,working_directory=str(cwd),
        script_sha256=sha(Path(__file__)),native_source_unchanged=True,fex_adapter_unchanged=True,
        dxvk_unchanged=True,shared_sdk_unchanged=sha(SDK_LIB)==OLD_LIB,
        target_resolution=[1280,720],hardware_tested=False,fps_gain_measured=False)
    write_json(dest/'native.json',receipt)
    (dest/'driver.json').write_bytes(driver_path.read_bytes())
    print('BUILT',BUILD,receipt['nro_sha256'],flush=True)


if __name__ == '__main__': main()
