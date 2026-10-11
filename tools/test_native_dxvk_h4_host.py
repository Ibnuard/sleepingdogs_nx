"""Validate the real native COM dispatcher on lavapipe, without claiming PE32/FEX execution."""
from pathlib import Path
import hashlib
import json
import os
import re
import select
import secrets
import socket
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    output=ROOT/'local/native-dxvk-h4-v3';output.mkdir(parents=True,exist_ok=True)
    build_receipt=ROOT/'local/native-dxvk-probe-v1/build-host.json';build=json.loads(build_receipt.read_text());library=Path(build['library'])
    assert sha(library)==build['sha256']
    source=library.parent.parent/'source';headers=library.parent.parent/'host-deps/usr/include'
    inputs=[ROOT/'tests/native_dxvk_com_host.cpp',*sorted((ROOT/'src/native_dxvk_com').glob('com_native*')),
            *[ROOT/'src/native_dxvk_com'/n for n in ('com_protocol.h','com_interfaces.h','com_methods.h','com_guids.inc','com_inheritance.inc')],ROOT/'src/native_dxvk/probe_shaders.h']
    executable=output/'h4-host-test'
    command=['g++','-O2','-std=c++17','-Wall','-Wextra','-Wno-missing-field-initializers','-DSD_COM_HOST_FAULT_TESTS',
             *['-I'+str(source/p) for p in ('include/native/windows','include/native/directx','include/native','include')],'-I'+str(headers),
             str(inputs[0]),str(ROOT/'src/native_dxvk_com/com_native.cpp'),str(library),'-ldl','-lpthread','/usr/lib/x86_64-linux-gnu/libxcb.so.1','-o',str(executable)]
    with (output/'host.compile.log').open('w') as log:compiled=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    if compiled.returncode:raise RuntimeError((output/'host.compile.log').read_text())
    display=None
    for candidate in range(91,191):
        with socket.socket() as check:
            try:check.bind(('127.0.0.1',6000+candidate))
            except OSError:continue
        display=candidate;break
    if display is None:raise RuntimeError('No free private display port')
    authority=output/'h4.Xauthority';authority.unlink(missing_ok=True);authority.touch(mode=0o600)
    subprocess.run(['xauth','-f',str(authority),'add','127.0.0.1:'+str(display),'MIT-MAGIC-COOKIE-1',secrets.token_hex(16)],check=True,capture_output=True)
    read_fd,write_fd=os.pipe();log=(output/'xvfb.log').open('w')
    xvfb=subprocess.Popen(['Xvfb',':'+str(display),'-displayfd',str(write_fd),'-screen','0','1280x720x24','-nolisten','unix','-listen','tcp','-auth',str(authority)],pass_fds=(write_fd,),stdout=log,stderr=log)
    os.close(write_fd)
    try:
        ready,_,_=select.select([read_fd],[],[],15)
        if not ready:raise RuntimeError('Private Xvfb startup timeout')
        actual=os.read(read_fd,100).decode().strip();assert actual.isdigit()
        cache=output/'host-cache';cache.mkdir(exist_ok=True);config=output/'host.conf';config.write_text('dxvk.numCompilerThreads = 2\n')
        environment=dict(os.environ,DISPLAY='127.0.0.1:'+actual,XAUTHORITY=str(authority),
                         VK_DRIVER_FILES='/usr/share/vulkan/icd.d/lvp_icd.json',VK_ICD_FILENAMES='/usr/share/vulkan/icd.d/lvp_icd.json',
                         DXVK_WSI_DRIVER='FEXTendoProbe',DXVK_LOG_PATH=str(output),DXVK_SHADER_CACHE_PATH=str(cache),DXVK_CONFIG_FILE=str(config))
        result=subprocess.run([str(executable)],cwd=output,env=environment,capture_output=True,text=True,timeout=120)
        (output/'host-stdout.log').write_text(result.stdout);(output/'host-stderr.log').write_text(result.stderr)
        if result.returncode:raise RuntimeError(result.stderr[-12000:])
        receipt=json.loads(result.stdout);driver=re.search(r'Found device: (.*)',result.stderr)
        begins=re.findall(r'\[SD-NDX-CALL\] BEGIN call=(\d+) [^\n]*name=(\w+)',result.stderr)
        ends=re.findall(r'\[SD-NDX-CALL\] END call=(\d+) [^\n]*name=(\w+)',result.stderr)
        assert begins==ends and 0<len(begins)<=128
        assert {'Map','Unmap','BindMap','Present'} <= {name for _,name in begins}
        assert result.stderr.count('[SD-NDX-CALL] startup trace complete;')==1
        receipt.update(executable_sha256=sha(executable),driver=driver.group(1) if driver else 'see DXVK log',software_vulkan=True,
                       native_dxvk_sha256=sha(library),build_receipt_sha256=sha(build_receipt),runner_sha256=sha(__file__),compile_argv=command,
                       source_files={str(p.relative_to(ROOT)):sha(p) for p in inputs},
                       allocation_rollback_cases=2,fault_injection_host_only=True,empty_update_boxes_verified=3,
                       startup_trace_pairs=len(begins),startup_trace_bounded=True,startup_trace_pairs_matched=True,
                       scope='Actual DXVK/lavapipe and low mmap; modeled Wine permission checks and host-only allocation failures; direct table entry. No PE32/FEX execution or game test.')
        (output/'host-test.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
    finally:
        os.close(read_fd);xvfb.terminate()
        try:xvfb.wait(timeout=5)
        except subprocess.TimeoutExpired:xvfb.kill();xvfb.wait()
        log.close()

if __name__=='__main__':main()
