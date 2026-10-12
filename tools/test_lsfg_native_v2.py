"""Execute native loader -> OSK -> LSFG -> raw Vulkan under validation."""
from pathlib import Path
import hashlib,json,os,select,shutil,subprocess
from launcher_v2_overlay import ROOT,SOURCE,replace
from build_launcher_v2 import WORK,LOCAL

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    old=Path('/home/blekjek/sleepingdogs-lsfg-v15');native=old/'native-source/wine-nx-probe/source'
    program=(ROOT/'tests/lsfg_present.cpp').read_text()
    program=replace(program,'#include "lsfg_config.h"','#include "lsfg_config.h"\n#include "lsfg_vulkan.h"\nextern "C" {\n#include "pes13/fextendo_osk_frame.h"\n}')
    program=replace(program,'int main() {',r'''
extern "C" PFN_vkVoidFunction __wrap_vkGetInstanceProcAddr(VkInstance,const char*);
extern "C" PFN_vkVoidFunction __wrap_vkGetDeviceProcAddr(VkDevice,const char*);
static unsigned osk_present_calls;
extern "C" void sd_keyboard_present_gate(void){osk_present_calls++;}
extern "C" int fx_osk_frame_visible(void){return 0;}
extern "C" int fx_osk_frame_get(int,int,fx_osk_frame*){return 0;}
extern "C" int fx_osk_frame_copy(const fx_osk_frame*,void*,int,int){return 0;}
extern "C" void fx_osk_frame_presented(uint64_t){}
extern "C" void fx_osk_frame_reject(uint64_t){}
static VkInstance test_instance;
#define NATIVE(name) reinterpret_cast<PFN_##name>(__wrap_vkGetInstanceProcAddr(test_instance,#name))
#define vkEnumeratePhysicalDevices NATIVE(vkEnumeratePhysicalDevices)
#define vkCreateDevice NATIVE(vkCreateDevice)
#define vkDestroyDevice NATIVE(vkDestroyDevice)
#define vkGetDeviceQueue NATIVE(vkGetDeviceQueue)
#define vkCreateSwapchainKHR NATIVE(vkCreateSwapchainKHR)
#define vkDestroySwapchainKHR NATIVE(vkDestroySwapchainKHR)
#define vkAcquireNextImageKHR NATIVE(vkAcquireNextImageKHR)
#define vkQueuePresentKHR NATIVE(vkQueuePresentKHR)
int main() {
''')
    program=replace(program,'VkInstance instance;check(vkCreateInstance(&ci,nullptr,&instance));',
                    'VkInstance instance;check(vkCreateInstance(&ci,nullptr,&instance));test_instance=instance;sd_lsfg_native_configure(1);')
    program=replace(program,'wine_nx_lsfg_configure(1,1,1);wine_nx_lsfg_device_features(instance,gpu,&features,&v12);','wine_nx_lsfg_configure(1,1,1);')
    program=replace(program,'            bool prepared=wine_nx_lsfg_prepare_swapchain(instance,gpu,&sc);if(prepared!=(test!=0))throw std::runtime_error("Unexpected prepare result");','')
    program=replace(program,'            auto* state=prepared?wine_nx_lsfg_create(instance,gpu,device,swapchain,&sc):nullptr;\n            if(prepared&&!state)throw std::runtime_error("Bridge did not create state");','')
    program=replace(program,'                VkResult result;int handled=wine_nx_lsfg_present(state,queue,family,true,&pi,&result);\n                if(handled!=(test!=0))throw std::runtime_error("Unexpected LSFG bypass");\n                if(!handled)result=vkQueuePresentKHR(queue,&pi);check(result);check(vkQueueWaitIdle(queue));',
                    '                check(vkQueuePresentKHR(queue,&pi));check(vkQueueWaitIdle(queue));')
    program=replace(program,'            wine_nx_lsfg_destroy(state);check(vkDeviceWaitIdle(device));','            check(vkDeviceWaitIdle(device));')
    # Both instance and device proc loaders must resolve to the native route.
    program=replace(program,'VkDevice device;check(vkCreateDevice(gpu,&dc,nullptr,&device));',
                    'VkDevice device;check(vkCreateDevice(gpu,&dc,nullptr,&device));if(__wrap_vkGetDeviceProcAddr(device,"vkQueuePresentKHR")!=__wrap_vkGetInstanceProcAddr(instance,"vkQueuePresentKHR"))throw std::runtime_error("Loader paths differ");')
    program=program.replace('PASS: production bridge;','PASS: real native host-loader + OSK + LSFG bridge;')
    program=replace(program,'for(unsigned test=0;test<3;++test){','for(unsigned test=0;test<4;++test){\n            bool wine_mode=test==3;sd_lsfg_native_configure(!wine_mode);osk_present_calls=0;')
    program=replace(program,'            auto previous=swapchain;',
                    '            if(wine_mode&&!wine_nx_lsfg_prepare_swapchain(instance,gpu,&sc))throw std::runtime_error("Wine preparation failed");\n            auto previous=swapchain;')
    program=replace(program,'            VkSemaphoreCreateInfo semInfo',
                    '            auto* wine_state=wine_mode?wine_nx_lsfg_create(instance,gpu,device,swapchain,&sc):nullptr;\n            VkSemaphoreCreateInfo semInfo')
    program=replace(program,'                check(vkQueuePresentKHR(queue,&pi));check(vkQueueWaitIdle(queue));',
                    '                VkResult result;\n                if(!wine_mode||!wine_nx_lsfg_present(wine_state,queue,family,true,&pi,&result))result=vkQueuePresentKHR(queue,&pi);\n                check(result);check(vkQueueWaitIdle(queue));')
    program=replace(program,'            for(auto sem:ready)',
                    '            if(osk_present_calls!=(wine_mode?14u:8u))throw std::runtime_error("Keyboard present hook missing/recursive");\n            wine_nx_lsfg_destroy(wine_state);\n            for(auto sem:ready)')
    program=program.replace('generated_sessions!=2','generated_sessions!=3')
    path=WORK/'tests/lsfg-native.cpp';path.parent.mkdir(exist_ok=True);path.write_text(program)
    exe=WORK/'tests/lsfg-native'
    cmd=['g++','-std=c++20','-O2','-I'+str(ROOT/'tests'),'-I'+str(SOURCE),'-I'+str(native),
        '-I'+str(old/'host-tools/usr/include'),'-I/home/blekjek/pes13-build/mesa-switch/include',
        '-I'+str(old/'backend/lsfg-vk-backend/include'),'-I'+str(old/'backend/lsfg-vk-common/include'),
        str(path),str(WORK/'source/osk.cpp'),str(WORK/'source/lsfg.cpp'),str(SOURCE/'lsfg_vulkan.cpp'),
        str(old/'backend-host/liblsfg-vk.a'),'/usr/lib/x86_64-linux-gnu/libvulkan.so.1','/usr/lib/x86_64-linux-gnu/libxcb.so.1',
        '-Wl,--wrap=vkGetInstanceProcAddr','-Wl,--wrap=vkGetDeviceProcAddr','-pthread','-o',str(exe)]
    build=subprocess.run(cmd,capture_output=True,text=True);(LOCAL/'lsfg.compile.log').write_text(build.stdout+build.stderr)
    assert not build.returncode,build.stderr[-12000:]
    fixture=WORK/'lsfg-fixture';data=fixture/'sdmc:/switch/sleepingdogs-fex'
    (data/'lsfg').mkdir(parents=True,exist_ok=True);(data/'cache').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'local/lsfg-shaders-v15/lsfg-3.1.sdp',data/'lsfg/lsfg-3.1.sdp')
    with (LOCAL/'lsfg.xvfb.log').open('w') as out:
        server=subprocess.Popen(['Xvfb','-displayfd','1','-screen','0','1280x720x24','-nolisten','tcp','-nolisten','unix'],stdout=subprocess.PIPE,stderr=out,text=True)
        try:
            assert select.select([server.stdout],[],[],10)[0]
            display=server.stdout.readline().strip();assert display.isdecimal()
            env=dict(os.environ,DISPLAY=':'+display,VK_ICD_FILENAMES='/usr/share/vulkan/icd.d/lvp_icd.json',
                VK_LAYER_PATH=str(old/'host-tools/usr/share/vulkan/explicit_layer.d'),LD_LIBRARY_PATH=str(old/'host-tools/usr/lib/x86_64-linux-gnu'))
            run=subprocess.run([str(exe)],cwd=fixture,env=env,capture_output=True,text=True,timeout=180)
        finally:server.terminate();server.wait(timeout=5)
    output=run.stdout+run.stderr;(LOCAL/'lsfg.test.log').write_text(output)
    print(output[-14000:]);assert not run.returncode
    assert output.count('first interpolated present submitted')==3
    report=dict(status='PASS',validation_errors=0,generated_sessions=3,real_host_loader=True,wine_osk_route_preserved=True,
        source_files={str(p):sha(p) for p in (path,WORK/'source/osk.cpp',WORK/'source/lsfg.cpp',SOURCE/'lsfg_vulkan.cpp')},
        output=output,hardware_tested=False,switch_fps_measured=False)
    (LOCAL/'lsfg-test.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
