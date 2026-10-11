"""Fail-closed capture classification; all fixtures below are SYNTHETIC text."""
from pathlib import Path
import copy
import importlib.util
import json
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('h4_analyzer',ROOT/'tools/analyze_native_dxvk_h4.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result=dict(status='PASS',stage='PASS',error=0,build='native-dxvk-h4-v7',guest_execution=True,com_proxy=True,
            buffer_bytes_verified=2048,mip_array_bytes_verified=80,pixels_verified=1843200,bad_pixels=0,
            present_calls=300,native_draws=302,live_interfaces=0,live_maps=0,bridge_failures=0,
            sampler_roundtrip_slots_verified=72,dsv_guard_checks=16,game_integration_tested=False,game_fps_measured=False)
runtime='\n'.join(['[SD-NDX-COM] BUILD native-dxvk-h4-v7 mode=COM-self-test target=/drive_c/sd-native-dxvk-h4-test.exe',
                  '[SD-NDX-COM] D3D11CreateDevice hr=00000000 device=00010001 context=00010002 feature=b000 native=ARM64',
                  '[SD-NDX-COM] FIRST_PRESENT real COM path','[SD-EXIT] code=00000000'])
guest='[SD-NDX-H4-GUEST] startup real PE32 COM client\n[SD-NDX-H4-GUEST] guest/native multithread references and critical section\n[SD-NDX-H4-GUEST] scalar DSV guards and six-stage sampler roundtrips\n[SD-NDX-H4-GUEST] PASS checks=1843200'
dxvk='DXVK: 3.1.1-sdbatch2-native-probe-v1\nBuild: horizon\nNVIDIA Tegra X1 (GM20B) NVK\nFound config file: sdmc:/switch/sleepingdogs-fex/native-dxvk-h4/com-test.conf\ndxgi.syncInterval = 1\nPresent mode: VK_PRESENT_MODE_FIFO_KHR'

