/* LGPL-2.1-or-later. API model adapted from PES13 38750c20 test.
 * Tests the real Sleeping Dogs interposer; no physical GPU is simulated. */
#define VK_USE_64_BIT_PTR_DEFINES 0
#include <vulkan/vulkan.h>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
extern "C" {
#include "../src/launcher/pes13/fextendo_osk_frame.h"
}
static VkSemaphore submitted_wait;
static unsigned step,fail_at,next_id,live,pools,submits,copies,rejects,records;
static int visible,stale,alloc_fail,format_rgba;
static struct fx_osk_frame frame;
struct object {int type,signaled;void *p;} objects[256];
enum {POOL=1,SEM,BUF,MEM,FENCE,CMD};
static VkResult api(void){return ++step==fail_at?VK_ERROR_OUT_OF_DEVICE_MEMORY:VK_SUCCESS;}
static uint64_t make(int type){unsigned i=++next_id;assert(i<256);objects[i].type=type;live++;return i;}
static void drop(uint64_t i,int type){if(!i)return;assert(i<256&&objects[i].type==type);free(objects[i].p);memset(&objects[i],0,sizeof(objects[i]));live--;}

int fx_osk_frame_visible(void){return visible;}
int fx_osk_frame_get(int w,int h,struct fx_osk_frame *f){assert(w==1280&&h==720);*f=frame;return visible;}
int fx_osk_frame_copy(const struct fx_osk_frame *f,void *p,int stride,int rgba){assert(f->generation==frame.generation&&stride==f->width*4&&p);format_rgba=rgba;if(stale)return 0;copies++;memset(p,255,(size_t)stride*f->height);return 1;}
void fx_osk_frame_reject(uint64_t s){assert(s==frame.session);rejects++;}
VkResult VKAPI_CALL vkGetSwapchainImagesKHR(VkDevice d,VkSwapchainKHR s,uint32_t *n,VkImage *p){(void)d;assert(s==55);VkResult r=api();if(r)return r;if(p){assert(*n==3);for(int i=0;i<3;i++)p[i]=100+i;}*n=3;return VK_SUCCESS;}
void VKAPI_CALL vkGetPhysicalDeviceMemoryProperties(VkPhysicalDevice d,VkPhysicalDeviceMemoryProperties *p){(void)d;memset(p,0,sizeof(*p));p->memoryTypeCount=1;p->memoryTypes[0].propertyFlags=VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;}
VkResult VKAPI_CALL vkCreateCommandPool(VkDevice d,const VkCommandPoolCreateInfo *i,const VkAllocationCallbacks *a,VkCommandPool *p){(void)d;(void)a;assert(i->flags==VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT);VkResult r=api();if(!r){*p=make(POOL);pools++;}return r;}
void VKAPI_CALL vkDestroyCommandPool(VkDevice d,VkCommandPool p,const VkAllocationCallbacks *a){(void)d;(void)a;drop(p,POOL);for(unsigned i=1;i<=next_id;i++)if(objects[i].type==CMD)drop(i,CMD);}
VkResult VKAPI_CALL vkCreateSemaphore(VkDevice d,const VkSemaphoreCreateInfo *i,const VkAllocationCallbacks *a,VkSemaphore *p){(void)d;(void)a;(void)i;VkResult r=api();if(!r)*p=make(SEM);return r;}
void VKAPI_CALL vkDestroySemaphore(VkDevice d,VkSemaphore p,const VkAllocationCallbacks *a){(void)d;(void)a;drop(p,SEM);}
VkResult VKAPI_CALL vkCreateBuffer(VkDevice d,const VkBufferCreateInfo *i,const VkAllocationCallbacks *a,VkBuffer *p){(void)d;(void)a;assert(i->size==1280*252*4&&i->usage==VK_BUFFER_USAGE_TRANSFER_SRC_BIT);VkResult r=api();if(!r)*p=make(BUF);return r;}
void VKAPI_CALL vkDestroyBuffer(VkDevice d,VkBuffer p,const VkAllocationCallbacks *a){(void)d;(void)a;drop(p,BUF);}
void VKAPI_CALL vkGetBufferMemoryRequirements(VkDevice d,VkBuffer b,VkMemoryRequirements *r){(void)d;assert(objects[b].type==BUF);*r=(VkMemoryRequirements){.size=1280*252*4,.alignment=4096,.memoryTypeBits=1};}
VkResult VKAPI_CALL vkAllocateMemory(VkDevice d,const VkMemoryAllocateInfo *i,const VkAllocationCallbacks *a,VkDeviceMemory *p){(void)d;(void)a;assert(i->memoryTypeIndex==0);VkResult r=api();if(!r){*p=make(MEM);objects[*p].p=calloc(1,i->allocationSize);assert(objects[*p].p);}return r;}
void VKAPI_CALL vkFreeMemory(VkDevice d,VkDeviceMemory m,const VkAllocationCallbacks *a){(void)d;(void)a;drop(m,MEM);}
VkResult VKAPI_CALL vkBindBufferMemory(VkDevice d,VkBuffer b,VkDeviceMemory m,VkDeviceSize o){(void)d;assert(!o&&objects[b].type==BUF&&objects[m].type==MEM);return api();}
VkResult VKAPI_CALL vkMapMemory(VkDevice d,VkDeviceMemory m,VkDeviceSize o,VkDeviceSize n,VkMemoryMapFlags flags,void **p){(void)d;(void)n;(void)flags;assert(!o&&objects[m].type==MEM);VkResult r=api();if(!r)*p=objects[m].p;return r;}
void VKAPI_CALL vkUnmapMemory(VkDevice d,VkDeviceMemory m){(void)d;assert(objects[m].type==MEM);}
VkResult VKAPI_CALL vkCreateFence(VkDevice d,const VkFenceCreateInfo *i,const VkAllocationCallbacks *a,VkFence *p){(void)d;(void)a;assert(i->flags==VK_FENCE_CREATE_SIGNALED_BIT);VkResult r=api();if(!r){*p=make(FENCE);objects[*p].signaled=1;}return r;}
void VKAPI_CALL vkDestroyFence(VkDevice d,VkFence f,const VkAllocationCallbacks *a){(void)d;(void)a;drop(f,FENCE);}
VkResult VKAPI_CALL vkWaitForFences(VkDevice d,uint32_t n,const VkFence *f,VkBool32 all,uint64_t limit){(void)d;assert(n==1&&all&&limit==50000000&&objects[*f].type==FENCE);VkResult r=api();return r?r:objects[*f].signaled?VK_SUCCESS:VK_TIMEOUT;}
VkResult VKAPI_CALL vkResetFences(VkDevice d,uint32_t n,const VkFence *f){(void)d;assert(n==1&&objects[*f].signaled);VkResult r=api();if(!r)objects[*f].signaled=0;return r;}
VkResult VKAPI_CALL vkAllocateCommandBuffers(VkDevice d,const VkCommandBufferAllocateInfo *i,VkCommandBuffer *p){(void)d;assert(objects[i->commandPool].type==POOL&&i->commandBufferCount==1);VkResult r=api();if(!r)*p=(VkCommandBuffer)(uintptr_t)make(CMD);return r;}
VkResult VKAPI_CALL vkResetCommandBuffer(VkCommandBuffer c,VkCommandBufferResetFlags f){assert(objects[(uintptr_t)c].type==CMD&&!f);return api();}
VkResult VKAPI_CALL vkBeginCommandBuffer(VkCommandBuffer c,const VkCommandBufferBeginInfo *i){(void)c;assert(!i->flags);records++;return api();}
VkResult VKAPI_CALL vkEndCommandBuffer(VkCommandBuffer c){(void)c;return api();}
void VKAPI_CALL vkCmdPipelineBarrier(VkCommandBuffer c,VkPipelineStageFlags src,VkPipelineStageFlags dst,VkDependencyFlags flags,uint32_t n,const VkMemoryBarrier *m,uint32_t nb,const VkBufferMemoryBarrier *b,uint32_t ni,const VkImageMemoryBarrier *i){
(void)c;(void)flags;(void)m;(void)b;assert(!n&&!nb&&ni==1&&i->image>=100&&i->image<=102);
if(i->oldLayout==VK_IMAGE_LAYOUT_PRESENT_SRC_KHR)assert(src==VK_PIPELINE_STAGE_ALL_COMMANDS_BIT&&dst==VK_PIPELINE_STAGE_TRANSFER_BIT&&i->newLayout==VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
else assert(src==VK_PIPELINE_STAGE_TRANSFER_BIT&&i->newLayout==VK_IMAGE_LAYOUT_PRESENT_SRC_KHR);}
void VKAPI_CALL vkCmdCopyBufferToImage(VkCommandBuffer c,VkBuffer b,VkImage i,VkImageLayout l,uint32_t n,const VkBufferImageCopy *r){(void)c;assert(objects[b].type==BUF&&i>=100&&i<=102&&l==VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL&&n==1);assert(r->imageOffset.y==frame.y&&r->imageExtent.width==1280&&r->imageExtent.height==252);}
VkResult VKAPI_CALL vkQueueSubmit(VkQueue q,uint32_t n,const VkSubmitInfo *s,VkFence f){(void)q;assert(n==1&&s->commandBufferCount==1&&s->signalSemaphoreCount==1&&objects[f].type==FENCE&&!objects[f].signaled);assert(s->waitSemaphoreCount==2&&s->pWaitSemaphores[0]==801&&s->pWaitSemaphores[1]==802);assert(s->pWaitDstStageMask[0]==VK_PIPELINE_STAGE_ALL_COMMANDS_BIT&&objects[*s->pSignalSemaphores].type==SEM);VkResult r=api();if(!r){submits++;submitted_wait=*s->pSignalSemaphores;}return r;}
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
