"""Game-specific source overlay for an isolated FEXTendo/FEX build.

This module only edits a copied native source tree.  It never edits PES13-NX.
"""
from __future__ import annotations

from pathlib import Path


GAME_DIR = "F1_2013"
GAME_EXE = "F1_2013.exe"
IMAGE_SIZE = 0x011ED000  # Read from the supplied PE32 SizeOfImage.
TOOL_DIR = Path(__file__).resolve().parent


def exact(source: str, old: str, new: str, count: int = 1) -> str:
    found = source.count(old)
    if found != count:
        raise ValueError(f"Expected {count} occurrences of {old[:80]!r}, found {found}")
    return source.replace(old, new)


def replace_function(source: str, signature: str, body: str) -> str:
    start = source.find(signature)
    if start < 0 or source.find(signature, start + 1) >= 0:
        raise ValueError(f"Function signature missing or duplicated: {signature}")
    brace = source.find("{", start + len(signature))
    if brace < 0:
        raise ValueError(f"Function body missing: {signature}")
    depth = 0
    for end in range(brace, len(source)):
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
            if depth == 0:
                return source[:start] + body + source[end + 1:]
    raise ValueError(f"Unclosed function: {signature}")


F1_RECOVER = r'''static int fx_recover(const char *root) {
    /* A profile is reapplied from its selected source before every launch. */
    (void)root;
    return 1;
}'''


F1_PRESET = r'''static int fx_apply_preset(const char *root,int selected) {
    char source[768], target[768], stage[800], choice[768];
    char renderer_file[768], renderer[2];
    if (selected < 0 || selected > 3) return 0;
    snprintf(renderer_file,sizeof(renderer_file),"%s/launcher/renderer-choice.txt",root);
    renderer[0]='0'; renderer[1]='\n';
    if (fx_read(renderer_file,renderer,sizeof(renderer))!=2 || renderer[0]!='1')
        renderer[0]='0';
    snprintf(source,sizeof(source),"%s/launcher/presets/%s/%s/dxvk.conf",
             root,fx_preset_ids[selected],fx_renderer_ids[renderer[0]-'0']);
    snprintf(target,sizeof(target),"%s/drive_c/F1_2013/dxvk.conf",root);
    snprintf(stage,sizeof(stage),"%s.f1-new",target);
    snprintf(choice,sizeof(choice),"%s/launcher/selected.txt",root);
    if (!fx_mkdir_parents(target) || !fx_mkdir_parents(choice)) return 0;
    if (!fx_copy_file(source,stage) || !fx_files_equal(source,stage)) {
        unlink(stage); return 0;
    }
    /* Horizon rename cannot replace an existing destination.  The old file is
     * retained until the new copy has been fully written and checked. */
    char backup[800]; snprintf(backup,sizeof(backup),"%s.f1-old",target);
    if (unlink(backup) && errno!=ENOENT) { unlink(stage); return 0; }
    if (!access(target,F_OK) && rename(target,backup)) { unlink(stage); return 0; }
    if (rename(stage,target)) { rename(backup,target); unlink(stage); return 0; }
    unlink(backup);
    char chosen[2]={(char)('0'+selected),'\n'};
    return fx_write(choice,chosen,sizeof(chosen));
}'''