def main():
    checks=0
    def expect(test):
        nonlocal checks
        checks+=1;assert test
    report=module.analyze('com',result,guest,runtime,dxvk);expect(report['status']=='PASS')
    expect(not report['stable_30fps_proven'] and not report['game_fps_measured'])
    for key in ('sampler_roundtrip_slots_verified','dsv_guard_checks'):
        altered=copy.deepcopy(result);altered.pop(key)
        expect(module.analyze('com',altered,guest,runtime,dxvk)['status']=='INCOMPLETE_OR_FAILED')
        altered[key]=1;expect(module.analyze('com',altered,guest,runtime,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    expect(module.analyze('com',result,guest.replace('scalar DSV guards and six-stage sampler roundtrips','missing'),runtime,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    for key,value in [('status','RUNNING'),('stage','startup'),('pixels_verified',921600),('bad_pixels',1),('live_maps',1),('live_interfaces',1),('bridge_failures',1),('present_calls',299),('com_proxy',False),('build','native-dxvk-h3-v1'),('build','native-dxvk-h4-v1'),('build','native-dxvk-h4-v2'),('build','native-dxvk-h4-v3')]:
        altered=copy.deepcopy(result);altered[key]=value
        expect(module.analyze('com',altered,guest,runtime,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    for altered in [runtime.replace('FIRST_PRESENT','NO_PRESENT'),runtime.replace('mode=COM-self-test','mode=SleepingDogs'),runtime.replace('code=00000000','code=00000001'),runtime+'\n[SD-NDX-COM] FAULT foo']:
        expect(module.analyze('com',result,guest,altered,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    expect(module.analyze('com',result,guest,runtime,dxvk.replace('Build: horizon','Build: host'))['status']=='INCOMPLETE_OR_FAILED')
    expect(module.analyze('com',result,'',runtime,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    game=runtime.replace('mode=COM-self-test','mode=SleepingDogs').replace('sd-native-dxvk-h4-test.exe','SleepingDogs/HKShip.exe')
    game+='\n[SD-NDX-COM] game selection native ARM64; LSFG OFF\n[SD-NDX-FPS] intervals=600 elapsed_us=10000000 mean_frame_us=16666 min_us=100 max_us=20000 LSFG=OFF'
    game_dxvk=dxvk.replace('/native-dxvk-h4/com-test.conf','/drive_c/SleepingDogs/dxvk.conf')
    report=module.analyze('game',{},'',game,game_dxvk);expect(report['status']=='ROUTE_OBSERVED');expect(report['native_present_windows'][0]['present_fps']==60)
    expect(not report['game_fps_measured'] and not report['game_integration_tested'] and not report['stable_30fps_proven'])
    expect(module.analyze('game',{},'',runtime,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    expect(module.analyze('game',{},'',game.replace('elapsed_us=10000000','elapsed_us=0'),game_dxvk)['native_present_windows']==[])
    # A game renderer log must not certify an otherwise passing COM session.
    for mode,actual_runtime,renderer in [('com',runtime,game_dxvk),('game',game,dxvk),('com',runtime,dxvk.split('Found config file:')[0])]:
        report=module.analyze(mode,result,guest,actual_runtime,renderer)
        expect(report['status']=='INCOMPLETE_OR_FAILED' and not report['validation']['renderer_log_mode_matches'])
    for renderer in [game_dxvk.replace('syncInterval = 1','syncInterval = 0'),game_dxvk.replace('FIFO_KHR','IMMEDIATE_KHR')]:
        expect(module.analyze('game',{},'',game,renderer)['status']=='INCOMPLETE_OR_FAILED')
    old_result=copy.deepcopy(result);old_result['build']='native-dxvk-h4-v2'
    expect(module.analyze('com',old_result,guest,runtime.replace('-v7','-v2'),dxvk,'native-dxvk-h4-v2')['status']=='PASS')
    v3_result=copy.deepcopy(result);v3_result['build']='native-dxvk-h4-v3'
    expect(module.analyze('com',v3_result,guest,runtime.replace('-v7','-v3'),dxvk,'native-dxvk-h4-v3')['status']=='PASS')
    expect(module.analyze('com',v3_result,guest,runtime.replace('-v7','-v3'),dxvk.replace('FIFO_KHR','IMMEDIATE_KHR'),'native-dxvk-h4-v3')['status']=='INCOMPLETE_OR_FAILED')
    v4_result=copy.deepcopy(result);v4_result['build']='native-dxvk-h4-v4'
    for key in ('sampler_roundtrip_slots_verified','dsv_guard_checks'):v4_result.pop(key)
    expect(module.analyze('com',v4_result,guest,runtime.replace('-v7','-v4'),dxvk,'native-dxvk-h4-v4')['status']=='PASS')
    expect(module.analyze('com',v4_result,guest,runtime.replace('-v7','-v4'),dxvk.replace('FIFO_KHR','IMMEDIATE_KHR'),'native-dxvk-h4-v4')['status']=='INCOMPLETE_OR_FAILED')
    v5_result=copy.deepcopy(result);v5_result['build']='native-dxvk-h4-v5'
    expect(module.analyze('com',v5_result,guest,runtime.replace('-v7','-v5'),dxvk,'native-dxvk-h4-v5')['status']=='PASS')
    v6_result=copy.deepcopy(result);v6_result['build']='native-dxvk-h4-v6'
    expect(module.analyze('com',v6_result,guest,runtime.replace('-v7','-v6'),dxvk,'native-dxvk-h4-v6')['status']=='PASS')
    v6_result.pop('dsv_guard_checks')
    expect(module.analyze('com',v6_result,guest,runtime.replace('-v7','-v6'),dxvk,'native-dxvk-h4-v6')['status']=='INCOMPLETE_OR_FAILED')
    v5_result.pop('sampler_roundtrip_slots_verified')
    expect(module.analyze('com',v5_result,guest,runtime.replace('-v7','-v5'),dxvk,'native-dxvk-h4-v5')['status']=='INCOMPLETE_OR_FAILED')
    progress=module.progress_trace('\n'.join([
        '[SD-NDX-LOG] async queue=512 batch=32',
        '[SD-NDX-PROGRESS] calls=5213 draws=2 presents=2 maps=0 refs=4753 copy_bytes=47185920 failures=0 gate_waiters=2; totals are last completed call',
        '[SD-NDX-ACTIVE] entry=5214 call=5214 thread=ff phase=execute interface=7 method=14 age_ms=30000',
        '[SD-NDX-ACTIVE] entry=5214 call=5214 thread=ff phase=idle interface=7 method=14 age_ms=60000 completed_wall_us=1000',
        '[SD-NDX-PROGRESS] snapshot busy; retry next interval',
        '[SD-NDX-LOG] dropped=12; queue full or busy',
        '[SD-NDX-LOG] dropped=3; queue full or busy']))
    expect(progress['async_logging_observed'] and progress['reported_dropped_lines']==15)
    expect(progress['snapshots'][0]['gate_waiters']==2 and progress['snapshots'][0]['presents']==2)
    expect(progress['call_states'][0]['call_in_progress'] and not progress['call_states'][1]['call_in_progress'])
    expect(progress['snapshot_busy_count']==1 and not progress['cause_confirmed'])
    begin='[SD-NDX-CALL] BEGIN call=8095 thread=ff name=Map interface=7 method=14 object=00010001 args=1,2,3'
    end='[SD-NDX-CALL] END call=8095 thread=ff name=Map ret=00000000 wall_us=1000'
    trace=module.startup_trace(begin+'\n'+end)
    expect(len(trace['completed_calls'])==1 and not trace['incomplete_calls'] and not trace['unmatched_ends'])
    trace=module.startup_trace(begin)
    expect(trace['incomplete_calls'][0]['name']=='Map' and not trace['cause_confirmed'])
    trace=module.startup_trace(begin+'\n'+end.replace('thread=ff','thread=ab'))
    expect(len(trace['incomplete_calls'])==1 and len(trace['unmatched_ends'])==1)
    expect(bool(module.startup_trace('[SD-NDX-CALL] BEGIN call=truncated')['malformed_events']))
    expect(module.startup_trace('[SD-NDX-CALL] startup trace complete;')['bounded_stop_observed'])
    with tempfile.TemporaryDirectory(prefix='h4-capture-') as temp:
        root=Path(temp);native=root/'native-dxvk-h4';native.mkdir()
        legacy=native/'HKShip_d3d11.log';actual=native/'HKShip.exe_d3d11.log'
        legacy.write_text('old');expect(module.capture_files(root,False,'com')['dxvk']==legacy)
        actual.write_text('new');expect(module.capture_files(root,False,'com')['dxvk']==actual)
        files=module.capture_files(root,False,'game');expect(files['runtime']==root/'fex-runtime.log')
        expect(module.capture_files(root,False,'com',root/'saved-com.txt')['dxvk']==root/'saved-com.txt')
        files=module.capture_files(root,True,'com');expect(files['result']==root/'native-dxvk-h4-result.json' and files['runtime']==root/'runtime.log')
    print(json.dumps(dict(status='PASS',checks=checks,fixtures='SYNTHETIC; no hardware execution',hardware_tested=False,game_fps_measured=False)))

if __name__=='__main__':main()
