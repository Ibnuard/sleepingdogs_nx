"""Execute the actual C launcher with ASan/UBSan and Horizon rename semantics."""
from pathlib import Path
import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from port_common import BASE, sha, write_json, profile_config
from dxvk_runtime import stage_renderers
from sleepingdogs_performance_hud import performance_config, FILES

HARNESS = r'''
#include <assert.h>
static uint64_t fex_frame_ok, fex_frame_errors;
static struct { uint64_t sum_us; } fex_frame_stats[4];
static char frame_line[512];
static void frame_log(const char *fmt,...) {
    va_list args;va_start(args,fmt);vsnprintf(frame_line,sizeof(frame_line),fmt,args);va_end(args);
}
#define armTicksToNs(x) (x)
#define log_line frame_log
#include "sd_frame_summary.h"
#undef log_line
static void check_frame_summary(void) {
    sd_frame_summary(1000000000ULL);assert(!frame_line[0]);
    fex_frame_ok=200;fex_frame_errors=1;
    fex_frame_stats[1].sum_us=1000000;fex_frame_stats[2].sum_us=20000;fex_frame_stats[3].sum_us=800000;
    sd_frame_summary(10000000000ULL);assert(!frame_line[0]);
    sd_frame_summary(11000000000ULL);
    assert(strstr(frame_line,"window_ms=10000 frames=200 fps_x100=2000 present_avg_us=5000 lock_avg_us=100 driver_avg_us=4000 errors=1"));
    sd_frame_summary(21000000000ULL);
    assert(strstr(frame_line,"frames=0 fps_x100=0 present_avg_us=0 lock_avg_us=0 driver_avg_us=0 errors=0"));
}
static void save_image(struct fx_canvas *c,const char *folder,const char *name) {
    char path[1024];snprintf(path,sizeof(path),"%s/%s.ppm",folder,name);
    FILE *f=fopen(path,"wb");assert(f);fprintf(f,"P6\n1280 720\n255\n");
    for(int y=0;y<FX_H;y++){
        for(int x=0;x<FX_W;x++){
            uint32_t p=c->pixels[y*c->stride+x];unsigned char rgb[]={p,p>>8,p>>16};
            assert(fwrite(rgb,1,3,f)==3);
        }
        for(int x=FX_W;x<c->stride;x++)assert(!c->pixels[y*c->stride+x]);
    }
    assert(!fclose(f));
}
int main(int argc,char **argv) {
    assert(argc==3);const char *root=argv[1];char path[1024],old[1030],config[8192];
    check_frame_summary();
    snprintf(path,sizeof(path),"%s/launcher/dx-log.txt",root);
    snprintf(old,sizeof(old),"%s.old",path);
    assert(fx_dx_hud_load(root)==0);
    assert(!fx_dx_hud_save(root,-1)&&!fx_dx_hud_save(root,3));
    assert(fx_write(path,"2\r\n",3));assert(fx_dx_hud_load(root)==2);
    assert(!rename(path,old));assert(fx_dx_hud_load(root)==2);
    assert(fx_dx_hud_save(root,1));assert(fx_dx_hud_load(root)==1);assert(access(old,F_OK));
    assert(fx_write(path,"2oops\n",6));assert(fx_dx_hud_load(root)==0);
    /* Interrupted writes cannot replace a valid saved value with an empty file. */
    snprintf(old,sizeof(old),"%s.new",path);assert(!mkdir(old,0700));
    assert(!fx_dx_hud_save(root,2));assert(fx_dx_hud_load(root)==0);assert(!rmdir(old));
    assert(fx_dx_hud_save(root,0));
    struct fx_view v={.screen=FX_SETTINGS,.settings_page=FX_SETTINGS_ROOT};
    for(int row=0;row<6;row++){
        if(row==4)continue;
        v.row=row;assert(fx_settings_choose(&v,root));
        assert(v.settings_page!=FX_SETTINGS_ROOT);
        fx_settings_back(&v);assert(v.settings_page==FX_SETTINGS_ROOT&&v.row==row);
    }
    for(int r=0;r<2;r++){
        assert(fx_renderer_save(root,r));assert(fx_apply_renderer(root,r));
        for(int p=0;p<5;p++) for(int h=0;h<3;h++){
            fx_settings_enter(&v,FX_SETTINGS_DX_LOG,h);
            assert(fx_settings_choose(&v,root));assert(fx_dx_hud==h&&fx_dx_hud_load(root)==h);
            fx_settings_enter(&v,FX_SETTINGS_GRAPHICS,p);
            assert(fx_settings_choose(&v,root));assert(v.selected==p&&fx_selected(root)==p);
            snprintf(path,sizeof(path),"%s/drive_c/SleepingDogs/dxvk.conf",root);
            size_t n=fx_read(path,config,sizeof(config)-1);config[n]=0;assert(n);
            assert(fx_renderer_option(config,"dxvk.hud",fx_dx_hud_values[h]));
            assert(fx_renderer_option(config,"dxgi.syncInterval",p==4?"0":"1"));
            assert(fx_renderer_option(config,"dxgi.maxFrameLatency",p==4?"3":p==1?"1":"2"));
            assert(fx_renderer_option(config,"dxvk.numCompilerThreads","1"));
            assert(fx_renderer_option(config,"dxvk.enableDescriptorBuffer","False"));
            assert(fx_renderer_option(config,"dxvk.enableDescriptorHeap","False"));
            if(r)assert(fx_renderer_option(config,"dxvk.enableAsync","True"));
        }
    }
    /* Invalid input never promotes a staged config over the installed one. */
    snprintf(path,sizeof(path),"%s/bad.conf",root);snprintf(old,sizeof(old),"%s/bad-stage.conf",root);
    assert(fx_write(path,"x\0y",3));assert(!fx_dx_hud_config(path,old,2));assert(access(old,F_OK));
    assert(fx_write(path,"dxvk.hud = full\n",16));assert(fx_dx_hud_config(path,old,1));
    size_t n=fx_read(old,config,sizeof(config)-1);config[n]=0;
    assert(fx_renderer_option(config,"dxvk.hud","fps"));
    assert(fx_renderer_save(root,0));assert(fx_apply_preset(root,2));
    fx_input_mode=fx_input_mode_load(root);
    struct fx_art art;assert(fx_art_load(&art,root));
    uint32_t *pixels=calloc(1296*FX_H,4);assert(pixels);
    struct fx_canvas c={.pixels=pixels,.stride=1296,.art=&art};
    v=(struct fx_view){.screen=FX_SETTINGS,.selected=2,.renderer=0,.sound=1,.music=1,
        .battery=100,.frame=32,.wall_time=1800000000};
    for(int h=0;h<3;h++){
        const char *names[]={"hud-none","hud-fps","hud-full"};
        fx_dx_hud=h;fx_settings_enter(&v,FX_SETTINGS_DX_LOG,h);
        fx_render(&c,&v);save_image(&c,argv[2],names[h]);
    }
    fx_settings_enter(&v,FX_SETTINGS_ROOT,5);fx_render(&c,&v);save_image(&c,argv[2],"settings-hud");
    v.selected=4;fx_settings_enter(&v,FX_SETTINGS_GRAPHICS,4);
    fx_render(&c,&v);save_image(&c,argv[2],"performance");
    fx_art_free(&art);free(pixels);
    puts("PASS: 30 renderer/profile/HUD combinations; persisted choices; malformed input; interrupted write recovery; group navigation; render bounds.");
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1/native-source'))
    p.add_argument('--output', type=Path, default=ROOT/'local/performance-hud-check')
    p.add_argument('--prepare-assets', action='store_true', help='Prepare preview pixels using host Pillow')
    a = p.parse_args()
    art_dir = a.output/'preview-assets'
    if a.prepare_assets:
        from PIL import Image, ImageFilter
        art_dir.mkdir(parents=True, exist_ok=True)
        bg = Image.open(ROOT/'assets/background.png').convert('RGBA')
        (art_dir/'background.rgba').write_bytes(bg.tobytes())
        (art_dir/'blur.rgba').write_bytes(bg.filter(ImageFilter.GaussianBlur(18)).tobytes())
        (art_dir/'icon.rgba').write_bytes(Image.open(ROOT/'assets/icon.png').convert('RGBA').tobytes())
        return
    native = a.source/'wine-nx-probe/source'
    source = (native/'runtime.c').read_text()
    start = source.index('#ifndef FEXTENDO_PRESETS_H')
    end = source.index('\n#endif', source.index('static void fx_render(')) + len('\n#endif')
    a.output.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('renderer', ROOT/'vendor/f1-tools/check_renderer_package.py')
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    preamble = renderer.PREAMBLE + ('\n#include <pthread.h>\n'
        'static pthread_mutex_t fx_debug_lock=PTHREAD_MUTEX_INITIALIZER;\n'
        'static char fx_debug_lines[21][120];\nstatic unsigned fx_debug_total;\n')
    program = a.output/'launcher.c'
    program.write_text(preamble+source[start:end]+HARNESS)
    exe = a.output/'launcher'
    subprocess.run([shutil.which('clang') or shutil.which('cc'), '-std=c11', '-O1', '-g',
                    '-D_POSIX_C_SOURCE=200809L', '-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all', '-I', str(native), str(program),
                    '-pthread', '-lm', '-o', str(exe)], check=True)
    with tempfile.TemporaryDirectory(dir=a.output, prefix='fixture-') as temp:
        root = Path(temp)
        renderer_receipt = stage_renderers(root, profile_config)
        for renderer_id in ('dxvk-3.1.1','dxvk-2.7.1-async'):
            for profile in ('balanced','low-latency','stable','quality','performance'):
                dest=root/'launcher/presets'/profile/renderer_id/'dxvk.conf'
                dest.parent.mkdir(parents=True,exist_ok=True)
                value = performance_config(renderer_id.endswith('async')) if profile=='performance' else profile_config(profile,renderer_id.endswith('async'))
                dest.write_text(value)
        for src in (BASE/'launcher').iterdir():
            if src.suffix in ('.rgba','.bin'):
                shutil.copy2(src,root/'launcher'/src.name)
        for name in ('background.rgba','blur.rgba','icon.rgba'):
            shutil.copy2(art_dir/name,root/'launcher'/name)
        run = subprocess.run([str(exe), str(root), str(a.output)], capture_output=True, text=True)
        assert run.returncode == 0, run.stdout+run.stderr
        print(run.stdout, end='')
    assert '__atomic_store_n(&f1_startup_watch_enabled,fx_ui_view.debug,__ATOMIC_RELEASE);' in source
    assert 'if (presented) sd_frame_summary(now);' in source
    report=dict(status='PASS',combinations=30,sanitizers=['address','undefined'],
                horizon_rename=True,hardware_tested=False,result=run.stdout.strip(),
                renderer_files=renderer_receipt,source_files={n:sha(a.source/n) for n in FILES},
                sources={'tests/check_performance_hud.py':sha(Path(__file__))},
                previews=[str(p) for p in sorted(a.output.glob('*.ppm'))])
    write_json(ROOT/'reports/low-window-v7-launcher.json',report)


if __name__=='__main__':main()
