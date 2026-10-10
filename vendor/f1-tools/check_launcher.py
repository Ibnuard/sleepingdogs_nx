"""Render the generated F1 C UI on the host and check isolated DOS mapping.

Run under WSL with clang. Previews come from the same C code compiled into
the NRO, including its cached background scenes.
"""
from pathlib import Path
import argparse
import subprocess
import shutil


HARNESS = r'''
#include <assert.h>
#include "launcher_list.h"
int main(int argc,char **argv) {
    assert(argc==3);
    char dos[512],path[1024];
    assert(launcher_dos_path("sdmc:/switch/f1-fex/drive_c/F1_2013/F1_2013.exe",dos,sizeof(dos)));
    assert(!strcmp(dos,"C:\\F1_2013\\F1_2013.exe"));
    assert(launcher_dos_path("sdmc:/switch/pes13-fex/drive_c/pes2013.exe",dos,sizeof(dos)));
    assert(dos[0]=='Z');
    struct fx_art art;assert(fx_art_load(&art,argv[1]));
    uint32_t *pixels=calloc(1296*FX_H,4);assert(pixels);
    struct fx_canvas c={.pixels=pixels,.stride=1296,.art=&art};
    const char *names[]={"settings","graphics","renderer","keyboard","audio","home","splash","debug","debug-failed","game-stopped","game-closed","worker-memory"};
    for(int n=0;n<12;n++){
        struct fx_view v={.screen=FX_SETTINGS,.settings_page=n,.sound=1,
            .music=1,.battery=100,.frame=32,.wall_time=1800000000};
        if(n==5){v.screen=FX_HOME;v.settings_page=0;}
        if(n==6){v.screen=FX_HOME;v.splash_ms=600;v.settings_page=0;}
        if(n>=7){
            v.screen=FX_LOADING;v.debug=1;v.settings_page=0;
            snprintf(fx_debug_lines[0],120,"[TARGET] C:\\F1_2013\\F1_2013.exe");
            snprintf(fx_debug_lines[1],120,"[INIT] Wine data: /switch/f1-fex/share/wine");
            fx_debug_total=2;
            if(n==8){v.fatal=1;v.message="F1: Cannot initialise graphics. See fex-runtime.log and F1_2013_dxgi.log.";}
        }
        if(n>=9){
            v.screen=FX_FAILED;v.debug=0;v.fatal=0;v.returned=n==9?2:1;
            v.message=n==9?"Game stopped (0xc0000005). Runtime restarted. Logs saved: fex-runtime.log and crash.log.":
                "The game has closed. The runtime was restarted. You can launch F1 again.";
        }
        if(n==11){v.returned=2;v.message="Cannot start game worker (0xc0000017): memory allocation failed. Runtime restarted. See fex-runtime.log.";}
        fx_render(&c,&v);
        snprintf(path,sizeof(path),"%s/%s.ppm",argv[2],names[n]);
        FILE *out=fopen(path,"wb");assert(out);
        fprintf(out,"P6\n1280 720\n255\n");
        for(int y=0;y<FX_H;y++){
            for(int x=0;x<FX_W;x++){
                uint32_t p=pixels[y*1296+x];unsigned char rgb[]={p,p>>8,p>>16};
                assert(fwrite(rgb,1,3,out)==3);
            }
            for(int x=FX_W;x<1296;x++)assert(pixels[y*1296+x]==0);
        }
        assert(!fclose(out));
    }
    struct fx_view v={.screen=FX_SETTINGS,.settings_page=FX_SETTINGS_ROOT};
    for(int row=0;row<4;row++){
        v.row=row;assert(fx_settings_choose(&v,argv[1]));
        assert(v.settings_page!=FX_SETTINGS_ROOT);
        fx_settings_back(&v);assert(v.settings_page==FX_SETTINGS_ROOT&&v.row==row);
    }
    fx_settings_back(&v);assert(v.screen==FX_HOME);
    fx_art_free(&art);free(pixels);
    puts("PASS: F1 maps to C:, PES stays outside C:, grouped navigation, render bounds.");
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    native = args.source.resolve() / "wine-nx-probe/source"
    source = (native / "runtime.c").read_text()
    start = source.index("#ifndef FEXTENDO_PRESETS_H")
    end = source.index("\n#endif", source.index("static void fx_render(")) + len("\n#endif")
    args.output.mkdir(parents=True, exist_ok=True)
    program = args.output.resolve() / "f1-ui-check.c"
    program.write_text("#include <pthread.h>\n"
        "static pthread_mutex_t fx_debug_lock=PTHREAD_MUTEX_INITIALIZER;\n"
        "static char fx_debug_lines[21][120];\nstatic unsigned fx_debug_total;\n" +
        source[start:end] + "\n" + HARNESS)
    exe = program.with_suffix("")
    compiler = shutil.which("clang") or shutil.which("cc")
    if not compiler:
        raise SystemExit("A host C compiler is required")
    subprocess.run([compiler, "-std=c11", "-O1", "-g", "-D_POSIX_C_SOURCE=200809L",
                    "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                    "-I", str(native), str(program), "-pthread", "-lm", "-o", str(exe)], check=True)
    subprocess.run([str(exe), str(args.prefix.resolve()), str(args.output.resolve())], check=True)


if __name__ == "__main__":
    main()