def patch_runtime(source: str) -> str:
    # Runtime and prefix paths are per-game so the two installations coexist.
    source = source.replace("switch/pes13-fex", "switch/f1-fex")
    source = exact(source, '"/PES13/pes2013.exe"', '"/F1_2013/F1_2013.exe"')
    source = source.replace('"/PES13/pes2013.keys.txt"',
                            '"/F1_2013/F1_2013.keys.txt"')
    source = source.replace("/drive_c/PES13/", "/drive_c/F1_2013/")
    source = source.replace("\\\\PES13\\\\dxvk.conf", "\\\\F1_2013\\\\dxvk.conf")
    source = exact(source, "wine_nx_pes13_registry_enabled = !guest_tests;",
                   "wine_nx_pes13_registry_enabled = 0; /* F1 has no PES installation metadata. */")
    source = source.replace("Wine preload exclusion=400000-1c9a000",
                            "Wine preload exclusion=400000-15ed000")
    source = exact(source, '"WINEPRELOADRESERVE", "400000-1c9a000"',
                   '"WINEPRELOADRESERVE", "400000-15ed000"')

    # The PES settings.dat format is incompatible with F1.  Profiles only
    # choose DXVK behavior; the game's own video settings remain untouched.
    source = exact(source,
        'static const char *const fx_preset_ids[4] = {"medium-720","low-720","extra-low-540","high-720"};',
        'static const char *const fx_preset_ids[4] = {"balanced","low-latency","stable","quality"};')
    source = exact(source,
        'static const char *const fx_preset_names[4] = {"Medium 720p","Low 720p","Extra Low 540p","High 720p"};',
        'static const char *const fx_preset_names[4] = {"Balanced","Low latency","Stable","Quality"};')
    source = exact(source,
        'static const char *const fx_preset_details[4] = {"1280 x 720  /  Balanced detail","1280 x 720  /  Reduced detail","960 x 540  /  Low detail","1280 x 720  /  Maximum detail"};',
        'static const char *const fx_preset_details[4] = {"Default DXVK pacing","Shortest frame queue","Conservative GPU load","Sharper texture filtering"};')
    source = replace_function(source, "static int fx_recover(const char *root)", F1_RECOVER)
    source = replace_function(source, "static int fx_apply_preset(const char *root,int selected)", F1_PRESET)
    # Renderer helper is declared after presets in the original source.  The
    # function definitions are ordered before runtime main, so add prototypes.
    source = exact(source, "static int fx_apply_preset(const char *root,int selected) {",
                   "static int fx_copy_file(const char *, const char *);\n"
                   "static int fx_files_equal(const char *, const char *);\n"
                   "static const char *const fx_renderer_ids[2];\n"
                   "static int fx_apply_preset(const char *root,int selected) {")
    source = source.replace('"Graphics preset"', '"DXVK profile"')
    source = source.replace('"Graphics, renderer, on-screen debug and sound."',
                            '"DXVK modes, on-screen debug and sound."')
    source = source.replace('"Choose the graphics preset for your next game."',
                            '"Choose DXVK pacing for your next race."')
    source = source.replace('"16:9 widescreen  /  VSync ON"', '"Game video settings stay in F1 2013"')
    source = source.replace('"%s  /  16:9  /  VSync ON"', '"%s  /  DXVK profile"')
    source = source.replace('"PES13"', '"F1 2013"')
    source = source.replace('"Starting PES13"', '"Starting F1 2013"')
    source = source.replace('"PES13 was not found. Check the game folder."',
                            '"F1 2013 was not found. Check the game folder."')
    source = source.replace('"Launch failed. PES13 exited before its first frame."',
                            '"Launch failed. F1 2013 exited before its first frame."')
    source = source.replace('"Fextendo could not start PES13. Check fex-runtime.log, then close and relaunch."',
                            '"F1 launcher could not start the game. Check fex-runtime.log."')
    source = source.replace('"Fextendo could not start PES13. Check the game and runtime files, then close and relaunch."',
                            '"F1 launcher could not start the game. Check fex-runtime.log."')
    source = source.replace('"PES13 could not start. Check fex-runtime.log."',
                            '"F1 2013 could not start. Check fex-runtime.log."')
    source = source.replace('"PES13 could not start. Check the game and runtime files."',
                            '"F1 2013 could not start. Check game and runtime files."')
    source = source.replace('"Starting PES13..."', '"Starting F1 2013..."')
    source = exact(source, '#define FX_APP_VERSION "0.3.7"',
                   '#define FX_APP_VERSION "0.1.28"')
    source = exact(source, '"pes13-fextendo-production-no-log-v1"',
                   '"f1-fextendo-0.1.28-memory-map"')
    source = exact(source, '#define FX_RELEASE "v3.6"',
                   '#define FX_RELEASE "F1 2013"')
    source = source.replace('"native launcher and PES-specific runtime work."',
                            '"native launcher and FEX runtime integration."')
    source = source.replace('"Unofficial project. Supply your own PES 2013 PC v1.0."',
                            '"Unofficial project. Supply your own F1 2013 PC files."')
    source = source.replace('"[FEXTENDO] launch requested; canonical settings=C:\\\\KONAMI\\\\Pro Evolution Soccer 2013\\\\settings.dat; VSync=on"',
                            '"[F1-FEX] launch requested; game settings remain owned by F1 2013"')
    # The release snapshot predates grouped Settings.  Keep the current PES
    # page model while binding Keyboard to the input modes this runtime has.
    source = exact(source,
        'enum fx_screen { FX_HOME,FX_SETTINGS,FX_LOADING,FX_FAILED,FX_CREDITS };',
        'enum fx_screen { FX_HOME,FX_SETTINGS,FX_LOADING,FX_FAILED,FX_CREDITS };')
    source = exact(source,
        'int tile,row,selected,saved,fatal,timestamp,sound,battery,charging,credit_page,music,renderer;',
        'int tile,row,selected,saved,fatal,timestamp,sound,battery,charging,credit_page,music,renderer,settings_page,debug;')
    source = exact(source,
        'struct fx_art { uint32_t',
        '#include "f1_settings.h"\nstruct fx_art { uint32_t')
    source = exact(source, '*tiles[3][FX_TILE_MAX-FX_TILE_MIN+1]',
                   '*tiles[4][FX_TILE_MAX-FX_TILE_MIN+1]')
    source = exact(source, 'for(int k=0;k<3;k++)for(int i=0;i<=FX_TILE_MAX-FX_TILE_MIN;i++)free(a->tiles[k][i]);',
                   'for(int k=0;k<4;k++)for(int i=0;i<=FX_TILE_MAX-FX_TILE_MIN;i++)free(a->tiles[k][i]);')
    source = exact(source, 'for(int id=0;id<3;id++)for(int w=FX_TILE_MIN;w<=FX_TILE_MAX;w++)',
                   'for(int id=0;id<4;id++)for(int w=FX_TILE_MIN;w<=FX_TILE_MAX;w++)')
    source = exact(source, 'id==0?a->icon:id==1?a->settings_icon:a->credits_icon',
                   'id<2?a->icon:id==2?a->settings_icon:a->credits_icon')
    source = exact(source,
        '#define FX_SETTINGS_ROWS 9\n#define FX_SETTINGS_MAX_SCROLL ((FX_SETTINGS_ROWS-3)*116.f)\n'
        'static float fx_settings_scroll_target(int row) {return fx_clamp(row-2.f,0,FX_SETTINGS_ROWS-3)*116.f;}\n', '')
    source = exact(source, 'target=fx_settings_scroll_target(v->row);',
                   'target=fx_settings_scroll_target(v->row,v->settings_page);')
    # Titles belong to the current settings page.  Baking the old flat menu
    # title into the cached scene causes the two headings to overlap.
    source = exact(source,
        '        fx_text(c,414,116,"Settings",2,FX_WHITE);\n'
        '        fx_text(c,417,172,"DXVK modes, on-screen debug and sound.",0,FX_MUTED);\n', '')
    # PES logo.rgba is the PES game title, not the shared FEXTendo wordmark.
    source = exact(source,
        'fx_image(c,c->art->logo,480,158,62,304,438,144,0,255);',
        'fx_image(c,c->art->wordmark,600,128,62,324,438,94,0,255);')
    source = exact(source,
        'fx_image(c,c->art->logo,480,158,63,477,276,91,0,220);',
        'fx_image(c,c->art->wordmark,600,128,63,495,276,59,0,220);')
    source = replace_function(source, 'static void fx_render(struct fx_canvas *c,const struct fx_view *v)',
                              (TOOL_DIR / 'f1_render.inc').read_text())
    source = exact(source, '"The beautiful game,"', '"A new race,"')
    source = exact(source, '"reborn."', '"on your Switch."')
    source = exact(source, '"PC football. On your Switch."', '"PC racing. On your Switch."')
    source = exact(source, '"Make it"', '"Set your"')
    source = exact(source, '"your game."', '"race up."')
    source = exact(source, '"Four presets."', '"Your preferences."')
    source = exact(source, '"One press to switch."', '"Organized by category."')

    # In the release source log_line and runtime_trace are empty.  The black
    # debug view receives a bounded thread-safe stream of Wine startup events.
    source = exact(source, 'static int wine_nx_console_active = 0;',
        'static int wine_nx_console_active = 0;\n'
        'static int fx_debug_live;\n'
        'static pthread_mutex_t fx_debug_lock=PTHREAD_MUTEX_INITIALIZER;\n'
        'static char fx_debug_lines[21][120];\n'
        'static unsigned fx_debug_total;\n'
        'static FILE *fx_debug_file;')
    source = replace_function(source, 'static void log_line( const char *fmt, ... )', r'''static void log_line( const char *fmt, ... )
{
    if (!__atomic_load_n(&fx_debug_live,__ATOMIC_ACQUIRE)) return;
    char line[1024];va_list args;
    va_start(args,fmt);vsnprintf(line,sizeof(line),fmt,args);va_end(args);
    if (!strncmp(line,"[BIND]",6)) return;
    pthread_mutex_lock(&fx_debug_lock);
    snprintf(fx_debug_lines[fx_debug_total%21],120,"%.119s",line);
    fx_debug_total++;
    if (fx_debug_file) { fprintf(fx_debug_file,"%s\n",line);fflush(fx_debug_file); }
    pthread_mutex_unlock(&fx_debug_lock);
}''')
    source = replace_function(source, 'void wine_nx_runtime_trace( const char *msg )',
        'void wine_nx_runtime_trace( const char *msg )\n{\n    log_line("%s",msg);\n}')
    source = exact(source, 'if(!fx_owned())return;\n    pthread_mutex_lock(&fx_ui_lock);',
                   'if(!fx_owned())return;\n    log_line("[STAGE] %s",text);\n    pthread_mutex_lock(&fx_ui_lock);')
    source = exact(source,
        'fx_ui_view.message=fx_ui_message;fx_ui_view.screen=FX_FAILED;fx_ui_view.fatal=1;',
        'fx_ui_view.message=fx_ui_message;\n'
        '        if(fx_ui_view.debug){fx_ui_view.fatal=1;log_line("[FAIL] %s",message);}\n'
        '        else {fx_ui_view.screen=FX_FAILED;fx_ui_view.fatal=1;}')
    source = exact(source, 'fx_ui_view.selected=fx_selected(RUNTIME_DIR);',
                   'fx_ui_view.selected=fx_selected(RUNTIME_DIR);\n    fx_input_mode=fx_input_mode_load(RUNTIME_DIR);')
    home_start = source.index('        if(fx_ui_view.screen==FX_HOME){',source.index('static void *fx_ui_main'))
    settings_start = source.index('        }else if(fx_ui_view.screen==FX_SETTINGS){',home_start)
    home = '''        if(fx_ui_view.screen==FX_HOME){
            if(dir)fx_ui_view.tile=(fx_ui_view.tile+dir+4)%4;
            if(down&HidNpadButton_B)fx_ui_view.tile=0;
            if(confirm&&fx_ui_view.tile==3){fx_ui_view.screen=FX_CREDITS;fx_ui_view.credit_page=0;}
            else if(confirm&&fx_ui_view.tile==2){fx_ui_view.screen=FX_SETTINGS;fx_settings_enter(&fx_ui_view,FX_SETTINGS_ROOT,0);}
            else if(confirm){
                FILE *game=fopen(DEFAULT_TARGET,"rb");
                if(!game){fx_ui_view.screen=FX_FAILED;fx_ui_view.fatal=0;fx_ui_view.message="F1 2013 was not found. Check the game folder.";}
                else{
                    fclose(game);
                    if(access(WINE_DRIVE_C "/windows/syswow64/rsaenh.dll",R_OK)){
                        fx_ui_view.screen=FX_FAILED;fx_ui_view.fatal=0;
                        fx_ui_view.message="rsaenh.dll missing. Copy the complete launcher update.";
                        continue;
                    }
                    fx_ui_view.debug=fx_ui_view.tile==1;
                    {
                        pthread_mutex_lock(&fx_debug_lock);
                        fx_debug_total=0;memset(fx_debug_lines,0,sizeof(fx_debug_lines));
                        fx_debug_file=fopen(RUNTIME_DIR "/fex-runtime.log","wb");
                        pthread_mutex_unlock(&fx_debug_lock);
                        __atomic_store_n(&fx_debug_live,1,__ATOMIC_RELEASE);
                        log_line("[F1-FEX] target=%s",DEFAULT_TARGET);
                        log_line("[F1-FEX] launch_mode=%s",fx_ui_view.debug?"debug":"gui");
                        if(fx_debug_file)log_line("[F1-FEX] live debug active; startup log=fex-runtime.log");
                        else log_line("[WARN] Could not open fex-runtime.log; photograph this screen");
                    }
                    fx_timestamp_arm(fx_ui_view.timestamp,frame_start);
                    fx_ui_view.screen=FX_LOADING;fx_ui_view.message="Preparing your game...";pending=1;started=frame_start;
                }
            }
'''
    source = source[:home_start] + home + source[settings_start:]
    settings_start = source.index('        }else if(fx_ui_view.screen==FX_SETTINGS){',home_start)
    credits_start = source.index('        }else if(fx_ui_view.screen==FX_CREDITS){',settings_start)
    settings = '''        }else if(fx_ui_view.screen==FX_SETTINGS){
            int rows=fx_settings_rows(fx_ui_view.settings_page);
            if(dir){fx_ui_view.row=(fx_ui_view.row+dir+rows)%rows;fx_ui_view.saved=0;}
            if(down&HidNpadButton_B)fx_settings_back(&fx_ui_view);
            else if(confirm){
                int music=fx_ui_view.music;
                if(!fx_settings_choose(&fx_ui_view,RUNTIME_DIR)){
                    fx_ui_view.screen=FX_FAILED;fx_ui_view.fatal=0;
                    fx_ui_view.message="Could not save settings. Check the SD card.";
                }
                if(music!=fx_ui_view.music)fx_music_set(fx_ui_view.music);
            }
'''
    source = source[:settings_start] + settings + source[credits_start:]
    source = exact(source,
        'fx_ui_view.screen=FX_FAILED;fx_ui_view.fatal=1;fx_ui_view.message="Startup timed out. Close and relaunch to retry.";',
        'if(fx_ui_view.debug){log_line("[FAIL] Startup timed out before the first frame");started=0;}\n'
        '            else {fx_ui_view.screen=FX_FAILED;fx_ui_view.fatal=1;fx_ui_view.message="Startup timed out. Close and relaunch to retry.";}')
    source = exact(source, 'log_line("[FEXTENDO] launcher stopped and framebuffer released before 3D handoff");',
        'log_line("[FEXTENDO] launcher stopped and framebuffer released before 3D handoff");\n'
        '        __atomic_store_n(&fx_debug_live,0,__ATOMIC_RELEASE);\n'
        '        pthread_mutex_lock(&fx_debug_lock);\n'
        '        if(fx_debug_file){fclose(fx_debug_file);fx_debug_file=NULL;}\n'
        '        pthread_mutex_unlock(&fx_debug_lock);')
    source = exact(source, 'if (!pes13_fex_context_preflight()) park_forever();',
        'if (!pes13_fex_context_preflight()) {log_line("[FAIL] FEX context preflight");fx_fail("FEX context preflight failed.");park_forever();}')
    source = exact(source, 'if (setenv("WINEPREFIX", "/switch/f1-fex", 1))\n    { wine_nx_runtime_trace("[FEX2] environment setup failed"); park_forever(); }',
        'if (setenv("WINEPREFIX", "/switch/f1-fex", 1))\n    { log_line("[FAIL] WINEPREFIX setup");fx_fail("WINEPREFIX setup failed.");park_forever(); }')
    return patch_thread_budget(patch_startup_monitor(patch_startup_diagnostics(patch_dx11_runtime(source))))


