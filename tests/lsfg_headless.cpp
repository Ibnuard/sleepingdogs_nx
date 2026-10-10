// Execute the real Horizon backend on a borrowed software Vulkan device.
#include <vulkan/vulkan.h>
#include "lsfg-vk-backend/lsfgvk.hpp"
#include "lsfg-vk-common/vulkan/command_buffer.hpp"
#include "lsfg-vk-common/vulkan/vulkan.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <vector>

static unsigned validation_errors;
static VKAPI_ATTR VkBool32 VKAPI_CALL debug(VkDebugUtilsMessageSeverityFlagBitsEXT severity,
        VkDebugUtilsMessageTypeFlagsEXT,const VkDebugUtilsMessengerCallbackDataEXT* data,void*) {
    if(severity&VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT){
        ++validation_errors;std::fprintf(stderr,"VALIDATION: %s\n",data->pMessage);
    }
    return VK_FALSE;
}
static void check(VkResult result) {if(result!=VK_SUCCESS)throw std::runtime_error("Vulkan error "+std::to_string(result));}
// Fixture transfers use their own pool; the backend keeps ownership of its
// private command buffers and is exercised through its public submit API.
struct TransferCommand {
    VkDevice device; VkQueue queue; VkCommandPool pool; VkCommandBuffer command;
    TransferCommand(VkDevice d,VkQueue q,uint32_t family):device(d),queue(q) {
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=family;
        check(vkCreateCommandPool(device,&pi,nullptr,&pool));
        VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
        check(vkAllocateCommandBuffers(device,&ai,&command));
        VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        check(vkBeginCommandBuffer(command,&bi));
    }
    void submit() {
        check(vkEndCommandBuffer(command));
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&command;
        check(vkQueueSubmit(queue,1,&si,VK_NULL_HANDLE));check(vkQueueWaitIdle(queue));
    }
    ~TransferCommand(){vkDestroyCommandPool(device,pool,nullptr);}
};
static VkImageMemoryBarrier barrier(VkImage img,VkImageLayout before,VkImageLayout after,
        VkAccessFlags src,VkAccessFlags dst) {
    return {VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,nullptr,src,dst,before,after,
        VK_QUEUE_FAMILY_IGNORED,VK_QUEUE_FAMILY_IGNORED,img,{VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
}
int main(int argc,char** argv) {
    try{
        if(argc!=2)return 2;
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.apiVersion=VK_API_VERSION_1_3;
        const char* extensions[]={VK_EXT_DEBUG_UTILS_EXTENSION_NAME,VK_KHR_SURFACE_EXTENSION_NAME};
        const char* layers[]={"VK_LAYER_KHRONOS_validation"};
        VkDebugUtilsMessengerCreateInfoEXT di{VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT};
        di.messageSeverity=VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
        di.messageType=VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT|VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT|VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT;
        di.pfnUserCallback=debug;
        VkInstanceCreateInfo ci{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};ci.pApplicationInfo=&app;
        ci.enabledExtensionCount=2;ci.ppEnabledExtensionNames=extensions;
        ci.enabledLayerCount=1;ci.ppEnabledLayerNames=layers;ci.pNext=&di;
        VkInstance instance;check(vkCreateInstance(&ci,nullptr,&instance));
        VkDebugUtilsMessengerEXT messenger;
        auto createDebug=reinterpret_cast<PFN_vkCreateDebugUtilsMessengerEXT>(vkGetInstanceProcAddr(instance,"vkCreateDebugUtilsMessengerEXT"));
        auto destroyDebug=reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(vkGetInstanceProcAddr(instance,"vkDestroyDebugUtilsMessengerEXT"));
        check(createDebug(instance,&di,nullptr,&messenger));
        uint32_t count=0;check(vkEnumeratePhysicalDevices(instance,&count,nullptr));if(!count)return 3;
        std::vector<VkPhysicalDevice> physical(count);check(vkEnumeratePhysicalDevices(instance,&count,physical.data()));
        VkPhysicalDeviceProperties props;vkGetPhysicalDeviceProperties(physical[0],&props);
        std::printf("Device: %s\n",props.deviceName);std::fflush(stdout);
        vkGetPhysicalDeviceQueueFamilyProperties(physical[0],&count,nullptr);
        std::vector<VkQueueFamilyProperties> queues(count);vkGetPhysicalDeviceQueueFamilyProperties(physical[0],&count,queues.data());
        uint32_t family=0;while(family<count && !(queues[family].queueFlags&VK_QUEUE_COMPUTE_BIT))++family;
        float priority=1;
        VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
        VkPhysicalDeviceVulkan12Features v12{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES};
        v12.timelineSemaphore=VK_TRUE;v12.vulkanMemoryModel=VK_TRUE;
        VkPhysicalDeviceFeatures features{};features.shaderStorageImageExtendedFormats=VK_TRUE;features.shaderStorageImageWriteWithoutFormat=VK_TRUE;
        VkDeviceCreateInfo deviceInfo{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};deviceInfo.pNext=&v12;
        const char* deviceExtensions[]={VK_KHR_SWAPCHAIN_EXTENSION_NAME};
        deviceInfo.enabledExtensionCount=1;deviceInfo.ppEnabledExtensionNames=deviceExtensions;
        deviceInfo.queueCreateInfoCount=1;deviceInfo.pQueueCreateInfos=&qi;deviceInfo.pEnabledFeatures=&features;
        VkDevice device;check(vkCreateDevice(physical[0],&deviceInfo,nullptr,&device));
        VkQueue queue;vkGetDeviceQueue(device,family,0,&queue);
        {
            lsfgvk::backend::Instance backend({instance,physical[0],device,family,queue,vkGetInstanceProcAddr,std::nullopt},argv[1],false);
            const auto& vk=backend.vulkan();
            unsigned failed=0;
            for(unsigned test=0;test<4;++test){
                uint32_t width=test?1280:256,height=test?720:256;bool perf=true;
                float flow=test<2?4.0f:test==2?8.0f:2.0f;
                auto& context=backend.openLocalContext(width,height,false,flow,perf,1);
                for(unsigned frame=0;frame<4;++frame){
                    if(!frame){
                        TransferCommand transfer(device,queue,family);
                        for(unsigned i=0;i<2;++i){
                            VkImage image=backend.sourceImage(context,i);
                            auto b=barrier(image,VK_IMAGE_LAYOUT_UNDEFINED,VK_IMAGE_LAYOUT_GENERAL,0,VK_ACCESS_TRANSFER_WRITE_BIT);
                            vkCmdPipelineBarrier(transfer.command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&b);
                            VkClearColorValue color{{0.2f,0.4f,0.7f,1.0f}};VkImageSubresourceRange range{VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
                            vkCmdClearColorImage(transfer.command,image,VK_IMAGE_LAYOUT_GENERAL,&color,1,&range);
                        }
                        transfer.submit();
                    }
                    vk::CommandBuffer cmd(vk);cmd.begin(vk);
                    cmd.memoryBarrier(vk);backend.recordFrame(context,cmd);cmd.end(vk);
                    cmd.submit(vk);check(vkQueueWaitIdle(queue));
                }
                VkBufferCreateInfo bi{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};bi.size=width*height*4;bi.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT;
                VkBuffer buffer;check(vkCreateBuffer(device,&bi,nullptr,&buffer));
                VkMemoryRequirements req;vkGetBufferMemoryRequirements(device,buffer,&req);
                VkPhysicalDeviceMemoryProperties memory;vkGetPhysicalDeviceMemoryProperties(physical[0],&memory);
                uint32_t type=0;for(;type<memory.memoryTypeCount;++type)if((req.memoryTypeBits&(1u<<type))&&
                    (memory.memoryTypes[type].propertyFlags&(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))==(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))break;
                VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ai.allocationSize=req.size;ai.memoryTypeIndex=type;
                VkDeviceMemory mem;check(vkAllocateMemory(device,&ai,nullptr,&mem));check(vkBindBufferMemory(device,buffer,mem,0));
                {
                    TransferCommand transfer(device,queue,family);
                    VkImage image=backend.destinationImage(context,0);
                    auto b=barrier(image,VK_IMAGE_LAYOUT_GENERAL,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_TRANSFER_READ_BIT);
                    vkCmdPipelineBarrier(transfer.command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&b);
                    VkBufferImageCopy region{};region.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1};region.imageExtent={width,height,1};
                    vkCmdCopyImageToBuffer(transfer.command,image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,buffer,1,&region);
                    transfer.submit();
                }
                void* mapped;check(vkMapMemory(device,mem,0,req.size,0,&mapped));auto bytes=static_cast<const unsigned char*>(mapped);
                unsigned worst=0,interiorWorst=0;uint64_t total=0,bad=0;const int expected[]={51,102,178};
                for(size_t i=0;i<width*height;++i)for(unsigned c=0;c<3;++c){
                    auto err=unsigned(std::abs(int(bytes[i*4+c])-expected[c]));worst=std::max(worst,err);total+=err;bad+=err>4;
                    unsigned x=i%width,y=i/width;
                    if(x>=16&&x+16<width&&y>=16&&y+16<height)interiorWorst=std::max(interiorWorst,err);
                }
                std::printf("RGB center=%u,%u,%u mean error=%.4f bad_channels=%llu\n",bytes[(width*(height/2)+width/2)*4],bytes[(width*(height/2)+width/2)*4+1],bytes[(width*(height/2)+width/2)*4+2],double(total)/(width*height*3),(unsigned long long)bad);
                vkUnmapMemory(device,mem);vkDestroyBuffer(device,buffer,nullptr);vkFreeMemory(device,mem,nullptr);
                std::printf("Output %ux%u %s motion=%.1f%%: max RGB error=%u interior=%u validation_errors=%u\n",width,height,perf?"performance":"quality",100.0f/flow,worst,interiorWorst,validation_errors);std::fflush(stdout);
                if(worst>4 || validation_errors)++failed;
                backend.closeContext(context);
            }
            if(failed)throw std::runtime_error("LSFG output/validation failed");
        }
        vkDestroyDevice(device,nullptr);destroyDebug(instance,messenger,nullptr);vkDestroyInstance(instance,nullptr);
        std::puts("PASS: real LSFG compute on software Vulkan; this is not a Switch performance measurement");
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
    return 0;
}
