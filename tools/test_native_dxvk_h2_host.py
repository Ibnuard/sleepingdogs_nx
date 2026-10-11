"""H2 host regression with real DXVK and a modeled Wine-permission fixture.

Tests real low-address buffers, protocol validation, Map and shader readback.
This direct-entry test cannot establish that Switch's actual Wine/FEX gate works.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=ROOT/'local/native-dxvk-h2-v1';out.mkdir(parents=True,exist_ok=True)
    prior=json.loads((ROOT/'local/native-dxvk-probe-v1/build-host.json').read_text())
    library=Path(prior['library']);assert sha(library)==prior['sha256']
    for name,digest in prior['probe_sources'].items():assert sha(ROOT/name)==digest
    exe=out/'h2-host-test'
    command=['g++','-O2','-std=c++17','-Wall','-Wextra','-I'+str(ROOT/'src/native_dxvk_bridge'),
             str(ROOT/'tests/native_dxvk_bridge_host.cpp'),str(ROOT/'src/native_dxvk_bridge/bridge_host.cpp'),
             str(library),'-ldl','-lpthread','-o',str(exe)]
    with (out/'host.compile.log').open('w') as f:p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:print((out/'host.compile.log').read_text());raise RuntimeError('H2 host compile')
    config=out/'host.conf';config.write_text('dxvk.numCompilerThreads = 2\n')
    cache=out/'host-cache';cache.mkdir(exist_ok=True)
    env=dict(os.environ,VK_DRIVER_FILES='/usr/share/vulkan/icd.d/lvp_icd.json',VK_ICD_FILENAMES='/usr/share/vulkan/icd.d/lvp_icd.json',
             DXVK_CONFIG_FILE=str(config),DXVK_SHADER_CACHE_PATH=str(cache),DXVK_LOG_PATH=str(out))
    p=subprocess.run([str(exe)],cwd=out,env=env,text=True,capture_output=True,timeout=120)
    (out/'host-stdout.log').write_text(p.stdout);(out/'host-stderr.log').write_text(p.stderr)
    if p.returncode:print(p.stderr[-9000:]);raise RuntimeError('H2 host regression')
    result=json.loads(p.stdout)
    result.update(executable_sha256=sha(exe),native_dxvk_sha256=sha(library),compile_argv=command,
                  runner_sha256=sha(__file__),source_files={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tests/native_dxvk_bridge_host.cpp',ROOT/'src/native_dxvk_bridge/bridge_host.cpp',ROOT/'src/native_dxvk_bridge/bridge_protocol.h']})
    (out/'host-test.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
