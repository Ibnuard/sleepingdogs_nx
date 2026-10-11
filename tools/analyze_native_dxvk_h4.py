"""Preserve H4 Switch COM/game captures without treating synthetic/menu FPS as gameplay."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
BUILD='native-dxvk-h4-v8'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def startup_trace(runtime):
    pending={};completed=[];unmatched=[];malformed=[];begins=0
    for line in runtime.splitlines():
        match=re.search(r'\[SD-NDX-CALL\] (BEGIN|END) (.*)',line)
        if not match:continue
        values=dict(re.findall(r'(\w+)=([^\s]+)',match[2]))
        if not values.get('call','').isdigit() or not values.get('thread') or not values.get('name'):
            malformed.append(line);continue
        values['call']=int(values['call']);key=(values['call'],values['thread'],values['name'])
        if match[1]=='BEGIN':
            begins+=1
            if key in pending:malformed.append(line)
            pending[key]=values
        elif key in pending:completed.append(dict(begin=pending.pop(key),end=values))
        else:unmatched.append(values)
    return dict(begin_count=begins,completed_calls=completed,incomplete_calls=list(pending.values()),
                unmatched_ends=unmatched,malformed_events=malformed,
                bounded_stop_observed='[SD-NDX-CALL] startup trace complete;' in runtime,
                cause_confirmed=False,
                limits='Missing END means no completion was captured, not proof of deadlock. V4 queued logging can drop events or lose its tail on forced restart. Wall time includes scheduling and logging (synchronous SD I/O in v3), not GPU time. Startup trace begins after packet validation and bridge lock acquisition.')

def progress_trace(runtime):
    snapshots=[];active=[];drops=[];busy=0
    for line in runtime.splitlines():
        if '[SD-NDX-PROGRESS] snapshot busy' in line:busy+=1
        elif '[SD-NDX-PROGRESS]' in line:
            values={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
            if 'calls' in values:snapshots.append(values)
        elif '[SD-NDX-ACTIVE]' in line:
            values=dict(re.findall(r'(\w+)=([^\s]+)',line))
            # Idle describes the last completed call, never a hung active call.
            values['call_in_progress']=values.get('phase') in ('validate','execute','result-copy')
            active.append(values)
        elif '[SD-NDX-LOG] dropped=' in line:
            match=re.search(r'\bdropped=(\d+)',line)
            if match:drops.append(int(match[1]))
    return dict(snapshots=snapshots,call_states=active,snapshot_busy_count=busy,
                reported_dropped_lines=sum(drops),async_logging_observed='[SD-NDX-LOG] async queue=' in runtime,
                cause_confirmed=False,
                limits='Snapshots never acquire the COM gate. V6 samples ordinary calls every 256 entries; critical calls and failures retain detailed state. Totals describe the last sampled completion and idle is not proof that another unsampled call is idle. Missing snapshots may mean scheduling/I/O delay or lost queued output. These are not GPU timings.')

def capture_files(root,flat,mode,dxvk_override=None):
    guest_root=root if flat else root/'drive_c';native_root=root if flat else root/'native-dxvk-h4'
    # DXVK uses the full executable basename. Retain the older name for archives.
    candidates=[native_root/'HKShip.exe_d3d11.log',native_root/'HKShip_d3d11.log']
    renderer=dxvk_override or next((path for path in candidates if path.is_file()),candidates[0])
    files={'runtime':root/'fex-runtime.log' if mode=='game' else native_root/'runtime.log','dxvk':renderer}
    if mode=='com':files.update(result=guest_root/'native-dxvk-h4-result.json',guest=guest_root/'native-dxvk-h4-guest.log')
    return files

def analyze(mode,result,guest,runtime,dxvk,expected_build=BUILD):
    configs=re.findall(r'Found config file:\s*([^\r\n]+)',dxvk)
    expected_config='/native-dxvk-h4/com-test.conf' if mode=='com' else '/drive_c/sleepingdogs/dxvk.conf'
    config_modes_match=bool(configs) and all(path.strip().replace('\\','/').lower().endswith(expected_config) for path in configs)
    validation={
        'build':f'[SD-NDX-COM] BUILD {expected_build} mode=' in runtime,
        'native_device':bool(re.search(r'\[SD-NDX-COM\] D3D11CreateDevice hr=00000000 [^\n]*native=ARM64',runtime)),
        'first_present':'[SD-NDX-COM] FIRST_PRESENT real COM path' in runtime,
        'native_renderer':'DXVK: 3.1.1-sdbatch2-native-probe-v1' in dxvk and 'Build: horizon' in dxvk,
        'switch_gpu':'NVIDIA Tegra X1 (GM20B)' in dxvk and 'NVK' in dxvk,
        'no_device_lost':'VK_ERROR_DEVICE_LOST' not in dxvk,
        'no_bridge_fault':'[SD-NDX-COM] FAULT ' not in runtime and '[SD-NDX-COM] UNSUPPORTED ' not in runtime,
        'renderer_log_mode_matches':config_modes_match,
    }
    if expected_build in ('native-dxvk-h4-v3','native-dxvk-h4-v4','native-dxvk-h4-v5','native-dxvk-h4-v6','native-dxvk-h4-v7',BUILD):
        validation.update(native_fifo_requested=bool(re.search(r'\bdxgi\.syncInterval\s*=\s*1\s*$',dxvk,re.M)),
                          fifo_present='VK_PRESENT_MODE_FIFO_KHR' in dxvk)
    if mode=='com':
        validation.update({
            'com_mode':f'BUILD {expected_build} mode=COM-self-test target=' in runtime and '/sd-native-dxvk-h4-test.exe' in runtime,
            'result_pass':result.get('status')=='PASS' and result.get('stage')=='PASS' and result.get('error')==0,
            'guest_build':result.get('build')==expected_build and result.get('guest_execution') is True and result.get('com_proxy') is True,
            'guest_completed':'[SD-NDX-H4-GUEST] startup real PE32 COM client' in guest and '[SD-NDX-H4-GUEST] PASS checks=' in guest and '[SD-EXIT] code=00000000' in runtime,
            'thread_test':'[SD-NDX-H4-GUEST] guest/native multithread references and critical section' in guest,
            'buffer_readback':result.get('buffer_bytes_verified')==2048,
            'bc1_readback':result.get('mip_array_bytes_verified')==80,
            'both_720p_readbacks':result.get('pixels_verified')==1843200 and result.get('bad_pixels')==0,
            'presents':result.get('present_calls')==300 and result.get('native_draws')==302,
            'no_external_refs_or_maps':result.get('live_interfaces')==0 and result.get('live_maps')==0 and result.get('bridge_failures')==0,
            'synthetic_only':result.get('game_integration_tested') is False and result.get('game_fps_measured') is False,
        })
        if expected_build in ('native-dxvk-h4-v5','native-dxvk-h4-v6','native-dxvk-h4-v7',BUILD):
            validation.update(sampler_roundtrip_slots=result.get('sampler_roundtrip_slots_verified')==72,
                              scalar_dsv_guards=result.get('dsv_guard_checks')==16,
                              com_output_stage='[SD-NDX-H4-GUEST] scalar DSV guards and six-stage sampler roundtrips' in guest)
        completed=all(validation.values());status='PASS' if completed else 'INCOMPLETE_OR_FAILED'
    else:
        validation.update({
            'game_target':bool(re.search(r'BUILD '+re.escape(expected_build)+r' mode=SleepingDogs target=[^\n]*HKShip\.exe',runtime)),
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
    return dict(status=status,mode=mode,build=expected_build,validation=validation,result=result if mode=='com' else None,
                hardware_capture_consistent=validation['native_renderer'] and validation['switch_gpu'] and config_modes_match,
                real_pe32_com_api_passed=mode=='com' and completed,game_native_present_observed=mode=='game' and completed,
                renderer_config_paths=configs,startup_trace=startup_trace(runtime),progress_trace=progress_trace(runtime),same_session_authenticated=False,
                native_present_windows=windows,unknown_iids=sorted(set(re.findall(r'\[SD-NDX-COM\] UNKNOWN_IID ([^\n]+)',runtime))),
                worker_markers=[line for line in runtime.splitlines() if '[SD-NDX-WORKER]' in line],
                unsupported_or_faults=[line for line in runtime.splitlines() if '[SD-NDX-COM] UNSUPPORTED ' in line or '[SD-NDX-COM] FAULT ' in line],
                game_integration_tested=False,game_fps_measured=False,stable_30fps_proven=False,
                visual_scanout_confirmed=None,clocks_mhz=None,running_binary_authenticated=False,
                limits=['COM self-test is a synthetic client, not Sleeping Dogs FPS.',
                        'Game Present windows can include menu, loading and pause. Scene/clock matched gameplay validation remains separate.',
                        'Logs do not authenticate running binary, clocks or visible scanout.',
                        'Renderer config must match COM/game mode. This rejects a game log overwriting COM output but does not authenticate an exact session. Save COM logs before launching the game.',
                        'Resource counters are bridge-owned external references/maps; they do not prove all DXVK/driver allocations are freed.'])

def main():
    parser=argparse.ArgumentParser(description=__doc__);source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--runtime-root',type=Path);source.add_argument('--log-dir',type=Path)
    parser.add_argument('--mode',choices=('com','game'),default='com')
    parser.add_argument('--expected-build',choices=('native-dxvk-h4-v2','native-dxvk-h4-v3','native-dxvk-h4-v4','native-dxvk-h4-v5','native-dxvk-h4-v6','native-dxvk-h4-v7',BUILD),default=BUILD)
    parser.add_argument('--dxvk-log',type=Path,help='Preserved renderer log from this COM/game session')
    args=parser.parse_args()
    files=capture_files(args.log_dir or args.runtime_root,bool(args.log_dir),args.mode,args.dxvk_log)
    for path in files.values():
        if not path.is_file():parser.error('Missing capture file: '+str(path))
    contents={name:path.read_text(encoding='utf-8-sig',errors='replace') for name,path in files.items()}
    result=json.loads(contents['result']) if args.mode=='com' else {}
    report=analyze(args.mode,result,contents.get('guest',''),contents['runtime'],contents['dxvk'],args.expected_build)
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
