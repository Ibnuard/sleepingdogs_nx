/* Actual native adapter against a synchronization/lifetime model. */
#define VK_USE_64_BIT_PTR_DEFINES 0
#include <vulkan/vulkan.h>
#include <cassert>
#include <condition_variable>
#include <cstdio>
#include <mutex>
#include <thread>
static VkInstance instance=reinterpret_cast<VkInstance>(1);
static VkPhysicalDevice physical=reinterpret_cast<VkPhysicalDevice>(2);
static VkDevice device=reinterpret_cast<VkDevice>(3);
static VkQueue queue=reinterpret_cast<VkQueue>(4);
static unsigned raw_presents,generated,resets,live,next_chain,feature_calls;
static bool pack=true,visible,wait_acquire,acquire_entered,acquire_release;
static uint32_t next_image;
static VkResult backend_error=VK_SUCCESS,acquire_result=VK_SUCCESS;
static std::mutex acquire_gate;
static std::condition_variable acquire_cv;
struct wine_nx_lsfg {VkSwapchainKHR swapchain;};
extern "C" {
PFN_vkVoidFunction __real_vkGetInstanceProcAddr(VkInstance,const char*){return nullptr;}
PFN_vkVoidFunction __wrap_vkGetInstanceProcAddr(VkInstance,const char*){return nullptr;}
void wine_nx_runtime_trace(const char*){}
int fx_osk_frame_visible(void){return visible;}
void wine_nx_lsfg_device_features(VkInstance i,VkPhysicalDevice p,VkPhysicalDeviceFeatures *f,const void*){assert(i==instance&&p==physical);f->shaderStorageImageExtendedFormats=1;feature_calls++;}
int wine_nx_lsfg_prepare_swapchain(VkInstance i,VkPhysicalDevice p,VkSwapchainCreateInfoKHR *s){assert(i==instance&&p==physical);s->imageUsage|=VK_IMAGE_USAGE_TRANSFER_SRC_BIT;return pack;}
wine_nx_lsfg* wine_nx_lsfg_create(VkInstance,VkPhysicalDevice,VkDevice,VkSwapchainKHR s,const VkSwapchainCreateInfoKHR*){live++;return new wine_nx_lsfg{s};}
void wine_nx_lsfg_destroy(wine_nx_lsfg* s){assert(live);live--;delete s;}
int wine_nx_lsfg_present(wine_nx_lsfg* s,VkQueue q,unsigned family,int generate,const VkPresentInfoKHR* info,VkResult* r){
    assert(s&&q==queue&&family==0&&info->pSwapchains[0]==s->swapchain);
    if(!generate){resets++;return 0;}generated++;*r=backend_error;return 1;
}
VkResult VKAPI_CALL vkEnumeratePhysicalDevices(VkInstance i,uint32_t *n,VkPhysicalDevice *p){assert(i==instance);*n=1;if(p)*p=physical;return VK_SUCCESS;}
VkResult VKAPI_CALL vkEnumeratePhysicalDeviceGroups(VkInstance,uint32_t *n,VkPhysicalDeviceGroupProperties *p){*n=1;if(p){p->physicalDeviceCount=1;p->physicalDevices[0]=physical;}return VK_SUCCESS;}
void VKAPI_CALL vkDestroyInstance(VkInstance,const VkAllocationCallbacks*){}
VkResult VKAPI_CALL vkCreateDevice(VkPhysicalDevice p,const VkDeviceCreateInfo *i,const VkAllocationCallbacks*,VkDevice *out){
    assert(p==physical);const auto *f2=static_cast<const VkPhysicalDeviceFeatures2*>(i->pNext);
    if(f2&&f2->sType==VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2)assert(f2->features.shaderStorageImageExtendedFormats);
    else assert(i->pEnabledFeatures&&i->pEnabledFeatures->shaderStorageImageExtendedFormats);*out=device;return VK_SUCCESS;
}
VkResult VKAPI_CALL vkCreateSwapchainKHR(VkDevice d,const VkSwapchainCreateInfoKHR*,const VkAllocationCallbacks*,VkSwapchainKHR *out){assert(d==device);*out=++next_chain;return VK_SUCCESS;}
VkResult VKAPI_CALL vkAcquireNextImageKHR(VkDevice,VkSwapchainKHR,uint64_t,VkSemaphore,VkFence,uint32_t *index){
    if(wait_acquire){std::unique_lock<std::mutex> l(acquire_gate);acquire_entered=true;acquire_cv.notify_all();acquire_cv.wait(l,[]{return acquire_release;});}
    *index=next_image;return acquire_result;
}
VkResult VKAPI_CALL vkAcquireNextImage2KHR(VkDevice d,const VkAcquireNextImageInfoKHR *i,uint32_t *index){return vkAcquireNextImageKHR(d,i->swapchain,i->timeout,i->semaphore,i->fence,index);}
VkResult VKAPI_CALL vkQueuePresentKHR(VkQueue q,const VkPresentInfoKHR*){assert(q==queue);raw_presents++;return VK_SUCCESS;}
}
#include "../src/launcher/lsfg_vulkan.cpp"
static void show(VkSwapchainKHR chain,uint32_t index){
    VkPresentInfoKHR info{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};info.swapchainCount=1;info.pSwapchains=&chain;info.pImageIndices=&index;
    assert(sd_lsfg_present(queue,&info)==backend_error);
}
int main(){
    sd_lsfg_native_configure(1);assert(sd_lsfg_backend_loader()==__real_vkGetInstanceProcAddr);uint32_t n=1;VkPhysicalDevice p;
    assert(!enumerate(instance,&n,&p));VkPhysicalDeviceFeatures features{};VkDeviceCreateInfo ci{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};ci.pEnabledFeatures=&features;
    VkDevice d;assert(!sd_lsfg_create_device(p,&ci,nullptr,&d));assert(!features.shaderStorageImageExtendedFormats&&feature_calls==1);
    VkPhysicalDeviceFeatures2 f2{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2};ci.pEnabledFeatures=nullptr;ci.pNext=&f2;
    assert(!sd_lsfg_create_device(p,&ci,nullptr,&d));assert(!f2.features.shaderStorageImageExtendedFormats&&feature_calls==2);
    sd_lsfg_queue(d,0,queue);VkSwapchainCreateInfoKHR sc{VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR};VkSwapchainKHR chain;
    assert(!sd_lsfg_create_chain(d,&sc,nullptr,&chain)&&live==1);
    uint32_t index;next_image=0;assert(!acquire(d,chain,0,0,1,&index));show(chain,index);assert(generated==1&&!raw_presents);
    /* Keyboard frames bypass/reset history but retain normal presentation. */
    assert(!acquire(d,chain,0,0,1,&index));visible=true;show(chain,index);visible=false;assert(resets==1&&raw_presents==1);
    /* Two application-owned images cannot be stolen by the extra acquire. */
    assert(!acquire(d,chain,0,0,1,&index));next_image=1;assert(!acquire(d,chain,0,0,1,&index));show(chain,0);show(chain,1);assert(resets==2&&generated==2);
    next_image=0;assert(!acquire(d,chain,0,0,1,&index));
    wait_acquire=true;acquire_result=VK_TIMEOUT;
    std::thread worker([&]{uint32_t unused;assert(acquire(d,chain,0,0,1,&unused)==VK_TIMEOUT);});
    {std::unique_lock<std::mutex> l(acquire_gate);acquire_cv.wait(l,[]{return acquire_entered;});}
    show(chain,0);assert(resets==3); // Must not block on the pending acquire.
    {std::lock_guard<std::mutex> l(acquire_gate);acquire_release=true;}acquire_cv.notify_all();worker.join();
    wait_acquire=false;acquire_result=VK_SUCCESS;
    VkAcquireNextImageInfoKHR ai{VK_STRUCTURE_TYPE_ACQUIRE_NEXT_IMAGE_INFO_KHR};ai.swapchain=chain;assert(!acquire2(d,&ai,&index));
    backend_error=VK_ERROR_DEVICE_LOST;unsigned before=raw_presents;show(chain,index);assert(raw_presents==before);backend_error=VK_SUCCESS;
    /* Retired swapchains can present acquired images, but never reacquire. */
    VkSwapchainKHR newer;sc.oldSwapchain=chain;assert(!sd_lsfg_create_chain(d,&sc,nullptr,&newer));show(chain,index);assert(resets==4);
    sd_lsfg_destroy_chain(chain);sd_lsfg_destroy_chain(newer);assert(!live);
    pack=false;sc.oldSwapchain=0;assert(!sd_lsfg_create_chain(d,&sc,nullptr,&chain)&&!live);show(chain,0);
    sd_lsfg_native_configure(0);assert(sd_lsfg_backend_loader()==__wrap_vkGetInstanceProcAddr);before=raw_presents;show(chain,0);assert(raw_presents==before+1);
    sd_lsfg_destroy_device(d);destroy_instance(instance,nullptr);
    assert(physicals.empty()&&devices.empty()&&queues.empty()&&chains.empty());
    assert(sd_lsfg_intercept("vkAcquireNextImageKHR",reinterpret_cast<PFN_vkVoidFunction>(vkAcquireNextImageKHR))==reinterpret_cast<PFN_vkVoidFunction>(acquire));
    assert(!sd_lsfg_intercept("vkAcquireNextImageKHR",nullptr));
    puts("PASS: native feature enable without input mutation; OFF/missing pack; keyboard/multiple/concurrent acquire bypass; both acquire APIs; retired swapchain; no retry after consumed present error; full lifetime cleanup");
}