def patch_thread_budget(source: str) -> str:
    source = exact(source, 'static int fx_launcher_start(void) {',
        'extern int wine_nx_f1_prepare_threads(char *, size_t);\nstatic int fx_launcher_start(void) {')
    source = exact(source,
        '        int ready=renderer_ready&&fx_apply_preset(RUNTIME_DIR,selected);',
        '        int ready=renderer_ready&&fx_apply_preset(RUNTIME_DIR,selected);\n'
        '        char thread_error[192];\n'
        '        const char *launch_error=renderer_ready?\n'
        '            "Cannot apply graphics profile. Check SD space and fex-runtime.log.":fx_renderer_error_text;\n'
        '        if(ready&&!wine_nx_f1_prepare_threads(thread_error,sizeof(thread_error))){\n'
        '            ready=0;launch_error=thread_error;\n'
        '            log_line("[F1-LAUNCH] %s",thread_error);\n'
        '        }')
    source = exact(source,
        '        if(!ready)log_line("[F1-RENDERER] %s",renderer_ready?"Cannot apply graphics preset":fx_renderer_error_detail);',
        '        if(!ready&&launch_error!=thread_error)log_line("[F1-RENDERER] %s",renderer_ready?"Cannot apply graphics preset":fx_renderer_error_detail);')
    return exact(source,
        '''        snprintf(fx_ui_message,sizeof(fx_ui_message),"%s",renderer_ready?
            "Cannot apply graphics profile. Check SD space and fex-runtime.log.":fx_renderer_error_text);''',
        '        snprintf(fx_ui_message,sizeof(fx_ui_message),"%s",launch_error);')


