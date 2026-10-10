"""Optional HUD/pacing controls and a lighter normal launch, based on v6."""
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT, profile_config

BUILD = 'sleepingdogs-low-window-v7-performance-hud'
MARKER = 'sleepingdogs-fextendo-0.1.0-low-window-v7-performance-hud'
FILES = {f'wine-nx-probe/source/{n}' for n in
         ('runtime.c', 'f1_settings.h', 'f1_dx_hud.h', 'sd_frame_summary.h', 'f1_crash.c')}


def performance_config(async_mode=False):
    # Keep the proven memory/descriptor/compiler settings. Only queueing,
    # requested sync interval and anisotropy differ from the Stable profile.
    return (profile_config('stable', async_mode)
            .replace('conservative DX11 bring-up', 'optional Performance profile')
            .replace('d3d9.presentInterval = 1', 'd3d9.presentInterval = 0')
            .replace('dxgi.syncInterval = 1', 'dxgi.syncInterval = 0')
            .replace('dxgi.maxFrameLatency = 2', 'dxgi.maxFrameLatency = 3'))


def settings(s):
    s = exact(s, '    FX_SETTINGS_PAGES };', '    FX_SETTINGS_DX_LOG, FX_SETTINGS_PAGES };')
    s = exact(s, 'counts[FX_SETTINGS_PAGES]={5,4,2,3,2}',
              'counts[FX_SETTINGS_PAGES]={6,5,2,3,2,3}')
    s = exact(s, 'v->settings_page==FX_SETTINGS_KEYBOARD?2:3;',
              'v->settings_page==FX_SETTINGS_KEYBOARD?2:v->settings_page==FX_SETTINGS_DX_LOG?5:3;')
    s = exact(s, '"Controller","Audio"};', '"Controller","Audio","DXVK HUD"};')
    s = exact(s, '"Launcher sounds and music."};',
              '"Launcher sounds and music.","Show DXVK statistics while you play."};')
    s = exact(s, '"Audio","Debug timestamp"};', '"Audio","Debug timestamp","DXVK HUD"};')
    s = exact(s, 'case FX_SETTINGS_GRAPHICS:return fx_preset_names[row];',
              'case FX_SETTINGS_DX_LOG:return fx_dx_hud_names[row];\n    case FX_SETTINGS_GRAPHICS:return fx_preset_names[row];')
    s = exact(s, 'row==3?"Menu sounds and background music":"On-screen stopwatch while you play";',
              'row==3?"Menu sounds and background music":row==5?fx_dx_hud_names[fx_dx_hud]:"On-screen stopwatch while you play";')
    s = exact(s, 'case FX_SETTINGS_GRAPHICS:return fx_preset_details[row];',
              'case FX_SETTINGS_DX_LOG:return row==0?"Hide the DXVK overlay.":row==1?"Frame rate only.":"Frame times, GPU estimate, memory and worker stats.";\n'
              '    case FX_SETTINGS_GRAPHICS:return fx_preset_details[row];')
    s = exact(s, '(v->settings_page==FX_SETTINGS_KEYBOARD&&fx_input_mode==row);',
              '(v->settings_page==FX_SETTINGS_KEYBOARD&&fx_input_mode==row)||\n'
              '        (v->settings_page==FX_SETTINGS_DX_LOG&&fx_dx_hud==row);')
    s = exact(s, 'v->settings_page==FX_SETTINGS_ROOT&&row<4;',
              'v->settings_page==FX_SETTINGS_ROOT&&(row<4||row==5);')
    s = exact(s, '    if(page==FX_SETTINGS_ROOT&&row<4){',
              '    if(page==FX_SETTINGS_ROOT&&row==5){fx_settings_enter(v,FX_SETTINGS_DX_LOG,fx_dx_hud);return 1;}\n'
              '    if(page==FX_SETTINGS_ROOT&&row<4){')
    s = exact(s, '    if(page==FX_SETTINGS_GRAPHICS){',
              '    if(page==FX_SETTINGS_DX_LOG){if(!fx_dx_hud_save(root,row))return 0;fx_dx_hud=row;}\n'
              '    else if(page==FX_SETTINGS_GRAPHICS){')
    return s


