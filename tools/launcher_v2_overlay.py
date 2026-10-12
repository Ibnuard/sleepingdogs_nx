"""Cached install verification, mandatory Light 720p and native LSFG routing."""
import re
import launcher_v1_overlay as v1
from launcher_v1_overlay import ROOT,SOURCE,replace,wine_overlay

def settings_overlay(text):
    text=v1.settings_overlay(text)
    text=replace(text,'FX_SETTINGS_GAME_QUALITY, ','')
    text=replace(text,'static int fx_input_mode,fx_game_quality;','static int fx_input_mode;')
    text=replace(text,'{11,5,3,3,2,3,2,3,3,FX_KEYBOARD_SHORTCUTS,FX_KEYBOARD_HOLD_CHOICES}',
                 '{10,5,3,3,2,3,2,3,FX_KEYBOARD_SHORTCUTS,FX_KEYBOARD_HOLD_CHOICES}')
    text=text.replace(',"Game detail"','').replace(',"Reduce game detail while keeping 1280x720."','')
    text=replace(text,'v->settings_page==FX_SETTINGS_GAME_QUALITY?7:','')
    text=re.sub(r'^    case FX_SETTINGS_GAME_QUALITY:.*\n','',text,flags=re.M)
    text=replace(text,'row==7?(fx_game_quality?"Light 720p - next launch":"Use current in-game options"):','')
    text=replace(text,'(v->settings_page==FX_SETTINGS_DX_LOG&&fx_dx_hud==row)||\n        (v->settings_page==FX_SETTINGS_GAME_QUALITY&&row<2&&fx_game_quality==row);',
                 '(v->settings_page==FX_SETTINGS_DX_LOG&&fx_dx_hud==row);')
    text=replace(text,'    if(page==FX_SETTINGS_ROOT&&row==7){fx_settings_enter(v,FX_SETTINGS_GAME_QUALITY,fx_game_quality);return 1;}\n','')
    start=text.index('    }else if(page==FX_SETTINGS_GAME_QUALITY){')
    end=text.index('    else if(page==FX_SETTINGS_LSFG){',start)
    text=text[:start]+'    }\n'+text[end:]
    text=replace(text,'||row==7||row==8||row==10','||row==8||row==10')
    # Only the root uses rows >= 7; shift remaining Keyboard/Debug/Check rows.
    text=re.sub(r'row==(?:8|9|10)\b',lambda m:'row=='+str(int(m[0][5:])-1),text)
    text=replace(text,'v->settings_page==FX_SETTINGS_OSK?8:','v->settings_page==FX_SETTINGS_OSK?7:')
    text=replace(text,'Copy the complete v15 update.','Copy the complete launcher v2 update.')
    text=replace(text,'Ready. Applies when you launch the game.','Ready for native DXVK and Wine; next launch.')
    assert 'FX_SETTINGS_GAME_QUALITY' not in text and 'fx_game_quality' not in text
    return text

def runtime_overlay(text):
    text=v1.runtime_overlay(text)
    text=text.replace('0.1.0-launcher.1','0.1.0-launcher.2').replace('sleepingdogs-launcher-v1-native-h4-v9','sleepingdogs-launcher-v2-native-h4-v9')
    text=replace(text,'if(!check_requested){sd_check_request();check_requested=1;}',
                 'if(!check_requested){sd_check_request();sd_check_force=0;check_requested=1;}')
    text=replace(text,'v->settings_page==FX_SETTINGS_GAME_QUALITY?"Light 720p applies at next launch.":"Choose Game detail for the Light 720p preset."',
                 '"Light 720p is always applied when the game starts."')
    text=replace(text,'    fx_game_quality=sd_game_quality_load(RUNTIME_DIR);\n    if(sd_game_quality_error)log_line("[SD-QUALITY] settings read failed: %s",sd_game_quality_error);','')
    text=replace(text,'            int quality=sd_game_quality_load(RUNTIME_DIR);\n            if(sd_game_quality_error||!sd_game_quality_apply(RUNTIME_DIR,quality)){',
                 '            if(!sd_game_quality_apply(RUNTIME_DIR,1)){')
    text=replace(text,'#include "lsfg_config.h"','#include "lsfg_config.h"\nvoid sd_lsfg_native_configure(int enabled);')
    text=replace(text,'            wine_nx_lsfg_configure(sd_com_enabled?0:lsfg.enabled,lsfg.performance,lsfg.flow);\n            if(sd_com_enabled)log_line("[SD-NDX-COM] game selection native ARM64; LSFG OFF; measured FPS pending");',
        '            sd_lsfg_native_configure(sd_com_enabled&&lsfg.enabled);\n'
        '            wine_nx_lsfg_configure(lsfg.enabled,lsfg.performance,lsfg.flow);\n'
        '            log_line("[SD-LSFG-NATIVE] requested=%d route=%s motion=%d; initialization/generation logged separately",lsfg.enabled,sd_com_enabled?"native":"Wine",lsfg.flow);')
    text=replace(text,'__atomic_store_n(&sd_com_enabled,1,__ATOMIC_RELEASE);wine_nx_lsfg_configure(0,1,0);',
                 '__atomic_store_n(&sd_com_enabled,1,__ATOMIC_RELEASE);sd_lsfg_native_configure(0);wine_nx_lsfg_configure(0,1,0);')
    return text

def osk_overlay(text):
    text=replace(text,'#include <vulkan/vulkan.h>','#include <vulkan/vulkan.h>\n#include "lsfg_vulkan.h"')
    for name,target in (('vkCreateDevice','sd_lsfg_create_device'),('vkCreateSwapchainKHR','sd_lsfg_create_chain'),('vkQueuePresentKHR','sd_lsfg_present')):
        text=text.replace(name+'(',target+'(')
    text=replace(text,'    }vkDestroyDevice(d,a);','    }sd_lsfg_destroy_device(d);vkDestroyDevice(d,a);')
    text=replace(text,'    vkDestroySwapchainKHR(d,s,a);','    sd_lsfg_destroy_chain(s);vkDestroySwapchainKHR(d,s,a);')
    text=replace(text,'vkGetDeviceQueue(d,family,index,q);try{','vkGetDeviceQueue(d,family,index,q);sd_lsfg_queue(d,family,*q);try{')
    text=replace(text,'vkGetDeviceQueue2(d,info,q);try{','vkGetDeviceQueue2(d,info,q);sd_lsfg_queue(d,info->queueFamilyIndex,*q);try{')
    text=replace(text,'    return real;','    return sd_lsfg_intercept(name,real);')
    return text