def patch_dx11_runtime(source: str) -> str:
    start = source.index('#ifndef FEXTENDO_RENDERERS_H')
    end = source.index('\n#endif', start) + len('\n#endif')
    source = source[:start] + (TOOL_DIR / 'f1_renderers.inc').read_text().rstrip() + source[end:]
    source = exact(source, 'static const char runtime_environment[] =\n', r'''static const char runtime_environment[] =
    "WINEDLLOVERRIDES=d3d9,d3d11,dxgi=n,b\0"
    "DXVK_LOG_LEVEL=info\0"
    "DXVK_LOG_PATH=C:\\F1_2013\0"
''')
    source = exact(source, 'if (setenv("WINEPREFIX", "/switch/f1-fex", 1))',
        'if (setenv("WINEDLLOVERRIDES", "d3d9,d3d11,dxgi=n,b", 1) ||\n'
        '        setenv("WINEPREFIX", "/switch/f1-fex", 1))')
    source = exact(source, 'selected=%s verified=1', 'selected=%s verified=1 dlls=d3d9,d3d11,dxgi')
    source = exact(source, 'int ready=fx_apply_renderer(RUNTIME_DIR,renderer)&&fx_apply_preset(RUNTIME_DIR,selected);',
                   'int renderer_ready=fx_apply_renderer(RUNTIME_DIR,renderer);\n'
                   '        int ready=renderer_ready&&fx_apply_preset(RUNTIME_DIR,selected);\n'
                   '        if(!ready)log_line("[F1-RENDERER] %s",renderer_ready?"Cannot apply graphics preset":fx_renderer_error_detail);')
    source = exact(source, 'fx_ui_view.message="Could not prepare the renderer. Copy both renderer folders and check SD space.";',
                   'snprintf(fx_ui_message,sizeof(fx_ui_message),"%s",renderer_ready?\n'
                   '            "Cannot apply graphics profile. Check SD space and fex-runtime.log.":fx_renderer_error_text);\n'
                   '        fx_ui_view.message=fx_ui_message;')
    source = exact(source, 'failed=fx_ui_view.screen==FX_FAILED;',
                   'failed=fx_ui_view.screen==FX_FAILED||fx_ui_view.fatal;')
    source = exact(source, 'if(fx_ui_view.screen==FX_LOADING){snprintf(fx_ui_message',
                   'if(fx_ui_view.screen==FX_LOADING&&!fx_ui_view.fatal){snprintf(fx_ui_message')
    source = exact(source, 'if(fx_ui_view.screen==FX_LOADING&&started&&armTicksToNs',
                   'if(fx_ui_view.screen==FX_LOADING&&!fx_ui_view.fatal&&started&&armTicksToNs')
    source = exact(source, 'static void fx_exit_check(void) {', r'''void wine_nx_runtime_startup_dialog(const char *title,const char *body) {
    if(!__atomic_load_n(&fx_boot_started,__ATOMIC_ACQUIRE)||
       __atomic_load_n(&fx_first_present,__ATOMIC_ACQUIRE))return;
    log_line("[F1-DIALOG] title=%s",title);
    log_line("[F1-DIALOG] text=%s",body);
    if(!strcmp(title,"Cannot initialise graphics"))
        fx_fail("F1: Cannot initialise graphics. See fex-runtime.log and F1_2013_dxgi.log.");
}
static void fx_exit_check(void) {''')
    return source


def patch_window_dialog(source: str) -> str:
    source = exact(source, '        NtUserGetClassName( hwnd, FALSE, &cls );\n',
                   '        NtUserGetClassName( hwnd, FALSE, &cls );\n'
                   '        if(cmd != SW_HIDE && !wcscmp(class_name,f1_dialog_class))\n'
                   '            f1_report_startup_dialog(hwnd,title);\n')
    return exact(source, 'static BOOL show_window( HWND hwnd, INT cmd )',
                 (TOOL_DIR / 'f1_window_dialog.inc').read_text() + '\nstatic BOOL show_window( HWND hwnd, INT cmd )')


