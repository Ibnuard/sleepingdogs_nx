"""Validate and preserve a supplied H2 Switch capture; never execute log text."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--runtime-root',type=Path,help='Copied switch/sleepingdogs-fex folder')
    source.add_argument('--log-dir',type=Path,help='Flat folder containing the four copied H2 files')
    args=parser.parse_args()
    if args.log_dir:
        root=args.log_dir
        files={'result':root/'native-dxvk-h2-result.json',
               'guest':root/'native-dxvk-h2-guest.log',
               'runtime':root/'runtime.log',
               'dxvk':root/'sd-dxvk-native-probe_d3d11.log'}
    else:
        root=args.runtime_root
        files={'result':root/'drive_c/native-dxvk-h2-result.json',
               'guest':root/'drive_c/native-dxvk-h2-guest.log',
               'runtime':root/'native-dxvk-h2/runtime.log',
               'dxvk':root/'native-dxvk-h2/sd-dxvk-native-probe_d3d11.log'}
    for p in files.values():assert p.is_file(), ('capture file missing',str(p))
    result=json.loads(files['result'].read_text(encoding='utf-8-sig'))
    guest=files['guest'].read_text(errors='replace');runtime=files['runtime'].read_text(errors='replace');dxvk=files['dxvk'].read_text(errors='replace')
    checks={
        'result_pass':result.get('status')=='PASS' and result.get('stage')=='PASS',
        'build':result.get('build')=='native-dxvk-h2-v1' and '[SD-NDX-H2] BUILD native-dxvk-h2-v1' in runtime,
        'guest_target':'/sd-native-dxvk-guest.exe' in runtime,
        'guest_completed':'[SD-NDX-H2-GUEST] PASS arena=' in guest,
        'guest_exit_zero':'[SD-EXIT] code=00000000' in runtime,
        'guest_execution':result.get('guest_execution') is True,
        'no_game_claim':result.get('game_integration') is False and result.get('game_fps_measured') is False and result.get('present_calls')==0,
        'buffer_readback':result.get('buffer_bytes_verified')==1024,
        '720p_readback':result.get('draw_pixels_verified')==921600 and result.get('bad_pixels')==0,
        'native_device':'[SD-NDX-H2] DEVICE value=0x00000000' in runtime,
        'native_closed':runtime.count('[SD-NDX-H2] CLOSE value=')==2,
        'actual_gpu':'NVIDIA Tegra X1 (GM20B)' in dxvk and 'NVK' in dxvk,
        'native_version':'DXVK: 3.1.1-sdbatch2-native-probe-v1' in dxvk and 'Build: horizon' in dxvk,
        'no_device_lost':'VK_ERROR_DEVICE_LOST' not in dxvk,
        'two_native_generations':'CLOSE value=0x00000001' in runtime and 'CLOSE value=0x00000002' in runtime,
        'expected_call_count':result.get('checks')==1096 and result.get('bridge_calls')==35 and result.get('rejected_requests')==5,
    }
    arenas=re.findall(r'INIT guest/native shared arena value=0x([0-9a-f]+)',runtime)
    checks['guest_native_arena_match']=bool(arenas) and all(int(a,16)==result.get('guest_arena') for a in arenas)
    status='PASS' if all(checks.values()) else 'INCOMPLETE_OR_FAILED'
    tag=sha(files['runtime'])[:12];folder=ROOT/'reports'/('native-dxvk-h2-'+tag);folder.mkdir(parents=True,exist_ok=True)
    (folder/'.gitattributes').write_text('* -text\n',newline='\n')
    evidence={}
    for name,p in files.items():
        dst=folder/(name+('.json' if name=='result' else '.txt'))
        if dst.exists():assert sha(dst)==sha(p), 'immutable capture collision'
        else:shutil.copyfile(p,dst)
        evidence[name]=dict(path=str(dst.relative_to(ROOT)).replace('\\','/'),sha256=sha(p),bytes=p.stat().st_size)
    allocator=re.search(r'\[FEX3-GPUARENA\] final[^\n]*',runtime)
    if not allocator:
        allocator=re.search(r'[^\n]*capacity=268435456[^\n]*used=0[^\n]*live=0[^\n]*',runtime)
    report=dict(status=status,build='native-dxvk-h2-v1',validation=checks,result=result,evidence=evidence,
                hardware_tested=status=='PASS',real_pe32_guest_bridge_passed=status=='PASS',game_integration=False,game_fps_measured=False,
                guest_arena_hex='0x%08x'%result.get('guest_arena',0),
                shader_cache_created='Created cache file:' in dxvk,
                gpu_allocator_cleanup_line=allocator.group(0) if allocator else None,
                expected_hresult_rejections={'80004001':'Offscreen swapchain is deliberately unsupported.',
                                             '80070057':'Stale resource token is deliberately rejected.'},
                clocks_mhz=None,analyzer_sha256=sha(__file__),limits=['Offscreen bounded API subset; no COM proxy or game.',
                'Shadow copies and full-arena page checks are diagnostic, not optimized.',
                'Logs identify H2 but do not authenticate a running binary hash.'])
    destination=ROOT/'reports'/('native-dxvk-h2-'+tag+'.json');destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=status,report=str(destination),validation=checks),indent=2))
    if status!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
