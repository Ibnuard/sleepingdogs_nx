/* SPDX-License-Identifier: MIT; per-present mode persistence, not just pNext. */
#include "lsfg_present_policy.h"
#include <cassert>
#include <cstdio>
int main() {
    SdLsfgPresentPolicy policy;
    VkPresentInfoKHR info{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};info.swapchainCount=1;
    assert(policy.update(&info));
    VkPresentModeKHR selected=VK_PRESENT_MODE_FIFO_KHR;
    VkSwapchainPresentModeInfoEXT mode{VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODE_INFO_EXT};
    mode.swapchainCount=1;mode.pPresentModes=&selected;
    VkPresentIdKHR id{VK_STRUCTURE_TYPE_PRESENT_ID_KHR};uint64_t serial=91;id.swapchainCount=1;id.pPresentIds=&serial;id.pNext=&mode;
    info.pNext=&id;assert(policy.update(&info));assert(info.pNext==&id&&id.pNext==&mode&&serial==91);
    selected=VK_PRESENT_MODE_MAILBOX_KHR;assert(!policy.update(&info));
    info.pNext=nullptr;assert(!policy.update(&info)); // Vulkan persists the last mode.
    selected=VK_PRESENT_MODE_FIFO_KHR;info.pNext=&id;assert(policy.update(&info));
    mode.swapchainCount=0;assert(!policy.update(&info));mode.swapchainCount=1;
    mode.pPresentModes=nullptr;assert(!policy.update(&info));mode.pPresentModes=&selected;
    info.swapchainCount=2;assert(!policy.update(&info));info.swapchainCount=1;
    unsigned emitted=0;for(unsigned i=0;i<5034;++i)emitted+=policy.log_bypass();assert(emitted==13);
    std::puts("PASS: FIFO metadata accepted, non-FIFO persists, invalid count/pointer bypass, 5034 bypasses -> 13 logs");
}
