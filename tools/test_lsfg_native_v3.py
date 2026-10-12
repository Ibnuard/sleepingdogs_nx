"""Extend the real LSFG fixture with DXVK's FIFO mode + real present fence."""
from pathlib import Path
from launcher_v1_overlay import ROOT,replace

def extend(program):
    program=replace(program,'VK_EXT_DEBUG_UTILS_EXTENSION_NAME};','VK_EXT_DEBUG_UTILS_EXTENSION_NAME,VK_KHR_GET_SURFACE_CAPABILITIES_2_EXTENSION_NAME,VK_EXT_SURFACE_MAINTENANCE_1_EXTENSION_NAME};')
    program=replace(program,'ci.enabledExtensionCount=3;','ci.enabledExtensionCount=5;')
    program=replace(program,'const char* deviceExtensions[]={VK_KHR_SWAPCHAIN_EXTENSION_NAME};',
        'VkPhysicalDeviceSwapchainMaintenance1FeaturesEXT maintenance{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SWAPCHAIN_MAINTENANCE_1_FEATURES_EXT};maintenance.swapchainMaintenance1=VK_TRUE;v12.pNext=&maintenance;\n'
        '        const char* deviceExtensions[]={VK_KHR_SWAPCHAIN_EXTENSION_NAME,VK_EXT_SWAPCHAIN_MAINTENANCE_1_EXTENSION_NAME};')
    program=replace(program,'dc.enabledExtensionCount=1;','dc.enabledExtensionCount=2;')
    program=replace(program,'for(unsigned test=0;test<4;++test){','for(unsigned test=0;test<5;++test){')
    program=replace(program,'            auto previous=swapchain;',
        '''            VkPresentModeKHR fifo=VK_PRESENT_MODE_FIFO_KHR;
            VkSwapchainPresentModesCreateInfoEXT modes{VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODES_CREATE_INFO_EXT};
            modes.presentModeCount=1;modes.pPresentModes=&fifo;if(test==4)sc.pNext=&modes;
            auto previous=swapchain;''')
    program=replace(program,'                VkResult result;','''                VkFence fence=VK_NULL_HANDLE;
                VkSwapchainPresentModeInfoEXT mode{VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODE_INFO_EXT};
                mode.swapchainCount=1;mode.pPresentModes=&fifo;
                VkSwapchainPresentFenceInfoEXT presentFence{VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_FENCE_INFO_EXT};
                if(test==4) {
                    VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};check(vkCreateFence(device,&fi,nullptr,&fence));
                    presentFence.swapchainCount=1;presentFence.pFences=&fence;presentFence.pNext=&mode;pi.pNext=&presentFence;
                }
                VkResult result;''')
    program=replace(program,'                check(result);check(vkQueueWaitIdle(queue));',
        '''                check(result);check(vkQueueWaitIdle(queue));
                if(test==4){check(vkWaitForFences(device,1,&fence,VK_TRUE,3000000000ull));vkDestroyFence(device,fence,nullptr);
                    if(pi.pNext!=&presentFence||presentFence.pNext!=&mode||mode.pPresentModes!=&fifo)throw std::runtime_error("Caller present metadata mutated");}''')
    program=program.replace('generated_sessions!=3','generated_sessions!=4')
    return program

def main():
    text=(ROOT/'tools/test_lsfg_native_v2.py').read_text()
    text=replace(text,'from build_launcher_v2 import WORK,LOCAL',"WORK=Path('/home/blekjek/sleepingdogs-launcher-v3')\nLOCAL=ROOT/'local/launcher-v3'")
    text=replace(text,"    path=WORK/'tests/lsfg-native.cpp';","    program=extend(program)\n    path=WORK/'tests/lsfg-native.cpp';")
    text=text.replace("==3\n","==4\n").replace('generated_sessions=3','generated_sessions=4')
    ns={'__name__':'v3_lsfg_fixture','__file__':__file__,'extend':extend}
    exec(compile(text,__file__,'exec'),ns);ns['main']()
if __name__=='__main__':main()
