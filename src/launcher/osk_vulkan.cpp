/* SPDX-License-Identifier: LGPL-2.1-or-later.
 * Sleeping Dogs adapter for PES13's fextendo_osk_vulkan.h / Autorun nx_osk_*.
 * Interposes the HOST loader, covering both native DXVK and Wine Vulkan.
 * Each acquired image owns its staging buffer, copy fence and semaphore.
 */
#include <vulkan/vulkan.h>
#include <cstdint>
#include <cstring>
#include <map>
#include <mutex>
#include <new>
#include <vector>
extern "C" {
#include "pes13/fextendo_osk_frame.h"
PFN_vkVoidFunction __real_vkGetInstanceProcAddr(VkInstance,const char*);
PFN_vkVoidFunction __real_vkGetDeviceProcAddr(VkDevice,const char*);
void wine_nx_runtime_trace(const char*);
void sd_keyboard_present_gate(void);
}
namespace {
struct Image {
    VkImage image=VK_NULL_HANDLE;VkBuffer buffer=VK_NULL_HANDLE;VkDeviceMemory memory=VK_NULL_HANDLE;
    VkCommandBuffer cmd=VK_NULL_HANDLE;VkSemaphore done=VK_NULL_HANDLE;VkFence fence=VK_NULL_HANDLE;
    void* pixels=nullptr;uint64_t generation=0,session=0;int x=-1,y=-1;
};
struct Chain {
    VkDevice device=VK_NULL_HANDLE;VkFormat format=VK_FORMAT_UNDEFINED;VkExtent2D extent{};
    VkCommandPool pool=VK_NULL_HANDLE;uint32_t family=UINT32_MAX;bool usable=false,failed=false;
    int width=0,height=0;std::vector<Image> images;
};
struct Queue {VkDevice device;uint32_t family;};
std::mutex gate;
std::map<VkDevice,VkPhysicalDevice> devices;
std::map<VkQueue,Queue> queues;
std::map<VkSwapchainKHR,Chain> chains;

void release(Chain& c) {
    // Destruction follows Vulkan's normal externally-synchronized lifetime.
    // Our own submissions also have to finish before mapped backing is freed.
    if(c.pool)vkDeviceWaitIdle(c.device);
    for(auto& p:c.images){
        if(p.pixels)vkUnmapMemory(c.device,p.memory);
        if(p.fence)vkDestroyFence(c.device,p.fence,nullptr);
        if(p.done)vkDestroySemaphore(c.device,p.done,nullptr);
        if(p.buffer)vkDestroyBuffer(c.device,p.buffer,nullptr);
        if(p.memory)vkFreeMemory(c.device,p.memory,nullptr);
    }
    if(c.pool)vkDestroyCommandPool(c.device,c.pool,nullptr);
    c.pool=VK_NULL_HANDLE;c.images.clear();
}
bool prepare(VkSwapchainKHR handle,Chain& c,uint32_t family,const fx_osk_frame& frame){
    if(c.failed||!c.usable)return false;
    if(c.pool)return c.family==family&&c.width==frame.width&&c.height==frame.height;
    auto d=devices.find(c.device);if(d==devices.end())return false;
    uint32_t families=0;vkGetPhysicalDeviceQueueFamilyProperties(d->second,&families,nullptr);
    if(family>=families)return false;
    std::vector<VkQueueFamilyProperties> props_queue(families);
    vkGetPhysicalDeviceQueueFamilyProperties(d->second,&families,props_queue.data());
    if(!(props_queue[family].queueFlags&(VK_QUEUE_GRAPHICS_BIT|VK_QUEUE_COMPUTE_BIT)))return false;
    uint32_t count=0;
    if(vkGetSwapchainImagesKHR(c.device,handle,&count,nullptr)||!count||count>16)return false;
    std::vector<VkImage> images(count);
    if(vkGetSwapchainImagesKHR(c.device,handle,&count,images.data()))return false;
    c.images.resize(count);c.family=family;c.width=frame.width;c.height=frame.height;
    VkCommandPoolCreateInfo pool{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
    pool.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;pool.queueFamilyIndex=family;
    if(vkCreateCommandPool(c.device,&pool,nullptr,&c.pool))return false;
    VkPhysicalDeviceMemoryProperties props{};vkGetPhysicalDeviceMemoryProperties(d->second,&props);
    for(uint32_t i=0;i<count;i++){
        auto& p=c.images[i];p.image=images[i];
        VkBufferCreateInfo buffer{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        buffer.size=VkDeviceSize(frame.width)*frame.height*4;buffer.usage=VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
        if(vkCreateBuffer(c.device,&buffer,nullptr,&p.buffer))return false;
        VkMemoryRequirements req{};vkGetBufferMemoryRequirements(c.device,p.buffer,&req);
        uint32_t type=0;const auto flags=VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
        for(;type<props.memoryTypeCount;type++)if((req.memoryTypeBits&(1u<<type))&&(props.memoryTypes[type].propertyFlags&flags)==flags)break;
        if(type==props.memoryTypeCount)return false;
        VkMemoryAllocateInfo alloc{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};alloc.allocationSize=req.size;alloc.memoryTypeIndex=type;
        if(vkAllocateMemory(c.device,&alloc,nullptr,&p.memory)||vkBindBufferMemory(c.device,p.buffer,p.memory,0)||
           vkMapMemory(c.device,p.memory,0,buffer.size,0,&p.pixels))return false;
        VkSemaphoreCreateInfo sem{VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
        VkFenceCreateInfo fence{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};fence.flags=VK_FENCE_CREATE_SIGNALED_BIT;
        if(vkCreateSemaphore(c.device,&sem,nullptr,&p.done)||vkCreateFence(c.device,&fence,nullptr,&p.fence))return false;
        VkCommandBufferAllocateInfo cmd{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        cmd.commandPool=c.pool;cmd.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;cmd.commandBufferCount=1;
        if(vkAllocateCommandBuffers(c.device,&cmd,&p.cmd))return false;
    }
    wine_nx_runtime_trace("[SD-OSK] in-frame transfer ready; per-image fence; game surface retained");return true;
}
bool record(Chain& c,Image& p,const fx_osk_frame& f){
    VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    if(vkResetCommandBuffer(p.cmd,0)||vkBeginCommandBuffer(p.cmd,&begin))return false;
    VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
    b.oldLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;b.newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    b.srcAccessMask=VK_ACCESS_MEMORY_WRITE_BIT;b.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
    b.srcQueueFamilyIndex=b.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;b.image=p.image;
    b.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
    vkCmdPipelineBarrier(p.cmd,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&b);
    VkBufferImageCopy copy{};copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1};
    copy.imageOffset={f.x,f.y,0};copy.imageExtent={uint32_t(c.width),uint32_t(c.height),1};
    vkCmdCopyBufferToImage(p.cmd,p.buffer,p.image,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,1,&copy);
    b.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;b.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
    b.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;b.dstAccessMask=0;
    vkCmdPipelineBarrier(p.cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,nullptr,0,nullptr,1,&b);
    if(vkEndCommandBuffer(p.cmd))return false;p.x=f.x;p.y=f.y;return true;
}
VkResult VKAPI_CALL create_device(VkPhysicalDevice physical,const VkDeviceCreateInfo* info,const VkAllocationCallbacks* a,VkDevice* out){
    auto result=vkCreateDevice(physical,info,a,out);
    if(result==VK_SUCCESS)try{std::lock_guard<std::mutex> lock(gate);devices[*out]=physical;}catch(const std::bad_alloc&){}return result;
}
void VKAPI_CALL destroy_device(VkDevice d,const VkAllocationCallbacks* a){
    {std::lock_guard<std::mutex> lock(gate);
        for(auto it=chains.begin();it!=chains.end();)if(it->second.device==d){release(it->second);it=chains.erase(it);}else ++it;
        for(auto it=queues.begin();it!=queues.end();)if(it->second.device==d)it=queues.erase(it);else ++it;
        devices.erase(d);
    }vkDestroyDevice(d,a);
}
void VKAPI_CALL get_queue(VkDevice d,uint32_t family,uint32_t index,VkQueue* q){
    vkGetDeviceQueue(d,family,index,q);try{std::lock_guard<std::mutex> lock(gate);queues[*q]={d,family};}catch(const std::bad_alloc&){}
}
void VKAPI_CALL get_queue2(VkDevice d,const VkDeviceQueueInfo2* info,VkQueue* q){
    vkGetDeviceQueue2(d,info,q);try{std::lock_guard<std::mutex> lock(gate);queues[*q]={d,info->queueFamilyIndex};}catch(const std::bad_alloc&){}
}
VkResult VKAPI_CALL create_chain(VkDevice d,const VkSwapchainCreateInfoKHR* input,const VkAllocationCallbacks* a,VkSwapchainKHR* out){
    auto info=*input;bool usable=false;
    {std::lock_guard<std::mutex> lock(gate);auto p=devices.find(d);VkSurfaceCapabilitiesKHR caps{};
        usable=p!=devices.end()&&!vkGetPhysicalDeviceSurfaceCapabilitiesKHR(p->second,info.surface,&caps)&&
            (caps.supportedUsageFlags&VK_IMAGE_USAGE_TRANSFER_DST_BIT)&&info.imageArrayLayers==1&&
            (info.imageFormat==VK_FORMAT_R8G8B8A8_UNORM||info.imageFormat==VK_FORMAT_R8G8B8A8_SRGB||
             info.imageFormat==VK_FORMAT_B8G8R8A8_UNORM||info.imageFormat==VK_FORMAT_B8G8R8A8_SRGB);
    }
    if(usable)info.imageUsage|=VK_IMAGE_USAGE_TRANSFER_DST_BIT;
    auto result=vkCreateSwapchainKHR(d,&info,a,out);
    if(result==VK_SUCCESS)try{std::lock_guard<std::mutex> lock(gate);auto& c=chains[*out];
        c.device=d;c.format=info.imageFormat;c.extent=info.imageExtent;c.usable=usable;}catch(const std::bad_alloc&){}
    return result;
}
void VKAPI_CALL destroy_chain(VkDevice d,VkSwapchainKHR s,const VkAllocationCallbacks* a){
    {std::lock_guard<std::mutex> lock(gate);auto it=chains.find(s);if(it!=chains.end()){release(it->second);chains.erase(it);}}
    vkDestroySwapchainKHR(d,s,a);
}
VkResult present_inner(VkQueue q,const VkPresentInfoKHR* input){
    sd_keyboard_present_gate();
    // Closed OSK: no registry mutex, allocation, pixel copy or extra submit.
    if(!fx_osk_frame_visible())return vkQueuePresentKHR(q,input);
    std::lock_guard<std::mutex> lock(gate);
    if(input->swapchainCount!=1)return vkQueuePresentKHR(q,input);
    auto queue=queues.find(q);auto chain=chains.find(input->pSwapchains[0]);
    if(queue==queues.end()||chain==chains.end())return vkQueuePresentKHR(q,input);
    auto& c=chain->second;fx_osk_frame frame{};
    if(!fx_osk_frame_get(c.extent.width,c.extent.height,&frame))return vkQueuePresentKHR(q,input);
    bool ok=queue->second.device==c.device&&frame.x>=0&&frame.y>=0&&frame.width>0&&frame.height>0&&
        uint64_t(frame.x)+frame.width<=c.extent.width&&uint64_t(frame.y)+frame.height<=c.extent.height&&
        prepare(chain->first,c,queue->second.family,frame);
    auto index=input->pImageIndices[0];ok=ok&&index<c.images.size();
    Image* p=ok?&c.images[index]:nullptr;
    if(ok)ok=vkWaitForFences(c.device,1,&p->fence,VK_TRUE,50000000)==VK_SUCCESS;
    if(ok&&(p->generation!=frame.generation||p->session!=frame.session)){
        bool rgba=c.format==VK_FORMAT_R8G8B8A8_UNORM||c.format==VK_FORMAT_R8G8B8A8_SRGB;
        // A concurrent move/close just skips this frame; no semaphore consumed.
        if(!fx_osk_frame_copy(&frame,p->pixels,frame.width*4,rgba))return vkQueuePresentKHR(q,input);
        p->generation=frame.generation;p->session=frame.session;
    }
    if(ok&&(p->x!=frame.x||p->y!=frame.y))ok=record(c,*p,frame);
    VkPresentInfoKHR info=*input;
    if(ok){
        std::vector<VkPipelineStageFlags> stages(info.waitSemaphoreCount,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT);
        VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.waitSemaphoreCount=info.waitSemaphoreCount;
        submit.pWaitSemaphores=info.pWaitSemaphores;submit.pWaitDstStageMask=stages.data();
        submit.commandBufferCount=1;submit.pCommandBuffers=&p->cmd;submit.signalSemaphoreCount=1;submit.pSignalSemaphores=&p->done;
        ok=!vkResetFences(c.device,1,&p->fence)&&!vkQueueSubmit(q,1,&submit,p->fence);
        if(ok){info.waitSemaphoreCount=1;info.pWaitSemaphores=&p->done;}
    }
    if(!ok){c.failed=true;fx_osk_frame_reject(frame.session);}
    auto result=vkQueuePresentKHR(q,&info);
    if(ok&&(result==VK_SUCCESS||result==VK_SUBOPTIMAL_KHR))fx_osk_frame_presented(frame.session);
    else if(ok)fx_osk_frame_reject(frame.session);
    return result;
}
VkResult VKAPI_CALL present(VkQueue q,const VkPresentInfoKHR* input){
    try{return present_inner(q,input);}catch(const std::bad_alloc&){
        // All potentially allocating operations precede queue submission.
        // Never consume the game's wait semaphores on allocation failure.
        std::lock_guard<std::mutex> lock(gate);
        if(input->swapchainCount==1){auto c=chains.find(input->pSwapchains[0]);if(c!=chains.end()){
            c->second.failed=true;fx_osk_frame f{};
            if(fx_osk_frame_get(c->second.extent.width,c->second.extent.height,&f))fx_osk_frame_reject(f.session);
        }}
        return vkQueuePresentKHR(q,input);
    }
}
}
extern "C" PFN_vkVoidFunction __wrap_vkGetInstanceProcAddr(VkInstance,const char*);
extern "C" PFN_vkVoidFunction __wrap_vkGetDeviceProcAddr(VkDevice,const char*);
static PFN_vkVoidFunction intercept(const char* name,PFN_vkVoidFunction real){
    if(!real)return nullptr;
#define SD_HOOK(api,fn) if(!std::strcmp(name,#api))return reinterpret_cast<PFN_vkVoidFunction>(fn)
    SD_HOOK(vkGetInstanceProcAddr,__wrap_vkGetInstanceProcAddr);SD_HOOK(vkGetDeviceProcAddr,__wrap_vkGetDeviceProcAddr);
    SD_HOOK(vkCreateDevice,create_device);SD_HOOK(vkDestroyDevice,destroy_device);
    SD_HOOK(vkGetDeviceQueue,get_queue);SD_HOOK(vkGetDeviceQueue2,get_queue2);
    SD_HOOK(vkCreateSwapchainKHR,create_chain);SD_HOOK(vkDestroySwapchainKHR,destroy_chain);SD_HOOK(vkQueuePresentKHR,present);
#undef SD_HOOK
    return real;
}
extern "C" PFN_vkVoidFunction __wrap_vkGetInstanceProcAddr(VkInstance i,const char* n){return intercept(n,__real_vkGetInstanceProcAddr(i,n));}
extern "C" PFN_vkVoidFunction __wrap_vkGetDeviceProcAddr(VkDevice d,const char* n){return intercept(n,__real_vkGetDeviceProcAddr(d,n));}