def patch_startup_monitor(source: str) -> str:
    source = exact(source, 'unsigned frame,splash_ms;', 'unsigned frame,splash_ms,debug_seconds;')
    source = exact(source, '        u64 render_start=armGetSystemTick();',
        '        if(started)fx_ui_view.debug_seconds=(unsigned)(armTicksToNs(frame_start-started)/1000000000ull);\n'
        '        u64 render_start=armGetSystemTick();')
    source = exact(source, 'static int fx_debug_live;',
        '#include "f1_startup_watch.h"\nstatic int fx_debug_live;\n'
        'static pthread_mutex_t fx_debug_file_lock=PTHREAD_MUTEX_INITIALIZER;')
    # Display snapshots must not wait for an SD flush. File writes still have
    # their own serialization; no UI/debug-ring mutex is held during SD I/O.
    source = exact(source,
        '    if (fx_debug_file) { fprintf(fx_debug_file,"%s\\n",line);fflush(fx_debug_file); }\n'
        '    pthread_mutex_unlock(&fx_debug_lock);',
        '    pthread_mutex_unlock(&fx_debug_lock);\n'
        '    pthread_mutex_lock(&fx_debug_file_lock);\n'
        '    if (fx_debug_file) { fprintf(fx_debug_file,"%s\\n",line);fflush(fx_debug_file); }\n'
        '    pthread_mutex_unlock(&fx_debug_file_lock);')
    source = exact(source,
        '        pthread_mutex_lock(&fx_debug_lock);\n'
        '        if(fx_debug_file){fclose(fx_debug_file);fx_debug_file=NULL;}\n'
        '        pthread_mutex_unlock(&fx_debug_lock);',
        '        __atomic_store_n(&f1_startup_watch_enabled,0,__ATOMIC_RELEASE);\n'
        '        pthread_mutex_lock(&fx_debug_file_lock);\n'
        '        if(fx_debug_file){fclose(fx_debug_file);fx_debug_file=NULL;}\n'
        '        pthread_mutex_unlock(&fx_debug_file_lock);')
    source = exact(source, '__atomic_store_n(&fx_debug_live,1,__ATOMIC_RELEASE);',
        '__atomic_store_n(&f1_startup_watch_enabled,1,__ATOMIC_RELEASE);\n'
        '                        __atomic_store_n(&fx_debug_live,1,__ATOMIC_RELEASE);')
    source = exact(source, 'static void *log_flusher( void *arg )\n{',
        (TOOL_DIR / 'f1_startup_monitor.inc').read_text() + '\nstatic void *log_flusher( void *arg )\n{')
    source = exact(source, '    pthread_detach(maintenance);',
        '    pthread_detach(maintenance);\n'
        '    pthread_t startup_monitor;\n'
        '    if (pthread_create(&startup_monitor,NULL,f1_startup_monitor,NULL)) {\n'
        '        fx_native_error("Unable to start startup monitor. Close and relaunch.");\n'
        '        return 1;\n'
        '    }\n'
        '    pthread_detach(startup_monitor);')
    source = exact(source,
        'log_line("[FEX3-HANG] v2 capture after 3s no presents; includes idle workers, max 3 captures");',
        'log_line("[F1-WATCH] heartbeat=5s; startup snapshots=30/45/60s; latest syscall/file boundaries and saved guest PCs; active status=ffffffff means no return yet");')
    return source


def patch_syscall_watch(source: str) -> str:
    source = exact(source, 'NTSTATUS wine_nx_do_syscall( ULONG_PTR *stack_args,', r'''#define F1_STARTUP_WATCH_IMPLEMENTATION
#include "f1_startup_watch.h"
#include "../ntsyscalls.h"
_Static_assert(offsetof(I386_CONTEXT,Eip)==0xb8, "startup saved EIP offset");
_Static_assert(offsetof(I386_CONTEXT,Esp)==0xc4, "startup saved ESP offset");
_Static_assert(offsetof(I386_CONTEXT,Ebp)==0xb4, "startup saved EBP offset");
_Static_assert(offsetof(TEB,TlsSlots)+WOW64_TLS_CPURESERVED*sizeof(void *)==0x1488,
               "startup TEB CPU area offset");
const char *f1_watch_syscall_name(unsigned id)
{
    switch (id) {
#define SYSCALL_ENTRY(number, name, args) case number: return #name;
        ALL_SYSCALLS
#undef SYSCALL_ENTRY
    default: return "win32u/unknown";
    }
}

NTSTATUS wine_nx_do_syscall( ULONG_PTR *stack_args,''')
    source = exact(source,
        '    arg_bytes = table->ArgumentTable ? table->ArgumentTable[func_idx] : 0;',
        '    arg_bytes = table->ArgumentTable ? table->ArgumentTable[func_idx] : 0;\n'
        '    uint64_t watch_serial = 0;\n'
        '    uint32_t watch_tid = 0;\n'
        '    if ((void *)handler != (void *)NtReadVirtualMemory &&\n'
        '        __atomic_load_n(&f1_startup_watch_enabled,__ATOMIC_RELAXED)) {\n'
        '        uint64_t args[8] = {x0,x1,x2,x3,x4,x5,x6,x7};\n'
        '        watch_tid = HandleToULong(NtCurrentTeb()->ClientId.UniqueThread);\n'
        '        watch_serial = f1_watch_begin(watch_tid,syscall_id,args,armGetSystemTick());\n'
        '    }')
    source = exact(source,
        '    if (trace_syscall)\n    {\n        char buf[128];\n'
        '        snprintf( buf, sizeof(buf), "[SYSCALL] id=0x%04x done status=0x%08x tid=%04x",',
        '    if (watch_serial) f1_watch_end(watch_tid,watch_serial,result,armGetSystemTick());\n'
        '    if (trace_syscall)\n    {\n        char buf[128];\n'
        '        snprintf( buf, sizeof(buf), "[SYSCALL] id=0x%04x done status=0x%08x tid=%04x",')
    return source


def patch_file_watch(source: str) -> str:
    source = exact(source, '#include "config.h"', '#include "config.h"\n#include "f1_startup_watch.h"')
    # Keep every early return/status of the original functions intact.
    for name, signature, arguments, begin, finish in (
        ('open_unix_file', 'NTSTATUS open_unix_file( HANDLE *handle,',
         'handle,unix_name,access,attr,attributes,sharing,disposition,options,ea_buffer,ea_length',
         'f1_watch_file_begin(tid,unix_name,0,0,armGetSystemTick())',
         '!status ? (uintptr_t)*handle : 0'),
        ('NtReadFile', 'NTSTATUS WINAPI NtReadFile( HANDLE handle,',
         'handle,event,apc,apc_user,io,buffer,length,offset,key',
         'f1_watch_file_begin(tid,NULL,(uintptr_t)handle,length,armGetSystemTick())',
         '(uintptr_t)handle')):
        start = source.index(signature)
        brace = source.index('{', start)
        declaration = source[start:brace].rstrip()
        changed = replace_function(source, signature, 'F1_FUNCTION_PLACEHOLDER')
        old_end = len(source) - (len(changed)-len('F1_FUNCTION_PLACEHOLDER')) + start
        original = source[start:old_end]
        impl = original.replace(name+'(', 'f1_original_'+name+'(', 1)
        wrapper = declaration + '''
{
    uint32_t tid = HandleToULong(NtCurrentTeb()->ClientId.UniqueThread);
    uint64_t serial = ''' + begin + ''';
    NTSTATUS status = f1_original_''' + name + '(' + arguments + ''');
    if (serial) f1_watch_file_end(tid,serial,''' + finish + ''',status,armGetSystemTick());
    return status;
}'''
        source = changed.replace('F1_FUNCTION_PLACEHOLDER', 'static '+impl+'\n\n'+wrapper)
    return source


