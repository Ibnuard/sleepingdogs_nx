"""Validate/preserve supplied H3 Switch logs; no game FPS or scanout claim."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--runtime-root',type=Path,help='Copied switch/sleepingdogs-fex folder')
    source.add_argument('--log-dir',type=Path,help='Flat folder containing the four H3 files')
    args=parser.parse_args()
    root=args.log_dir or args.runtime_root
    guest_root=root if args.log_dir else root/'drive_c'
    native_root=root if args.log_dir else root/'native-dxvk-h3'
    files={'result':guest_root/'native-dxvk-h3-result.json',
           'guest':guest_root/'native-dxvk-h3-guest.log',
           'runtime':native_root/'runtime.log',
           'dxvk':native_root/'sd-dxvk-native-probe_d3d11.log'}
    for path in files.values():
        if not path.is_file():parser.error('Missing capture file: '+str(path))
    result=json.loads(files['result'].read_text(encoding='utf-8-sig'))
    guest=files['guest'].read_text(errors='replace')
    runtime=files['runtime'].read_text(errors='replace')
    dxvk=files['dxvk'].read_text(errors='replace')
    arenas=re.findall(r'INIT guest/native shared arena value=0x([0-9a-f]+)',runtime)
    validation={
        'result_pass':result.get('status')=='PASS' and result.get('stage')=='PASS' and result.get('error')==0,
        'build':result.get('build')=='native-dxvk-h3-v1' and '[SD-NDX-H3] BUILD native-dxvk-h3-v1' in runtime,
        'actual_guest':'/sd-native-dxvk-h3-guest.exe' in runtime and result.get('guest_execution') is True,
        'guest_completed':'[SD-NDX-H3-GUEST] PASS arena=' in guest and '[SD-EXIT] code=00000000' in runtime,
        'native_device':'[SD-NDX-H3] DEVICE value=0x00000000' in runtime,
        'trusted_window':'[SD-NDX-H3] trusted NWindow=' in runtime and 'console framebuffer released; no guest HWND' in runtime,
        'arena_match':len(arenas)==2 and all(int(value,16)==result.get('guest_arena') for value in arenas),
        'buffer_readback':result.get('buffer_bytes_verified')==1024,
        'offscreen_readback':result.get('draw_pixels_verified')==921600 and result.get('bad_pixels')==0,
        'backbuffer_readback':result.get('backbuffer_pixels_verified')==921600,
        'native_presents':result.get('present_calls')==300 and bool(re.search(r'\[SD-NDX-H3\] PRESENT value=0x00000000[^\n]*presents=300 ',runtime)),
        'present_timing':isinstance(result.get('present_elapsed_us'),int) and 0<result['present_elapsed_us']<0xffffffff,
        'payload_checks_retained':result.get('full_arena_scans')==11,
        'negative_tests':result.get('rejected_requests')==7,
        'native_closed':runtime.count('[SD-NDX-H3] CLOSE value=')==2 and '[SD-NDX-H3] EXIT cleanup' not in runtime,
        'native_renderer':'DXVK: 3.1.1-sdbatch2-native-probe-v1' in dxvk and 'Build: horizon' in dxvk,
        'actual_gpu':'NVIDIA Tegra X1 (GM20B)' in dxvk and 'NVK' in dxvk,
        'no_device_lost':'VK_ERROR_DEVICE_LOST' not in dxvk,
        'no_game_claim':result.get('game_integration') is False and result.get('game_fps_measured') is False and result.get('com_proxy') is False,
    }
    status='PASS' if all(validation.values()) else 'INCOMPLETE_OR_FAILED'
    tag=sha(files['runtime'])[:12]
    folder=ROOT/'reports'/('native-dxvk-h3-'+tag);folder.mkdir(parents=True,exist_ok=True)
    (folder/'.gitattributes').write_text('* -text\n',newline='\n')
    evidence={}
    for name,path in files.items():
        destination=folder/(name+('.json' if name=='result' else '.txt'))
        if destination.exists():
            if sha(destination)!=sha(path):raise RuntimeError('Immutable capture collision: '+str(destination))
        else:shutil.copyfile(path,destination)
        evidence[name]=dict(path=str(destination.relative_to(ROOT)).replace('\\','/'),sha256=sha(path),bytes=path.stat().st_size)
    report=dict(status=status,build='native-dxvk-h3-v1',validation=validation,result=result,evidence=evidence,
                hardware_tested=status=='PASS',real_pe32_native_present_api_passed=status=='PASS',
                visual_scanout_confirmed=None,clocks_mhz=None,game_integration=False,game_fps_measured=False,
                analyzer_sha256=sha(__file__),limits=[
                    'Synthetic bounded packet subset, not COM/game integration.',
                    'API success and backbuffer readback do not authenticate visible scanout; report blue-screen observation separately.',
                    'Native dispatch includes readback/waits; it is not a GPU timestamp.',
                    'Single controlled arena owner; no concurrent unmap or production mapping guarantee.',
                    'Clocks and running binary hash are not authenticated by these logs.'])
    destination=ROOT/'reports'/('native-dxvk-h3-'+tag+'.json')
    destination.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(status=status,report=str(destination),validation=validation),indent=2))
    if status!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
