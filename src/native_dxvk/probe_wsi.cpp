/* SPDX-License-Identifier: MIT
 * Original FEXTendo diagnostic WSI; one 1280x720 window, no game integration.
 * Implements DXVK's WsiDriver interface. Host XCB is a validation backend;
 * Horizon uses the libnx native window with VK_NN_vi_surface.
 */
#include "wsi_platform.h"
#include <cstring>
#ifdef __SWITCH__
#pragma push_macro("interface")
#undef interface
#include <switch.h>
#pragma pop_macro("interface")
#else
#include <xcb/xcb.h>
#endif

namespace dxvk::wsi {
  class ProbeDriver final : public WsiDriver {
    uint32_t width = 1280, height = 720;
    HMONITOR monitor = reinterpret_cast<HMONITOR>(uintptr_t(1));
  public:
    std::vector<const char*> getInstanceExtensions() override {
#ifdef __SWITCH__
      return {"VK_KHR_surface", "VK_NN_vi_surface"};
#else
      return {"VK_KHR_surface", "VK_KHR_xcb_surface"};
#endif
    }
    HMONITOR getDefaultMonitor() override { return monitor; }
    HMONITOR enumMonitors(uint32_t i) override { return i ? nullptr : monitor; }
    HMONITOR enumMonitors(const LUID*[], uint32_t, uint32_t i) override { return enumMonitors(i); }
    bool getDisplayName(HMONITOR, WCHAR (&name)[32]) override {
      const char* label = "FEXTendo Native Probe";
      std::memset(name, 0, sizeof(name));
      for (unsigned i = 0; label[i] && i < 31; ++i) name[i] = WCHAR(label[i]);
      return true;
    }
    bool getDesktopCoordinates(HMONITOR, RECT* r) override {
      if (!r) return false;
      *r = {0, 0, LONG(width), LONG(height)}; return true;
    }
    bool getDisplayMode(HMONITOR, uint32_t n, WsiMode* m) override {
      if (n || !m) return false;
      *m = {width, height, {60, 1}, 32, false}; return true;
    }
    bool getCurrentDisplayMode(HMONITOR m, WsiMode* mode) override { return getDisplayMode(m, 0, mode); }
    bool getDesktopDisplayMode(HMONITOR m, WsiMode* mode) override { return getDisplayMode(m, 0, mode); }
    WsiEdidData getMonitorEdid(HMONITOR) override { return {}; }
    void getWindowSize(HWND, uint32_t* w, uint32_t* h) override { if (w) *w = width; if (h) *h = height; }
    void resizeWindow(HWND, DxvkWindowState*, uint32_t w, uint32_t h) override { width = w; height = h; }
    void saveWindowState(HWND, DxvkWindowState*, bool) override {}
    void restoreWindowState(HWND, DxvkWindowState*, bool) override {}
    bool setWindowMode(HMONITOR, HWND, DxvkWindowState*, const WsiMode& mode) override {
      return mode.width == width && mode.height == height;
    }
    bool enterFullscreenMode(HMONITOR, HWND, DxvkWindowState*, bool) override { return true; }
    bool leaveFullscreenMode(HWND, DxvkWindowState*) override { return true; }
    bool restoreDisplayMode() override { return true; }
    HMONITOR getWindowMonitor(HWND) override { return monitor; }
    bool isWindow(HWND w) override { return w != nullptr; }
    bool isMinimized(HWND) override { return false; }
    bool isOccluded(HWND) override { return false; }
    void updateFullscreenWindow(HMONITOR, HWND, bool) override {}
    VkResult createSurface(HWND window, PFN_vkGetInstanceProcAddr proc, VkInstance instance, VkSurfaceKHR* out) override {
#ifdef __SWITCH__
      auto create = reinterpret_cast<PFN_vkCreateViSurfaceNN>(proc(instance, "vkCreateViSurfaceNN"));
      if (!create || !out) return VK_ERROR_EXTENSION_NOT_PRESENT;
      VkViSurfaceCreateInfoNN info = {};
      info.sType = VK_STRUCTURE_TYPE_VI_SURFACE_CREATE_INFO_NN;
      info.window = window;
      return create(instance, &info, nullptr, out);
#else
      struct XcbWindow { xcb_connection_t* connection; xcb_window_t window; };
      if (!window || !out) return VK_ERROR_INITIALIZATION_FAILED;
      auto* w = reinterpret_cast<XcbWindow*>(window);
      auto create = reinterpret_cast<PFN_vkCreateXcbSurfaceKHR>(proc(instance, "vkCreateXcbSurfaceKHR"));
      if (!create) return VK_ERROR_EXTENSION_NOT_PRESENT;
      VkXcbSurfaceCreateInfoKHR info = {};
      info.sType = VK_STRUCTURE_TYPE_XCB_SURFACE_CREATE_INFO_KHR;
      info.connection = w->connection; info.window = w->window;
      return create(instance, &info, nullptr, out);
#endif
    }
  };
  WsiBootstrap ProbeWSI = {"FEXTendoProbe", [](WsiDriver** p) { *p = new ProbeDriver; return true; }};
}
