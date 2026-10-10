"""Apply a narrow LSFG integration to the existing FEXTendo v14.1 inputs."""
from pathlib import Path
import shutil, difflib
from port_common import ROOT,sha,write_json
from build_lsfg_backend import WORK

BASE=Path('/home/blekjek/sleepingdogs-low-window-v1/native-source')
NATIVE=WORK/'native-source'

def replace(text,old,new):
    assert text.count(old)==1,(old[:160],text.count(old))
    return text.replace(old,new)

def main():
    source=BASE/'wine-nx-probe/source';target=NATIVE/'wine-nx-probe/source'
    target.mkdir(parents=True,exist_ok=True)
    # Copy neighboring headers/assets without redirecting or modifying shared SDKs.
    for p in source.iterdir():
        if p.is_file():shutil.copy2(p,target/p.name)
    for name in ('lsfg.cpp','lsfg.h','lsfg_config.h'):
        shutil.copy2(ROOT/'local/research-lsfg/autorun/horizon-wine/source'/name,target/name)
    for name in ('sd_lsfg_settings.h','sd_lsfg_pack.hpp','sd_fullscreen_extent.h'):
        shutil.copy2(ROOT/'tools'/name,target/name)
    config=target/'lsfg_config.h'
    config.write_text(config.read_text().replace('void wine_nx_lsfg_configure(',
        'int wine_nx_lsfg_available(void);\nvoid wine_nx_lsfg_configure('))
    api=target/'lsfg.h'
    api.write_text(api.read_text().replace('VkPhysicalDeviceFeatures *features);',
        'VkPhysicalDeviceFeatures *features, const void *device_chain);'))
    cpp=(target/'lsfg.cpp').read_text()
    cpp=cpp.replace('#include "lsfg.h"','#include "lsfg.h"\n#include "sd_lsfg_pack.hpp"\n#include <chrono>')
    cpp=cpp.replace('sdmc:/switch/wine/lsfg/Lossless.dll','sdmc:/switch/sleepingdogs-fex/lsfg/lsfg-3.1.sdp')
    cpp=cpp.replace('sdmc:/switch/wine/cache/lsfg-vk.bin','sdmc:/switch/sleepingdogs-fex/cache/lsfg-v15.bin')
    cpp=cpp.replace('"[LSFG] %s"','"[SD-LSFG-V15] %s"')
    cpp=replace(cpp,'    performance = perf != 0;',
        '    (void)perf;\n    performance = true; // v15 validated Performance shader path only')
    cpp=cpp.replace('VkPhysicalDeviceFeatures *features)\n{',
        'VkPhysicalDeviceFeatures *features, const void *device_chain)\n{')
    cpp=replace(cpp,'    features->shaderStorageImageExtendedFormats |= supported.shaderStorageImageExtendedFormats;', '''    // The converted DXBC uses the Vulkan memory model. Verify that the game
    // enabled it and timeline semaphores before borrowing its logical device.
    bool memory_model=false, timeline=false;
    for (auto next=static_cast<const VkBaseInStructure*>(device_chain);next;next=next->pNext) {
        if (next->sType==VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES) {
            auto f=reinterpret_cast<const VkPhysicalDeviceVulkan12Features*>(next);
            memory_model=f->vulkanMemoryModel; timeline=f->timelineSemaphore;
        } else if (next->sType==VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_MEMORY_MODEL_FEATURES)
            memory_model=reinterpret_cast<const VkPhysicalDeviceVulkanMemoryModelFeatures*>(next)->vulkanMemoryModel;
        else if (next->sType==VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_TIMELINE_SEMAPHORE_FEATURES)
            timeline=reinterpret_cast<const VkPhysicalDeviceTimelineSemaphoreFeatures*>(next)->timelineSemaphore;
    }
    if (!memory_model || !timeline) {
        trace("disabled: renderer must enable Vulkan memory model and timeline semaphores");
        enabled=false; return;
    }
    features->shaderStorageImageExtendedFormats |= supported.shaderStorageImageExtendedFormats;''')
    start=cpp.index('    if (!enabled) return;',cpp.index('extern "C" void wine_nx_lsfg_configure'))
    end=cpp.index('\n}',start)
    cpp=cpp[:start]+'''    if (!enabled) { trace("configured off; native presentation"); return; }
    try { sd_lsfg_read_pack(shader_path); }
    catch (const std::exception& e) { trace(e.what()); enabled=false; }
    if (enabled) trace("configured 2x; shader pack validated; GPU initialization pending");'''+cpp[end:]
    cpp=replace(cpp,'extern "C" void wine_nx_lsfg_configure', '''extern "C" int wine_nx_lsfg_available(void)
{
    try { sd_lsfg_read_pack(shader_path); return 1; }
    catch (const std::exception&) { return 0; }
}

extern "C" void wine_nx_lsfg_configure''')
    cpp=cpp.replace('"2x active, %ux%u, motion %.1f%%, %s"','"2x initialized, %ux%u, motion %.1f%%, %s; warming history"')
    cpp=replace(cpp,'        return vk.df().QueuePresentKHR(vk.queue(), &info);','''        VkResult result=vk.df().QueuePresentKHR(vk.queue(), &info);
        if (result==VK_SUCCESS || result==VK_SUBOPTIMAL_KHR) {
            if (generated) {
                if (!generated_total++) trace("2x generating; first interpolated present submitted");
                ++generated_window;
            } else ++real_window;
            auto now=std::chrono::steady_clock::now();
            auto ms=std::chrono::duration_cast<std::chrono::milliseconds>(now-window_start).count();
            if (ms>=10000) {
                char message[256];
                std::snprintf(message,sizeof(message),
                    "window_ms=%lld real=%llu generated=%llu presented=%llu; submissions, not scanout",
                    (long long)ms,(unsigned long long)real_window,
                    (unsigned long long)generated_window,(unsigned long long)(real_window+generated_window));
                trace(message); real_window=generated_window=0; window_start=now;
            }
        }
        return result;''')
    cpp=replace(cpp,'    unsigned int warmup{2};','''    unsigned int warmup{2};
    uint64_t generated_total{}, real_window{}, generated_window{};
    std::chrono::steady_clock::time_point window_start{std::chrono::steady_clock::now()};''')
    # A present-mode override in the application could bypass the FIFO chosen for
    # generated frames. Decline this combination before consuming any semaphore.
    cpp=replace(cpp,'    if (!state || state->failed) return 0;', '''    if (!state || state->failed) return 0;
    for (auto next=static_cast<const VkBaseInStructure*>(info->pNext); next; next=next->pNext)
        if (next->sType==VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODE_INFO_EXT) {
            if (state->presentation) state->presentation->reset_history();
            trace("generation bypassed: per-present mode override");
            return 0;
        }''')
    (target/'lsfg.cpp').write_text(cpp)
    # Keep the backend's SPIR-V registry and add a validated personal pack reader.
    pack_target=WORK/'backend/lsfg-vk-backend/src/extraction/sd_lsfg_pack.hpp'
    shutil.copy2(ROOT/'tools/sd_lsfg_pack.hpp',pack_target)
    reader=WORK/'backend/lsfg-vk-backend/src/extraction/dll_reader.cpp'
    text=reader.read_text()
    if '#include "sd_lsfg_pack.hpp"' not in text:
        text=text.replace('#include "dll_reader.hpp"','#include "dll_reader.hpp"\n#include "sd_lsfg_pack.hpp"')
        text=replace(text,'        const std::filesystem::path& dll) {',
            '        const std::filesystem::path& dll) {\n    if (dll.extension()==".sdp") return sd_lsfg_read_pack(dll);')
        reader.write_text(text)

    settings=(target/'f1_settings.h').read_text()
    settings=settings.replace('FX_SETTINGS_DX_LOG, FX_SETTINGS_PAGES','FX_SETTINGS_DX_LOG, FX_SETTINGS_LSFG, FX_SETTINGS_PAGES')
    settings=settings.replace('static int fx_input_mode;','#include "sd_lsfg_settings.h"\n\nstatic int fx_input_mode;')
    settings=settings.replace('{6,5,2,3,2,3}','{7,5,2,3,2,3,2}')
    settings=settings.replace('v->settings_page==FX_SETTINGS_KEYBOARD?2:',
        'v->settings_page==FX_SETTINGS_LSFG?6:v->settings_page==FX_SETTINGS_KEYBOARD?2:')
    settings=settings.replace('"Audio","DXVK HUD"','"Audio","DXVK HUD","Frame Generation"')
    settings=settings.replace('"Debug timestamp","DXVK HUD"','"Debug timestamp","DXVK HUD","Frame Generation"')
    settings=settings.replace('"Show DXVK statistics while you play."','"Show DXVK statistics while you play.","Performance mode. Adds display frames, not game speed."')
    settings=replace(settings,'    case FX_SETTINGS_DX_LOG:return fx_dx_hud_names[row];',
        '    case FX_SETTINGS_LSFG:return row==0?"LSFG 2x":"Motion resolution";\n    case FX_SETTINGS_DX_LOG:return fx_dx_hud_names[row];')
    settings=settings.replace('row==3?"Menu sounds and background music":row==5?',
        'row==6?(fx_lsfg.enabled?"LSFG 2x - next launch":"Off"):row==3?"Menu sounds and background music":row==5?')
    settings=replace(settings,'    case FX_SETTINGS_DX_LOG:return row==0?',
        '    case FX_SETTINGS_LSFG:return row==0?(fx_lsfg_available?"Ready. Applies when you launch the game.":"Shader pack missing or invalid."):fx_lsfg_motion[fx_lsfg.flow];\n    case FX_SETTINGS_DX_LOG:return row==0?')
    settings=settings.replace('    if(v->settings_page==FX_SETTINGS_AUDIO)return row?v->music:v->sound;',
        '    if(v->settings_page==FX_SETTINGS_AUDIO)return row?v->music:v->sound;\n    if(v->settings_page==FX_SETTINGS_LSFG&&row==0)return fx_lsfg.enabled;')
    settings=settings.replace('(row<4||row==5)','(row<4||row==5||row==6)')
    settings=replace(settings,'    if(page==FX_SETTINGS_ROOT&&row==5)',
        '    if(page==FX_SETTINGS_ROOT&&row==6){fx_settings_enter(v,FX_SETTINGS_LSFG,0);return 1;}\n    if(page==FX_SETTINGS_ROOT&&row==5)')
    settings=replace(settings,'    if(page==FX_SETTINGS_DX_LOG){', '''    if(page==FX_SETTINGS_LSFG){
        struct sd_lsfg_settings next=fx_lsfg;
        if(row==0){
            if(!next.enabled&&!fx_lsfg_available){
                v->screen=FX_FAILED;v->fatal=0;
                v->message="LSFG shader pack is missing or invalid. Copy the complete v15 update.";
                return 1;
            }
            next.enabled=!next.enabled;
        }else next.flow=(next.flow+1)%3;
        if(!fx_lsfg_save(root,next))return 0;fx_lsfg=next;
    }
    else if(page==FX_SETTINGS_DX_LOG){''')
    (target/'f1_settings.h').write_text(settings)
    runtime=(target/'runtime.c').read_text()
    runtime=replace(runtime,'sleepingdogs-fextendo-0.1.0-low-window-v11-frame-diagnostics',
        'sleepingdogs-fextendo-0.1.0-v15-native-lsfg')
    runtime=replace(runtime,'#define FX_APP_VERSION "0.1.0-v11-diag"',
        '#define FX_APP_VERSION "0.1.0-v15-native"')
    runtime=replace(runtime,'#include "f1_settings.h"',
        'int wine_nx_native_present_enabled=1;\nextern int wine_nx_config_file_bool(const char *,int);\n#include "f1_settings.h"')
    runtime=replace(runtime,'#include "f1_settings.h"','#include "f1_settings.h"\n#include "lsfg_config.h"')
    runtime=replace(runtime,'    fx_dx_hud=fx_dx_hud_load(RUNTIME_DIR);',
        '    fx_dx_hud=fx_dx_hud_load(RUNTIME_DIR);\n    fx_lsfg=fx_lsfg_load(RUNTIME_DIR);\n    fx_lsfg_available=wine_nx_lsfg_available();')
    runtime=replace(runtime,'            log_line("[SD-GRAPHICS] game-owned',
        '            struct sd_lsfg_settings lsfg=fx_lsfg_load(RUNTIME_DIR);\n            wine_nx_lsfg_configure(lsfg.enabled,lsfg.performance,lsfg.flow);\n'
        '            wine_nx_native_present_enabled=wine_nx_config_file_bool(RUNTIME_DIR "/launcher/native-present.txt",1);\n'
        '            log_line("[SD-NATIVE-V15] fullscreen geometry correction=%d; target=1280x720; FPS gain unmeasured",wine_nx_native_present_enabled);\n'
        '            log_line("[SD-GRAPHICS] game-owned')
    (target/'runtime.c').write_text(runtime)

    window=(BASE/'dlls/win32u/window.c').read_text()
    window=replace(window,'static BOOL calc_winpos( WINDOWPOS *winpos,', '''#ifdef __SWITCH__
#include "sd_fullscreen_extent.h"
static void sd_fix_fullscreen_extent(WINDOWPOS *pos)
{
    extern int wine_nx_native_present_enabled;
    static const WCHAR game_class[]={'O','r','a','n','g','e','L','o','t','u','s','W','i','n','d','o','w','C','l','a','s','s',0};
    WCHAR name[64]={0};
    UNICODE_STRING cls={0,sizeof(name)-sizeof(WCHAR),name};
    if(!wine_nx_native_present_enabled || pos->cx<=1280 || pos->cy<=720)return;
    NtUserGetClassName(pos->hwnd,FALSE,&cls);
    if(sd_fullscreen_extent(get_window_long(pos->hwnd,GWL_STYLE),
            get_window_long(pos->hwnd,GWL_EXSTYLE),pos->flags,
            !!get_window_relative(pos->hwnd,GW_OWNER),!wcscmp(name,game_class),pos->cx,pos->cy)) {
        nx_window_trace("[SD-NATIVE-V15] borderless extent %dx%d -> 1280x720 hwnd=%p",
                        pos->cx,pos->cy,pos->hwnd);
        pos->cx=1280;pos->cy=720;
    }
}
#endif

static BOOL calc_winpos( WINDOWPOS *winpos,''')
    window=replace(window,'        send_message( winpos->hwnd, WM_WINDOWPOSCHANGING, 0, (LPARAM)winpos );',
        '        send_message( winpos->hwnd, WM_WINDOWPOSCHANGING, 0, (LPARAM)winpos );\n'
        '#ifdef __SWITCH__\n    sd_fix_fullscreen_extent(winpos);\n#endif')
    window_dest=NATIVE/'dlls/win32u/window.c';window_dest.parent.mkdir(parents=True,exist_ok=True)
    window_dest.write_text(window)

    vulkan=(BASE/'dlls/win32u/vulkan.c').read_text()
    # Keep the driver's valid capabilities if no Win32 rect exists (minimized
    # windows); never manufacture an extent from uninitialized stack bytes.
    vulkan=replace(vulkan,'    get_surface_rect( surface->hwnd, &client_rect, NtUserGetDpiForWindow( surface->hwnd ) );',
        '    if (!get_surface_rect( surface->hwnd, &client_rect, NtUserGetDpiForWindow( surface->hwnd ) )) return;')
    vulkan=replace(vulkan,'    *ret = swapchain->obj.client.swapchain;', '''    {
        extern void wine_nx_runtime_trace(const char *);
        char message[192];
        snprintf(message,sizeof(message),"[SD-NATIVE-V15] swapchain=%ux%u host=%ux%u extra_scale=%d",
                 swapchain->extents.width,swapchain->extents.height,
                 create_info_host.imageExtent.width,create_info_host.imageExtent.height,!!swapchain->fshack_dpi);
        wine_nx_runtime_trace(message);
    }
    *ret = swapchain->obj.client.swapchain;''')
    vulkan=replace(vulkan,'static struct vulkan_funcs vulkan_funcs;',
        'static struct vulkan_funcs vulkan_funcs;\n#include "lsfg.h"\nstatic pthread_mutex_t sd_lsfg_present_lock = PTHREAD_MUTEX_INITIALIZER;')
    vulkan=replace(vulkan,'struct swapchain\n{\n    struct vulkan_swapchain obj;',
        'struct swapchain\n{\n    struct vulkan_swapchain obj;\n    struct wine_nx_lsfg *lsfg;\n    unsigned int lsfg_acquires;')
    needle='            create_info->pEnabledFeatures = &features;\n        }\n}'
    vulkan=replace(vulkan,needle,needle[:-1]+'''        wine_nx_lsfg_device_features(instance->host.instance,physical_device->host.physical_device,
                                     features2 ? &features2->features : &features,create_info->pNext);
}''')
    vulkan=replace(vulkan,'    VkSwapchainKHR host_swapchain;','    VkSwapchainKHR host_swapchain;\n    BOOL lsfg;')
    vulkan=replace(vulkan,'    if ((res = device->p_vkCreateSwapchainKHR(',
        '    lsfg=wine_nx_lsfg_prepare_swapchain(instance->host.instance,physical_device->host.physical_device,&create_info_host);\n    if ((res = device->p_vkCreateSwapchainKHR(')
    vulkan=replace(vulkan,'    *ret = swapchain->obj.client.swapchain;',
        '    if(lsfg)swapchain->lsfg=wine_nx_lsfg_create(instance->host.instance,physical_device->host.physical_device,\n        device->host.device,host_swapchain,&create_info_host);\n    *ret = swapchain->obj.client.swapchain;')
    vulkan=replace(vulkan,'    if (!swapchain) return;\n',
        '    if (!swapchain) return;\n    wine_nx_lsfg_destroy(swapchain->lsfg);\n')
    for func in ('vkAcquireNextImage2KHR','vkAcquireNextImageKHR'):
        start=vulkan.index('    res = device->p_'+func+'(')
        end=vulkan.index(';',start)+1
        call=vulkan[start:end]
        def sync(op):return f'''    if(swapchain->lsfg){{
        pthread_mutex_lock(&sd_lsfg_present_lock);{op}swapchain->lsfg_acquires;
        pthread_mutex_unlock(&sd_lsfg_present_lock);
    }}
'''
        vulkan=vulkan[:start]+sync('++')+call+'\n'+sync('--')+vulkan[end:]
    vulkan=replace(vulkan,'    static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;\n','')
    vulkan=vulkan.replace('pthread_mutex_lock( &lock );','pthread_mutex_lock( &sd_lsfg_present_lock );')
    vulkan=vulkan.replace('pthread_mutex_unlock( &lock );','pthread_mutex_unlock( &sd_lsfg_present_lock );')
    vulkan=replace(vulkan,'    res = device->p_vkQueuePresentKHR( queue->host.queue, present_info );',
        '''    if(!present_info->swapchainCount ||
       !wine_nx_lsfg_present(swapchain_from_handle(client_swapchains[0])->lsfg,
           queue->host.queue,queue->info.queueFamilyIndex,
           !swapchain_from_handle(client_swapchains[0])->lsfg_acquires,present_info,&res))
        res = device->p_vkQueuePresentKHR( queue->host.queue, present_info );''')
    dest=NATIVE/'dlls/win32u/vulkan.c';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(vulkan)
    patch=[]
    for name in ('wine-nx-probe/source/runtime.c','wine-nx-probe/source/f1_settings.h','dlls/win32u/vulkan.c','dlls/win32u/window.c'):
        patch.extend(difflib.unified_diff((BASE/name).read_text().splitlines(True),
            (NATIVE/name).read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    (ROOT/'local/research-lsfg/sleepingdogs-lsfg-v15.patch').write_text(''.join(patch))
    write_json(WORK/'native-prepared.json',dict(base=str(BASE),source=str(NATIVE),
        files={str(p.relative_to(NATIVE)):sha(p) for p in (target/'runtime.c',target/'f1_settings.h',dest,window_dest,target/'lsfg.cpp')}))
    print('Prepared selective native LSFG integration')

if __name__=='__main__':main()