def patch_startup_diagnostics(source: str) -> str:
    # The production PES snapshot turns off *both* the PE channel table and
    # the Unix output bridge. Enabling WINEDEBUG alone does not restore them.
    source = exact(source, '        options[0].flags = 0;',
                   '        fx_wine_debug_channels(options, fx_ui_view.debug);')
    source = exact(source, 'static void std_stream_log( void *ctx, const char *line )',
        'static unsigned f1_resource_abort;\n\nstatic void std_stream_log( void *ctx, const char *line )')
    source = exact(source, '    if (stream->lines.lines < STD_STREAM_LOG_LINES)',
        '    if (stream == &std_streams[1] && strstr(line,"Resource temporarily unavailable"))\n'
        '        __atomic_store_n(&f1_resource_abort,1,__ATOMIC_RELEASE);\n'
        '    if (stream->lines.lines < STD_STREAM_LOG_LINES)')
    source = exact(source, 'int main( int argc, char **argv )', r'''/* The PE ntdlls read this sorted table from the page after the WoW64 PEB.
 * Do not call Unix dbg_init(): launcher/maintenance threads have no Wine TEB. */
static void fx_wine_debug_channels(struct __wine_debug_channel *options, int debug)
{
    const unsigned char errors = 1 << __WINE_DBCL_ERR;
    memset(options, 0, 5 * sizeof(*options));
    if (debug)
    {
        strcpy(options[0].name, "crypt");
        options[0].flags = errors | (1 << __WINE_DBCL_WARN) | (1 << __WINE_DBCL_TRACE);
        strcpy(options[1].name, "loaddll");
        options[1].flags = errors | (1 << __WINE_DBCL_TRACE);
        strcpy(options[2].name, "module");
        options[2].flags = errors | (1 << __WINE_DBCL_WARN) | (1 << __WINE_DBCL_TRACE);
        strcpy(options[3].name, "seh");
        options[3].flags = errors | (1 << __WINE_DBCL_WARN);
        options[4].flags = errors;
    }
    else options[0].flags = errors;
}

/* The native termination path parks after a guest exits. Notify the GUI
 * immediately, while retaining the black trace screen in Debug mode. */
void wine_nx_runtime_process_exit(unsigned int code)
{
    char message[160];
    if (code == 0xc0000142u)
        snprintf(message, sizeof(message), "DLL initialization failed (0xc0000142). See fex-runtime.log.");
    else if (code == 0xc0000135u)
        snprintf(message, sizeof(message), "A required DLL was not found (0xc0000135). See fex-runtime.log.");
    else if (code == 3 && __atomic_load_n(&f1_resource_abort,__ATOMIC_ACQUIRE))
        snprintf(message, sizeof(message), "Game aborted: startup resources unavailable. See fex-runtime.log.");
    else
        snprintf(message, sizeof(message), "Game stopped (0x%08x). See fex-runtime.log and crash.log.", code);
    fx_fail(message);
}

int main( int argc, char **argv )''')
    source = replace_function(source,
        'void wine_nx_runtime_std_write( int stream, const char *data, size_t size )', r'''void wine_nx_runtime_std_write( int stream, const char *data, size_t size )
{
    if (!__atomic_load_n(&fx_debug_live,__ATOMIC_ACQUIRE) || !data || !size) return;
    if (stream < 1 || stream > 2) return;
    pthread_mutex_lock(&std_stream_mutex);
    std_stream_lines_feed(&std_streams[stream-1].lines, data, size,
                          std_stream_log, &std_streams[stream-1]);
    pthread_mutex_unlock(&std_stream_mutex);
}''')
    source = exact(source, 'static void runtime_tick_std_streams(void)\n{', r'''static struct std_stream_lines wine_debug_lines;

static void fx_wine_debug_line(void *context, const char *line)
{
    (void)context;
    log_line("[WINE] %s", line);
}

/* Receives both ARM64 and x86 PE Wine diagnostics through the Unix call gate.
 * Keep partial and long writes intact; logging never changes the guest status. */
void wine_nx_runtime_wine_write(const char *data, unsigned int size)
{
    if (!__atomic_load_n(&fx_debug_live,__ATOMIC_ACQUIRE) || !data || !size) return;
    pthread_mutex_lock(&std_stream_mutex);
    std_stream_lines_feed(&wine_debug_lines, data, size, fx_wine_debug_line, NULL);
    pthread_mutex_unlock(&std_stream_mutex);
}

static void runtime_tick_std_streams(void)
{''')
    source = exact(source,
        '        std_stream_lines_tick( &std_streams[i].lines, STD_STREAM_IDLE_TICKS, std_stream_log, &std_streams[i] );',
        '        std_stream_lines_tick( &std_streams[i].lines, STD_STREAM_IDLE_TICKS, std_stream_log, &std_streams[i] );\n'
        '    std_stream_lines_tick(&wine_debug_lines, STD_STREAM_IDLE_TICKS, fx_wine_debug_line, NULL);')
    source = replace_function(source, 'void wine_nx_runtime_dump_std_streams(void)', r'''void wine_nx_runtime_dump_std_streams(void)
{
    pthread_mutex_lock(&std_stream_mutex);
    for (unsigned int i=0; i<sizeof(std_streams)/sizeof(std_streams[0]); i++)
        std_stream_lines_emit(&std_streams[i].lines, std_stream_log, &std_streams[i]);
    std_stream_lines_emit(&wine_debug_lines, fx_wine_debug_line, NULL);
    pthread_mutex_unlock(&std_stream_mutex);
}''')
    source = exact(source, '    runtime_alternate_clean();\n}',
        '    runtime_alternate_clean();\n'
        '    if (__atomic_load_n(&fx_debug_live,__ATOMIC_ACQUIRE)) runtime_tick_std_streams();\n}')
    # The installed null device still provides guest handles, but NtWriteFile
    # already forwards their bytes to wine_nx_runtime_std_write above.
    return source


def patch_wine_debug(source: str) -> str:
    return replace_function(source,
        'static int wine_nx_dbg_write( const char *str, unsigned int str_len )', r'''static int wine_nx_dbg_write( const char *str, unsigned int str_len )
{
    extern void wine_nx_runtime_wine_write(const char *, unsigned int);
    wine_nx_runtime_wine_write(str, str_len);
    return str_len;
}''')


def patch_process_exit(source: str) -> str:
    return exact(source,
        '        for (;;) usleep( 1000 * 1000 );',
        '        extern void wine_nx_runtime_process_exit(unsigned int);\n'
        '        wine_nx_runtime_process_exit((unsigned int)exit_code);\n'
        '        for (;;) usleep( 1000 * 1000 );')


