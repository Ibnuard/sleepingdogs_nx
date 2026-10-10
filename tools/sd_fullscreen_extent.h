/* Sleeping Dogs' borderless 720p window can retain a decorated minimum size
 * after WM_WINDOWPOSCHANGING. Correct the real Win32 geometry before Wine
 * computes the client rect; Vulkan and the game then see the same extent.
 * This guard deliberately excludes lower resolutions, popups and other apps.
 */
#ifndef SD_FULLSCREEN_EXTENT_H
#define SD_FULLSCREEN_EXTENT_H
static int sd_fullscreen_extent(unsigned style, unsigned exstyle, unsigned flags,
                                int owner, int game_class, int width, int height)
{
    /* WS_CHILD, WS_POPUP, WS_MINIMIZE, WS_CAPTION, WS_THICKFRAME. */
    const unsigned decorated = 0xc0c40000u | 0x20000000u;
    /* WS_EX_DLGMODALFRAME, WS_EX_TOOLWINDOW, WS_EX_WINDOWEDGE,
     * WS_EX_CLIENTEDGE, WS_EX_STATICEDGE. */
    const unsigned edge = 0x00020381u;
    if (!game_class || owner || !(style & 0x10000000u) ||
        (style & decorated) || (exstyle & edge) ||
        (flags & 0x81u)) /* SWP_NOSIZE or SWP_HIDEWINDOW */
        return 0;
    /* Observed at 1292x732. Match equal, small decoration padding only,
     * without depending on the currently configured Windows border metric.
     * Full 720p and the game's lower display modes are left untouched. */
    return width > 1280 && width <= 1312 && height > 720 &&
           width - 1280 == height - 720;
}
#endif
