/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Adapted from Autorun (Wine-NX), dlls/win32u/vulkan.c, nx_osk_*:
 * https://github.com/autorunhq/autorun/blob/cbb0e4e6e7fa7f47f328d92441f51bfb507f266f/dlls/win32u/vulkan.c
 * Copyright contributors to Autorun/Wine. See COPYING.LIB and AUTHORS.
 * FEXTendo additions: per-image transfer fences, checked begin/reset, partial
 * allocation cleanup, geometry snapshots, presenter acknowledgement and fail
 * recovery. Closed keyboard performs no allocation, copy or extra submission.
 */
struct nx_osk_image
{
    VkCommandBuffer cmd;
    VkSemaphore done;
    VkBuffer buffer;
    VkDeviceMemory memory;
    void *pixels;
    uint64_t generation;
    VkFence fence;
    int x, y, recorded;
};

struct nx_osk_overlay
{
    uint32_t count, family;
    VkImage *images;
    struct nx_osk_image *per;
    VkCommandPool pool;
    int width, height;
    BOOL failed;
};

static void nx_osk_release( struct vulkan_device *device, struct nx_osk_overlay *osk )
{
    uint32_t i;

    for (i = 0; osk->per && i < osk->count; i++)
    {
        struct nx_osk_image *per = &osk->per[i];

        if (per->pixels) device->p_vkUnmapMemory( device->host.device, per->memory );
        device->p_vkDestroyFence( device->host.device, per->fence, NULL );
        device->p_vkDestroySemaphore( device->host.device, per->done, NULL );
        device->p_vkDestroyBuffer( device->host.device, per->buffer, NULL );
        device->p_vkFreeMemory( device->host.device, per->memory, NULL );
    }
    if (osk->pool) device->p_vkDestroyCommandPool( device->host.device, osk->pool, NULL );
    osk->pool = VK_NULL_HANDLE;
    if (osk->per) memset( osk->per, 0, osk->count * sizeof(*osk->per) );
    osk->width = osk->height = 0;
}

static void nx_osk_free( struct vulkan_device *device, struct nx_osk_overlay *osk )
{
    nx_osk_release( device, osk );
    free( osk->per );
    free( osk->images );
    free( osk );
}

