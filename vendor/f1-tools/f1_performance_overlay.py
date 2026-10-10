"""Performance/HUD changes applied on top of the verified as39-test1 source."""
from pathlib import Path
from f1_overlay import exact

VERSION = "0.1.29-perf1"
BUILD = "f1-fextendo-0.1.29-performance-hud"
TOOLS = Path(__file__).resolve().parent


def settings(s: str) -> str:
    s = exact(s, '    FX_SETTINGS_PAGES };', '    FX_SETTINGS_DX_LOG, FX_SETTINGS_PAGES };')
    s = exact(s, 'counts[FX_SETTINGS_PAGES]={5,4,2,3,2}',
              'counts[FX_SETTINGS_PAGES]={6,5,2,3,2,3}')
    s = exact(s, 'v->settings_page==FX_SETTINGS_KEYBOARD?2:3;',
              'v->settings_page==FX_SETTINGS_KEYBOARD?2:v->settings_page==FX_SETTINGS_DX_LOG?5:3;')
    s = exact(s, '"Keyboard","Audio"};', '"Keyboard","Audio","Show DX Log"};')
    s = exact(s, '"Launcher sounds and music."};',
              '"Launcher sounds and music.","Show DXVK statistics while you play."};')
    s = exact(s, '"Audio","Debug timestamp"};', '"Audio","Debug timestamp","Show DX Log"};')
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


def apply(source: Path) -> list[str]:
    native = source / 'wine-nx-probe/source'
    p = native / 'runtime.c'
    s = p.read_text()
    s = exact(s, '#define FX_APP_VERSION "0.1.28-as39t1"', f'#define FX_APP_VERSION "{VERSION}"')
    s = exact(s, '"f1-fextendo-0.1.28-as39-test1"', f'"{BUILD}"')
    s = exact(s, 'fx_preset_ids[4] = {"balanced","low-latency","stable","quality"}',
              'fx_preset_ids[5] = {"balanced","low-latency","stable","quality","performance"}')
    s = exact(s, 'fx_preset_names[4] = {"Balanced","Low latency","Stable","Quality"}',
              'fx_preset_names[5] = {"Balanced","Low latency","Stable","Quality","Performance"}')
    s = exact(s, 'fx_preset_details[4] = {"Default DXVK pacing","Shortest frame queue","Conservative GPU load","Sharper texture filtering"}',
              'fx_preset_details[5] = {"VSync on / 2 frames / game filtering","VSync off / 1 frame / quick response",'
              '"VSync on / 2 frames / lighter filtering","VSync on / 2 frames / 4x filtering",'
              '"VSync off / up to 3 frames / lighter filtering"}')
    s = exact(s, "b[0]<='3' && b[1]=='\\n'", "b[0]<='4' && b[1]=='\\n'")
    s = exact(s, 'if (selected < 0 || selected > 3) return 0;',
              'if (selected < 0 || selected > 4) return 0;')
    s = exact(s, 'static int fx_apply_preset(const char *root,int selected) {',
              '#include "f1_dx_hud.h"\nstatic int fx_apply_preset(const char *root,int selected) {')
    s = exact(s, '    if (!fx_copy_file(source,stage) || !fx_files_equal(source,stage)) {',
              '    if (!fx_dx_hud_config(source,stage,fx_dx_hud_load(root))) {')
    s = exact(s, '    fx_input_mode=fx_input_mode_load(RUNTIME_DIR);',
              '    fx_input_mode=fx_input_mode_load(RUNTIME_DIR);\n    fx_dx_hud=fx_dx_hud_load(RUNTIME_DIR);')
    # Renderer bundles carry a default config; profiles may disable VSync.
    s = exact(s, '!fx_renderer_option(config,"d3d9.presentInterval","1")||',
              '(!fx_renderer_option(config,"d3d9.presentInterval","1")&&\n'
              '        !fx_renderer_option(config,"d3d9.presentInterval","0"))||')
    marker = '            log_line("[FEXTENDO-RENDERER] selected=%s verified=1 dlls=d3d9,d3d11,dxgi",fx_renderer_ids[renderer]);break;}'
    s = exact(s, marker,
              '            log_line("[F1-DXVK-CONFIG] profile=%s renderer=%s hud=%s",\n'
              '                     fx_preset_ids[selected],fx_renderer_ids[renderer],fx_dx_hud_names[fx_dx_hud_load(RUNTIME_DIR)]);\n' + marker)
    s = exact(s, 'static void *f1_startup_monitor(void *unused)',
              '#include "f1_frame_summary.h"\nstatic void *f1_startup_monitor(void *unused)')
    s = exact(s, '        if (seconds-last < (presented ? 30u : 5u)) continue;',
              '        if (presented) f1_frame_summary(now);\n'
              '        if (seconds-last < (presented ? 30u : 5u)) continue;')
    p.write_text(s)
    (native / 'f1_settings.h').write_text(settings((native / 'f1_settings.h').read_text()))
    (native / 'f1_dx_hud.h').write_bytes((TOOLS / 'f1_dx_hud.h').read_bytes())
    (native / 'f1_frame_summary.h').write_bytes((TOOLS / 'f1_frame_summary.h').read_bytes())
    p = native / 'f1_crash.c'
    s = exact(p.read_text(), 'f1-fextendo-0.1.28-as39-test1', BUILD)
    s = s.replace('/ crash.log / 0.1.28-as39t1', f'/ crash.log / {VERSION}')
    s = exact(s, 'static const char *profiles[] = {"Balanced", "Low latency", "Stable", "Quality"};',
              'static const char *profiles[] = {"Balanced", "Low latency", "Stable", "Quality", "Performance"};')
    s = exact(s, 'profile >= 0 && profile < 4 ? profiles[profile]',
              'profile >= 0 && profile < 5 ? profiles[profile]')
    p.write_text(s)
    return ['wine-nx-probe/source/' + name for name in
            ('runtime.c', 'f1_settings.h', 'f1_dx_hud.h', 'f1_frame_summary.h', 'f1_crash.c')]