def patch_preload(source: str, expected_size: int) -> str:
    if expected_size != IMAGE_SIZE:
        raise ValueError(f"Unexpected F1 PE image size: {expected_size:#x}")
    return exact(source, "#define PES_IMAGE_SIZE ((size_t)0x0189a000)",
                 f"#define PES_IMAGE_SIZE ((size_t)0x{IMAGE_SIZE:08x})")


def patch_graphics(source: str) -> str:
    return replace_function(source,
        "static const char *pes13_graphics_environment(const char *target, size_t *bytes)",
        "static const char *pes13_graphics_environment(const char *target, size_t *bytes)\n"
        "{\n    (void)target;\n    *bytes = sizeof(runtime_environment);\n"
        "    return runtime_environment;\n}")


def patch_crypto_registry(source: str) -> str:
    source = exact(source, '#include "pes13_registry.h"',
                   '#include "pes13_registry.h"\n#include "f1_crypto_registry.h"')
    return exact(source, '    horizon_registry_hives[0] = machine;', r'''    {
        unsigned int views, status = f1_crypto_registry_install(&horizon_registry, machine, &views);
        char line[192];
        snprintf(line, sizeof(line), "[F1-CRYPTO] rsaenh provider registry views=%u status=%08x", views, status);
        wine_nx_runtime_trace(line);
        if (status)
        {
            horizon_reg_release(&horizon_registry, horizon_registry.root);
            horizon_registry.root = NULL;
            return status;
        }
    }
    horizon_registry_hives[0] = machine;''')


def patch_apc_server(source: str) -> str:
    source = exact(source, 'struct horizon_server_object;\n',
                   '#include "f1_apc_queue.h"\n\nstruct horizon_server_object;\n')
    source = exact(source, '    struct horizon_thread_state thread;\n',
                   '    struct horizon_thread_state thread;\n    struct f1_apc_queue f1_apcs;\n')
    source = exact(source, '    horizon_completion_clear( &object->completion );',
                   '    f1_apc_clear(&object->f1_apcs);\n    horizon_completion_clear( &object->completion );')
    source = exact(source, '    connection->thread = NULL;\n',
                   '    connection->thread = NULL;\n    f1_apc_clear(&thread->f1_apcs);\n')
    marker = 'static int horizon_server_handle_select( struct horizon_server_connection *connection,'
    source = exact(source, marker, (TOOL_DIR / 'f1_apc_server.inc').read_text() + '\n' + marker)
    source = exact(source, '    struct horizon_select_reply reply;\n',
                   '    struct horizon_select_reply reply;\n    union apc_call f1_call;\n')
    source = exact(source,
        '        reply.header.error = horizon_server_select_status( request, data, data_size, initial );',
        '''        reply.header.error = horizon_server_select_status( request, data, data_size, initial );
        if (f1_server_select_apc(connection, request, reply.header.error, &f1_call)) {
            reply.header.error = STATUS_USER_APC;
            reply.header.reply_size = sizeof(f1_call);
            break;
        }''')
    source = exact(source,
        '''           request->size, request->timeout, reply.header.error );
    return horizon_server_write_reply( connection->reply_fd, &reply, sizeof(reply), NULL, 0 );''',
        '''           request->size, request->timeout, reply.header.error );
    return horizon_server_write_reply( connection->reply_fd, &reply, sizeof(reply),
                                      reply.header.reply_size ? &f1_call : NULL, reply.header.reply_size );''')
    return exact(source, '        case HORIZON_REQ_SELECT:\n',
        '''        case REQ_queue_apc:
            status = f1_server_queue_apc(connection, message, request_data, header->request_size);
            break;
        case HORIZON_REQ_SELECT:
''')


def patch_apc_dispatch(source: str) -> str:
    # Only replace the Switch stub. The ordinary Linux implementation below
    # the #else still owns its syscall_frame and must remain untouched.
    stub = '''    (void)context;
    (void)flags;
    (void)arg1;
    (void)arg2;
    (void)arg3;
    (void)func;
    (void)status;
    return STATUS_NOT_IMPLEMENTED;'''
    start = source.index('NTSTATUS call_user_apc_dispatcher(')
    end = source.index('\n}', start) + 2
    if stub not in source[start:end]:
        raise ValueError('Horizon APC dispatcher stub changed')
    return source[:start] + (TOOL_DIR / 'f1_apc_dispatch.inc').read_text() + source[end:]


def patch_read_apc_status(source: str) -> str:
    start = source.index('NTSTATUS WINAPI NtReadFile(')
    end = source.index('\n}', start) + 2
    code = exact(source[start:end],
        '''        if (apc && (!status || async_read)) NtQueueApcThread( GetCurrentThread(), (PNTAPCFUNC)apc,
                                                              (ULONG_PTR)apc_user, iosb_ptr, 0 );''',
        '''        if (apc && (!status || async_read))
        {
            NTSTATUS queued = NtQueueApcThread( GetCurrentThread(), (PNTAPCFUNC)apc,
                                               (ULONG_PTR)apc_user, iosb_ptr, 0 );
            /* A pending ReadFileEx must have a scheduled completion. If the
             * queue fails, surface the error instead of waiting forever. */
            if (queued)
            {
                set_sync_iosb( io, queued, 0, options );
                return queued;
            }
        }''')
    return source[:start] + code + source[end:]


THREAD_FAILURE_DECL = '''extern void wine_nx_f1_thread_failure(const char *, unsigned,
                                            unsigned long, unsigned long, int);
extern void wine_nx_f1_game_thread_result(unsigned, uintptr_t);
'''


def patch_thread_failures(source: str) -> str:
    start = source.index('NTSTATUS WINAPI NtCreateThreadEx(')
    end = source.index('\n}', start) + 2
    original = source[start:end]
    signature = original[:original.index('{')]
    original = original.replace('NTSTATUS WINAPI NtCreateThreadEx(',
                                'static NTSTATUS WINAPI f1_create_thread_original(', 1)
    # The base horizon_trace is a no-op, including these early failures that
    # previously disappeared before the successful pthread log statement.
    original = exact(original,
        '        horizon_trace( "[THREAD] virtual_alloc_teb failed status=%08x\\n", status );',
        '        wine_nx_f1_thread_failure("wine-teb", status, stack_reserve, stack_commit, errno);')
    original = exact(original,
        '''        horizon_trace( "[THREAD] init_thread_stack failed status=%08x reserve=%lx commit=%lx\\n",
                       status, (unsigned long)stack_reserve, (unsigned long)stack_commit );''',
        '        wine_nx_f1_thread_failure("wine-stack", status, stack_reserve, stack_commit, errno);')
    wrapper = signature + '''{
    NTSTATUS status = f1_create_thread_original(handle, access, attr, process, start, param,
                                               flags, zero_bits, stack_commit, stack_reserve, attr_list);
    if (status) wine_nx_f1_thread_failure("NtCreateThreadEx", status, stack_reserve, stack_commit, errno);
    wine_nx_f1_game_thread_result(status, (uintptr_t)start);
    return status;
}'''
    return source[:start] + THREAD_FAILURE_DECL + original + '\n\n' + wrapper + source[end:]


