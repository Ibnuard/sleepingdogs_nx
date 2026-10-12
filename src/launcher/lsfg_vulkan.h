/* SPDX-License-Identifier: GPL-3.0-or-later. Native host presentation adapter. */
#pragma once
#include <vulkan/vulkan.h>
extern "C" {
void sd_lsfg_native_configure(int enabled);
PFN_vkVoidFunction sd_lsfg_intercept(const char*,PFN_vkVoidFunction);
VkResult sd_lsfg_create_device(VkPhysicalDevice,const VkDeviceCreateInfo*,const VkAllocationCallbacks*,VkDevice*);
void sd_lsfg_destroy_device(VkDevice);
void sd_lsfg_queue(VkDevice,uint32_t,VkQueue);
VkResult sd_lsfg_create_chain(VkDevice,const VkSwapchainCreateInfoKHR*,const VkAllocationCallbacks*,VkSwapchainKHR*);
void sd_lsfg_destroy_chain(VkSwapchainKHR);
VkResult sd_lsfg_present(VkQueue,const VkPresentInfoKHR*);
}
