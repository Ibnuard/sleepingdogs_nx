"""Run the Linux DXVK Native correctness probe on a private Xvfb/lavapipe display.

This is not a GPU performance benchmark or a test of Switch/FEX integration.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import select
import secrets
import socket
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1'))
    args = parser.parse_args()
    executable = args.work / 'build-host/sd_native_dxvk_host_probe'
    if not executable.is_file():
        parser.error('Build --target host first')
    output = ROOT / 'local/native-dxvk-probe-v1'
    output.mkdir(parents=True, exist_ok=True)
    build_receipt = output / 'build-host.json'
    build = json.loads(build_receipt.read_text())
    for name, digest in build['probe_sources'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Rebuild the host probe after changing '+name)
    if hashlib.sha256(Path(build['library']).read_bytes()).hexdigest() != build['sha256']:
        raise RuntimeError('Native archive differs from its build receipt')
    # WSLg can own /tmp/.X11-unix. Use an authenticated TCP display instead
    # of changing that shared directory or disturbing the user's X server.
    display_number = None
    for candidate in range(91, 191):
        with socket.socket() as check:
            try:
                check.bind(('127.0.0.1', 6000+candidate))
            except OSError:
                continue
        display_number = candidate
        break
    if display_number is None:
        raise RuntimeError('No free probe display port')
    authority = output / 'probe.Xauthority'
    if authority.exists():
        authority.unlink()
    authority.touch(mode=0o600)
    subprocess.run(['xauth', '-f', str(authority), 'add', '127.0.0.1:'+str(display_number),
                    'MIT-MAGIC-COOKIE-1', secrets.token_hex(16)], check=True, capture_output=True)
    read_fd, write_fd = os.pipe()
    display_log = (output / 'xvfb.log').open('w')
    xvfb = subprocess.Popen(['Xvfb', ':'+str(display_number), '-displayfd', str(write_fd), '-screen', '0',
                             '1280x720x24', '-nolisten', 'unix', '-listen', 'tcp', '-auth', str(authority)], pass_fds=(write_fd,),
                            stdout=display_log, stderr=display_log)
    os.close(write_fd)
    try:
        ready, _, _ = select.select([read_fd], [], [], 15)
        if not ready:
            raise RuntimeError('Xvfb did not start within 15 seconds')
        display = os.read(read_fd, 100).decode().strip()
        if not display.isdigit():
            raise RuntimeError('Xvfb did not return a display number')
        environment = dict(os.environ, DISPLAY='127.0.0.1:'+display, XAUTHORITY=str(authority),
                           VK_DRIVER_FILES='/usr/share/vulkan/icd.d/lvp_icd.json',
                           VK_ICD_FILENAMES='/usr/share/vulkan/icd.d/lvp_icd.json',
                           DXVK_WSI_DRIVER='FEXTendoProbe', DXVK_LOG_PATH=str(output),
                           DXVK_STATE_CACHE_PATH=str(output),
                           DXVK_CONFIG_FILE=str(output/'probe.conf'))
        (output/'probe.conf').write_text('# Isolated probe; no game overrides.\n')
        result = subprocess.run([str(executable)], cwd=output, env=environment,
                                capture_output=True, text=True, timeout=120)
        (output/'host-stdout.log').write_text(result.stdout)
        (output/'host-stderr.log').write_text(result.stderr)
        if result.returncode:
            print(result.stderr[-14000:])
            raise RuntimeError(f'Native probe failed with exit code {result.returncode}')
        receipt = json.loads(result.stdout)
        receipt['executable_sha256'] = hashlib.sha256(executable.read_bytes()).hexdigest()
        driver = re.search(r'Found device: (.*)', result.stderr)
        receipt['driver'] = driver.group(1) if driver else 'unavailable; inspect DXVK log'
        receipt['software_vulkan'] = True
        receipt['stderr_sha256'] = hashlib.sha256(result.stderr.encode()).hexdigest()
        receipt['build_receipt_sha256'] = hashlib.sha256(build_receipt.read_bytes()).hexdigest()
        receipt['runner_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (output/'host-test.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt,indent=2))
    finally:
        os.close(read_fd)
        xvfb.terminate()
        try:
            xvfb.wait(timeout=5)
        except subprocess.TimeoutExpired:
            xvfb.kill(); xvfb.wait()
        display_log.close()


if __name__ == '__main__':
    main()
