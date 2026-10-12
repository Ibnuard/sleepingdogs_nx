/* SPDX-License-Identifier: GPL-3.0-or-later.
 * Native DXVK does not traverse Wine's Vulkan thunks. Attach the existing
 * LSFG backend to the host loader, while leaving Wine's route independent.
 */
#include "lsfg_vulkan.h"
#include "lsfg.h"
#include <atomic>
#include <cstdio>
#include <cstring>
#include <map>
#include <mutex>
#include <new>
extern "C" int fx_osk_frame_visible(void);
extern "C" void wine_nx_runtime_trace(const char*);
extern "C" PFN_vkVoidFunction __real_vkGetInstanceProcAddr(VkInstance,const char*);
extern "C" PFN_vkVoidFunction __wrap_vkGetInstanceProcAddr(VkInstance,const char*);
namespace {
std::atomic<bool> requested{false};
std::mutex gate;
struct Device {VkInstance instance;VkPhysicalDevice physical;bool eligible;};
struct Queue {VkDevice device;uint32_t family;};
struct Chain {
    VkDevice device{};wine_nx_lsfg* state{};unsigned acquiring{};
    uint64_t acquired{},bypasses{};bool retired{};
};
std::map<VkPhysicalDevice,VkInstance> physicals;
std::map<VkDevice,Device> devices;
std::map<VkQueue,Queue> queues;
std::map<VkSwapchainKHR,Chain> chains;
void trace(const char* s){wine_nx_runtime_trace(s);}
VkResult VKAPI_CALL enumerate(VkInstance instance,uint32_t* count,VkPhysicalDevice* out){
    auto r=vkEnumeratePhysicalDevices(instance,count,out);
    if(requested.load(std::memory_order_relaxed)&&out&&(r==VK_SUCCESS||r==VK_INCOMPLETE))
        try{std::lock_guard<std::mutex> l(gate);for(uint32_t i=0;i<*count;i++)physicals[out[i]]=instance;}catch(const std::bad_alloc&){}
    return r;
}
VkResult VKAPI_CALL groups(VkInstance instance,uint32_t* count,VkPhysicalDeviceGroupProperties* out){
    auto r=vkEnumeratePhysicalDeviceGroups(instance,count,out);
    if(requested.load(std::memory_order_relaxed)&&out&&(r==VK_SUCCESS||r==VK_INCOMPLETE))
        try{std::lock_guard<std::mutex> l(gate);for(uint32_t i=0;i<*count;i++)
            for(uint32_t j=0;j<out[i].physicalDeviceCount;j++)physicals[out[i].physicalDevices[j]]=instance;}catch(const std::bad_alloc&){}
    return r;
}
void VKAPI_CALL destroy_instance(VkInstance instance,const VkAllocationCallbacks* alloc){
    {std::lock_guard<std::mutex> l(gate);
        for(auto i=physicals.begin();i!=physicals.end();)if(i->second==instance)i=physicals.erase(i);else ++i;
    }vkDestroyInstance(instance,alloc);
}
bool begin_acquire(VkSwapchainKHR s){
    if(!requested.load(std::memory_order_relaxed))return false;
    std::lock_guard<std::mutex> l(gate);auto c=chains.find(s);if(c==chains.end())return false;
    ++c->second.acquiring;return true;
}
void end_acquire(VkSwapchainKHR s,VkResult r,const uint32_t* index){
    std::lock_guard<std::mutex> l(gate);auto c=chains.find(s);if(c==chains.end())return;
    --c->second.acquiring;
    if((r==VK_SUCCESS||r==VK_SUBOPTIMAL_KHR)&&*index<64)c->second.acquired|=UINT64_C(1)<<*index;
}
VkResult VKAPI_CALL acquire(VkDevice d,VkSwapchainKHR s,uint64_t timeout,VkSemaphore sem,VkFence fence,uint32_t* index){
    bool tracked=begin_acquire(s);auto r=vkAcquireNextImageKHR(d,s,timeout,sem,fence,index);
    if(tracked)end_acquire(s,r,index);return r;
}
VkResult VKAPI_CALL acquire2(VkDevice d,const VkAcquireNextImageInfoKHR* info,uint32_t* index){
    bool tracked=begin_acquire(info->swapchain);auto r=vkAcquireNextImage2KHR(d,info,index);
    if(tracked)end_acquire(info->swapchain,r,index);return r;
}
void bypass(Chain& c,const char* reason){
    if((++c.bypasses&(c.bypasses-1))!=0)return;
    char s[192];std::snprintf(s,sizeof(s),"[SD-LSFG-NATIVE] generation bypass count=%llu reason=%s; real frame retained",
        (unsigned long long)c.bypasses,reason);trace(s);
}
}
extern "C" void sd_lsfg_native_configure(int enabled){requested.store(enabled!=0,std::memory_order_release);}
extern "C" PFN_vkGetInstanceProcAddr sd_lsfg_backend_loader(void){
    /* Native frames already passed the OSK stage before entering LSFG.
     * Wine enters LSFG earlier, so its backend retains the OSK present hook. */
    return requested.load(std::memory_order_acquire)?__real_vkGetInstanceProcAddr:__wrap_vkGetInstanceProcAddr;
}
extern "C" PFN_vkVoidFunction sd_lsfg_intercept(const char* name,PFN_vkVoidFunction real){
    if(!real)return nullptr;
#define HOOK(api,fn) if(!std::strcmp(name,#api))return reinterpret_cast<PFN_vkVoidFunction>(fn)
    HOOK(vkEnumeratePhysicalDevices,enumerate);HOOK(vkEnumeratePhysicalDeviceGroups,groups);
    HOOK(vkEnumeratePhysicalDeviceGroupsKHR,groups);HOOK(vkDestroyInstance,destroy_instance);
    HOOK(vkAcquireNextImageKHR,acquire);HOOK(vkAcquireNextImage2KHR,acquire2);
#undef HOOK
    return real;
}
extern "C" VkResult sd_lsfg_create_device(VkPhysicalDevice physical,const VkDeviceCreateInfo* input,const VkAllocationCallbacks* alloc,VkDevice* out){
    if(!requested.load(std::memory_order_acquire))return vkCreateDevice(physical,input,alloc,out);
    VkInstance instance{};
    {std::lock_guard<std::mutex> l(gate);auto p=physicals.find(physical);if(p!=physicals.end())instance=p->second;}
    auto info=*input;VkPhysicalDeviceFeatures features{};VkPhysicalDeviceFeatures2 features2{};
    const VkPhysicalDeviceFeatures2* original=nullptr;
    for(auto p=static_cast<const VkBaseInStructure*>(input->pNext);p;p=p->pNext)
        if(p->sType==VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2)original=reinterpret_cast<const VkPhysicalDeviceFeatures2*>(p);
    bool supported_chain=(!original||input->pNext==original);
    if(instance&&supported_chain){
        features=original?original->features:input->pEnabledFeatures?*input->pEnabledFeatures:VkPhysicalDeviceFeatures{};
        wine_nx_lsfg_device_features(instance,physical,&features,input->pNext);
        if(original){features2=*original;features2.features=features;info.pNext=&features2;}
        else info.pEnabledFeatures=&features;
    }
    bool eligible=instance&&supported_chain&&features.shaderStorageImageExtendedFormats;
    if(!eligible)trace("[SD-LSFG-NATIVE] inactive: device feature/instance prerequisites unavailable");
    auto r=vkCreateDevice(physical,&info,alloc,out);
    if(r==VK_SUCCESS)try{std::lock_guard<std::mutex> l(gate);devices[*out]={instance,physical,eligible};}
    catch(const std::bad_alloc&){trace("[SD-LSFG-NATIVE] inactive: device tracking allocation failed");}
    return r;
}
extern "C" void sd_lsfg_destroy_device(VkDevice device){
    std::lock_guard<std::mutex> l(gate);
    for(auto c=chains.begin();c!=chains.end();)if(c->second.device==device){wine_nx_lsfg_destroy(c->second.state);c=chains.erase(c);}else ++c;
    for(auto q=queues.begin();q!=queues.end();)if(q->second.device==device)q=queues.erase(q);else ++q;
    devices.erase(device);
}
extern "C" void sd_lsfg_queue(VkDevice device,uint32_t family,VkQueue queue){
    if(!requested.load(std::memory_order_relaxed))return;
    try{std::lock_guard<std::mutex> l(gate);queues[queue]={device,family};}catch(const std::bad_alloc&){}
}
extern "C" VkResult sd_lsfg_create_chain(VkDevice device,const VkSwapchainCreateInfoKHR* input,const VkAllocationCallbacks* alloc,VkSwapchainKHR* out){
    if(!requested.load(std::memory_order_relaxed))return vkCreateSwapchainKHR(device,input,alloc,out);
    std::lock_guard<std::mutex> l(gate);auto info=*input;auto d=devices.find(device);
    bool prepared=d!=devices.end()&&d->second.eligible&&wine_nx_lsfg_prepare_swapchain(d->second.instance,d->second.physical,&info);
    /* oldSwapchain is retired even when creation fails. Never reacquire it. */
    auto previous=chains.find(info.oldSwapchain);if(previous!=chains.end())previous->second.retired=true;
    auto r=vkCreateSwapchainKHR(device,&info,alloc,out);
    if(r==VK_SUCCESS&&prepared){
        auto* state=wine_nx_lsfg_create(d->second.instance,d->second.physical,device,*out,&info);
        if(state)try{chains.emplace(*out,Chain{device,state});trace("[SD-LSFG-NATIVE] swapchain attached; GPU initialization/history pending");}
        catch(const std::bad_alloc&){wine_nx_lsfg_destroy(state);trace("[SD-LSFG-NATIVE] inactive: swapchain tracking allocation failed");}
    }
    if(!prepared)trace("[SD-LSFG-NATIVE] inactive for this swapchain; see capability/pack reason");
    return r;
}
extern "C" void sd_lsfg_destroy_chain(VkSwapchainKHR s){
    std::lock_guard<std::mutex> l(gate);auto c=chains.find(s);
    if(c!=chains.end()){wine_nx_lsfg_destroy(c->second.state);chains.erase(c);}
}
extern "C" VkResult sd_lsfg_present(VkQueue queue,const VkPresentInfoKHR* info){
    if(!requested.load(std::memory_order_relaxed))return vkQueuePresentKHR(queue,info);
    /* Serialize history and our extra acquire with starts of application
     * acquires. Never hold this lock over an application's blocking acquire. */
    std::lock_guard<std::mutex> l(gate);
    auto q=queues.find(queue);auto c=info->swapchainCount==1?chains.find(info->pSwapchains[0]):chains.end();
    VkResult result;bool handled=false;
    if(q!=queues.end()&&c!=chains.end()&&q->second.device==c->second.device){
        auto& s=c->second;uint32_t index=info->pImageIndices[0];
        uint64_t bit=index<64?UINT64_C(1)<<index:0;
        const char* reason=s.retired?"retired swapchain":s.acquiring?"concurrent acquire":
            (!bit||s.acquired!=bit)?"additional/untracked acquired image":fx_osk_frame_visible()?"keyboard open":nullptr;
        if(reason)bypass(s,reason);
        handled=wine_nx_lsfg_present(s.state,queue,q->second.family,!reason,info,&result)!=0;
    }
    if(!handled)result=vkQueuePresentKHR(queue,info);
    if(result==VK_SUCCESS||result==VK_SUBOPTIMAL_KHR||result==VK_ERROR_OUT_OF_DATE_KHR||result==VK_ERROR_SURFACE_LOST_KHR){
        for(uint32_t i=0;i<info->swapchainCount;i++){
            auto s=chains.find(info->pSwapchains[i]);if(s!=chains.end()&&info->pImageIndices[i]<64)s->second.acquired&=~(UINT64_C(1)<<info->pImageIndices[i]);
        }
    }
    return result;
}
