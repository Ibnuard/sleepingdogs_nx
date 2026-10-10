"""Test production present code under Khronos validation, in an invisible Xvfb."""
from pathlib import Path
import os,subprocess,sys,shutil,select
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_lsfg_backend import WORK,MESA_HEADERS
from prepare_lsfg_native import NATIVE
from port_common import sha,write_json

def main():
    exe=WORK/'lsfg-present'
    subprocess.run(['c++','-std=c++20','-O2','-I'+str(MESA_HEADERS),'-I'+str(WORK/'host-tools/usr/include'),
        '-I'+str(NATIVE/'wine-nx-probe/source'),'-I'+str(WORK/'backend/lsfg-vk-backend/include'),
        '-I'+str(WORK/'backend/lsfg-vk-common/include'),str(ROOT/'tests/lsfg_present.cpp'),
        str(NATIVE/'wine-nx-probe/source/lsfg.cpp'),str(WORK/'backend-host/liblsfg-vk.a'),
        '/usr/lib/x86_64-linux-gnu/libvulkan.so.1','/usr/lib/x86_64-linux-gnu/libxcb.so.1','-o',str(exe)],check=True)
    run_dir=WORK/'present-fixture';data=run_dir/'sdmc:/switch/sleepingdogs-fex';(data/'lsfg').mkdir(parents=True,exist_ok=True);(data/'cache').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'local/lsfg-shaders-v15/lsfg-3.1.sdp',data/'lsfg/lsfg-3.1.sdp')
    # WSLg owns the read-only filesystem socket directory. Keep this test on
    # its own abstract Unix socket, with no TCP listener or visible desktop.
    server_log=(WORK/'present-xvfb.log').open('w')
    server=subprocess.Popen(['Xvfb','-displayfd','1','-screen','0','1280x720x24',
        '-nolisten','tcp','-nolisten','unix'],stdout=subprocess.PIPE,stderr=server_log,text=True)
    try:
        assert select.select([server.stdout],[],[],10)[0], 'Xvfb startup timed out'
        display=server.stdout.readline().strip();assert display.isdecimal(), 'See present-xvfb.log'
        env=dict(os.environ,DISPLAY=':'+display,VK_ICD_FILENAMES='/usr/share/vulkan/icd.d/lvp_icd.json',
            VK_LAYER_PATH=str(WORK/'host-tools/usr/share/vulkan/explicit_layer.d'),LD_LIBRARY_PATH=str(WORK/'host-tools/usr/lib/x86_64-linux-gnu'))
        run=subprocess.run([str(exe)],cwd=run_dir,env=env,capture_output=True,text=True,timeout=120)
    finally:server.terminate();server.wait(timeout=5);server_log.close()
    (WORK/'present.log').write_text(run.stdout+run.stderr)
    print((run.stdout+run.stderr)[-16000:]);assert run.returncode==0
    write_json(ROOT/'reports/lsfg-present-check.json',dict(status='PASS',output=run.stdout,
        bridge_sha256=sha(NATIVE/'wine-nx-probe/source/lsfg.cpp'),validation_errors=0,
        hardware_tested=False,switch_performance_measured=False))

if __name__=='__main__':main()
