static unsigned presented,frame_ack,gates;
void fx_osk_frame_presented(uint64_t session){assert(session==frame.session);frame_ack++;}
extern "C" void wine_nx_runtime_trace(const char*){}
extern "C" void sd_keyboard_present_gate(void){gates++;}
VkResult VKAPI_CALL vkDeviceWaitIdle(VkDevice){for(auto& p:objects)if(p.type==FENCE)p.signaled=1;return VK_SUCCESS;}
VkResult VKAPI_CALL vkCreateDevice(VkPhysicalDevice,const VkDeviceCreateInfo*,const VkAllocationCallbacks*,VkDevice* d){*d=(VkDevice)1;return VK_SUCCESS;}
void VKAPI_CALL vkDestroyDevice(VkDevice,const VkAllocationCallbacks*){}
void VKAPI_CALL vkGetDeviceQueue(VkDevice,uint32_t family,uint32_t,VkQueue* q){*q=(VkQueue)(uintptr_t)(2+family);}
void VKAPI_CALL vkGetDeviceQueue2(VkDevice d,const VkDeviceQueueInfo2* i,VkQueue* q){vkGetDeviceQueue(d,i->queueFamilyIndex,i->queueIndex,q);}
void VKAPI_CALL vkGetPhysicalDeviceQueueFamilyProperties(VkPhysicalDevice,uint32_t* n,VkQueueFamilyProperties* p){
    if(p){assert(*n==2);memset(p,0,2*sizeof(*p));p[0].queueFlags=VK_QUEUE_GRAPHICS_BIT;}*n=2;
}
VkResult VKAPI_CALL vkGetPhysicalDeviceSurfaceCapabilitiesKHR(VkPhysicalDevice,VkSurfaceKHR,VkSurfaceCapabilitiesKHR* c){memset(c,0,sizeof(*c));c->supportedUsageFlags=VK_IMAGE_USAGE_TRANSFER_DST_BIT;return VK_SUCCESS;}
VkResult VKAPI_CALL vkCreateSwapchainKHR(VkDevice,const VkSwapchainCreateInfoKHR* i,const VkAllocationCallbacks*,VkSwapchainKHR* s){assert(i->imageUsage&VK_IMAGE_USAGE_TRANSFER_DST_BIT);*s=55;return VK_SUCCESS;}
void VKAPI_CALL vkDestroySwapchainKHR(VkDevice,VkSwapchainKHR,const VkAllocationCallbacks*){}
VkResult VKAPI_CALL vkQueuePresentKHR(VkQueue,const VkPresentInfoKHR* i){
    if(submitted_wait)assert(i->waitSemaphoreCount==1&&*i->pWaitSemaphores==submitted_wait);
    else assert(i->waitSemaphoreCount==2&&i->pWaitSemaphores[0]==801&&i->pWaitSemaphores[1]==802);
    submitted_wait=0;presented++;return VK_SUCCESS;
}
extern "C" PFN_vkVoidFunction __real_vkGetInstanceProcAddr(VkInstance,const char*){return (PFN_vkVoidFunction)1;}
extern "C" PFN_vkVoidFunction __real_vkGetDeviceProcAddr(VkDevice,const char*){return (PFN_vkVoidFunction)1;}
#include "../src/launcher/osk_vulkan.cpp"
static VkDevice test_device;
static VkQueue test_queue;
static VkSwapchainKHR test_chain;
static void fresh(){
    if(test_device)destroy_device(test_device,nullptr);
    assert(!live&&chains.empty()&&devices.empty()&&queues.empty());memset(objects,0,sizeof(objects));
    step=fail_at=next_id=pools=submits=copies=rejects=records=presented=frame_ack=gates=0;visible=1;stale=alloc_fail=0;
    frame={0,468,1280,252,1,1};submitted_wait=0;
    VkDeviceCreateInfo device{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};assert(create_device((VkPhysicalDevice)1,&device,nullptr,&test_device)==VK_SUCCESS);
    get_queue(test_device,0,0,&test_queue);
    VkSwapchainCreateInfoKHR chain{VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR};chain.imageArrayLayers=1;
    chain.imageExtent={1280,720};chain.imageFormat=VK_FORMAT_B8G8R8A8_UNORM;
    assert(create_chain(test_device,&chain,nullptr,&test_chain)==VK_SUCCESS);
}
static void tick(unsigned i){VkSemaphore waits[]={801,802};VkPresentInfoKHR p{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};
    p.swapchainCount=1;p.pSwapchains=&test_chain;p.pImageIndices=&i;p.waitSemaphoreCount=2;p.pWaitSemaphores=waits;
    assert(present(test_queue,&p)==VK_SUCCESS);
}
static void finish(unsigned i){objects[chains.at(test_chain).images[i].fence].signaled=1;}
int main(){
    fresh();visible=0;tick(0);assert(!step&&!live&&!rejects&&presented==1&&gates==1);
    visible=1;tick(0);assert(submits==1&&copies==1&&!format_rgba&&frame_ack==1);unsigned total=step;finish(0);
    tick(0);assert(copies==1&&records==1);finish(0);
    frame.y=0;frame.generation++;tick(0);assert(pools==1&&records==2&&copies==2);finish(0);
    tick(1);finish(1);tick(2);finish(2);
    for(unsigned n=1;n<=total;n++){fresh();fail_at=n;tick(0);assert(rejects==1&&!submits&&presented==1&&!frame_ack);}
    fresh();stale=1;tick(0);assert(!submits&&!rejects);stale=0;tick(0);assert(submits==1);finish(0);
    fresh();tick(0);frame.generation++;tick(0);assert(copies==1&&records==1&&submits==1&&rejects==1);
    fresh();chains.at(test_chain).usable=false;tick(0);assert(!step&&rejects==1);
    fresh();get_queue(test_device,1,0,&test_queue);tick(0);assert(!step&&rejects==1);
    fresh();chains.at(test_chain).format=VK_FORMAT_R8G8B8A8_SRGB;tick(0);assert(format_rgba);finish(0);
    fresh();tick(3);assert(rejects==1&&!submits);
    assert(__wrap_vkGetInstanceProcAddr(nullptr,"vkQueuePresentKHR")==reinterpret_cast<PFN_vkVoidFunction>(present));
    assert(__wrap_vkGetDeviceProcAddr(test_device,"vkGetDeviceProcAddr")==reinterpret_cast<PFN_vkVoidFunction>(__wrap_vkGetDeviceProcAddr));
    destroy_device(test_device,nullptr);test_device=nullptr;assert(!live);
    puts("PASS: native/Wine loader hooks; closed OSK no allocation/copy/submit; per-image fences and original wait chain; API failure injection; cached/moved pixels; timeout; invalid queue; full cleanup");
}
