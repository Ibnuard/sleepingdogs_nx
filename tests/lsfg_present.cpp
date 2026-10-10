// Exercise the production presentation bridge on Xvfb + software Vulkan.
#define VK_USE_PLATFORM_XCB_KHR
#define main unused_compute_fixture
#include "lsfg_headless.cpp"
#undef main
#include "lsfg.h"
#include "lsfg_config.h"
#include <cstring>

static unsigned generated_sessions;
extern "C" void wine_nx_runtime_trace(const char* msg) {
    std::puts(msg);
    if(std::strstr(msg,"first interpolated present submitted"))++generated_sessions;
}
int main() {
    try {
        int screen_no=0;auto* conn=xcb_connect(nullptr,&screen_no);
        if(xcb_connection_has_error(conn))throw std::runtime_error("Xvfb connection failed");
        auto iter=xcb_setup_roots_iterator(xcb_get_setup(conn));for(int i=0;i<screen_no;++i)xcb_screen_next(&iter);
        auto* screen=iter.data;xcb_window_t window=xcb_generate_id(conn);
        xcb_create_window(conn,XCB_COPY_FROM_PARENT,window,screen->root,0,0,1280,720,0,XCB_WINDOW_CLASS_INPUT_OUTPUT,screen->root_visual,0,nullptr);
        xcb_map_window(conn,window);xcb_flush(conn);
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.apiVersion=VK_API_VERSION_1_3;
        const char* extensions[]={VK_KHR_SURFACE_EXTENSION_NAME,VK_KHR_XCB_SURFACE_EXTENSION_NAME,VK_EXT_DEBUG_UTILS_EXTENSION_NAME};
        const char* layers[]={"VK_LAYER_KHRONOS_validation"};
        VkDebugUtilsMessengerCreateInfoEXT di{VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT};
        di.messageSeverity=VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
        di.messageType=VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT|VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT;di.pfnUserCallback=debug;
        VkInstanceCreateInfo ci{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};ci.pApplicationInfo=&app;ci.pNext=&di;
        ci.enabledExtensionCount=3;ci.ppEnabledExtensionNames=extensions;ci.enabledLayerCount=1;ci.ppEnabledLayerNames=layers;
        VkInstance instance;check(vkCreateInstance(&ci,nullptr,&instance));
        auto createDebug=reinterpret_cast<PFN_vkCreateDebugUtilsMessengerEXT>(vkGetInstanceProcAddr(instance,"vkCreateDebugUtilsMessengerEXT"));
        auto destroyDebug=reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(vkGetInstanceProcAddr(instance,"vkDestroyDebugUtilsMessengerEXT"));
        VkDebugUtilsMessengerEXT messenger;check(createDebug(instance,&di,nullptr,&messenger));
        VkXcbSurfaceCreateInfoKHR si{VK_STRUCTURE_TYPE_XCB_SURFACE_CREATE_INFO_KHR};si.connection=conn;si.window=window;
        VkSurfaceKHR surface;check(vkCreateXcbSurfaceKHR(instance,&si,nullptr,&surface));
        uint32_t count=0;check(vkEnumeratePhysicalDevices(instance,&count,nullptr));if(!count)return 2;
        std::vector<VkPhysicalDevice> physical(count);check(vkEnumeratePhysicalDevices(instance,&count,physical.data()));
        VkPhysicalDevice gpu=physical[0];vkGetPhysicalDeviceQueueFamilyProperties(gpu,&count,nullptr);
        std::vector<VkQueueFamilyProperties> queues(count);vkGetPhysicalDeviceQueueFamilyProperties(gpu,&count,queues.data());
        uint32_t family=0;for(;family<count;++family){VkBool32 supported=0;check(vkGetPhysicalDeviceSurfaceSupportKHR(gpu,family,surface,&supported));
            if(supported&&(queues[family].queueFlags&VK_QUEUE_COMPUTE_BIT))break;}
        if(family==count)return 3;
        float priority=1;VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
        VkPhysicalDeviceVulkan12Features v12{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES};v12.timelineSemaphore=VK_TRUE;v12.vulkanMemoryModel=VK_TRUE;
        VkPhysicalDeviceFeatures features{};
        if(!wine_nx_lsfg_available())throw std::runtime_error("Pack not found by real bridge");
        wine_nx_lsfg_configure(1,1,1);wine_nx_lsfg_device_features(instance,gpu,&features,&v12);
        const char* deviceExtensions[]={VK_KHR_SWAPCHAIN_EXTENSION_NAME};
        VkDeviceCreateInfo dc{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};dc.pNext=&v12;dc.pEnabledFeatures=&features;
        dc.queueCreateInfoCount=1;dc.pQueueCreateInfos=&qi;dc.enabledExtensionCount=1;dc.ppEnabledExtensionNames=deviceExtensions;
        VkDevice device;check(vkCreateDevice(gpu,&dc,nullptr,&device));VkQueue queue;vkGetDeviceQueue(device,family,0,&queue);
        VkSwapchainKHR swapchain=VK_NULL_HANDLE;
        for(unsigned test=0;test<3;++test){
            wine_nx_lsfg_configure(test!=0,1,test==2?0:1);
            VkSurfaceCapabilitiesKHR caps;check(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(gpu,surface,&caps));
            VkSwapchainCreateInfoKHR sc{VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR};sc.surface=surface;
            sc.minImageCount=std::max(caps.minImageCount,3u);if(caps.maxImageCount)sc.minImageCount=std::min(sc.minImageCount,caps.maxImageCount);
            sc.imageFormat=VK_FORMAT_B8G8R8A8_UNORM;sc.imageColorSpace=VK_COLOR_SPACE_SRGB_NONLINEAR_KHR;
            sc.imageExtent=caps.currentExtent;sc.imageArrayLayers=1;sc.imageUsage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT;
            sc.imageSharingMode=VK_SHARING_MODE_EXCLUSIVE;sc.preTransform=caps.currentTransform;sc.compositeAlpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
            sc.presentMode=VK_PRESENT_MODE_FIFO_KHR;sc.clipped=VK_TRUE;sc.oldSwapchain=swapchain;
            bool prepared=wine_nx_lsfg_prepare_swapchain(instance,gpu,&sc);if(prepared!=(test!=0))throw std::runtime_error("Unexpected prepare result");
            auto previous=swapchain;check(vkCreateSwapchainKHR(device,&sc,nullptr,&swapchain));if(previous)vkDestroySwapchainKHR(device,previous,nullptr);
            auto* state=prepared?wine_nx_lsfg_create(instance,gpu,device,swapchain,&sc):nullptr;
            if(prepared&&!state)throw std::runtime_error("Bridge did not create state");
            check(vkGetSwapchainImagesKHR(device,swapchain,&count,nullptr));std::vector<VkImage> images(count);check(vkGetSwapchainImagesKHR(device,swapchain,&count,images.data()));
            VkSemaphoreCreateInfo semInfo{VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};VkSemaphore acquire;check(vkCreateSemaphore(device,&semInfo,nullptr,&acquire));
            std::vector<VkSemaphore> ready(count);for(auto& sem:ready)check(vkCreateSemaphore(device,&semInfo,nullptr,&sem));
            for(unsigned frame=0;frame<8;++frame){
                uint32_t index;check(vkAcquireNextImageKHR(device,swapchain,UINT64_MAX,acquire,VK_NULL_HANDLE,&index));
                TransferCommand transfer(device,queue,family);
                auto b=barrier(images[index],VK_IMAGE_LAYOUT_UNDEFINED,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,0,VK_ACCESS_TRANSFER_WRITE_BIT);
                vkCmdPipelineBarrier(transfer.command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&b);
                VkClearColorValue color{{0.1f*frame,0.4f,0.7f,1.0f}};VkImageSubresourceRange range{VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
                vkCmdClearColorImage(transfer.command,images[index],VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&color,1,&range);
                b=barrier(images[index],VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,VK_ACCESS_TRANSFER_WRITE_BIT,0);
                vkCmdPipelineBarrier(transfer.command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,nullptr,0,nullptr,1,&b);
                check(vkEndCommandBuffer(transfer.command));VkPipelineStageFlags stage=VK_PIPELINE_STAGE_TRANSFER_BIT;
                VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.waitSemaphoreCount=1;submit.pWaitSemaphores=&acquire;submit.pWaitDstStageMask=&stage;
                submit.commandBufferCount=1;submit.pCommandBuffers=&transfer.command;submit.signalSemaphoreCount=1;submit.pSignalSemaphores=&ready[index];check(vkQueueSubmit(queue,1,&submit,VK_NULL_HANDLE));
                VkPresentInfoKHR pi{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};pi.waitSemaphoreCount=1;pi.pWaitSemaphores=&ready[index];pi.swapchainCount=1;pi.pSwapchains=&swapchain;pi.pImageIndices=&index;
                VkResult result;int handled=wine_nx_lsfg_present(state,queue,family,true,&pi,&result);
                if(handled!=(test!=0))throw std::runtime_error("Unexpected LSFG bypass");
                if(!handled)result=vkQueuePresentKHR(queue,&pi);check(result);check(vkQueueWaitIdle(queue));
            }
            wine_nx_lsfg_destroy(state);check(vkDeviceWaitIdle(device));
            for(auto sem:ready)vkDestroySemaphore(device,sem,nullptr);vkDestroySemaphore(device,acquire,nullptr);
        }
        check(vkDeviceWaitIdle(device));vkDestroySwapchainKHR(device,swapchain,nullptr);vkDestroyDevice(device,nullptr);
        vkDestroySurfaceKHR(instance,surface,nullptr);destroyDebug(instance,messenger,nullptr);vkDestroyInstance(instance,nullptr);
        xcb_destroy_window(conn,window);xcb_disconnect(conn);
        if(validation_errors||generated_sessions!=2)throw std::runtime_error("Present validation/generation check failed");
        std::printf("PASS: production bridge; off, 2x, recreate, warmup, generated presents; validation_errors=%u\n",validation_errors);
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
    return 0;
}
