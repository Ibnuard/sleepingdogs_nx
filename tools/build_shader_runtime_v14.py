"""Reproduce v13, then relink only the isolated v14 shader-driver overlay."""
from pathlib import Path
import json
import os
import struct
import subprocess
import zipfile
from port_common import ROOT,sha,write_json
from build_mesa_shader_v14 import WORK,PREVIOUS,OLD_LIB,prepare

OLD_ZIP='43e233720d7f48d0ec320a77c836af085917a00cfc0ddc0d23e469b190dee9c5'
OLD_ELF='bf67f1a9e666735cc331b9abd65c49e2c91ad3a26aff75f805fe95063df9eb35'
OLD_NRO='635728655ee1fbf11ce7d882882e61b561825567b79f2929cf653691bbf681a6'
BUILD='sleepingdogs-low-window-v14-gm20b-shaders'
DEST=ROOT/'dist/low-window-gm20b-shaders'


def main():
    prepared=prepare()
    tests=json.loads((ROOT/'reports/mesa-v14-shader-host.json').read_text())
    assert tests['status']=='PASS' and tests['changed_sources']==prepared['changed']
    for n,h in tests['sources'].items():assert sha(ROOT/n)==h,n
    previous=json.loads((ROOT/'dist/low-window-mesa-backport/native.json').read_text())
    driver=json.loads((WORK/'build.json').read_text())
    assert driver['status']=='PASS' and driver['baseline_library_sha256']==OLD_LIB
    assert driver['builder_sha256']==sha(ROOT/'tools/build_mesa_shader_v14.py')
    assert driver['prepared_sha256']==sha(WORK/'prepared.json')
    assert driver['rust_report_sha256']==sha(WORK/'rust.json')
    library=Path(driver['library']);assert sha(library)==driver['library_sha256']
    for n,h in previous['inputs'].items():assert sha(Path(n))==h,n
    for n,h in json.loads((WORK/'c-dependencies.json').read_text()).items():assert sha(Path(n))==h,n
    for n,h in json.loads((WORK/'rust.json').read_text())['externs'].items():assert sha(Path(n))==h,n
    assert previous['elf_sha256']==sha(ROOT/'local/symbols/sleepingdogs-low-window-v13.elf')==OLD_ELF
    assert sha(PREVIOUS/'library/libvulkan.a')==OLD_LIB
    env=dict(os.environ,DEVKITPRO='/opt/devkitpro',DEVKITA64='/opt/devkitpro/devkitA64')
    out=WORK/'runtime';out.mkdir(exist_ok=True)
    cwd=Path(previous['working_directory'])
    original=previous['link_argv']
    index=original.index('-o')+1
    baseline=out/'baseline/wine-nx-runtime.elf';baseline.parent.mkdir(exist_ok=True)
    cmd=[('-Wl,-Map='+str(out/'baseline.map')) if x.startswith('-Wl,-Map=') else x for x in original]
    cmd[index]=str(baseline)
    with (out/'baseline.log').open('w') as log:
        subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    assert sha(baseline)==OLD_ELF,'v13 baseline no longer reproduces'
    print('PASS reproduced identical v13 ELF',flush=True)
    candidate=out/'candidate/wine-nx-runtime.elf';candidate.parent.mkdir(exist_ok=True)
    cmd=[str(library) if x==str(PREVIOUS/'library/libvulkan.a') else
         '-Wl,-Map='+str(out/'candidate.map') if x.startswith('-Wl,-Map=') else x for x in original]
    cmd[index]=str(candidate)
    explicit=driver['explicit_link_objects']
    for n,e in explicit.items():assert sha(Path(e['path']))==e['sha256'],n
    cmd[1:1]=[e['path'] for n,e in sorted(explicit.items()) if e['path'] not in cmd]
    with (out/'candidate.log').open('w') as log:
        subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    mapping=(out/'candidate.map').read_text()
    for n,e in explicit.items():
        assert 'LOAD '+e['path'] in mapping,n
        assert '.a('+n+')' not in mapping,'An archive provided an old compiler/Horizon object: '+n
    assert driver['version'].encode() in candidate.read_bytes()
    package=ROOT/'dist/sleepingdogs-fex-low-window-mesa-backport.zip'
    assert sha(package)==OLD_ZIP
    with zipfile.ZipFile(package) as z: old=z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    import hashlib
    assert hashlib.sha256(old).hexdigest()==OLD_NRO
    size=struct.unpack_from('<I',old,0x18)[0];assert old[size:size+4]==b'ASET'
    io,il,no,nl,ro,rl=struct.unpack_from('<6Q',old,size+8);assert rl==0
    (out/'icon.jpg').write_bytes(old[size+io:size+io+il])
    (out/'app.nacp').write_bytes(old[size+no:size+no+nl])
    nro=out/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro',str(candidate),str(nro),
        '--icon='+str(out/'icon.jpg'),'--nacp='+str(out/'app.nacp')],check=True)
    data=nro.read_bytes();newsize=struct.unpack_from('<I',data,0x18)[0]
    assert data[newsize:]==old[size:],'NRO assets changed'
    for n,h in previous['inputs'].items():assert sha(Path(n))==h,n
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/nro.name).write_bytes(data)
    (ROOT/'local/symbols/sleepingdogs-low-window-v14.elf').write_bytes(candidate.read_bytes())
    (DEST/'driver.json').write_bytes((WORK/'build.json').read_bytes())
    receipt=dict(status='BUILT',build=BUILD,nro_sha256=sha(nro),elf_sha256=sha(candidate),
        baseline_zip_sha256=OLD_ZIP,baseline_elf_sha256=OLD_ELF,baseline_reproduced=True,
        baseline_library_sha256=OLD_LIB,candidate_vulkan_sha256=sha(library),
        driver_build_sha256=sha(WORK/'build.json'),explicit_link_objects=explicit,
        inputs=previous['inputs'],link_argv=cmd,working_directory=str(cwd),
        link_map_sha256=sha(out/'candidate.map'),script_sha256=sha(Path(__file__)),
        host_test_sha256=sha(ROOT/'reports/mesa-v14-shader-host.json'),
        wine_objects_unchanged=True,fex_adapter_unchanged=True,dxvk_unchanged=True,
        shared_sdk_unchanged=True,target_resolution=[1280,720],hardware_tested=False,fps_gain_measured=False)
    write_json(DEST/'native.json',receipt)
    print('BUILT v14 NRO',receipt['nro_sha256'],flush=True)


if __name__=='__main__':main()
