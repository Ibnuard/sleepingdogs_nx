/* Actual overlay against a Vulkan resource/synchronization model. No GPU claimed. */
#define VK_USE_64_BIT_PTR_DEFINES 0
#include <vulkan/vulkan_core.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../src/runtime/fextendo_osk_frame.h"
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define ERR(...) ((void)0)
#define nx_vk_trace(...) ((void)0)
struct vulkan_instance {PFN_vkGetPhysicalDeviceMemoryProperties p_vkGetPhysicalDeviceMemoryProperties;};
struct vulkan_physical_device {struct vulkan_instance *instance;struct {VkPhysicalDevice physical_device;} host;};
struct vulkan_device {struct {VkDevice device;} host;struct vulkan_physical_device *physical_device;VkQueueFamilyProperties *queue_props;
PFN_vkAllocateCommandBuffers p_vkAllocateCommandBuffers;
PFN_vkAllocateMemory p_vkAllocateMemory;
PFN_vkBeginCommandBuffer p_vkBeginCommandBuffer;
PFN_vkBindBufferMemory p_vkBindBufferMemory;
PFN_vkCmdCopyBufferToImage p_vkCmdCopyBufferToImage;
PFN_vkCmdPipelineBarrier p_vkCmdPipelineBarrier;
PFN_vkCreateBuffer p_vkCreateBuffer;
PFN_vkCreateCommandPool p_vkCreateCommandPool;
PFN_vkCreateFence p_vkCreateFence;
PFN_vkCreateSemaphore p_vkCreateSemaphore;
PFN_vkDestroyBuffer p_vkDestroyBuffer;
PFN_vkDestroyCommandPool p_vkDestroyCommandPool;
PFN_vkDestroyFence p_vkDestroyFence;
PFN_vkDestroySemaphore p_vkDestroySemaphore;
PFN_vkEndCommandBuffer p_vkEndCommandBuffer;
PFN_vkFreeMemory p_vkFreeMemory;
PFN_vkGetBufferMemoryRequirements p_vkGetBufferMemoryRequirements;
PFN_vkGetSwapchainImagesKHR p_vkGetSwapchainImagesKHR;
PFN_vkMapMemory p_vkMapMemory;
PFN_vkQueueSubmit p_vkQueueSubmit;
PFN_vkResetCommandBuffer p_vkResetCommandBuffer;
PFN_vkResetFences p_vkResetFences;
PFN_vkUnmapMemory p_vkUnmapMemory;
PFN_vkWaitForFences p_vkWaitForFences;
};
struct vulkan_queue {struct vulkan_device *device;struct {VkQueue queue;} host;struct {uint32_t queueFamilyIndex;} info;};
struct nx_osk_overlay;
struct swapchain {struct {struct {VkSwapchainKHR swapchain;} host;} obj;VkExtent2D nx_extent;VkFormat nx_format;BOOL nx_osk_usable;struct nx_osk_overlay *nx_osk;};
static struct swapchain chain;
static struct swapchain *swapchain_from_handle(VkSwapchainKHR h){assert(h==1);return &chain;}
struct mempool {void *p;};
static unsigned step,fail_at,next_id,live,pools,submits,copies,rejects,records;
static int visible,stale,alloc_fail,format_rgba;
static struct fx_osk_frame frame;
struct object {int type,signaled;void *p;} objects[256];
enum {POOL=1,SEM,BUF,MEM,FENCE,CMD};
static VkResult api(void){return ++step==fail_at?VK_ERROR_OUT_OF_DEVICE_MEMORY:VK_SUCCESS;}
static uint64_t make(int type){unsigned i=++next_id;assert(i<256);objects[i].type=type;live++;return i;}
static void drop(uint64_t i,int type){if(!i)return;assert(i<256&&objects[i].type==type);free(objects[i].p);memset(&objects[i],0,sizeof(objects[i]));live--;}
static void *mem_alloc(struct mempool *p,size_t n){assert(!p->p);if(alloc_fail)return NULL;return p->p=calloc(1,n);}
int fx_osk_frame_visible(void){return visible;}
int fx_osk_frame_get(int w,int h,struct fx_osk_frame *f){assert(w==1280&&h==720);*f=frame;return visible;}
int fx_osk_frame_copy(const struct fx_osk_frame *f,void *p,int stride,int rgba){assert(f->generation==frame.generation&&stride==f->width*4&&p);format_rgba=rgba;if(stale)return 0;copies++;memset(p,255,(size_t)stride*f->height);return 1;}
void fx_osk_frame_reject(uint64_t s){assert(s==frame.session);rejects++;}
static VkResult images(VkDevice d,VkSwapchainKHR s,uint32_t *n,VkImage *p){(void)d;assert(s==55);VkResult r=api();if(r)return r;if(p){assert(*n==3);for(int i=0;i<3;i++)p[i]=100+i;}*n=3;return 0;}
static void props(VkPhysicalDevice d,VkPhysicalDeviceMemoryProperties *p){(void)d;memset(p,0,sizeof(*p));p->memoryTypeCount=1;p->memoryTypes[0].propertyFlags=VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;}
static VkResult create_pool(VkDevice d,const VkCommandPoolCreateInfo *i,const VkAllocationCallbacks *a,VkCommandPool *p){(void)d;(void)a;assert(i->flags==VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT);VkResult r=api();if(!r){*p=make(POOL);pools++;}return r;}
static void destroy_pool(VkDevice d,VkCommandPool p,const VkAllocationCallbacks *a){(void)d;(void)a;drop(p,POOL);for(unsigned i=1;i<=next_id;i++)if(objects[i].type==CMD)drop(i,CMD);}
static VkResult create_sem(VkDevice d,const VkSemaphoreCreateInfo *i,const VkAllocationCallbacks *a,VkSemaphore *p){(void)d;(void)a;(void)i;VkResult r=api();if(!r)*p=make(SEM);return r;}
static void destroy_sem(VkDevice d,VkSemaphore p,const VkAllocationCallbacks *a){(void)d;(void)a;drop(p,SEM);}
static VkResult create_buffer(VkDevice d,const VkBufferCreateInfo *i,const VkAllocationCallbacks *a,VkBuffer *p){(void)d;(void)a;assert(i->size==1280*252*4&&i->usage==VK_BUFFER_USAGE_TRANSFER_SRC_BIT);VkResult r=api();if(!r)*p=make(BUF);return r;}
static void destroy_buffer(VkDevice d,VkBuffer p,const VkAllocationCallbacks *a){(void)d;(void)a;drop(p,BUF);}
static void req(VkDevice d,VkBuffer b,VkMemoryRequirements *r){(void)d;assert(objects[b].type==BUF);*r=(VkMemoryRequirements){.size=1280*252*4,.alignment=4096,.memoryTypeBits=1};}
static VkResult allocate(VkDevice d,const VkMemoryAllocateInfo *i,const VkAllocationCallbacks *a,VkDeviceMemory *p){(void)d;(void)a;assert(i->memoryTypeIndex==0);VkResult r=api();if(!r){*p=make(MEM);objects[*p].p=calloc(1,i->allocationSize);assert(objects[*p].p);}return r;}
static void free_mem(VkDevice d,VkDeviceMemory m,const VkAllocationCallbacks *a){(void)d;(void)a;drop(m,MEM);}
static VkResult bind(VkDevice d,VkBuffer b,VkDeviceMemory m,VkDeviceSize o){(void)d;assert(!o&&objects[b].type==BUF&&objects[m].type==MEM);return api();}
static VkResult map(VkDevice d,VkDeviceMemory m,VkDeviceSize o,VkDeviceSize n,VkMemoryMapFlags flags,void **p){(void)d;(void)n;(void)flags;assert(!o&&objects[m].type==MEM);VkResult r=api();if(!r)*p=objects[m].p;return r;}
static void unmap(VkDevice d,VkDeviceMemory m){(void)d;assert(objects[m].type==MEM);}
static VkResult create_fence(VkDevice d,const VkFenceCreateInfo *i,const VkAllocationCallbacks *a,VkFence *p){(void)d;(void)a;assert(i->flags==VK_FENCE_CREATE_SIGNALED_BIT);VkResult r=api();if(!r){*p=make(FENCE);objects[*p].signaled=1;}return r;}
static void destroy_fence(VkDevice d,VkFence f,const VkAllocationCallbacks *a){(void)d;(void)a;drop(f,FENCE);}
static VkResult wait_fence(VkDevice d,uint32_t n,const VkFence *f,VkBool32 all,uint64_t limit){(void)d;assert(n==1&&all&&limit==50000000&&objects[*f].type==FENCE);VkResult r=api();return r?r:objects[*f].signaled?VK_SUCCESS:VK_TIMEOUT;}
static VkResult reset_fence(VkDevice d,uint32_t n,const VkFence *f){(void)d;assert(n==1&&objects[*f].signaled);VkResult r=api();if(!r)objects[*f].signaled=0;return r;}
static VkResult alloc_cmd(VkDevice d,const VkCommandBufferAllocateInfo *i,VkCommandBuffer *p){(void)d;assert(objects[i->commandPool].type==POOL&&i->commandBufferCount==1);VkResult r=api();if(!r)*p=(VkCommandBuffer)(uintptr_t)make(CMD);return r;}
static VkResult reset_cmd(VkCommandBuffer c,VkCommandBufferResetFlags f){assert(objects[(uintptr_t)c].type==CMD&&!f);return api();}
static VkResult begin(VkCommandBuffer c,const VkCommandBufferBeginInfo *i){(void)c;assert(!i->flags);records++;return api();}
static VkResult end(VkCommandBuffer c){(void)c;return api();}
static void barrier(VkCommandBuffer c,VkPipelineStageFlags src,VkPipelineStageFlags dst,VkDependencyFlags flags,uint32_t n,const VkMemoryBarrier *m,uint32_t nb,const VkBufferMemoryBarrier *b,uint32_t ni,const VkImageMemoryBarrier *i){
(void)c;(void)flags;(void)m;(void)b;assert(!n&&!nb&&ni==1&&i->image>=100&&i->image<=102);
if(i->oldLayout==VK_IMAGE_LAYOUT_PRESENT_SRC_KHR)assert(src==VK_PIPELINE_STAGE_ALL_COMMANDS_BIT&&dst==VK_PIPELINE_STAGE_TRANSFER_BIT&&i->newLayout==VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
else assert(src==VK_PIPELINE_STAGE_TRANSFER_BIT&&i->newLayout==VK_IMAGE_LAYOUT_PRESENT_SRC_KHR);}
static void copy(VkCommandBuffer c,VkBuffer b,VkImage i,VkImageLayout l,uint32_t n,const VkBufferImageCopy *r){(void)c;assert(objects[b].type==BUF&&i>=100&&i<=102&&l==VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL&&n==1);assert(r->imageOffset.y==frame.y&&r->imageExtent.width==1280&&r->imageExtent.height==252);}
static VkResult submit(VkQueue q,uint32_t n,const VkSubmitInfo *s,VkFence f){(void)q;assert(n==1&&s->commandBufferCount==1&&s->signalSemaphoreCount==1&&objects[f].type==FENCE&&!objects[f].signaled);assert(s->waitSemaphoreCount==2&&s->pWaitSemaphores[0]==801&&s->pWaitSemaphores[1]==802);assert(s->pWaitDstStageMask[0]==VK_PIPELINE_STAGE_ALL_COMMANDS_BIT&&objects[*s->pSignalSemaphores].type==SEM);VkResult r=api();if(!r)submits++;return r;}
#include "../src/runtime/fextendo_osk_vulkan.h"
static struct vulkan_instance instance={.p_vkGetPhysicalDeviceMemoryProperties=props};
static struct vulkan_physical_device physical={.instance=&instance};
static VkQueueFamilyProperties families[2]={{.queueFlags=VK_QUEUE_GRAPHICS_BIT},{.queueFlags=0}};
static struct vulkan_device device={.physical_device=&physical,.queue_props=families,
.p_vkAllocateCommandBuffers=alloc_cmd,
.p_vkAllocateMemory=allocate,
.p_vkBeginCommandBuffer=begin,
.p_vkBindBufferMemory=bind,
.p_vkCmdCopyBufferToImage=copy,
.p_vkCmdPipelineBarrier=barrier,
.p_vkCreateBuffer=create_buffer,
.p_vkCreateCommandPool=create_pool,
.p_vkCreateFence=create_fence,
.p_vkCreateSemaphore=create_sem,
.p_vkDestroyBuffer=destroy_buffer,
.p_vkDestroyCommandPool=destroy_pool,
.p_vkDestroyFence=destroy_fence,
.p_vkDestroySemaphore=destroy_sem,
.p_vkEndCommandBuffer=end,
.p_vkFreeMemory=free_mem,
.p_vkGetBufferMemoryRequirements=req,
.p_vkGetSwapchainImagesKHR=images,
.p_vkMapMemory=map,
.p_vkQueueSubmit=submit,
.p_vkResetCommandBuffer=reset_cmd,
.p_vkResetFences=reset_fence,
.p_vkUnmapMemory=unmap,
.p_vkWaitForFences=wait_fence,
};
static struct vulkan_queue queue={.device=&device};
static void fresh(void){if(chain.nx_osk)nx_osk_free(&device,chain.nx_osk);assert(!live);memset(objects,0,sizeof(objects));chain=(struct swapchain){.obj.host.swapchain=55,.nx_extent={1280,720},.nx_format=VK_FORMAT_B8G8R8A8_UNORM,.nx_osk_usable=1};step=fail_at=next_id=pools=submits=copies=rejects=records=0;visible=1;stale=alloc_fail=0;frame=(struct fx_osk_frame){.width=1280,.height=252,.y=468,.session=1,.generation=1};queue.info.queueFamilyIndex=0;}
static uint64_t present(unsigned index){VkSwapchainKHR client=1;VkSemaphore waits[]={801,802};struct mempool pool={0};VkPresentInfoKHR p={.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,.swapchainCount=1,.pSwapchains=&client,.pImageIndices=&index,.waitSemaphoreCount=2,.pWaitSemaphores=waits};uint64_t s=nx_osk_present(&queue,&p,&client,&pool);if(s){assert(p.waitSemaphoreCount==1&&p.pWaitSemaphores!=waits&&*p.pWaitSemaphores==chain.nx_osk->per[index].done);}else assert(p.waitSemaphoreCount==2&&p.pWaitSemaphores==waits);free(pool.p);return s;}
static void finish(unsigned i){objects[chain.nx_osk->per[i].fence].signaled=1;}
int main(void){
fresh();visible=0;assert(!present(0)&&!step&&!live&&!rejects);
visible=1;assert(present(0)==1&&submits==1&&copies==1&&!format_rgba);unsigned total=step;finish(0);
assert(present(0)==1&&copies==1&&records==1);finish(0);
frame.y=0;frame.generation++;assert(present(0)==1&&pools==1&&records==2&&copies==2);finish(0);
assert(present(1)==1&&pools==1);finish(1);assert(present(2)==1);finish(2);
for(unsigned i=1;i<=total;i++){fresh();fail_at=i;assert(!present(0)&&rejects==1&&!submits);}
fresh();stale=1;assert(!present(0)&&!submits&&!rejects);stale=0;assert(present(0)==1);finish(0);
fresh();assert(present(0)==1);frame.generation++;assert(!present(0)&&copies==1&&records==1&&submits==1&&rejects==1);
fresh();alloc_fail=1;assert(!present(0)&&rejects==1&&!submits);
fresh();chain.nx_osk_usable=0;assert(!present(0)&&!step&&rejects==1);
fresh();queue.info.queueFamilyIndex=1;assert(!present(0)&&!step&&rejects==1);
fresh();chain.nx_format=VK_FORMAT_R8G8B8A8_SRGB;assert(present(0)&&format_rgba);finish(0);
fresh();assert(!present(3)&&rejects==1&&!submits);
fresh();assert(!live);puts("PASS: Vulkan wait chain, fences, no hidden work, cached pixels, move, all API failures, cleanup and stale snapshot");return 0;}
