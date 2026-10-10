"""Run the built launcher's C preflight on byte-exact files extracted from an update ZIP."""
from pathlib import Path
import argparse
import shutil
import subprocess
import tempfile
import zipfile

HARNESS = r'''
static void check_config_formats(const char *root,const char *dll){
    const char *good[]={
        "d3d9.presentInterval = 1\ndxvk.enableAsync = True\n",
        "d3d9.presentInterval = 1\r\ndxvk.enableAsync = True\r\n",
        "# Windows config\r\nd3d9.presentInterval = 1\ndxvk.enableAsync = True",
        "  d3d9.presentInterval\t= 1  \r\ndxvk.enableAsync = True\r\n",
        "# d3d9.presentInterval = 0\nd3d9.presentInterval = 1\ndxvk.enableAsync = True\n"};
    const char *bad[]={
        "# d3d9.presentInterval = 1\ndxvk.enableAsync = True\n",
        "d3d9.presentInterval = 0\r\ndxvk.enableAsync = True\r\n",
        "d3d9.presentInterval = 1\ndxvk.enableAsync = False\n",
        "d3d9.presentInterval = 1\ndxvk.enableAsync = True\nd3d9.presentInterval = 0\n",
        "d3d9.presentInterval = 1\n"};
    char file[768];snprintf(file,sizeof(file),"%s/config-format-test.conf",root);
    for(unsigned i=0;i<sizeof(good)/sizeof(*good);i++){
        assert(fx_write(file,good[i],strlen(good[i])));assert(fx_renderer_valid(dll,file,1));
    }
    for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++){
        assert(fx_write(file,bad[i],strlen(bad[i])));assert(!fx_renderer_valid(dll,file,1));
    }
    assert(fx_write(file,"",0));assert(!fx_renderer_valid(dll,file,0));
    assert(!unlink(file));assert(!fx_renderer_valid(dll,file,0));
    assert(!fx_renderer_valid(file,file,0));
    puts("PASS: LF/CRLF/mixed lines/spacing/no final newline; wrong options, comments, missing config and missing DLL still rejected.");
}
int main(int argc,char **argv){
    assert(argc==3);const char *root=argv[1];int reject=atoi(argv[2]),valid=0,total=0;
    char dll[768],conf[768],target[768],choice[768],bytes[2];
    const char *names[]={"d3d9.dll","d3d11.dll","dxgi.dll"};
    for(int r=0;r<2;r++){
        snprintf(conf,sizeof(conf),"%s/launcher/renderers/%s/dxvk.conf",root,fx_renderer_ids[r]);
        for(int d=0;d<3;d++){
            snprintf(dll,sizeof(dll),"%s/launcher/renderers/%s/%s",root,fx_renderer_ids[r],names[d]);
            valid+=!!fx_renderer_valid(dll,conf,r);total++;
        }
        for(int p=0;p<4;p++){
            snprintf(conf,sizeof(conf),"%s/launcher/presets/%s/%s/dxvk.conf",root,fx_preset_ids[p],fx_renderer_ids[r]);
            valid+=!!fx_renderer_valid(dll,conf,r);total++;
        }
    }
    if(reject){assert(!valid);printf("REPRODUCED: original launcher rejects all %d checks on complete ZIP configs.\n",total);return 0;}
    assert(valid==total);
    check_config_formats(root,dll);
    /* Install from the archive, then exercise both choices and all presets.
     * rename follows Horizon semantics: replacing an existing target fails. */
    for(int r=0;r<2;r++){
        assert(fx_renderer_save(root,r));assert(fx_apply_renderer(root,r));
        for(int d=0;d<3;d++){
            snprintf(dll,sizeof(dll),"%s/launcher/renderers/%s/%s",root,fx_renderer_ids[r],names[d]);
            snprintf(target,sizeof(target),"%s/drive_c/F1_2013/%s",root,names[d]);
            assert(fx_files_equal(dll,target));
        }
        for(int p=0;p<4;p++){
            assert(fx_apply_preset(root,p));
            snprintf(conf,sizeof(conf),"%s/launcher/presets/%s/%s/dxvk.conf",root,fx_preset_ids[p],fx_renderer_ids[r]);
            snprintf(target,sizeof(target),"%s/drive_c/F1_2013/dxvk.conf",root);
            assert(fx_files_equal(conf,target));
            snprintf(choice,sizeof(choice),"%s/launcher/selected.txt",root);
            assert(fx_read(choice,bytes,2)==2&&bytes[0]=='0'+p&&bytes[1]=='\n');
        }
        /* An overwrite update keeps the renderer selection/version index.
         * A stale target must still be replaced from the changed source set. */
        snprintf(target,sizeof(target),"%s/drive_c/F1_2013/d3d11.dll",root);
        const char *stale="MZ-stale-installed-renderer";
        assert(fx_write(target,stale,strlen(stale)));
        assert(fx_renderer_selected(root)==r&&fx_apply_renderer(root,r));
        for(int d=0;d<3;d++){
            snprintf(dll,sizeof(dll),"%s/launcher/renderers/%s/%s",root,fx_renderer_ids[r],names[d]);
            snprintf(target,sizeof(target),"%s/drive_c/F1_2013/%s",root,names[d]);
            assert(fx_files_equal(dll,target));
        }
    }
    puts("PASS: unchanged renderer selection still replaces stale installed DLLs from the complete new set.");
    printf("PASS: %d archive preflight checks, both renderer installations, all 8 presets using byte-exact ZIP files and Horizon rename semantics.\n",total);
}
'''
PREAMBLE = r'''
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <stdarg.h>
static void log_line(const char *fmt,...){va_list args;va_start(args,fmt);vfprintf(stderr,fmt,args);fputc('\n',stderr);va_end(args);}
static int horizon_rename(const char *a,const char *b){if(!access(b,F_OK)){errno=EEXIST;return -1;}return rename(a,b);}
#define rename horizon_rename
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--update', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expect-config-rejection', action='store_true')
    p.add_argument('--require-legacy-descriptors', action='store_true')
    args = p.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    native = args.source / 'wine-nx-probe/source'
    source = (native / 'runtime.c').read_text()
    start = source.index('#ifndef FEXTENDO_PRESETS_H')
    end = source.index('\n#endif', source.index('#ifndef FEXTENDO_RENDERERS_H')) + len('\n#endif')
    file = out / 'archive-preflight.c'; exe = file.with_suffix('')
    file.write_text(PREAMBLE + source[start:end] + HARNESS)
    subprocess.run([shutil.which('clang') or shutil.which('cc'), '-std=c11', '-O1', '-g',
                    '-D_POSIX_C_SOURCE=200809L', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    '-I', str(native), str(file), '-o', str(exe)], check=True)
    with tempfile.TemporaryDirectory(prefix='f1-update-preflight-', dir=out) as temp:
        root = Path(temp)
        configs = 0
        with zipfile.ZipFile(args.update) as z:
            for name in z.namelist():
                rel = name.removeprefix('switch/f1-fex/')
                if not rel.startswith(('launcher/renderers/', 'launcher/presets/')) or not rel.endswith(('.dll', '.conf')):
                    continue
                target = (root / rel).resolve()
                if not target.is_relative_to(root):
                    raise ValueError('Archive path escapes fixture')
                target.parent.mkdir(parents=True, exist_ok=True)
                data = z.read(name)
                target.write_bytes(data)
                if args.require_legacy_descriptors and rel.endswith('.conf'):
                    options = dict(line.strip().split(' = ') for line in data.decode('utf-8-sig').splitlines()
                                   if line.strip() and not line.lstrip().startswith('#'))
                    assert options['dxvk.enableDescriptorBuffer'] == 'False', name
                    assert options['dxvk.enableDescriptorHeap'] == 'False', name
                    assert options['dxvk.numCompilerThreads'] == '1', name
                    configs += 1
        if args.require_legacy_descriptors:
            assert configs == 11, configs  # 2 renderer defaults, 8 presets, active preset default
            print('PASS: all 11 byte-exact archive configs select legacy descriptors and one compiler worker.', flush=True)
        subprocess.run([str(exe), str(root), str(int(args.expect_config_rejection))], check=True)


if __name__ == '__main__':
    main()
