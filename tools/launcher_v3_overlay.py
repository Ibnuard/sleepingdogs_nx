"""Keep launcher v2 behavior; fix FIFO pNext rejection and identify this build."""
import launcher_v2_overlay as v2
from launcher_v2_overlay import ROOT,SOURCE,settings_overlay,wine_overlay,osk_overlay,replace
def runtime_overlay(text):
    return v2.runtime_overlay(text).replace('0.1.0-launcher.2','0.1.0-launcher.3').replace('sleepingdogs-launcher-v2-native-h4-v9','sleepingdogs-launcher-v3-state-v1')

def lsfg_overlay(text):
    text=replace(text,'#include "lsfg.h"','#include "lsfg.h"\n#include "lsfg_present_policy.h"')
    text=replace(text,'    VkResult error{VK_SUCCESS};','    VkResult error{VK_SUCCESS};\n    SdLsfgPresentPolicy policy;')
    start=text.index('    for (auto next=static_cast<const VkBaseInStructure*>(info->pNext);')
    end=text.index('    if (state->error != VK_SUCCESS)',start)
    text=text[:start]+'''    const bool fifo=state->policy.update(info);
    if (!fifo) {
        if (state->presentation) state->presentation->reset_history();
        if (state->policy.log_bypass()) trace("generation bypassed: non-FIFO present mode; log throttled");
        return 0;
    }
    if (info->pNext && !state->policy.noted_fifo) {
        trace("FIFO present metadata accepted; generation eligible");
        state->policy.noted_fifo=true;
    }
'''+text[end:]
    # The generated present carries only the mode override. The game's ID,
    # present fence and pResults are reserved for the real present, once.
    text=replace(text,'        info.pNext = generated ? nullptr : original.pNext;', '''        info.pNext = generated ? nullptr : original.pNext;
        VkSwapchainPresentModeInfoEXT mode{VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODE_INFO_EXT};
        if (generated) {
            for (auto next=static_cast<const VkBaseInStructure*>(original.pNext);next;next=next->pNext)
                if (next->sType==VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODE_INFO_EXT) {
                    mode=*reinterpret_cast<const VkSwapchainPresentModeInfoEXT*>(next);
                    mode.pNext=nullptr;info.pNext=&mode;break;
                }
        }''')
    # A consumed-semaphore error always takes precedence over a later mode
    # change. Falling through to the raw presenter would wait a second time.
    start=text.index('    const bool fifo=state->policy.update(info);')
    error=text.index('    if (state->error != VK_SUCCESS)',start)
    end=text.index('    if (!generate',error)
    text=text[:start]+text[error:end]+text[start:error]+text[end:]
    return text