def apply(source: Path):
    native = source / 'wine-nx-probe/source'
    p = native / 'runtime.c'
    s = p.read_text()
    s = exact(s, 'sleepingdogs-fextendo-0.1.0-low-window-v6-cpu-topology-fix', MARKER)
    s = exact(s, '#define FX_APP_VERSION "0.1.0"', '#define FX_APP_VERSION "0.1.0-v7"')
    s = exact(s, 'fx_preset_ids[4] = {"balanced","low-latency","stable","quality"}',
              'fx_preset_ids[5] = {"balanced","low-latency","stable","quality","performance"}')
    s = exact(s, 'fx_preset_names[4] = {"Balanced","Low latency","Stable","Quality"}',
              'fx_preset_names[5] = {"Balanced","Low latency","Stable","Quality","Performance"}')
    s = exact(s, 'fx_preset_details[4] = {"Default DXVK pacing","Shortest frame queue","Conservative GPU load","Sharper texture filtering"}',
              'fx_preset_details[5] = {"Default DXVK pacing","Shortest frame queue","Conservative GPU load","Sharper texture filtering",'
              '"VSync off / up to 3 frames / lighter filtering"}')
    s = exact(s, "b[0]<='3' && b[1]=='\\n'", "b[0]<='4' && b[1]=='\\n'")
    s = exact(s, 'if (selected < 0 || selected > 3) return 0;', 'if (selected < 0 || selected > 4) return 0;')
    s = exact(s, 'static int fx_apply_preset(const char *root,int selected) {',
              '#include "f1_dx_hud.h"\nstatic int fx_apply_preset(const char *root,int selected) {')
    s = exact(s, '    if (!fx_copy_file(source,stage) || !fx_files_equal(source,stage)) {',
              '    if (!fx_dx_hud_config(source,stage,fx_dx_hud_load(root))) {')
    s = exact(s, '    fx_input_mode=fx_input_mode_load(RUNTIME_DIR);',
              '    fx_input_mode=fx_input_mode_load(RUNTIME_DIR);\n    fx_dx_hud=fx_dx_hud_load(RUNTIME_DIR);')
    s = exact(s, '!fx_renderer_option(config,"d3d9.presentInterval","1")||',
              '(!fx_renderer_option(config,"d3d9.presentInterval","1")&&\n'
              '        !fx_renderer_option(config,"d3d9.presentInterval","0"))||')
    marker = '            log_line("[FEXTENDO-RENDERER] selected=%s verified=1 dlls=d3d9,d3d11,dxgi",fx_renderer_ids[renderer]);break;}'
    s = exact(s, marker,
              '            log_line("[SD-DXVK-CONFIG] profile=%s renderer=%s hud=%s",\n'
              '                     fx_preset_ids[selected],fx_renderer_ids[renderer],fx_dx_hud_names[fx_dx_hud_load(RUNTIME_DIR)]);\n' + marker)
    s = exact(s, '__atomic_store_n(&f1_startup_watch_enabled,1,__ATOMIC_RELEASE);',
              '__atomic_store_n(&f1_startup_watch_enabled,fx_ui_view.debug,__ATOMIC_RELEASE);')
    s = exact(s, '#include "sd_loading_report.inc"',
              '#include "sd_loading_report.inc"\n#include "sd_frame_summary.h"')
    s = exact(s, '        unsigned presented = __atomic_load_n(&fx_first_present, __ATOMIC_ACQUIRE);',
              '        unsigned presented = __atomic_load_n(&fx_first_present, __ATOMIC_ACQUIRE);\n'
              '        if (presented) sd_frame_summary(now);')
    s = exact(s, '[SD-WATCH] v3 sync lifecycle + first-invalid object; debug detail=600s;',
              '[SD-WATCH] v4 normal=frame-summary-only; Launch Debug detail=600s;')
    p.write_text(s)
    p = native / 'f1_settings.h'
    p.write_text(settings(p.read_text()))
    (native / 'f1_dx_hud.h').write_bytes((ROOT / 'tools/f1_dx_hud.h').read_bytes())
    (native / 'sd_frame_summary.h').write_bytes((ROOT / 'src/low_window/sd_frame_summary.h').read_bytes())
    p = native / 'f1_crash.c'
    s = exact(p.read_text(), 'static const char *profiles[] = {"Balanced", "Low latency", "Stable", "Quality"};',
              'static const char *profiles[] = {"Balanced", "Low latency", "Stable", "Quality", "Performance"};')
    s = exact(s, 'profile >= 0 && profile < 4 ? profiles[profile]', 'profile >= 0 && profile < 5 ? profiles[profile]')
    p.write_text(s)

