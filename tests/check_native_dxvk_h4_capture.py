"""Fail-closed capture classification; all fixtures below are SYNTHETIC text."""
from pathlib import Path
import copy
import importlib.util
import json

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('h4_analyzer',ROOT/'tools/analyze_native_dxvk_h4.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
result=dict(status='PASS',stage='PASS',error=0,build='native-dxvk-h4-v2',guest_execution=True,com_proxy=True,
            buffer_bytes_verified=2048,mip_array_bytes_verified=80,pixels_verified=1843200,bad_pixels=0,
            present_calls=300,native_draws=302,live_interfaces=0,live_maps=0,bridge_failures=0,
            game_integration_tested=False,game_fps_measured=False)
runtime='\n'.join(['[SD-NDX-COM] BUILD native-dxvk-h4-v2 mode=COM-self-test target=/drive_c/sd-native-dxvk-h4-test.exe',
                  '[SD-NDX-COM] D3D11CreateDevice hr=00000000 device=00010001 context=00010002 feature=b000 native=ARM64',
                  '[SD-NDX-COM] FIRST_PRESENT real COM path','[SD-EXIT] code=00000000'])
guest='[SD-NDX-H4-GUEST] startup real PE32 COM client\n[SD-NDX-H4-GUEST] guest/native multithread references and critical section\n[SD-NDX-H4-GUEST] PASS checks=1843200'
dxvk='DXVK: 3.1.1-sdbatch2-native-probe-v1\nBuild: horizon\nNVIDIA Tegra X1 (GM20B) NVK'

def main():
    checks=0
    def expect(test):
        nonlocal checks
        checks+=1;assert test
    report=module.analyze('com',result,guest,runtime,dxvk);expect(report['status']=='PASS')
    expect(not report['stable_30fps_proven'] and not report['game_fps_measured'])
    for key,value in [('status','RUNNING'),('stage','startup'),('pixels_verified',921600),('bad_pixels',1),('live_maps',1),('live_interfaces',1),('bridge_failures',1),('present_calls',299),('com_proxy',False),('build','native-dxvk-h3-v1'),('build','native-dxvk-h4-v1')]:
        altered=copy.deepcopy(result);altered[key]=value
        expect(module.analyze('com',altered,guest,runtime,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    for altered in [runtime.replace('FIRST_PRESENT','NO_PRESENT'),runtime.replace('mode=COM-self-test','mode=SleepingDogs'),runtime.replace('code=00000000','code=00000001'),runtime+'\n[SD-NDX-COM] FAULT foo']:
        expect(module.analyze('com',result,guest,altered,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    expect(module.analyze('com',result,guest,runtime,dxvk.replace('Build: horizon','Build: host'))['status']=='INCOMPLETE_OR_FAILED')
    expect(module.analyze('com',result,'',runtime,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    game=runtime.replace('mode=COM-self-test','mode=SleepingDogs').replace('sd-native-dxvk-h4-test.exe','SleepingDogs/HKShip.exe')
    game+='\n[SD-NDX-COM] game selection native ARM64; LSFG OFF\n[SD-NDX-FPS] intervals=600 elapsed_us=10000000 mean_frame_us=16666 min_us=100 max_us=20000 LSFG=OFF'
    report=module.analyze('game',{},'',game,dxvk);expect(report['status']=='ROUTE_OBSERVED');expect(report['native_present_windows'][0]['present_fps']==60)
    expect(not report['game_fps_measured'] and not report['game_integration_tested'] and not report['stable_30fps_proven'])
    expect(module.analyze('game',{},'',runtime,dxvk)['status']=='INCOMPLETE_OR_FAILED')
    expect(module.analyze('game',{},'',game.replace('elapsed_us=10000000','elapsed_us=0'),dxvk)['native_present_windows']==[])
    print(json.dumps(dict(status='PASS',checks=checks,fixtures='SYNTHETIC; no hardware execution',hardware_tested=False,game_fps_measured=False)))

if __name__=='__main__':main()
