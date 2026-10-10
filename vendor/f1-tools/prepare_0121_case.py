"""Freeze the reported Career run and prepare isolated 0.1.21 build scripts."""
from pathlib import Path
import hashlib, json, shutil

root = Path(__file__).resolve().parents[1]
case = root / 'debug/0.1.20-thread-memory'
case.mkdir(exist_ok=False)
log = Path('C:/Users/Administrator/Pictures/pesnx/SS/fex-runtime.log')
shutil.copy2(log, case/'fex-runtime.log')
data = log.read_bytes()
evidence = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), build='0.1.20',
    mode='Career (confirmed by user)', fex_mode='fastest', dxvk='3.1.1-f1mem1',
    failed_native_stack_bytes=1048576, native_result='00000559', guest_result='c0000017',
    failed_guest_worker='00cae1b0', free_threads=145, heap_available_at_failure=62741296,
    graphics='1280x720 fullscreen, LOD2; user confirms no manual resolution change',
    guest_process_exited=False, later_vulkan_scratch_recovery_bytes=16777216,
    grand_prix='User reports crash persists; current SS/crash.log is older build 0.1.16, not paired with this run.')
(case/'hardware-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
old = root/'debug/0.1.19-restart-memory'
for name in ('build_0120.py','check_native.py','check_relaunch.py','check_ui.py',
             'native_links_0120.py','package_0120.py','sync_inputs.py','render_previews.py'):
    s = (old/name).read_text()
    s = s.replace('0.1.19-restart-memory', '0.1.20-thread-memory')
    s = s.replace('f1-fex-restart-memory-final', 'f1-fex-thread-memory')
    s = s.replace('0.1.20', '0.1.21').replace('0120', '0121')
    # The case describes the incoming 0.1.20 log, not the outgoing release.
    s = s.replace('debug/0.1.21-thread-memory', 'debug/0.1.20-thread-memory')
    s = s.replace('circuit-memory-v2.txt','circuit-memory-v3.txt')
    s = s.replace('0.1.21-restart-memory','0.1.21-thread-memory')
    s = s.replace('f1-fex-update-0.1.19', 'f1-fex-update-0.1.20')
    s = s.replace('bd105787e0c5b1dac11866a1da9e4c071d7d351995e8653c2de72ae8eb90267e',
                  'ddfd53a8f4fe9a3366c39e0be6ba56c441d6ed0c4f91da3ae99eee6fc449d272')
    (case/name.replace('0120','0121')).write_text(s,encoding='utf-8',newline='\n')
shutil.copy2(old/'hardware_settings_config.xml',case/'hardware_settings_config.xml')
# Reuse unchanged rendered launcher assets as inputs for the actual C UI test.
shutil.copytree(old/'ui-assets', case/'ui-assets')
for name in ('f1_overlay.py','f1_crash.c','build_launcher.py'):
    p = root/'tools'/name
    s = p.read_text().replace('0.1.20-restart-memory','0.1.21-thread-memory').replace('0.1.20','0.1.21')
    p.write_text(s,encoding='utf-8',newline='\n')
print(json.dumps(evidence,indent=2))