def patch_thread_server(source: str) -> str:
    start = source.index('static int horizon_server_handle_new_thread(')
    end = source.index('\n}', start) + 2
    code = source[start:end]
    code = exact(code,
        '        horizon_trace( "[server] new_thread tid=%u: connection thread failed errno=%d",\n'
        '                       thread_connection->tid, errno );',
        '        wine_nx_f1_thread_failure("wine-server-pthread", HORIZON_STATUS_NO_MEMORY, 0, 0, errno);')
    return source[:start] + THREAD_FAILURE_DECL + code + source[end:]


def patch_destroy_window(source: str) -> str:
    signature = 'static int horizon_server_handle_destroy_window('
    start = source.index(signature)
    end = source.index('\n}', start) + 2
    body = source[start:end]
    body = exact(body,
        '    for (ptr = &horizon_windows; *ptr; ptr = &(*ptr)->next)',
        '    /* A null handle means this connection\'s thread windows. Keep the\n'
        '     * link at the successor after unlinking; advancing then skips a\n'
        '     * window and dereferences NULL when the removed node was last. */\n'
        '    for (ptr = &horizon_windows; *ptr;)')
    body = exact(body,
        '        if (request->handle && window->handle != request->handle) continue;',
        '        if (request->handle ? window->handle != request->handle :\n'
        '            (window->pid != connection->pid || window->tid != connection->tid))\n'
        '        {\n'
        '            ptr = &window->next;\n'
        '            continue;\n'
        '        }')
    return source[:start] + body + source[end:]


def apply(source_root: Path, image_size: int) -> list[Path]:
    from f1_crash_overlay import patch_runtime_crash, patch_native_exception, patch_vulkan, patch_surface, patch_thread_detach
    runtime = source_root / "wine-nx-probe/source/runtime.c"
    preload = source_root / "wine-nx-probe/source/pes13_preload.c"
    graphics = source_root / "wine-nx-probe/source/pes13_graphics.h"
    updated = {runtime: patch_runtime_crash(patch_runtime(runtime.read_text())),
               preload: patch_preload(preload.read_text(), image_size),
               graphics: patch_graphics(graphics.read_text())}
    window = source_root / 'dlls/win32u/window.c'
    updated[window] = patch_window_dialog(window.read_text())
    for name, patch in (('debug.c', patch_wine_debug), ('process.c', patch_process_exit),
                        ('horizon_registry_server.h', patch_crypto_registry),
                        ('horizon.c', lambda s: patch_destroy_window(patch_native_exception(patch_thread_server(patch_apc_server(s))))),
                        ('thread.c', patch_thread_failures),
                        ('signal_arm64.c', lambda s: patch_syscall_watch(patch_apc_dispatch(s))),
                        ('file.c', lambda s: patch_file_watch(patch_read_apc_status(s)))):
        path = source_root / 'dlls/ntdll/unix' / name
        updated[path] = patch(path.read_text())
    for name, patch in (('vulkan.c', patch_vulkan), ('winnx_vulkan.c', patch_surface),
                        ('sysparams.c', patch_thread_detach)):
        path = source_root / 'dlls/win32u' / name
        updated[path] = patch(path.read_text())
    for path, data in updated.items():
        path.write_text(data)
    settings = source_root / "wine-nx-probe/source/f1_settings.h"
    settings.write_bytes((TOOL_DIR / "f1_settings.h").read_bytes())
    crypto = source_root / "dlls/ntdll/unix/f1_crypto_registry.h"
    crypto.write_bytes((TOOL_DIR / "f1_crypto_registry.h").read_bytes())
    apc_queue = source_root / 'dlls/ntdll/unix/f1_apc_queue.h'
    apc_queue.write_bytes((TOOL_DIR / 'f1_apc_queue.h').read_bytes())
    watch = source_root / "dlls/ntdll/unix/f1_startup_watch.h"
    watch.write_bytes((TOOL_DIR / "f1_startup_watch.h").read_bytes())
    runtime_watch = source_root / "wine-nx-probe/source/f1_startup_watch.h"
    runtime_watch.write_bytes(watch.read_bytes())
    profile = source_root / "wine-nx-probe/source/thread_profile.c"
    profile.write_text(profile.read_text() + '\n' + (TOOL_DIR / 'f1_thread_snapshot.inc').read_text())
    diagnostics = source_root / 'wine-nx-probe/source/f1_thread_diagnostics.c'
    diagnostics.write_bytes((TOOL_DIR / 'f1_thread_diagnostics.c').read_bytes())
    budget = source_root / 'wine-nx-probe/source/f1_thread_budget.c'
    budget.write_bytes((TOOL_DIR / 'f1_thread_budget.c').read_bytes())
    crash = source_root / 'wine-nx-probe/source/f1_crash.c'
    crash.write_bytes((TOOL_DIR / 'f1_crash.c').read_bytes())
    cmake = source_root / 'wine-nx-probe/CMakeLists.txt'
    cmake.write_text(cmake.read_text() + '\n'
        'target_sources(wine-nx-runtime PRIVATE source/f1_thread_diagnostics.c source/f1_thread_budget.c source/f1_crash.c)\n'
        'target_link_options(wine-nx-runtime PRIVATE -Wl,--wrap=threadCreate -Wl,--wrap=pthread_create -Wl,--wrap=abort -Wl,--wrap=diagAbortWithResult -Wl,--wrap=svcBreak -Wl,--wrap=exit -Wl,--wrap=_exit)\n')
    # Drive mapping, DLL search, NLS, registry and session storage are owned by
    # other translation units too.  Port the complete copied source tree so
    # C: and the guest environment cannot borrow the installed PES prefix.
    changed = [*updated, settings, crypto, apc_queue, watch, runtime_watch, profile, diagnostics, budget, crash, cmake]
    for path in source_root.rglob("*"):
        if not path.is_file() or path.suffix not in (".c", ".h", ".in", ".txt"):
            continue
        data = path.read_text(errors="surrogateescape")
        if "switch/pes13-fex" in data:
            path.write_text(data.replace("switch/pes13-fex", "switch/f1-fex"),
                            errors="surrogateescape")
            if path not in changed:
                changed.append(path)
    return changed
