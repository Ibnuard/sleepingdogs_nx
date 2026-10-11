"""Preserve H4 Switch COM/game captures without treating synthetic/menu FPS as gameplay."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
BUILD='native-dxvk-h4-v2'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def analyze(mode,result,guest,runtime,dxvk):
    validation={
        'build':f'[SD-NDX-COM] BUILD {BUILD} mode=' in runtime,
        'native_device':bool(re.search(r'\[SD-NDX-COM\] D3D11CreateDevice hr=00000000 [^\n]*native=ARM64',runtime)),
        'first_present':'[SD-NDX-COM] FIRST_PRESENT real COM path' in runtime,
        'native_renderer':'DXVK: 3.1.1-sdbatch2-native-probe-v1' in dxvk and 'Build: horizon' in dxvk,
        'switch_gpu':'NVIDIA Tegra X1 (GM20B)' in dxvk and 'NVK' in dxvk,
        'no_device_lost':'VK_ERROR_DEVICE_LOST' not in dxvk,
        'no_bridge_fault':'[SD-NDX-COM] FAULT ' not in runtime and '[SD-NDX-COM] UNSUPPORTED ' not in runtime,
    }
    if mode=='com':
        validation.update({
            'com_mode':f'BUILD {BUILD} mode=COM-self-test target=' in runtime and '/sd-native-dxvk-h4-test.exe' in runtime,
            'result_pass':result.get('status')=='PASS' and result.get('stage')=='PASS' and result.get('error')==0,
            'guest_build':result.get('build')==BUILD and result.get('guest_execution') is True and result.get('com_proxy') is True,
            'guest_completed':'[SD-NDX-H4-GUEST] startup real PE32 COM client' in guest and '[SD-NDX-H4-GUEST] PASS checks=' in guest and '[SD-EXIT] code=00000000' in runtime,
            'thread_test':'[SD-NDX-H4-GUEST] guest/native multithread references and critical section' in guest,
            'buffer_readback':result.get('buffer_bytes_verified')==2048,
            'bc1_readback':result.get('mip_array_bytes_verified')==80,
            'both_720p_readbacks':result.get('pixels_verified')==1843200 and result.get('bad_pixels')==0,
            'presents':result.get('present_calls')==300 and result.get('native_draws')==302,
            'no_external_refs_or_maps':result.get('live_interfaces')==0 and result.get('live_maps')==0 and result.get('bridge_failures')==0,
            'synthetic_only':result.get('game_integration_tested') is False and result.get('game_fps_measured') is False,
        })
        completed=all(validation.values());status='PASS' if completed else 'INCOMPLETE_OR_FAILED'
    else:
        validation.update({
            'game_target':bool(re.search(r'BUILD '+BUILD+r' mode=SleepingDogs target=[^\n]*HKShip\.exe',runtime)),
            'native_selection':'[SD-NDX-COM] game selection native ARM64; LSFG OFF' in runtime,
        })
        completed=all(validation.values());status='ROUTE_OBSERVED' if completed else 'INCOMPLETE_OR_FAILED'
    windows=[]
    for line in runtime.splitlines():
        if '[SD-NDX-FPS]' not in line:continue
        values=dict(re.findall(r'(\w+)=(\d+)',line))
        intervals=int(values.get('intervals',0));elapsed=int(values.get('elapsed_us',0))
        if intervals<=0 or elapsed<=0 or 'LSFG=OFF' not in line:continue
        windows.append(dict(intervals=intervals,elapsed_us=elapsed,present_fps=intervals*1000000/elapsed,
                            mean_frame_us=int(values.get('mean_frame_us',0)),min_us=int(values.get('min_us',0)),max_us=int(values.get('max_us',0)),
                            scene_identified=False))
    return dict(status=status,mode=mode,build=BUILD,validation=validation,result=result if mode=='com' else None,
                hardware_capture_consistent=validation['native_renderer'] and validation['switch_gpu'],
                real_pe32_com_api_passed=mode=='com' and completed,game_native_present_observed=mode=='game' and completed,
                native_present_windows=windows,unknown_iids=sorted(set(re.findall(r'\[SD-NDX-COM\] UNKNOWN_IID ([^\n]+)',runtime))),
                worker_markers=[line for line in runtime.splitlines() if '[SD-NDX-WORKER]' in line],
                unsupported_or_faults=[line for line in runtime.splitlines() if '[SD-NDX-COM] UNSUPPORTED ' in line or '[SD-NDX-COM] FAULT ' in line],
                game_integration_tested=False,game_fps_measured=False,stable_30fps_proven=False,
                visual_scanout_confirmed=None,clocks_mhz=None,running_binary_authenticated=False,
                limits=['COM self-test is a synthetic client, not Sleeping Dogs FPS.',
                        'Game Present windows can include menu, loading and pause. Scene/clock matched gameplay validation remains separate.',
                        'Logs do not authenticate running binary, clocks or visible scanout.',
                        'Resource counters are bridge-owned external references/maps; they do not prove all DXVK/driver allocations are freed.'])

def main():
    parser=argparse.ArgumentParser(description=__doc__);source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--runtime-root',type=Path);source.add_argument('--log-dir',type=Path)
    parser.add_argument('--mode',choices=('com','game'),default='com');args=parser.parse_args()
    root=args.log_dir or args.runtime_root;guest_root=root if args.log_dir else root/'drive_c'
    native_root=root if args.log_dir else root/'native-dxvk-h4'
    files={'runtime':(root/'fex-runtime.log' if args.runtime_root else root/'fex-runtime.log') if args.mode=='game' else native_root/'runtime.log',
           'dxvk':native_root/'HKShip_d3d11.log'}
    if args.mode=='com':files.update(result=guest_root/'native-dxvk-h4-result.json',guest=guest_root/'native-dxvk-h4-guest.log')
    for path in files.values():
        if not path.is_file():parser.error('Missing capture file: '+str(path))
    contents={name:path.read_text(encoding='utf-8-sig',errors='replace') for name,path in files.items()}
    result=json.loads(contents['result']) if args.mode=='com' else {}
    report=analyze(args.mode,result,contents.get('guest',''),contents['runtime'],contents['dxvk'])
    tag=sha(files['runtime'])[:12];folder=ROOT/'reports'/f'native-dxvk-h4-{args.mode}-{tag}';folder.mkdir(parents=True,exist_ok=True)
    (folder/'.gitattributes').write_text('* -text\n',newline='\n');evidence={}
    for name,path in files.items():
        destination=folder/(name+('.json' if name=='result' else '.txt'))
        if destination.exists():
            if sha(destination)!=sha(path):raise RuntimeError('Immutable capture collision: '+str(destination))
        else:shutil.copyfile(path,destination)
        evidence[name]=dict(path=destination.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
    report.update(evidence=evidence,analyzer_sha256=sha(__file__))
    destination=folder.with_suffix('.json');destination.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(status=report['status'],report=str(destination),validation=report['validation']),indent=2))
    if report['status']=='INCOMPLETE_OR_FAILED':raise SystemExit(1)

if __name__=='__main__':main()
