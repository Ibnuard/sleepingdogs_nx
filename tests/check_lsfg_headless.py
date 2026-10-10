"""Compile and exercise the Horizon backend using Lavapipe + Vulkan validation."""
from pathlib import Path
import subprocess,sys,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_lsfg_backend import WORK,MESA_HEADERS
from port_common import sha,write_json

def main():
    subprocess.run(['cmake','-S',str(WORK/'recipe'),'-B',str(WORK/'backend-host'),'-G','Ninja',
        '-DCMAKE_BUILD_TYPE=Release','-DLSFG_SOURCE='+str(WORK/'backend'),
        '-DCMAKE_CXX_FLAGS=-D__SWITCH__',
        '-DGLSLANG_VALIDATOR='+str(WORK/'host-tools/usr/bin/glslangValidator')],check=True)
    subprocess.run(['ninja','-C',str(WORK/'backend-host'),'-j6'],check=True)
    exe=WORK/'lsfg-headless'
    subprocess.run(['c++','-std=c++20','-O2','-I'+str(MESA_HEADERS),
        '-I'+str(WORK/'backend/lsfg-vk-backend/include'),'-I'+str(WORK/'backend/lsfg-vk-common/include'),
        str(ROOT/'tests/lsfg_headless.cpp'),str(WORK/'backend-host/liblsfg-vk.a'),
        '/usr/lib/x86_64-linux-gnu/libvulkan.so.1','-o',str(exe)],check=True)
    env=dict(os.environ,VK_ICD_FILENAMES='/usr/share/vulkan/icd.d/lvp_icd.json',
        VK_LAYER_PATH=str(WORK/'host-tools/usr/share/vulkan/explicit_layer.d'),
        LD_LIBRARY_PATH=str(WORK/'host-tools/usr/lib/x86_64-linux-gnu'))
    run=subprocess.run([str(exe),str(ROOT/'local/lsfg-shaders-v15/lsfg-3.1.sdp')],env=env,capture_output=True,text=True)
    (WORK/'headless.log').write_text(run.stdout+run.stderr)
    print(run.stdout+run.stderr)
    assert run.returncode==0
    write_json(ROOT/'reports/lsfg-headless-check.json',dict(status='PASS',
        backend_library_sha256=sha(WORK/'backend-host/liblsfg-vk.a'),
        pack_sha256=sha(ROOT/'local/lsfg-shaders-v15/lsfg-3.1.sdp'),output=run.stdout,
        validation_errors=0,hardware_tested=False,switch_performance_measured=False))

if __name__=='__main__':main()
