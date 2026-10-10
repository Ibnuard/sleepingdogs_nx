"""Build v9 shader backports on the verified v8 FEXTendo runtime; preserve rollback."""
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
from sleepingdogs_shader_optimizations import apply, BUILD, MARKER, FILES, COPIES
from verify_shader_abi import verify
import f1_base_build as base

V8_SHA = 'b85ca33634a33467b9756f8fa408009add613ab92f3f88d584921f78eae9dd2e'
INPUTS = tuple(sorted(set(COPIES.values()) | {'tools/build_shader_optimizations.py',
    'tools/sleepingdogs_shader_optimizations.py','tools/verify_shader_abi.py'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    parser.add_argument('--jobs',type=int,default=4)
    args=parser.parse_args()
    package=ROOT/'dist/sleepingdogs-fex-low-window-perf-counters.zip'
    assert sha(package)==V8_SHA
    with zipfile.ZipFile(package) as z:
        previous=json.loads(z.read('source/low-window-perf-counters/native.json'))
        old_nro=z.read('switch/sleepingdogs-fex/sleepingdogs-fex.nro')
    assert sha(ROOT/'local/symbols/sleepingdogs-low-window-v8.elf')==previous['elf_sha256']
    for name,digest in previous['build_inputs'].items():
        assert sha(ROOT/name)==digest,name
    tests=json.loads((ROOT/'reports/low-window-v9-shaders-prebuild.json').read_text())
    assert tests['status']=='PASS'
    for name,digest in tests['sources'].items():
        assert sha(ROOT/name)==digest,('stale tests',name)
    inputs=dict(previous['build_inputs'])
    inputs.update({name:sha(ROOT/name) for name in INPUTS})
    abi=verify()
    work,source=args.work,args.work/'native-source'
    stamp=work/'shader-optimizations-prepared.json'
    backup=work/'shader-optimizations-v8-source'
    if stamp.exists():
        old=json.loads(stamp.read_text())
        assert old['base_zip_sha256']==V8_SHA
        assert manifest(source)==old['source'],'Unexpected source changes after preparation'
        if old['inputs']!=inputs:
            # Reapply only our owned overlay after a local correction, from verified v8 bytes.
            for name in FILES:
                if name in previous['source_files']:
                    assert sha(backup/name)==previous['source_files'][name]
                    shutil.copy2(backup/name,source/name)
            apply(source)
            write_json(stamp,dict(inputs=inputs,source=manifest(source),adapter=previous['adapter_files'],base_zip_sha256=V8_SHA))
    else:
        assert manifest(source)==previous['source_files'],'v8 source changed'
        assert manifest(work/'fex-adapter')==previous['adapter_files'],'FEXTendo adapter changed'
        assert not backup.exists(),'Preserve previous source backup'
        for name in FILES:
            if (source/name).exists():
                dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source/name,dest)
        apply(source)
        write_json(stamp,dict(inputs=inputs,source=manifest(source),adapter=previous['adapter_files'],base_zip_sha256=V8_SHA))
    prepared=json.loads(stamp.read_text())
    assert prepared['inputs']==inputs
    assert manifest(source)==prepared['source']
    assert manifest(work/'fex-adapter')==prepared['adapter']
    changed={n for n,h in prepared['source'].items() if previous['source_files'].get(n)!=h}
    assert changed==FILES and not set(previous['source_files'])-set(prepared['source'])
    for name,digest in tests['source_files'].items():
        assert prepared['source'][name]==digest,('overlay differs from tested source',name)
    size=struct.unpack_from('<I',old_nro,0x18)[0]
    assert old_nro[size:size+4]==b'ASET'
    io,il,no,nl=struct.unpack_from('<4Q',old_nro,size+8)
    icon,nacp=work/'nro-icon.jpg',work/'sleepingdogs-fex.nacp'
    icon.write_bytes(old_nro[size+io:size+io+il]);nacp.write_bytes(old_nro[size+no:size+no+nl])
    print('Verified v8 and native ABI; building FEXTendo v9 shader backports',flush=True)
    with (work/'shader-optimizations-build.log').open('w') as log:
        original_run=base.run
        def logged_run(command,**kwargs):
            kwargs.setdefault('stdout',log);kwargs.setdefault('stderr',subprocess.STDOUT)
            return original_run(command,**kwargs)
        base.run=logged_run
        with contextlib.redirect_stdout(log):
            elf,_=base.build_nro(work,source,Path('/home/blekjek/pes13-build'),args.jobs,icon=icon)
    out=ROOT/'dist/low-window-shader-optimizations';out.mkdir(parents=True,exist_ok=True)
    nro=out/'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro',str(elf),str(nro),'--nacp='+str(nacp),'--icon='+str(icon)],check=True)
    shutil.copy2(elf,ROOT/'local/symbols/sleepingdogs-low-window-v9.elf')
    data=nro.read_bytes()
    for marker in (MARKER.encode(),b'[SD-SHADER]',b'[SD-SHADER-CACHE]',b'[SD-PERF]',b'[SD-FRAME]',
                   b'[SD-CPU-TOPOLOGY] v1',b'[SD-LOWVA] v1',b'[SD-SYNC] v1'):
        assert marker in data,marker
    assert manifest(source)==prepared['source']
    assert manifest(work/'fex-adapter')==prepared['adapter']
    for name,digest in inputs.items():assert sha(ROOT/name)==digest,name
    receipt=dict(previous,build=BUILD,nro_sha256=sha(nro),elf_sha256=sha(elf),build_inputs=inputs,
        source_files=prepared['source'],source_changes={n:prepared['source'][n] for n in sorted(changed)},
        previous_package_sha256=V8_SHA,hardware_tested=False,performance_optimization=True,
        fps_gain_measured=False,cpu_gpu_scheduling_unchanged=False,cpu_translator_unchanged=True,
        fex_port_origin='FEXTendo / AndroSwitch Project / Ibnuard, inherited from project pes13-fex; not Autorun FEX integration',
        backported_from_autorun=['5a75cfb647a010704a2811f535323fc4b39c9109',
            'e823a778f5ccf40ae8392209b9ff769b42780c14','e7168c3f438ace433c4e77da2cb4533762a77399'],
        shader_switches=['shader-affinity.txt','shader-cache.txt'],shader_abi=abi,
        shader_cache_limit_per_worker=1048576,shader_cache_worker_limit=8,
        synchronization_backend_unchanged=True,guest_dlls_unchanged=True)
    write_json(out/'native.json',receipt)
    print('Built',BUILD,receipt['nro_sha256'],flush=True)


if __name__=='__main__':main()
