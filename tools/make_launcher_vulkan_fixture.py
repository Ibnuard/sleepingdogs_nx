"""Adapt the pinned PES Vulkan API model to our native loader interposer."""
from pathlib import Path
from launcher_v1_overlay import ROOT

def main():
    old=(ROOT/'tests/pes13/fextendo_osk_vulkan.c').read_text()
    core=old[old.index('static unsigned step'):old.index('#include "../src/runtime/fextendo_osk_vulkan.h"')]
    core=core.replace('static void *mem_alloc(struct mempool *p,size_t n){assert(!p->p);if(alloc_fail)return NULL;return p->p=calloc(1,n);}','')
    pairs={'images':'vkGetSwapchainImagesKHR','props':'vkGetPhysicalDeviceMemoryProperties','create_pool':'vkCreateCommandPool',
        'destroy_pool':'vkDestroyCommandPool','create_sem':'vkCreateSemaphore','destroy_sem':'vkDestroySemaphore',
        'create_buffer':'vkCreateBuffer','destroy_buffer':'vkDestroyBuffer','req':'vkGetBufferMemoryRequirements','allocate':'vkAllocateMemory',
        'free_mem':'vkFreeMemory','bind':'vkBindBufferMemory','map':'vkMapMemory','unmap':'vkUnmapMemory','create_fence':'vkCreateFence',
        'destroy_fence':'vkDestroyFence','wait_fence':'vkWaitForFences','reset_fence':'vkResetFences','alloc_cmd':'vkAllocateCommandBuffers',
        'reset_cmd':'vkResetCommandBuffer','begin':'vkBeginCommandBuffer','end':'vkEndCommandBuffer','barrier':'vkCmdPipelineBarrier',
        'copy':'vkCmdCopyBufferToImage','submit':'vkQueueSubmit'}
    import re
    for short,api in pairs.items():
        core=re.sub(r'static (VkResult|void) '+short+r'\(',r'\1 VKAPI_CALL '+api+'(',core)
    core=core.replace('return 0;}','return VK_SUCCESS;}')
    core=core.replace('if(!r)submits++;','if(!r){submits++;submitted_wait=*s->pSignalSemaphores;}')
    header='''/* LGPL-2.1-or-later. API model adapted from PES13 38750c20 test.
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
'''
    tail=(ROOT/'tests/launcher_vulkan_tail.inc').read_text()
    (ROOT/'tests/launcher_osk_vulkan.cpp').write_text(header+core+tail,newline='\n')
if __name__=='__main__':main()
