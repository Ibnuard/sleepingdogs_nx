"""Execute and render the actual H4 Game detail UI with the real disk helper.

Run in the prepared WSL build environment. This uses throwaway XML/preferences,
never an installed game's settings. Screenshots use the approved launcher font
and art plus the already prepared Sleeping Dogs preview pixels.
"""
from pathlib import Path
import hashlib
import json
import os
import shlex
import shutil
import struct
import subprocess
import tempfile
import zlib

from build_native_dxvk_h4 import BUILD, LOCAL, PIN, ROOT, SOURCES, WORK, overlay_runtime, overlay_settings
from port_common import BASE


PREAMBLE = r'''
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <stdarg.h>
#include <string.h>
#include <pthread.h>
static int sync_countdown=-1;
static unsigned sync_failures;
static int corrupt_mode_after_commit;
static unsigned corruptions_injected;
static unsigned quality_init_errors,quality_launch_errors,quality_apply_logs;
static char last_log[1024];
static int ui_fsync(int fd){
    if(sync_countdown==0){sync_countdown=-1;sync_failures++;errno=EIO;return -1;}
    if(sync_countdown>0)--sync_countdown;
    return fsync(fd);
}
static int horizon_rename(const char *from,const char *to){
    if(!access(to,F_OK)){errno=EEXIST;return -1;}
    return rename(from,to);
}
static int ui_unlink(const char *path){
    int result=unlink(path);
    static const char suffix[]="/launcher/game-quality.txt.sdq-done";
    size_t length=strlen(path),suffix_length=sizeof(suffix)-1;
    if(!result&&corrupt_mode_after_commit&&length>=suffix_length&&!strcmp(path+length-suffix_length,suffix)){
        /* Simulate preference corruption between acknowledged save and UI
         * reload; do not replace the helper or settings functions with mocks. */
        char mode[768];size_t n=length-strlen(".sdq-done");assert(n<sizeof(mode));
        memcpy(mode,path,n);mode[n]=0;
        FILE *file=fopen(mode,"wb");assert(file);assert(fwrite("x\n",1,2,file)==2);assert(!fclose(file));
        corrupt_mode_after_commit=0;corruptions_injected++;
    }
    return result;
}
#define SDGQ_FSYNC ui_fsync
#define SDGQ_UNLINK ui_unlink
#define rename horizon_rename
static void log_line(const char *fmt,...){
    va_list ap;va_start(ap,fmt);vsnprintf(last_log,sizeof(last_log),fmt,ap);va_end(ap);
    if(strstr(last_log,"[SD-QUALITY] settings read failed:"))quality_init_errors++;
    if(strstr(last_log,"[SD-QUALITY] launch stopped:"))quality_launch_errors++;
    if(strstr(last_log,"[SD-GAME-QUALITY] mode="))quality_apply_logs++;
    fprintf(stderr,"%s\n",last_log);
}
static pthread_mutex_t fx_debug_lock=PTHREAD_MUTEX_INITIALIZER;
static char fx_debug_lines[21][120];
static unsigned fx_debug_total;
'''

