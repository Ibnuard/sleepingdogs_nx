"""Build the bounded v11 diagnostic overlay on the verified, preserved v10."""
from pathlib import Path
import argparse
import contextlib
import json
import shutil
import struct
import subprocess
import zipfile
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from sleepingdogs_frame_diagnostics import apply, BUILD, MARKER, FILES, COPIES, MODIFIED
from verify_shader_abi import verify
import f1_base_build as base

V10_SHA='b352ef810914d90fc2cda9b153b5c2f871e85004678102f8c9b77aabcc73bacf'
INPUTS=tuple(sorted(set(COPIES.values())|{'tools/build_frame_diagnostics.py','tools/sleepingdogs_frame_diagnostics.py'}))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    p.add_argument('--jobs',type=int,default=2)
    a=p.parse_args()
    package=ROOT/'dist/sleepingdogs-fex-low-window-direct-sync.zip'
    assert sha(package)==V10_SHA
    with zipfile.ZipFile(package) as z:
        previous=json.loads(z.read('source/low-window-direct-sync/native.json'))
        old_nro=z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    assert sha(ROOT/'local/symbols/sleepingdogs-low-window-v10.elf')==previous['elf_sha256']
    for n,h in previous['build_inputs'].items(): assert sha(ROOT/n)==h,n
    tests=json.loads((ROOT/'reports/low-window-v11-frame-diagnostics.json').read_text())
    assert tests['status']=='PASS'
    for n,h in tests['sources'].items(): assert sha(ROOT/n)==h,('stale tests',n)
    inputs=dict(previous['build_inputs']); inputs.update({n:sha(ROOT/n) for n in INPUTS})
    assert verify()==previous['shader_abi']
    work, source=a.work,a.work/'native-source'
    stamp,backup=work/'frame-diagnostics-prepared.json',work/'frame-diagnostics-v10-source'
    if stamp.exists():
        old=json.loads(stamp.read_text())
        assert old['base_zip_sha256']==V10_SHA and manifest(source)==old['source']
        if old['inputs']!=inputs:
            for n in MODIFIED:
                assert sha(backup/n)==previous['source_files'][n]
                shutil.copy2(backup/n,source/n)
            apply(source)
            write_json(stamp,dict(inputs=inputs,source=manifest(source),adapter=previous['adapter_files'],base_zip_sha256=V10_SHA))
    else:
        assert manifest(source)==previous['source_files'],'v10 native source changed'
        assert manifest(work/'fex-adapter')==previous['adapter_files'],'FEXTendo adapter changed'
        assert not backup.exists(),'Preserve previous source backup'
        for n in MODIFIED:
            target=backup/n; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source/n,target)
        apply(source)
        write_json(stamp,dict(inputs=inputs,source=manifest(source),adapter=previous['adapter_files'],base_zip_sha256=V10_SHA))
    prepared=json.loads(stamp.read_text())
    assert prepared['inputs']==inputs and manifest(source)==prepared['source']
    assert manifest(work/'fex-adapter')==prepared['adapter']
    changed={n for n,h in prepared['source'].items() if previous['source_files'].get(n)!=h}
    assert changed==FILES and not set(previous['source_files'])-set(prepared['source'])
    for n,h in tests['source_files'].items(): assert prepared['source'][n]==h,('tested overlay differs',n)
    size=struct.unpack_from('<I',old_nro,0x18)[0]
    assert old_nro[size:size+4]==b'ASET'
    io,il,no,nl=struct.unpack_from('<4Q',old_nro,size+8)
    icon,nacp=work/'nro-icon.jpg',work/'sleepingdogs-fex.nacp'
    icon.write_bytes(old_nro[size+io:size+io+il]); nacp.write_bytes(old_nro[size+no:size+no+nl])
    print('Verified v10 source, FEXTendo adapter and SDK ABI; compiling bounded diagnostics',flush=True)
    with (work/'frame-diagnostics-build.log').open('w') as log:
        original_run=base.run
        def logged_run(command,**kwargs):
            kwargs.setdefault('stdout',log); kwargs.setdefault('stderr',subprocess.STDOUT)
            return original_run(command,**kwargs)
        base.run=logged_run
        try:
            with contextlib.redirect_stdout(log):
                elf,_=base.build_nro(work,source,Path('/home/blekjek/pes13-build'),a.jobs,icon=icon)
        finally: base.run=original_run
    out=ROOT/'dist/low-window-frame-diagnostics'; out.mkdir(parents=True,exist_ok=True)
    nro=out/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro',str(elf),str(nro),'--nacp='+str(nacp),'--icon='+str(icon)],check=True)
    shutil.copy2(elf,ROOT/'local/symbols/sleepingdogs-low-window-v11.elf')
    data=nro.read_bytes()
    for marker in (MARKER.encode(),b'[SD-DIAG-WAIT]',b'[SD-DIAG-FRAME]',b'[SD-DIAG-MAP]',
                   b'[SD-DIRECT-SYNC]',b'[SD-PERF]',b'[SD-FRAME]',b'[SD-CPU-TOPOLOGY] v1',b'[SD-LOWVA] v1'):
        assert marker in data,marker
    assert manifest(source)==prepared['source'] and manifest(work/'fex-adapter')==prepared['adapter']
    for n,h in inputs.items(): assert sha(ROOT/n)==h,n
    receipt=dict(previous,build=BUILD,nro_sha256=sha(nro),elf_sha256=sha(elf),build_inputs=inputs,
        source_files=prepared['source'],source_changes={n:prepared['source'][n] for n in sorted(changed)},
        previous_package_sha256=V10_SHA,hardware_tested=False,performance_optimization=False,
        fps_gain_measured=False,cpu_gpu_scheduling_unchanged=True,synchronization_backend_unchanged=True,
        cpu_translator_unchanged=True,guest_dlls_unchanged=True,graphics_resolution_unchanged=True,
        target_resolution=[1280,720],diagnostics=dict(duration_ms=30000,trigger='two consecutive 3-25 FPS windows',
        enabled_file='frame-diagnostics.txt',package_enabled=True,sampler=False,thread_pausing=False,
        gpu_execution_measured=False,thread_tick_queries='one per Present during capture'))
    write_json(out/'native.json',receipt)
    print('Built',BUILD,receipt['nro_sha256'],flush=True)

if __name__=='__main__': main()
