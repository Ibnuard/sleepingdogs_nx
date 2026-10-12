"""Isolated launcher delta over the proven native H4 v9 runtime."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'src/launcher'

def replace(text,old,new):
    assert text.count(old)==1,(old[:110],text.count(old))
    return text.replace(old,new)

def settings_overlay(text):
    text=replace(text,'FX_SETTINGS_GAME_QUALITY, FX_SETTINGS_PAGES','FX_SETTINGS_GAME_QUALITY, FX_SETTINGS_OSK, FX_SETTINGS_SHORTCUT, FX_SETTINGS_HOLD, FX_SETTINGS_PAGES')
    text=replace(text,'{8,5,3,3,2,3,2,3}','{11,5,3,3,2,3,2,3,3,FX_KEYBOARD_SHORTCUTS,FX_KEYBOARD_HOLD_CHOICES}')
    text=replace(text,'    int row=v->settings_page==FX_SETTINGS_GRAPHICS?0:',
        '    if(v->settings_page==FX_SETTINGS_SHORTCUT||v->settings_page==FX_SETTINGS_HOLD){fx_settings_enter(v,FX_SETTINGS_OSK,v->settings_page==FX_SETTINGS_HOLD?2:0);return;}\n'
        '    int row=v->settings_page==FX_SETTINGS_OSK?8:v->settings_page==FX_SETTINGS_GRAPHICS?0:')
    text=replace(text,'"Frame Generation","Game detail"};\n    return titles[page];',
        '"Frame Generation","Game detail","Keyboard","Keyboard shortcut","Shortcut hold"};\n    return titles[page];')
    text=replace(text,'"Reduce game detail while keeping 1280x720."};',
        '"Reduce game detail while keeping 1280x720.","Type directly over the game.","Choose how to open the keyboard.","Choose how long to hold the button combo."};')
    text=replace(text,'"Frame Generation","Game detail"};\n    static const char *const keyboard',
        '"Frame Generation","Game detail","Keyboard","Show debug launch","System Check"};\n    static const char *const keyboard')
    text=replace(text,'    case FX_SETTINGS_GAME_QUALITY:return row==0?"Game settings"',
        '    case FX_SETTINGS_OSK:return row==0?"Shortcut":row==1?"Position":"Hold time";\n'
        '    case FX_SETTINGS_SHORTCUT:return fx_keyboard_shortcut_names[row];\n'
        '    case FX_SETTINGS_HOLD:return fx_keyboard_hold_names[row];\n'
        '    case FX_SETTINGS_GAME_QUALITY:return row==0?"Game settings"')
    text=replace(text,'        return row==0?fx_preset_names[v->selected]',
        '        return row==8?fx_keyboard_shortcut_names[fx_keyboard_options.shortcut]:row==9?"Show Launch Debug on the home screen":row==10?"Recheck patch, game and runtime files":row==0?fx_preset_names[v->selected]')
    text=replace(text,'    case FX_SETTINGS_GAME_QUALITY:return row==0?"Keep current options;',
        '    case FX_SETTINGS_OSK:return row==0?fx_keyboard_shortcut_names[fx_keyboard_options.shortcut]:row==1?(fx_keyboard_options.top?"Top":"Bottom"):fx_keyboard_hold_names[fx_keyboard_hold_index(fx_keyboard_options.hold_ms)];\n'
        '    case FX_SETTINGS_SHORTCUT:return row==FX_KEYBOARD_DISABLED?"Disable the manual shortcut":row==FX_KEYBOARD_CAPTURE?"Short press; replaces screenshots during gameplay":"Single Joy-Con: SL + SR + Stick";\n'
        '    case FX_SETTINGS_HOLD:return fx_keyboard_options.shortcut==FX_KEYBOARD_CAPTURE?"Capture always uses a short press":"Applies to the selected button combo";\n'
        '    case FX_SETTINGS_GAME_QUALITY:return row==0?"Keep current options;')
    text=replace(text,'    return (v->settings_page==FX_SETTINGS_GRAPHICS',
        '    return (v->settings_page==FX_SETTINGS_SHORTCUT&&row==fx_keyboard_options.shortcut)||\n'
        '        (v->settings_page==FX_SETTINGS_HOLD&&fx_keyboard_hold_ms[row]==(unsigned)fx_keyboard_options.hold_ms)||\n'
        '        (v->settings_page==FX_SETTINGS_GRAPHICS')
    text=replace(text,'    if(v->settings_page==FX_SETTINGS_ROOT&&row==4)',
        '    if(v->settings_page==FX_SETTINGS_ROOT&&row==9)return v->debug_launch;\n    if(v->settings_page==FX_SETTINGS_ROOT&&row==4)')
    text=replace(text,'    return v->settings_page==FX_SETTINGS_ROOT&&(row<4||row==5||row==6||row==7);',
        '    return (v->settings_page==FX_SETTINGS_OSK&&(row==0||row==2))||(v->settings_page==FX_SETTINGS_ROOT&&(row<4||row==5||row==6||row==7||row==8||row==10));')
    text=replace(text,'    if(page==FX_SETTINGS_ROOT&&row==7){',
        '    if(page==FX_SETTINGS_ROOT&&row==8){fx_settings_enter(v,FX_SETTINGS_OSK,0);return 1;}\n'
        '    if(page==FX_SETTINGS_ROOT&&row==10){sd_check_request();return 1;}\n'
        '    if(page==FX_SETTINGS_OSK&&row!=1){fx_settings_enter(v,row==0?FX_SETTINGS_SHORTCUT:FX_SETTINGS_HOLD,row==0?fx_keyboard_options.shortcut:fx_keyboard_hold_index(fx_keyboard_options.hold_ms));return 1;}\n'
        '    if(page==FX_SETTINGS_ROOT&&row==7){')
    text=replace(text,'    if(page==FX_SETTINGS_GAME_QUALITY){',
        '    if(page==FX_SETTINGS_OSK||page==FX_SETTINGS_SHORTCUT||page==FX_SETTINGS_HOLD){\n'
        '        struct fx_keyboard_options next=fx_keyboard_options;\n'
        '        if(page==FX_SETTINGS_OSK)next.top=!next.top;else if(page==FX_SETTINGS_SHORTCUT)next.shortcut=row;else next.hold_ms=fx_keyboard_hold_ms[row];\n'
        '        if(!fx_keyboard_options_save(root,next))return 0;fx_keyboard_options=next;\n'
        '    }else if(page==FX_SETTINGS_ROOT&&row==9){\n'
        '        if(!fx_debug_launch_save(root,!v->debug_launch))return 0;v->debug_launch=!v->debug_launch;\n'
        '        if(!v->debug_launch&&v->tile==3){v->tile=0;v->tile_mix=0;}\n'
        '    }else if(page==FX_SETTINGS_GAME_QUALITY){')
    return text

def runtime_overlay(text):
    text=replace(text,'#include <switch.h>','#include <switch.h>\n#include "boot_memory.h"\n#include "startup_heap.h"')
    text=replace(text,'#define FX_APP_VERSION "0.1.0-h4.9"','#define FX_APP_VERSION "0.1.0-launcher.1"')
    text=replace(text,'#define WINE_NX_RUNTIME_BUILD "sleepingdogs-native-dxvk-h4-v9"','#define WINE_NX_RUNTIME_BUILD "sleepingdogs-launcher-v1-native-h4-v9"')
    text=replace(text,'enum fx_screen { FX_HOME', '#include "system_check.h"\n#include "preferences.h"\nstatic void sd_check_request(void);\nenum fx_screen { FX_HOME')
    text=replace(text,'struct fx_view { enum fx_screen screen;', 'struct fx_view { struct sd_check_view check;int debug_launch;enum fx_screen screen;')
    text=replace(text,'static void fx_render(struct fx_canvas *c,const struct fx_view *v) {',
        '#include "checker_ui.h"\nstatic void fx_render(struct fx_canvas *c,const struct fx_view *v) {\n    if(v->check.visible){sd_check_draw(c,v);return;}')
    text=replace(text,'v->settings_page==FX_SETTINGS_GAME_QUALITY?"Light 720p applies at next launch.":"Choose Game detail for the Light 720p preset."',
        'v->settings_page>=FX_SETTINGS_OSK?"In game: Y moves the keyboard. B closes it.":v->settings_page==FX_SETTINGS_GAME_QUALITY?"Light 720p applies at next launch.":"Choose Game detail for the Light 720p preset."')
    text=replace(text,'fx_play(c,76,552,v->tile<2,v->frame);','fx_play(c,76,552,v->tile==0||(v->debug_launch&&v->tile==3),v->frame);')
    text=replace(text,'        for(i=0;i<4;i++){\n            float amount=', '        for(i=0;i<(v->debug_launch?4:3);i++){\n            float amount=')
    text=replace(text,'fx_tile_image(c,x,yy,w,i,!selected);','fx_tile_image(c,x,yy,w,i==0?0:i==1?2:i==2?3:1,!selected);')
    text=replace(text,'i==1?"Launch Debug":i==2?"Settings":"Credits"','i==1?"Settings":i==2?"Credits":"Launch Debug"')
    text=replace(text,'i==1?"Wine trace":i==2?"Preferences":"About"','i==1?"Preferences":i==2?"About":"Wine trace"')
    text=replace(text,'static char fx_ui_message[192];','static char fx_ui_message[192];\n#include "checker_runtime.h"')
    text=replace(text,'psm_ready=0,splash_done=0;','psm_ready=0,splash_done=0,check_requested=0;')
    text=replace(text,'    if(!fx_art_load(&art,RUNTIME_DIR)){','    if(!sd_boot_art_load(&art)){')
    text=replace(text,'    fx_ui_view.selected=fx_selected(RUNTIME_DIR);',
        '    fx_ui_view.check=(struct sd_check_view){.visible=1,.percent=-1};\n'
        '    fx_ui_view.debug_launch=fx_debug_launch(RUNTIME_DIR);\n'
        '    fx_keyboard_options=fx_keyboard_options_load(RUNTIME_DIR);\n'
        '    fx_ui_view.selected=fx_selected(RUNTIME_DIR);')
    text=replace(text,'        int old_tile=fx_ui_view.tile,old_row=fx_ui_view.row,old_page=fx_ui_view.credit_page;',
        '        if(!check_requested){sd_check_request();check_requested=1;}\n'
        '        if(fx_ui_view.check.complete){\n'
        '            fx_art_free(&art);art=sd_checked_art;memset(&sd_checked_art,0,sizeof(sd_checked_art));\n'
        '            fx_ui_view.check=(struct sd_check_view){0};fx_ui_view.screen=FX_HOME;fx_ui_view.tile=0;fx_ui_view.tile_mix=0;\n'
        '            splash_done=1;fx_ui_view.splash_ms=0;confirm=dir=0;down=held=0;\n'
        '        }\n'
        '        int old_tile=fx_ui_view.tile,old_row=fx_ui_view.row,old_page=fx_ui_view.credit_page;')
    text=replace(text,'        if(fx_ui_view.screen==FX_HOME||fx_ui_view.screen==FX_SETTINGS||fx_ui_view.screen==FX_CREDITS){',
        '        if(!fx_ui_view.check.visible&&(fx_ui_view.screen==FX_HOME||fx_ui_view.screen==FX_SETTINGS||fx_ui_view.screen==FX_CREDITS)){')
    text=replace(text,'        if(fx_ui_view.screen==FX_HOME){\n            if(dir)fx_ui_view.tile=(fx_ui_view.tile+dir+4)%4;',
        '        if(fx_ui_view.check.visible){\n'
        '            if(fx_ui_view.check.failed&&confirm)sd_check_request();\n'
        '            else if(down&(HidNpadButton_B|HidNpadButton_Plus)){__atomic_store_n(&fx_ui_command,-1,__ATOMIC_RELEASE);pthread_mutex_unlock(&fx_ui_lock);break;}\n'
        '        }else if(fx_ui_view.screen==FX_HOME){\n'
        '            int tiles=fx_ui_view.debug_launch?4:3;\n'
        '            if(dir)fx_ui_view.tile=(fx_ui_view.tile+dir+tiles)%tiles;')
    text=replace(text,'if(confirm&&fx_ui_view.tile==3){fx_ui_view.screen=FX_CREDITS;','if(confirm&&fx_ui_view.tile==2){fx_ui_view.screen=FX_CREDITS;')
    text=replace(text,'else if(confirm&&fx_ui_view.tile==2){fx_ui_view.screen=FX_SETTINGS;','else if(confirm&&fx_ui_view.tile==1){fx_ui_view.screen=FX_SETTINGS;')
    text=replace(text,'fx_ui_view.debug=fx_ui_view.tile==1;','fx_ui_view.debug=fx_ui_view.debug_launch&&fx_ui_view.tile==3;')
    text=replace(text,'fx_ui_view.message="rsaenh.dll missing. Copy the complete launcher update.";\n                        continue;',
        'fx_ui_view.message="rsaenh.dll missing. Copy the complete launcher update.";\n                        goto sd_ui_frame;')
    text=replace(text,'        if(confirm)fx_sfx_play(', 'sd_ui_frame:\n        if(confirm)fx_sfx_play(')
    text=replace(text,'        /* Main thread performs SD I/O',
        '        if(command==2){sd_check_run();continue;}\n'
        '        if(!sd_check_ready){pthread_mutex_lock(&fx_ui_lock);sd_check_request();pthread_mutex_unlock(&fx_ui_lock);continue;}\n'
        '        /* Main thread performs SD I/O')
    text=replace(text,'if(command<0){pthread_join(fx_ui_thread,NULL);fx_ui_created=0;return 0;}',
        'if(command<0){pthread_join(fx_ui_thread,NULL);fx_ui_created=0;fx_art_free(&sd_checked_art);return 0;}')
    # Keyboard has no controller mapper replacement and is inactive until launch.
    text=replace(text,'int wine_nx_pointer_poll( int *x, int *y, unsigned int *buttons )',
        '#include "keyboard_runtime.h"\nint wine_nx_pointer_poll( int *x, int *y, unsigned int *buttons )')
    text=replace(text,'    stick = padGetStickPos( &wine_nx_pad, 1 );',
        '    stick = padGetStickPos( &wine_nx_pad, 1 );\n    int keyboard_blocked=fx_keyboard_input_blocked();\n    if(keyboard_blocked){held=0;stick.x=stick.y=0;}')
    text=replace(text,'if (hidGetTouchScreenStates( &touch, 1 ) && touch.count > 0)',
        'if (!keyboard_blocked && hidGetTouchScreenStates( &touch, 1 ) && touch.count > 0)')
    text=replace(text,'        if (gamepad) keys = 0;','        if (gamepad || keyboard_blocked) keys = 0;')
    text=replace(text,'    wine_nx_f1_gpu_heap_init();',
        '    if(!guest_tests&&!sd_keyboard_start()){fx_native_error("Keyboard worker could not start. Close and relaunch.");return 1;}\n    wine_nx_f1_gpu_heap_init();')
    return text

def wine_overlay(name,text):
    if name=='winnx_drv':
        text=replace(text,'BOOL wine_nx_drv_ProcessEvents( DWORD mask )','#define FX_KEYBOARD_OVERLAY 1\n#include "pes13/fextendo_keyboard_wine.h"\nBOOL wine_nx_drv_ProcessEvents( DWORD mask )')
        text=replace(text,'    keys = wine_nx_send_keys();','    keys = wine_nx_send_keys();\n    keys |= fx_wine_text_pump();')
    elif name=='driver':
        text=replace(text,'            extern BOOL wine_nx_drv_ProcessEvents( DWORD );',
            '            extern BOOL wine_nx_drv_ProcessEvents( DWORD );\n            extern void wine_nx_drv_DestroyWindow(HWND);\n            extern void wine_nx_drv_NotifyIMEStatus(HWND,UINT);\n            extern BOOL wine_nx_drv_SetIMECompositionRect(HWND,RECT);')
        text=replace(text,'            null_user_driver.pProcessEvents        = wine_nx_drv_ProcessEvents;',
            '            null_user_driver.pProcessEvents        = wine_nx_drv_ProcessEvents;\n            null_user_driver.pDestroyWindow=wine_nx_drv_DestroyWindow;\n            null_user_driver.pNotifyIMEStatus=wine_nx_drv_NotifyIMEStatus;\n            null_user_driver.pSetIMECompositionRect=wine_nx_drv_SetIMECompositionRect;')
    elif name=='xinput':
        text=replace(text,'static pthread_mutex_t pad_mutex','extern int fx_keyboard_input_blocked(void);\nstatic pthread_mutex_t pad_mutex')
        text=replace(text,'        if (memcmp( &gamepad, &last_gamepad, sizeof(gamepad) ))',
            '        if(fx_keyboard_input_blocked())memset(&gamepad,0,sizeof(gamepad));\n        if (memcmp( &gamepad, &last_gamepad, sizeof(gamepad) ))')
    elif name=='horizon_keyboard':
        text=replace(text,'    unsigned int kf = 0, up = flags & HORIZON_KEYEVENTF_KEYUP;',
            '    unsigned int kf = 0, up = flags & HORIZON_KEYEVENTF_KEYUP;\n'
            '    if(!input_vkey&&(flags&0x0004)){event->message=up?HORIZON_KBD_WM_KEYUP:HORIZON_KBD_WM_KEYDOWN;event->vkey=0xe7;event->lparam=((unsigned long long)scan<<16)|1;event->data_flags=0;return;}')
    elif name=='horizon':
        text=replace(text,'        if ((raw_device = horizon_rawinput_find( horizon_rawinput_devices, horizon_rawinput_device_count,\n                                                 HORIZON_RAWINPUT_USAGE_KEYBOARD )))',
            '        if (!(kbd->flags&0x0004) && (raw_device = horizon_rawinput_find( horizon_rawinput_devices, horizon_rawinput_device_count,\n                                                 HORIZON_RAWINPUT_USAGE_KEYBOARD )))')
    else:raise ValueError(name)
    return text
