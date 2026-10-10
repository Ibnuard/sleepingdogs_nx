"""Exercise production ZCULL, descriptor-delta and submission guards on host."""
from pathlib import Path
import argparse
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from build_mesa_backport import WORK, prepare, sha, write_json


def function(source, name):
    text = source.read_text()
    match = re.search(r'^'+re.escape(name)+r'\(', text, re.M)
    assert match, name
    start = text.rfind('\n', 0, match.start()-1)+1
    opening = text.index('{', match.end())
    depth = 1
    end = opening+1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]+'\n'


PRELUDE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <stddef.h>
#include <pthread.h>
#define __SWITCH__ 1
#define HAVE_SWITCH_PLATFORM 1
#define DIV_ROUND_UP(a,b) (((a)+(b)-1)/(b))
#define VK_IMAGE_TYPE_2D 1
#define VK_IMAGE_CREATE_ALIAS_BIT 1024
#define VK_IMAGE_LAYOUT_UNDEFINED 0
#define VK_IMAGE_ASPECT_DEPTH_BIT 2
#define VK_SUCCESS 0
#define NVKMD_MEM_SHARED 16
#define VKAPI_ATTR
#define VKAPI_CALL
#define VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT 1
#define VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT 2
#define VK_MEMORY_PROPERTY_HOST_COHERENT_BIT 4
#define VK_MEMORY_PROPERTY_HOST_CACHED_BIT 8
#define VK_MEMORY_HEAP_DEVICE_LOCAL_BIT 1
#define VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_ALLOCATION_BIT_EXT 128
#define VK_ERROR_INVALID_EXTERNAL_HANDLE -4
#define VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT 1024
#define NV_DEVICE_TYPE_SOC 1
#define BITFIELD_BIT(i) (1u<<(i))
#define vk_error(dev,err) ((void)(dev),(err))
typedef int VkResult;
struct nil_zcull {uint64_t size_B, align_B;};
struct nvk_zcull_plane {struct nil_zcull nil; uint64_t addr, plane_offset_B; bool transient_eligible;};
struct nvk_image {struct {uint32_t image_type, mip_levels, array_layers, external_handle_types, create_flags,usage; struct {uint32_t width,height;} extent;} vk; struct nvk_zcull_plane zcull;};
struct nv_zcull_device_info {uint32_t width_align_pixels,height_align_pixels,pixel_squares_by_aliquots,aliquot_total,zcull_region_byte_multiplier,zcull_region_header_size,zcull_subregion_header_size,subregion_count,subregion_width_align_pixels,subregion_height_align_pixels,ctxsw_size,ctxsw_align;};
struct nv_device_info {bool has_zcull_info; struct nv_zcull_device_info zcull_info;uint32_t type;uint64_t vram_size_B,bar_size_B;};
typedef uint32_t VkMemoryPropertyFlags;
typedef uint32_t VkExternalMemoryHandleTypeFlagBits;
typedef struct {uint32_t propertyFlags,heapIndex;} VkMemoryType;
typedef struct {uint32_t memoryTypeBits;} VkMemoryHostPointerPropertiesEXT;
struct nvk_physical_device {struct nv_device_info info;uint32_t mem_heap_count,mem_type_count;VkMemoryType mem_types[3];struct {uint32_t flags;} mem_heaps[3];};
struct nvk_device {struct nvk_physical_device *pdev;};
typedef struct nvk_device *VkDevice;
static const struct nvk_physical_device *nvk_device_physical(struct nvk_device *dev) {return dev->pdev;}
static unsigned zcull_log_count;
static void _debug_printf(const char *fmt,...) {if(strstr(fmt,"ZCULL active"))__atomic_fetch_add(&zcull_log_count,1,__ATOMIC_RELAXED);}
typedef struct {uint32_t width_align_pixels,height_align_pixels,pixel_squares_by_aliquots,aliquot_total,region_byte_multiplier,region_header_size,subregion_header_size,subregion_count,subregion_width_align_pixels,subregion_height_align_pixels;} nvioctl_zcull_info;
static nvioctl_zcull_info geometry;
static bool missing_geometry;
static uint32_t context_size = 4096;
static const nvioctl_zcull_info *nvGpuGetZcullInfo(void) {return missing_geometry?NULL:&geometry;}
static uint32_t nvGpuGetZcullCtxSize(void) {return context_size;}
struct nvk_image_view {struct {struct nvk_image *image; uint32_t base_mip_level,base_array_layer,layer_count;} vk;};
struct nvk_rendering_state {struct {struct nvk_image_view *iview;} depth_att; bool linear; uint32_t view_mask,layer_count; struct {struct {uint32_t width,height;} extent;} area;};
struct fake_va {uint64_t addr;};
struct fake_mem {uint32_t flags; struct fake_va *va;};
struct nvk_device_memory {struct fake_mem *mem;struct {void *host_ptr;} vk;};
struct nvk_cmd_buffer {uint32_t unused;};
typedef struct {uint32_t oldLayout,newLayout;struct {uint32_t aspectMask;} subresourceRange;struct nvk_image *image;} VkImageMemoryBarrier2;
typedef struct {uint32_t imageMemoryBarrierCount; const VkImageMemoryBarrier2 *pImageMemoryBarriers;} VkDependencyInfo;
struct nv_push {uint32_t unused;};
static struct nv_push push;
static uint32_t fills, completions, methods;
static uint64_t last_fill_addr, last_fill_size;
#define VK_FROM_HANDLE(type,name,handle) struct type *name=(handle)
static void nvk_cmd_fill_memory_ce(struct nvk_cmd_buffer *cmd,uint64_t addr,uint64_t size,uint32_t value) {(void)cmd;assert(addr&&size&&value==0);fills++;last_fill_addr=addr;last_fill_size=size;}
static struct nv_push *nvk_cmd_buffer_push(struct nvk_cmd_buffer *cmd,uint32_t count) {(void)cmd;assert(count==5);completions++;return &push;}
#define P_MTHD(...) ((void)0)
#define P_NV90B5_LINE_LENGTH_IN(p,v) assert((p)==&push && (v)==0)
#define P_NV90B5_LINE_COUNT(p,v) assert((p)==&push && (v)==0)
#define P_IMMD(...) (methods++)
#define GPFIFO_QUEUE_SIZE 0x800u
#define NOUVEAU_HORIZON_GPFIFO_SUBMIT_CAPACITY (GPFIFO_QUEUE_SIZE - 3u)
enum nouveau_horizon_status {NOUVEAU_HORIZON_SUCCESS,NOUVEAU_HORIZON_ERROR_NO_SPACE};
struct nouveau_horizon_device {bool total_order_channels;};
struct nouveau_horizon_channel {struct nouveau_horizon_device *device; struct {uint32_t num_entries;} gpu_channel;bool mapped_completion_enabled;};
'''

HARNESS = r'''
static uint32_t seed=137;
static uint32_t random_u32(void) {seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;return seed;}
static void *log_worker(void *arg) {(void)arg;for(unsigned i=0;i<10000;i++)nvk_sd_v13_report_zcull(i&1);return NULL;}
int main(void) {
  uint64_t cases=0;
  struct nvk_physical_device physical={.info={.type=NV_DEVICE_TYPE_SOC},.mem_heap_count=1};
  setup_soc_memory(&physical);
  assert(physical.mem_type_count==3 && physical.mem_heaps[0].flags==VK_MEMORY_HEAP_DEVICE_LOCAL_BIT);
  assert(physical.mem_types[0].propertyFlags==VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
  assert(physical.mem_types[1].propertyFlags==(VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT|VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_CACHED_BIT));
  assert(physical.mem_types[2].propertyFlags==(VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT|VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT));
  for(unsigned i=0;i<3;i++)assert(physical.mem_types[i].heapIndex==0);
  struct nvk_device device_props={&physical};VkMemoryHostPointerPropertiesEXT imported={0};
  assert(nvk_GetMemoryHostPointerPropertiesEXT(&device_props,VK_EXTERNAL_MEMORY_HANDLE_TYPE_HOST_ALLOCATION_BIT_EXT,&physical,&imported)==VK_SUCCESS);
  assert(imported.memoryTypeBits==6); /* GPU-only type never enters 32-bit imports. */
  assert(nvk_GetMemoryHostPointerPropertiesEXT(&device_props,999,&physical,&imported)==VK_ERROR_INVALID_EXTERNAL_HANDLE);
  struct nvk_image mask_image={0};assert(image_memory_types(&physical,&mask_image)==7);
  mask_image.vk.usage=VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT;physical.info.vram_size_B=1024;physical.info.bar_size_B=0;
  assert(image_memory_types(&physical,&mask_image)==6);
  pthread_t threads[8];for(unsigned i=0;i<8;i++)assert(pthread_create(&threads[i],NULL,log_worker,NULL)==0);
  for(unsigned i=0;i<8;i++)assert(pthread_join(threads[i],NULL)==0);
  assert(zcull_log_count==2);
  /* Compare real descriptor helper against a simple byte-validity oracle. */
  uint32_t before[64], after[64];
  for(uint32_t run=0;run<100000;run++) {
    uint32_t start=random_u32()%65,end=start+random_u32()%(65-start);
    uint64_t valid=((uint64_t)random_u32()<<32)|random_u32();
    for(uint32_t i=0;i<64;i++) {before[i]=random_u32();after[i]=(random_u32()%3)?before[i]:random_u32();}
    struct nvk_descriptor_delta got=nvk_descriptor_delta(before,after,valid,start,end);
    uint64_t changed=0;uint32_t first=end,last=end;
    for(uint32_t i=start;i<end;i++) {
      if(before[i]!=after[i])changed|=UINT64_C(1)<<i;
      if(before[i]!=after[i] || !(valid&(UINT64_C(1)<<i))) {if(first==end)first=i;last=i+1;}
    }
    assert(got.changed==changed && got.first==first && got.count==last-first);
    uint64_t range=0;for(uint32_t i=start;i<end;i++)range|=UINT64_C(1)<<i;
    assert(nvk_descriptor_range_mask(start,end)==range);cases++;
  }
  assert(nvk_descriptor_range_mask(0,64)==UINT64_MAX);
  /* Valid runtime geometry, then each invalid field/overflow guard. */
  geometry=(nvioctl_zcull_info){16,16,16,512,32,32,32,16,16,16};
  struct nv_device_info info={0};nouveau_horizon_add_zcull_info(&info);
  assert(info.has_zcull_info && info.zcull_info.ctxsw_size==4096 && info.zcull_info.ctxsw_align==4096);
  nvioctl_zcull_info saved=geometry;
  const size_t offsets[]={offsetof(nvioctl_zcull_info,width_align_pixels),offsetof(nvioctl_zcull_info,height_align_pixels),offsetof(nvioctl_zcull_info,pixel_squares_by_aliquots),offsetof(nvioctl_zcull_info,aliquot_total),offsetof(nvioctl_zcull_info,region_byte_multiplier),offsetof(nvioctl_zcull_info,region_header_size),offsetof(nvioctl_zcull_info,subregion_header_size),offsetof(nvioctl_zcull_info,subregion_count),offsetof(nvioctl_zcull_info,subregion_width_align_pixels),offsetof(nvioctl_zcull_info,subregion_height_align_pixels)};
  for(unsigned f=0;f<10;f++) {
    uint32_t *field=(uint32_t *)((char *)&geometry+offsets[f]);
    geometry=saved;*field=0;nouveau_horizon_add_zcull_info(&info);
    if(f!=5 && f!=6)assert(!info.has_zcull_info);
    cases++;
  }
  const unsigned narrow[]={0,1,3,8,9};
  for(unsigned i=0;i<5;i++){geometry=saved;*(uint32_t *)((char *)&geometry+offsets[narrow[i]])=65536;nouveau_horizon_add_zcull_info(&info);assert(!info.has_zcull_info);cases++;}
  geometry=saved;geometry.subregion_count=17;nouveau_horizon_add_zcull_info(&info);assert(!info.has_zcull_info);
  geometry=saved;geometry.region_byte_multiplier=3;nouveau_horizon_add_zcull_info(&info);assert(!info.has_zcull_info);
  geometry=saved;geometry.region_header_size=3;nouveau_horizon_add_zcull_info(&info);assert(!info.has_zcull_info);
  geometry=saved;geometry.subregion_header_size=3;nouveau_horizon_add_zcull_info(&info);assert(!info.has_zcull_info);
  geometry=saved;geometry.region_byte_multiplier=UINT32_MAX-3;nouveau_horizon_add_zcull_info(&info);assert(!info.has_zcull_info);
  geometry=saved;missing_geometry=true;nouveau_horizon_add_zcull_info(&info);assert(!info.has_zcull_info);missing_geometry=false;
  context_size=0;nouveau_horizon_add_zcull_info(&info);assert(!info.has_zcull_info);context_size=4096;
  nouveau_horizon_add_zcull_info(NULL);nouveau_horizon_add_zcull_info(&info);
  struct nvk_image im={.vk={.image_type=VK_IMAGE_TYPE_2D,.mip_levels=1,.array_layers=1,.extent={1280,720}},.zcull={.nil={4096,4096},.addr=0x100000}};
  assert(nvk_switch_image_has_zcull_layout(&im,&info.zcull_info));
  struct nvk_image original=im;
  im.vk.mip_levels=2;assert(!nvk_switch_image_has_zcull_layout(&im,&info.zcull_info));im=original;
  im.vk.array_layers=2;assert(!nvk_switch_image_has_zcull_layout(&im,&info.zcull_info));im=original;
  im.vk.image_type=3;assert(!nvk_switch_image_has_zcull_layout(&im,&info.zcull_info));im=original;
  im.vk.external_handle_types=1;assert(!nvk_switch_image_has_zcull_layout(&im,&info.zcull_info));im=original;
  im.vk.create_flags=VK_IMAGE_CREATE_ALIAS_BIT;assert(!nvk_switch_image_has_zcull_layout(&im,&info.zcull_info));im=original;
  im.vk.extent.width=UINT32_MAX;assert(!nvk_switch_image_has_zcull_layout(&im,&info.zcull_info));im=original;
  im.vk.extent.height=65536;assert(!nvk_switch_image_has_zcull_layout(&im,&info.zcull_info));im=original;
  struct nvk_image_view view={.vk={.image=&im,.layer_count=1}};
  struct nvk_rendering_state render={.depth_att={&view},.layer_count=1,.area={{1280,720}}};
  assert(nvk_get_zcull_image(&render)==&im);
  render.linear=true;assert(nvk_get_zcull_image(&render)==NULL);render.linear=false;
  render.view_mask=2;assert(nvk_get_zcull_image(&render)==NULL);render.view_mask=0;
  render.layer_count=2;assert(nvk_get_zcull_image(&render)==NULL);render.layer_count=1;
  render.area.extent.width=0;assert(nvk_get_zcull_image(&render)==NULL);render.area.extent.width=1280;
  view.vk.base_mip_level=1;assert(nvk_get_zcull_image(&render)==NULL);view.vk.base_mip_level=0;
  view.vk.base_array_layer=1;assert(nvk_get_zcull_image(&render)==NULL);view.vk.base_array_layer=0;
  view.vk.layer_count=2;assert(nvk_get_zcull_image(&render)==NULL);view.vk.layer_count=1;
  render.depth_att.iview=NULL;assert(nvk_get_zcull_image(&render)==NULL);
  /* Imported/shared backing is deliberately ineligible: never silently bypass. */
  struct fake_va va={0x200000};struct fake_mem memory={0,&va};
  struct nvk_device_memory devmem={&memory,{NULL}};
  assert(nvk_image_zcull_bind(&im.zcull,&devmem,4096)==VK_SUCCESS && im.zcull.addr==0x201000);
  memory.flags=NVKMD_MEM_SHARED;nvk_image_zcull_bind(&im.zcull,&devmem,4096);assert(im.zcull.addr==0);
  memory.flags=0;devmem.vk.host_ptr=&va;nvk_image_zcull_bind(&im.zcull,&devmem,4096);assert(im.zcull.addr==0);
  im=original;
  struct nvk_cmd_buffer cmd={0};
  VkImageMemoryBarrier2 barriers[2]={{0,1,{VK_IMAGE_ASPECT_DEPTH_BIT},&im},{0,1,{VK_IMAGE_ASPECT_DEPTH_BIT},&im}};
  VkDependencyInfo dep={2,barriers};
  nvk_cmd_image_layout_transition(&cmd,&dep);assert(fills==2 && completions==1 && methods==1 && last_fill_addr==im.zcull.addr && last_fill_size==4096);
  fills=completions=methods=0;barriers[0].subresourceRange.aspectMask=1;barriers[1].oldLayout=1;
  nvk_cmd_image_layout_transition(&cmd,&dep);assert(fills==0 && completions==0);
  barriers[0].subresourceRange.aspectMask=VK_IMAGE_ASPECT_DEPTH_BIT;im.zcull.addr=0;
  nvk_cmd_image_layout_transition(&cmd,&dep);assert(fills==0 && completions==0);
  im=original;barriers[0].newLayout=0;nvk_cmd_image_layout_transition(&cmd,&dep);assert(fills==0 && completions==0);
  /* Fence/report reservations, native pre/post fences and empty ring slot. */
  struct nouveau_horizon_device device={false};struct nouveau_horizon_channel ch={.device=&device};
  for(unsigned mapped=0;mapped<2;mapped++)for(unsigned order=0;order<2;order++) {
    ch.mapped_completion_enabled=mapped;device.total_order_channels=order;
    for(unsigned current=0;current<2052;current++)for(unsigned incoming=0;incoming<2052;incoming+=7) {
      ch.gpu_channel.num_entries=current;
      uint64_t required=(uint64_t)current+incoming+(mapped?2:1)+order+3;
      bool fit=required<=GPFIFO_QUEUE_SIZE;
      assert((nouveau_horizon_channel_reserve_entries_locked(&ch,incoming,0)==NOUVEAU_HORIZON_SUCCESS)==fit);cases++;
    }
  }
  ch.gpu_channel.num_entries=UINT32_MAX;assert(nouveau_horizon_channel_reserve_entries_locked(&ch,UINT32_MAX,UINT32_MAX)==NOUVEAU_HORIZON_ERROR_NO_SPACE);
  printf("PASS %llu production guard/delta cases; ZCULL import exclusions and one completion per fill batch retained\n",(unsigned long long)cases);
  return 0;
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=WORK)
    work=p.parse_args().work
    prepared=prepare(work)
    source=work/'source'
    checks=work/'checks';checks.mkdir(exist_ok=True)
    parts=[PRELUDE,'#define USE_GCC_ATOMIC_BUILTINS 1\n#include "'+str(source/'src/util/u_atomic.h')+'"',
           (source/'src/nouveau/vulkan/nvk_descriptor_delta.h').read_text()]
    selected={
        'src/nouveau/horizon/nouveau_horizon_device.c':['nouveau_horizon_add_zcull_info'],
        'src/nouveau/vulkan/nvk_image.c':['nvk_switch_image_has_zcull_layout','nvk_image_zcull_bind'],
        'src/nouveau/vulkan/nvk_cmd_draw.c':['nvk_get_zcull_image','nvk_sd_v13_report_zcull'],
        'src/nouveau/vulkan/nvk_cmd_buffer.c':['nvk_cmd_image_layout_transition'],
        'src/nouveau/vulkan/nvk_device_memory.c':['nvk_GetMemoryHostPointerPropertiesEXT'],
        'src/nouveau/horizon/nouveau_horizon_channel.c':['nouveau_horizon_channel_reserve_entries_locked'],
    }
    for name, functions in selected.items():
        for func in functions:parts.append(function(source/name,func))
    physical=(source/'src/nouveau/vulkan/nvk_physical_device.c').read_text()
    start=physical.index('   if (pdev->info.type == NV_DEVICE_TYPE_SOC) {')
    end=physical.index('   } else {',start)
    parts.append('static void setup_soc_memory(struct nvk_physical_device *pdev) {\nconst uint32_t sysmem_heap_idx=0;\n'+physical[start:end]+'\n}\n}\n')
    image=(source/'src/nouveau/vulkan/nvk_image.c').read_text()
    start=image.index('   uint32_t memory_types = (1 << pdev->mem_type_count) - 1;')
    end=image.index('   uint64_t size_B = 0;',start)
    parts.append('static uint32_t image_memory_types(const struct nvk_physical_device *pdev,struct nvk_image *image) {\n'+image[start:end]+'return memory_types;\n}\n')
    parts.append(HARNESS)
    c=checks/'production-guards.c';c.write_text('\n'.join(parts))
    exe=checks/'production-guards'
    with (checks/'compile.log').open('w') as log:
        subprocess.run(['cc','-std=c11','-O1','-g','-fsanitize=address,undefined',
                        '-fno-sanitize-recover=all','-fno-pie','-no-pie','-pthread',
                        '-I'+str(source/'include'),str(c),'-o',str(exe)],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
    output=subprocess.check_output([str(exe)],text=True,timeout=60).strip()
    write_json(ROOT/'reports/mesa-v13-host.json',dict(status='PASS',result=output,
        sanitizers=['address','undefined'],hardware_tested=False,
        changed_sources=prepared['changed'],production_functions=selected,
        test_sources={n:sha(ROOT/n) for n in ('tests/check_mesa_backport.py','tools/build_mesa_backport.py')},
        generated_harness_sha256=sha(c)))
    print(output,flush=True)


if __name__=='__main__':main()