HARNESS = r'''
static const char original_xml[]=
    "<?xml version=\"1.0\" encoding=\"ascii\"?>\r\n"
    "<DisplaySettings>\r\n<!-- fixture only; keep other preferences -->\r\n"
    "<Version>1</Version><AdapterUID>2468</AdapterUID><MonitorUID>1357</MonitorUID>\r\n"
    "<ResolutionWidth>1280</ResolutionWidth><ResolutionHeight>720</ResolutionHeight>\r\n"
    "<RefreshRateNumerator>60000</RefreshRateNumerator><RefreshRateDenominator>1001</RefreshRateDenominator>\r\n"
    "<ScalingMode>unspecified</ScalingMode><ScanlineMode>progressive</ScanlineMode>\r\n"
    "<Fullscreen>1</Fullscreen><Stereo3D>0</Stereo3D><StereoEyeDistance>0.030000</StereoEyeDistance>\r\n"
    "<VSync>1</VSync><AAQuality>2</AAQuality><HighResTextures>1</HighResTextures>\r\n"
    "<ShadowRes>2</ShadowRes><ShadowFilter>1</ShadowFilter><MotionBlur>2</MotionBlur><SSAO>1</SSAO>\r\n"
    "<FPSLimiter>0</FPSLimiter><Option3DDepth>1</Option3DDepth><Option3DConvergence>10</Option3DConvergence>\r\n"
    "<WorldDensity>2</WorldDensity><GlobalSetting>-1</GlobalSetting>\r\n</DisplaySettings>\r\n";

static void same_bytes(const char *path,const char *expected,size_t n){
    char buffer[8192];assert(n<sizeof(buffer));
    assert(fx_read(path,buffer,sizeof(buffer))==n);assert(!memcmp(buffer,expected,n));
}
static void quality_choose(struct fx_view *view,const char *root,int row){
    view->screen=FX_SETTINGS;view->message=NULL;
    fx_settings_enter(view,FX_SETTINGS_GAME_QUALITY,row);
    assert(fx_settings_choose(view,root));
}
static void choice_is(struct fx_view *view,const char *root,int mode){
    assert(fx_game_quality==mode&&sd_game_quality_load(root)==mode);
    assert(fx_settings_selected(view,mode));
    assert(!fx_settings_selected(view,1-mode));
    assert(!fx_settings_selected(view,2)); /* Restore is an action, never a mode. */
}
static void save_image(struct fx_canvas *canvas,const char *folder,const char *name){
    char path[1024];snprintf(path,sizeof(path),"%s/%s.ppm",folder,name);
    FILE *file=fopen(path,"wb");assert(file);fprintf(file,"P6\n1280 720\n255\n");
    for(int y=0;y<FX_H;y++){
        for(int x=0;x<FX_W;x++){
            uint32_t pixel=canvas->pixels[y*canvas->stride+x];
            unsigned char rgb[]={pixel,pixel>>8,pixel>>16};assert(fwrite(rgb,1,3,file)==3);
        }
        for(int x=FX_W;x<canvas->stride;x++)assert(!canvas->pixels[y*canvas->stride+x]);
    }
    assert(!fclose(file));
}
/* Check actual nontransparent glyph bounds, including bearings/overhangs. */
static void text_inside(const struct fx_art *art,const char *text,int font,
                        int x,int y,int left,int top,int right,int bottom){
    static const int heights[4]={20,26,40,14};
    for(;*text;text++){
        unsigned index=(unsigned char)*text;assert(index>=32&&index<=126);
        const unsigned char *g=art->font+8+(font*95+index-32)*16;
        int bx=(int16_t)(g[4]|g[5]<<8),by=(int16_t)(g[6]|g[7]<<8);
        int w=g[8]|g[9]<<8,h=g[10]|g[11]<<8;
        const unsigned char *mask=art->font+6088+fx_u32(g);
        for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++)if(mask[yy*w+xx]){
            int px=x+bx+xx,py=y+heights[font]+by+yy;
            assert(px>=left&&px<right&&py>=top&&py<bottom);
        }
        x+=g[12]|g[13]<<8;
    }
}
int main(int argc,char **argv){
    assert(argc==3);const char *root=argv[1];
    char xml[768],backup[800],hidden[810],save[768],mode_path[768],buffer[8192];
    snprintf(xml,sizeof(xml),"%s/drive_c/SleepingDogs/Data/DisplaySettings.xml",root);
    snprintf(backup,sizeof(backup),"%s.fextendo-original",xml);
    snprintf(hidden,sizeof(hidden),"%s.hidden",backup);
    snprintf(save,sizeof(save),"%s/drive_c/SleepingDogs/Data/UserOptions.dat",root);
    snprintf(mode_path,sizeof(mode_path),"%s/launcher/game-quality.txt",root);
    assert(fx_write(xml,original_xml,sizeof(original_xml)-1));
    assert(fx_write(save,"untouched user options",22));
    /* Execute the actual startup and prelaunch fragments from overlay_runtime,
     * preserving the original ready gate and load/apply short circuit. */
    assert(fx_write(mode_path,"2\n",2));fx_game_quality=1;
    actual_quality_init(root);
    assert(fx_game_quality==0&&sd_game_quality_error&&quality_init_errors==1);
    assert(strstr(last_log,"invalid game-quality.txt; using Game settings"));
    const char *launch_error=NULL;unsigned applied_before=quality_apply_logs;
    assert(!actual_quality_prelaunch(root,1,&launch_error));
    assert(launch_error&&!strcmp(launch_error,"invalid game-quality.txt; using Game settings"));
    assert(quality_launch_errors==1&&quality_apply_logs==applied_before);
    same_bytes(xml,original_xml,sizeof(original_xml)-1);same_bytes(mode_path,"2\n",2);
    launch_error=NULL;assert(!actual_quality_prelaunch(root,0,&launch_error));
    assert(!launch_error&&quality_launch_errors==1&&quality_apply_logs==applied_before);
    assert(sd_game_quality_save(root,0));actual_quality_init(root);
    assert(fx_game_quality==0&&!sd_game_quality_error&&quality_init_errors==1);
    assert(actual_quality_prelaunch(root,1,&launch_error)&&!launch_error);
    assert(quality_apply_logs==applied_before+1);
    fx_game_quality=sd_game_quality_load(root);assert(!fx_game_quality);
    struct fx_view view={.screen=FX_SETTINGS,.settings_page=FX_SETTINGS_ROOT,.selected=2,
        .renderer=2,.sound=1,.music=1,.battery=100,.frame=32,.wall_time=1800000000};
    assert(FX_SETTINGS_PAGES==8&&fx_settings_rows(FX_SETTINGS_ROOT)==8);
    assert(fx_settings_rows(FX_SETTINGS_GAME_QUALITY)==3&&fx_settings_rows(FX_SETTINGS_RENDERER)==3);
    static const int pages[]={FX_SETTINGS_GRAPHICS,FX_SETTINGS_RENDERER,FX_SETTINGS_KEYBOARD,
        FX_SETTINGS_AUDIO,-1,FX_SETTINGS_DX_LOG,FX_SETTINGS_LSFG,FX_SETTINGS_GAME_QUALITY};
    for(int row=0;row<8;row++)if(row!=4){
        fx_settings_enter(&view,FX_SETTINGS_ROOT,row);assert(fx_settings_group(&view,row));
        assert(fx_settings_choose(&view,root));assert(view.settings_page==pages[row]);
        fx_settings_back(&view);assert(view.settings_page==FX_SETTINGS_ROOT&&view.row==row);
    }
    assert(!fx_settings_group(&view,4));
    assert(!strcmp(fx_settings_label(&view,7),"Game detail"));
    assert(!strcmp(fx_settings_detail(&view,7),"Use current in-game options"));
    fx_settings_enter(&view,FX_SETTINGS_ROOT,7);assert(view.settings_scroll==580.f);
    assert(fx_settings_choose(&view,root)&&view.row==0&&view.settings_scroll==0);
    assert(!strcmp(fx_settings_title(view.settings_page),"Game detail"));
    assert(!strcmp(fx_settings_label(&view,0),"Game settings"));
    assert(!strcmp(fx_settings_label(&view,1),"Light 720p"));
    assert(!strcmp(fx_settings_label(&view,2),"Restore original"));
    for(int row=0;row<3;row++){
        fx_settings_enter(&view,FX_SETTINGS_RENDERER,row);
        assert(fx_settings_choose(&view,root)&&view.renderer==row&&view.saved);
        assert(fx_renderer_selected(root)==row&&fx_settings_selected(&view,row));
    }
    assert(!strcmp(fx_settings_label(&view,2),"DXVK Native ARM64"));
    assert(!strcmp(fx_renderer_ids[2],"dxvk-native-h4"));
    quality_choose(&view,root,1);assert(view.screen==FX_SETTINGS&&view.saved);choice_is(&view,root,1);
    same_bytes(xml,original_xml,sizeof(original_xml)-1); /* Choice takes effect at launch. */
    fx_game_quality=0;fx_game_quality=sd_game_quality_load(root);choice_is(&view,root,1);
    fx_settings_back(&view);assert(view.row==7&&view.settings_scroll==580.f);
    assert(!strcmp(fx_settings_detail(&view,7),"Light 720p - next launch"));
    assert(fx_settings_choose(&view,root)&&view.row==1);
    assert(sd_game_quality_apply(root,sd_game_quality_load(root)));
    same_bytes(backup,original_xml,sizeof(original_xml)-1);
    size_t light_n=fx_read(xml,buffer,sizeof(buffer)-1);buffer[light_n]=0;assert(light_n);
    assert(strstr(buffer,"<ResolutionWidth>1280</ResolutionWidth><ResolutionHeight>720</ResolutionHeight>"));
    assert(strstr(buffer,"<WorldDensity>0</WorldDensity><GlobalSetting>0</GlobalSetting>"));
    assert(strstr(buffer,"<AdapterUID>2468</AdapterUID><MonitorUID>1357</MonitorUID>"));
    quality_choose(&view,root,0);assert(view.saved);choice_is(&view,root,0);
    same_bytes(xml,buffer,light_n); /* Game settings stops enforcement; does not restore. */
    quality_choose(&view,root,1);quality_choose(&view,root,2);
    assert(view.screen==FX_SETTINGS&&view.saved);choice_is(&view,root,0);
    same_bytes(xml,original_xml,sizeof(original_xml)-1);
    same_bytes(backup,original_xml,sizeof(original_xml)-1);

    /* Restore saves mode 0 before checking backup. UI must refresh stale mode 1
     * and retain the original error even though loading the mode clears it. */
    quality_choose(&view,root,1);assert(!rename(backup,hidden));
    quality_choose(&view,root,2);
    assert(view.screen==FX_FAILED&&!view.fatal&&!view.saved);
    assert(view.message&&!strcmp(view.message,"no readable original DisplaySettings backup"));
    choice_is(&view,root,0);same_bytes(xml,original_xml,sizeof(original_xml)-1);
    struct fx_view restore_failure=view;
    assert(!rename(hidden,backup));

    /* When disabling fails first, the persisted mode stays 1; the UI must not
     * falsely mark Game settings selected. Exercise save and restore paths. */
    quality_choose(&view,root,1);sync_countdown=0;quality_choose(&view,root,0);
    assert(view.screen==FX_FAILED&&!view.saved&&!view.fatal);
    assert(view.message&&strstr(view.message,"temporary settings"));choice_is(&view,root,1);
    sync_countdown=0;quality_choose(&view,root,2);
    assert(view.screen==FX_FAILED&&!view.saved&&!view.fatal);
    assert(view.message&&strstr(view.message,"temporary settings"));choice_is(&view,root,1);
    assert(sync_failures==2);
    quality_choose(&view,root,2);assert(view.screen==FX_SETTINGS&&view.saved);choice_is(&view,root,0);
    same_bytes(xml,original_xml,sizeof(original_xml)-1);same_bytes(save,"untouched user options",22);
    /* A successful operation is still a UI failure when its immediate mode
     * reload fails. This exercises both save and restore success paths. */
    corrupt_mode_after_commit=1;quality_choose(&view,root,1);
    assert(view.screen==FX_FAILED&&!view.saved&&!view.fatal);
    assert(view.message&&!strcmp(view.message,"invalid game-quality.txt; using Game settings"));
    assert(fx_game_quality==0&&sd_game_quality_load(root)==0&&sd_game_quality_error);
    same_bytes(xml,original_xml,sizeof(original_xml)-1);
    quality_choose(&view,root,1);assert(view.screen==FX_SETTINGS&&view.saved);choice_is(&view,root,1);
    corrupt_mode_after_commit=1;quality_choose(&view,root,2);
    assert(view.screen==FX_FAILED&&!view.saved&&!view.fatal);
    assert(view.message&&!strcmp(view.message,"invalid game-quality.txt; using Game settings"));
    assert(fx_game_quality==0&&sd_game_quality_load(root)==0&&sd_game_quality_error);
    assert(corruptions_injected==2);
    quality_choose(&view,root,0);assert(view.screen==FX_SETTINGS&&view.saved);choice_is(&view,root,0);
    view.row=-1;assert(!fx_settings_choose(&view,root));view.row=3;assert(!fx_settings_choose(&view,root));
    assert(sd_game_quality_load(root)==0);

    struct fx_art art;assert(fx_art_load(&art,root));
    uint32_t *pixels=calloc(1296*FX_H,sizeof(uint32_t));assert(pixels);
    struct fx_canvas canvas={.pixels=pixels,.stride=1296,.art=&art};
    view.screen=FX_SETTINGS;view.message=NULL;view.saved=0;
    fx_game_quality=1; /* Show the persisted Light choice in the screenshots. */
    assert(sd_game_quality_save(root,1));
    static const char *names[]={"game-detail-game","game-detail-light-720p","game-detail-restore"};
    for(int row=0;row<3;row++){
        fx_settings_enter(&view,FX_SETTINGS_GAME_QUALITY,row);
        text_inside(&art,fx_settings_title(view.settings_page),2,417,122,417,110,1116,166);
        text_inside(&art,fx_settings_subtitle(view.settings_page),0,417,172,417,168,1178,204);
        for(int item=0;item<3;item++){
            int y=216+item*116;
            text_inside(&art,fx_settings_label(&view,item),1,435,y+20,412,y,1060,y+61);
            text_inside(&art,fx_settings_detail(&view,item),0,437,y+61,412,y,1178,y+100);
        }
        fx_render(&canvas,&view);save_image(&canvas,argv[2],names[row]);
    }
    fx_settings_enter(&view,FX_SETTINGS_ROOT,7);
    text_inside(&art,fx_settings_label(&view,7),1,435,468,412,448,1060,509);
    text_inside(&art,fx_settings_detail(&view,7),0,437,509,412,448,1178,548);
    fx_render(&canvas,&view);save_image(&canvas,argv[2],"settings-game-detail");
    fx_settings_enter(&view,FX_SETTINGS_RENDERER,2);
    fx_render(&canvas,&view);save_image(&canvas,argv[2],"renderer-native");
    fx_render(&canvas,&restore_failure);save_image(&canvas,argv[2],"game-detail-restore-failed");
    fx_settings_enter(&view,FX_SETTINGS_ROOT,7);fx_settings_back(&view);assert(view.screen==FX_HOME);
    fx_art_free(&art);free(pixels);
    puts("PASS: actual startup/prelaunch rejects corrupt mode; eight settings pages; seven group enter/back routes; three persisted renderers; Light choice deferred to launch; 720p retained; exact restore; operation/reload errors preserved; successful save/restore with corrupt reload rejected; six bounded renders; unrelated user options preserved.");
}
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def png_from_ppm(path):
    """Encode the harness's RGB P6 output without optional image dependencies."""
    header, pixels = path.read_bytes().split(b"\n255\n", 1)
    assert header == b"P6\n1280 720" and len(pixels) == 1280 * 720 * 3
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    scanlines = b"".join(b"\0" + pixels[y * 3840:(y + 1) * 3840] for y in range(720))
    result = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1280, 720, 8, 2, 0, 0, 0))
              + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))
    path.with_suffix(".png").write_bytes(result)


def main():
    assert os.name == "posix", "Run with WSL Python in the prepared build environment"
    source_files = {name: sha(ROOT / name) for name in (
        "tools/build_native_dxvk_h4.py", "tools/test_native_dxvk_h4_game_quality_ui.py", "src/native_dxvk_com/game_quality.h")}
    LOCAL.mkdir(parents=True, exist_ok=True)
    output = LOCAL / "game-quality-ui"
    output.mkdir(parents=True, exist_ok=True)
    work = WORK / "game-quality-ui"
    work.mkdir(parents=True, exist_ok=True)
    pin = json.loads(PIN.read_text())
    baseline = Path(pin["runtime_source"])
    assert sha(baseline) == pin["runtime_sha256"]
    runtime = overlay_runtime(baseline.read_text())
    settings = overlay_settings((baseline.parent / "f1_settings.h").read_text())
    (work / "f1_settings.h").write_text(settings)
    shutil.copyfile(SOURCES / "game_quality.h", work / "game_quality.h")
    start = runtime.index("#ifndef FEXTENDO_PRESETS_H")
    end = runtime.index("\n#endif", runtime.index("static void fx_render(")) + len("\n#endif")
    init_start = runtime.index("    fx_game_quality=sd_game_quality_load(RUNTIME_DIR);")
    init_fragment = runtime[init_start:runtime.index("\n    fx_dx_hud=", init_start)]
    launch_start = runtime.index("        if(ready){\n            int quality=sd_game_quality_load(RUNTIME_DIR);")
    launch_fragment = runtime[launch_start:runtime.index("        if(ready&&!wine_nx_f1_prepare_threads", launch_start)]
    runtime_wrappers = ("\n#define RUNTIME_DIR root\nstatic void actual_quality_init(const char *root){\n" + init_fragment
                        + "\n}\nstatic int actual_quality_prelaunch(const char *root,int was_ready,const char **error){\n"
                        + "int ready=was_ready;const char *launch_error=NULL;\n" + launch_fragment
                        + "\n*error=launch_error;return ready;\n}\n#undef RUNTIME_DIR\n")
    program = work / "game-quality-ui.c"
    program.write_text(PREAMBLE + runtime[start:end] + runtime_wrappers + HARNESS)
    executable = work / "game-quality-ui"
    dependencies = work / "game-quality-ui.d"
    command = [shutil.which("clang") or shutil.which("gcc"), "-std=c11", "-O1", "-g",
               "-D_POSIX_C_SOURCE=200809L", "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
               "-I" + str(work), "-I" + str(baseline.parent), "-MMD", "-MF", str(dependencies),
               str(program), "-pthread", "-lm", "-o", str(executable)]
    compiled = subprocess.run(command, capture_output=True, text=True)
    (LOCAL / "game-quality-ui.compile.log").write_text(compiled.stdout + compiled.stderr)
    if compiled.returncode:
        raise RuntimeError(compiled.stdout + compiled.stderr)
    assets = {file.name: file for file in (BASE / "launcher").iterdir() if file.suffix in (".rgba", ".bin")}
    preview = ROOT / "local/lsfg-launcher-check/preview-assets"
    for name in ("background.rgba", "blur.rgba", "icon.rgba"):
        assets[name] = preview / name
    asset_hashes = {name: {"source": str(path), "sha256": sha(path)} for name, path in assets.items()}
    # These fixtures verify UI/file-call behavior, not persistent-media durability.
    # Use the host temporary filesystem, avoiding WSL virtual-disk journal stalls.
    with tempfile.TemporaryDirectory(prefix="sd-h4-ui-") as temporary:
        root = Path(temporary)
        # Render on the Linux filesystem before copying previews across /mnt.
        # Host-mount I/O must not consume the executable's 90-second test limit.
        rendered = root / "renders"
        rendered.mkdir()
        (root / "launcher").mkdir()
        (root / "drive_c/SleepingDogs/Data").mkdir(parents=True)
        for name, path in assets.items():
            shutil.copyfile(path, root / "launcher" / name)
        run = subprocess.run([str(executable), str(root), str(rendered)], capture_output=True, text=True, timeout=90)
        (LOCAL / "game-quality-ui.stdout.log").write_text(run.stdout)
        (LOCAL / "game-quality-ui.stderr.log").write_text(run.stderr)
        if run.returncode:
            raise RuntimeError(run.stdout + run.stderr)
        for ppm in sorted(rendered.glob("*.ppm")):
            png_from_ppm(ppm)
            shutil.copyfile(ppm, output / ppm.name)
            png = ppm.with_suffix(".png")
            shutil.copyfile(png, output / png.name)
    for name, digest in source_files.items():
        assert sha(ROOT / name) == digest, "source changed during test: " + name
    headers = {}
    for name in shlex.split(dependencies.read_text().replace("\\\n", "").split(":", 1)[1]):
        path = Path(name)
        if path != program:
            headers[str(path)] = sha(path)
    assert sha(work / "game_quality.h") == sha(SOURCES / "game_quality.h"), "helper changed during test"
    assert settings == overlay_settings((baseline.parent / "f1_settings.h").read_text()), "settings changed during test"
    assert runtime == overlay_runtime(baseline.read_text()), "runtime changed during test"
    receipt = dict(
        status="PASS", build=BUILD, source_files=source_files, runner_sha256=sha(__file__),
        runtime_sha256=hashlib.sha256(runtime.encode()).hexdigest(),
        settings_sha256=hashlib.sha256(settings.encode()).hexdigest(),
        baseline_runtime_sha256=sha(baseline), baseline_settings_sha256=sha(baseline.parent / "f1_settings.h"),
        fixture_sha256=sha(program), compiled_headers=headers, compile_argv=command,
        sanitizers=["address", "undefined"], horizon_no_replace_rename=True,
        real_host_fsync_with_injected_failures=2, settings_pages=8, root_rows=8, detail_rows=3,
        fixture_storage_root=tempfile.gettempdir(), persistent_media_durability_tested=False,
        group_enter_back_routes=7, renderer_choices_persisted=3,
        deferred_apply_verified=True, resolution_1280x720_preserved=True, exact_original_restore=True,
        stop_enforcement_keeps_current_options=True, unrelated_user_options_preserved=True,
        restore_failure_after_mode_saved_reloads_memory=True,
        save_and_restore_failure_before_mode_saved_reloads_memory=True, precise_error_message_survives_reload=True,
        successful_save_and_restore_with_corrupt_reload_reported=True, preference_corruptions_injected=2,
        actual_startup_logs_corrupt_preference=True, actual_prelaunch_rejects_corrupt_preference=True,
        actual_prelaunch_short_circuit_skips_apply=True,
        startup_fragment_sha256=hashlib.sha256(init_fragment.encode()).hexdigest(),
        prelaunch_fragment_sha256=hashlib.sha256(launch_fragment.encode()).hexdigest(),
        actual_glyph_pixel_bounds_checked=True, padded_framebuffer_preserved=True,
        previews={path.name: sha(path) for path in sorted(output.glob("*.png"))}, preview_assets=asset_hashes,
        hardware_tested=False, game_tested=False, measured_fps=None,
        scope="Actual overlaid launcher C navigation/rendering and helper on temporary host files; host fsync with injected errors and modeled Horizon rename. No controller/Horizon filesystem/game performance validation.",
        result=run.stdout.strip(),
    )
    (LOCAL / "game-quality-ui.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in ("status", "build", "result", "previews")}, indent=2))


if __name__ == "__main__":
    main()