static VkResult nx_osk_record( struct vulkan_device *device, struct nx_osk_overlay *osk, uint32_t i, const struct fx_osk_frame *frame )
{
    VkResult result;
    VkCommandBufferBeginInfo begin = {.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    VkImageMemoryBarrier barrier = {.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
    VkBufferImageCopy region = {0};
    VkCommandBuffer cmd = osk->per[i].cmd;

    if ((result = device->p_vkResetCommandBuffer( cmd, 0 ))) return result;
    if ((result = device->p_vkBeginCommandBuffer( cmd, &begin ))) return result;
    /* Whatever wrote the image before, in this queue or waited for, is done:
     * the program's frame stays, the keyboard goes over it. */
    barrier.oldLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
    barrier.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    barrier.srcAccessMask = VK_ACCESS_MEMORY_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    barrier.srcQueueFamilyIndex = barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.image = osk->images[i];
    barrier.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    barrier.subresourceRange.levelCount = barrier.subresourceRange.layerCount = 1;
    device->p_vkCmdPipelineBarrier( cmd, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT,
                                    0, 0, NULL, 0, NULL, 1, &barrier );
    region.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    region.imageSubresource.layerCount = 1;
    region.imageOffset.x = frame->x;
    region.imageOffset.y = frame->y;
    region.imageExtent.width = osk->width;
    region.imageExtent.height = osk->height;
    region.imageExtent.depth = 1;
    device->p_vkCmdCopyBufferToImage( cmd, osk->per[i].buffer, osk->images[i],
                                      VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &region );
    barrier.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    barrier.newLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
    barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    barrier.dstAccessMask = 0;
    device->p_vkCmdPipelineBarrier( cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,
                                    0, 0, NULL, 0, NULL, 1, &barrier );
    return device->p_vkEndCommandBuffer( cmd );
}

/* One staging allocation, command, fence and completion semaphore per image.
 * Keep these until swapchain destruction; moving the keyboard only re-records
 * the current image after its previous transfer fence has completed. */
static BOOL nx_osk_prepare( struct vulkan_device *device, struct swapchain *swapchain, uint32_t family,
                            const struct fx_osk_frame *frame )
{
    struct vulkan_physical_device *physical_device = device->physical_device;
    struct nx_osk_overlay *osk = swapchain->nx_osk;
    VkPhysicalDeviceMemoryProperties props;
    uint32_t i, t;

    if (!osk)
    {
        if (!(osk = swapchain->nx_osk = calloc( 1, sizeof(*osk) ))) return FALSE;
        if (device->p_vkGetSwapchainImagesKHR( device->host.device, swapchain->obj.host.swapchain, &osk->count, NULL ) ||
            !osk->count || osk->count > 16 ||
            !(osk->images = calloc( osk->count, sizeof(*osk->images) )) ||
            !(osk->per = calloc( osk->count, sizeof(*osk->per) )) ||
            device->p_vkGetSwapchainImagesKHR( device->host.device, swapchain->obj.host.swapchain, &osk->count, osk->images ))
            osk->failed = TRUE;
    }
    if (osk->failed) return FALSE;
    if (osk->pool)
        return osk->family == family && osk->width == frame->width && osk->height == frame->height;

    physical_device->instance->p_vkGetPhysicalDeviceMemoryProperties( physical_device->host.physical_device, &props );
    {
        VkCommandPoolCreateInfo pool_info = {.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};

        pool_info.queueFamilyIndex = family;
        pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        if (device->p_vkCreateCommandPool( device->host.device, &pool_info, NULL, &osk->pool )) goto failed;
    }
    osk->family = family;
    osk->width = frame->width;
    osk->height = frame->height;
    for (i = 0; i < osk->count; i++)
    {
        struct nx_osk_image *per = &osk->per[i];
        VkBufferCreateInfo buffer_info = {.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        VkMemoryAllocateInfo alloc = {.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        VkCommandBufferAllocateInfo cmd_info = {.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        VkSemaphoreCreateInfo semaphore_info = {.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
        VkFenceCreateInfo fence_info = {.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO, .flags = VK_FENCE_CREATE_SIGNALED_BIT};
        VkMemoryRequirements req;

        buffer_info.size = (VkDeviceSize)frame->width * frame->height * 4;
        buffer_info.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
        if (device->p_vkCreateBuffer( device->host.device, &buffer_info, NULL, &per->buffer )) goto failed;
        device->p_vkGetBufferMemoryRequirements( device->host.device, per->buffer, &req );
        for (t = 0; t < props.memoryTypeCount; t++)
            if ((req.memoryTypeBits & (1u << t)) &&
                (props.memoryTypes[t].propertyFlags & (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) ==
                    (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))
                break;
        if (t == props.memoryTypeCount) goto failed;
        alloc.allocationSize = req.size;
        alloc.memoryTypeIndex = t;
        if (device->p_vkAllocateMemory( device->host.device, &alloc, NULL, &per->memory ) ||
            device->p_vkBindBufferMemory( device->host.device, per->buffer, per->memory, 0 ) ||
            device->p_vkMapMemory( device->host.device, per->memory, 0, buffer_info.size, 0, &per->pixels ) ||
            device->p_vkCreateSemaphore( device->host.device, &semaphore_info, NULL, &per->done ) ||
            device->p_vkCreateFence( device->host.device, &fence_info, NULL, &per->fence ))
            goto failed;
        cmd_info.commandPool = osk->pool;
        cmd_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        cmd_info.commandBufferCount = 1;
        if (device->p_vkAllocateCommandBuffers( device->host.device, &cmd_info, &per->cmd ))
            goto failed;
    }
    nx_vk_trace( "[NXVK] floating keyboard %dx%d at %d,%d on %u images", frame->width, frame->height,
                 frame->x, frame->y, osk->count );
    return TRUE;

failed:
    ERR( "could not set up the floating keyboard's copy\n" );
    nx_vk_trace( "[NXVK] floating keyboard: could not set up its copy into the swapchain images" );
    nx_osk_release( device, osk );
    osk->failed = TRUE;
    return FALSE;
}

/* The keyboard over the image this present shows, when it is up. The present
 * then waits for the copy, which waits for what the present waited for. */
static uint64_t nx_osk_present( struct vulkan_queue *queue, VkPresentInfoKHR *present_info,
                                const VkSwapchainKHR *client_swapchains, struct mempool *pool )
{
    struct vulkan_device *device = queue->device;
    VkSubmitInfo submit = {.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO};
    struct fx_osk_frame frame;
    struct nx_osk_image *per;
    struct swapchain *swapchain;
    VkPipelineStageFlags *stages;
    uint32_t index, i;

    if (!fx_osk_frame_visible() || present_info->swapchainCount != 1) return 0;
    swapchain = swapchain_from_handle( client_swapchains[0] );
    if (!fx_osk_frame_get( swapchain->nx_extent.width, swapchain->nx_extent.height, &frame )) return 0;
    if (!swapchain->nx_osk_usable ||
        !(device->queue_props[queue->info.queueFamilyIndex].queueFlags &
          (VK_QUEUE_GRAPHICS_BIT | VK_QUEUE_COMPUTE_BIT | VK_QUEUE_TRANSFER_BIT))) goto failed;
    if (frame.x < 0 || frame.y < 0 || frame.width < 1 || frame.height < 1 ||
        frame.x + frame.width > (int)swapchain->nx_extent.width ||
        frame.y + frame.height > (int)swapchain->nx_extent.height) goto failed;
    if (!nx_osk_prepare( device, swapchain, queue->info.queueFamilyIndex, &frame )) goto failed;
    index = present_info->pImageIndices[0];
    if (index >= swapchain->nx_osk->count) goto failed;
    per = &swapchain->nx_osk->per[index];
    /* Acquire's GPU semaphore alone does not order host writes to staging.
     * This fence explicitly protects its previous copy and command buffer. */
    if (device->p_vkWaitForFences( device->host.device, 1, &per->fence, VK_TRUE, 50000000 )) goto failed;
    if (per->generation != frame.generation)
    {
        if (!fx_osk_frame_copy( &frame, per->pixels, frame.width * 4,
                               swapchain->nx_format == VK_FORMAT_R8G8B8A8_UNORM ||
                               swapchain->nx_format == VK_FORMAT_R8G8B8A8_SRGB )) return 0;
        per->generation = frame.generation;
    }
    if (!per->recorded || per->x != frame.x || per->y != frame.y)
    {
        if (nx_osk_record( device, swapchain->nx_osk, index, &frame )) goto failed;
        per->recorded = 1; per->x = frame.x; per->y = frame.y;
    }
    if (!(stages = mem_alloc( pool, sizeof(*stages) * (present_info->waitSemaphoreCount + 1) ))) goto failed;
    for (i = 0; i < present_info->waitSemaphoreCount; i++) stages[i] = VK_PIPELINE_STAGE_ALL_COMMANDS_BIT;
    submit.waitSemaphoreCount = present_info->waitSemaphoreCount;
    submit.pWaitSemaphores = present_info->pWaitSemaphores;
    submit.pWaitDstStageMask = stages;
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &per->cmd;
    submit.signalSemaphoreCount = 1;
    submit.pSignalSemaphores = &per->done;
    if (device->p_vkResetFences( device->host.device, 1, &per->fence ) ||
        device->p_vkQueueSubmit( queue->host.queue, 1, &submit, per->fence )) goto failed;
    /* Never consume/replace the game's waits unless our submit succeeded. */
    present_info->waitSemaphoreCount = 1;
    present_info->pWaitSemaphores = &per->done;
    return frame.session;
failed:
    fx_osk_frame_reject( frame.session );
    return 0;
}
