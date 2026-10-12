/* SPDX-License-Identifier: MIT; preserve Vulkan's persistent present mode. */
#pragma once
#include <vulkan/vulkan.h>
struct SdLsfgPresentPolicy {
    VkPresentModeKHR mode=VK_PRESENT_MODE_FIFO_KHR;
    unsigned bypasses=0;
    bool noted_fifo=false;
    bool update(const VkPresentInfoKHR *info) {
        if(info->swapchainCount!=1)return false;
        for(auto next=static_cast<const VkBaseInStructure*>(info->pNext);next;next=next->pNext)
            if(next->sType==VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODE_INFO_EXT) {
                auto modes=reinterpret_cast<const VkSwapchainPresentModeInfoEXT*>(next);
                if(modes->swapchainCount!=1||!modes->pPresentModes)return false;
                mode=modes->pPresentModes[0];
            }
        return mode==VK_PRESENT_MODE_FIFO_KHR;
    }
    bool log_bypass(){unsigned n=++bypasses;return (n&(n-1))==0;}
};
