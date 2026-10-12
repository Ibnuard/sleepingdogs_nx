"""Host regression/rendering of the actual launcher and imported keyboard."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile
from launcher_v2_overlay import ROOT,SOURCE
from test_native_dxvk_h4_game_quality_ui import PREAMBLE,HARNESS,png_from_ppm

LOCAL=ROOT/'local/launcher-v2'
WORK=Path('/home/blekjek/sleepingdogs-launcher-v2')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,name,cwd=None):
    r=subprocess.run([str(x) for x in argv],cwd=cwd,capture_output=True,text=True,timeout=180)
    (LOCAL/(name+'.log')).write_text(r.stdout+r.stderr)
    assert not r.returncode,(name,r.stdout+r.stderr)
    return r.stdout.strip()

def main():
    assert os.name=='posix'
    work=WORK/'tests';work.mkdir(exist_ok=True)
    runtime=(WORK/'source/runtime.c').read_text()
    assert 'sd_game_quality_apply(RUNTIME_DIR,1)' in runtime and 'sd_game_quality_load(RUNTIME_DIR)' not in runtime
    assert 'sd_com_enabled?0:lsfg.enabled' not in runtime
    assert 'sd_check_force=0;check_requested=1' in runtime
    start=runtime.index('#ifndef FEXTENDO_PRESETS_H');end=runtime.index('\n#endif',runtime.index('static void fx_render('))+len('\n#endif')
    prefix=PREAMBLE+'\n#include "boot_memory.h"\n'+runtime[start:end]+'\nstatic int checks_requested;\nstatic void sd_check_request(void){checks_requested++;}\n'
    (work/'ui.h').write_text(prefix)
    helpers=HARNESS[HARNESS.index('static void save_image'):HARNESS.index('int main(')]
    program=work/'launcher.c';program.write_text('#include "ui.h"\n'+helpers+(ROOT/'tests/launcher_v2.c').read_text())
    common=['gcc','-std=gnu11','-O1','-g','-D_POSIX_C_SOURCE=200809L','-fsanitize=address,undefined','-fno-sanitize-recover=all',
            '-I'+str(work),'-I'+str(WORK/'source'),'-I'+str(SOURCE),'-I'+str(SOURCE/'pes13'),'-I'+str(ROOT/'src/native_dxvk_com'),
            '-I/home/blekjek/sleepingdogs-apc-v18/native-source/wine-nx-probe/source',
            '-pthread','-Wno-deprecated-declarations']
    results={};assets=json.loads((LOCAL/'catalog.json').read_text())
    with tempfile.TemporaryDirectory(prefix='sd-launcher-v2-') as temporary:
        root=Path(temporary);render=root/'renders';render.mkdir()
        (root/'drive_c/SleepingDogs/Data').mkdir(parents=True);(root/'launcher').mkdir()
        for e in assets:
            if e['path'].startswith('launcher/') and Path(e['path']).suffix in ('.bin','.rgba'):
                p=root/e['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(e['source'],p)
        run([*common,program,WORK/'source/boot_font.c','-lcrypto','-lm','-o',work/'launcher'],'ui.compile')
        results['ui']=run([work/'launcher',root,render],'ui.test')
        preview=LOCAL/'previews';preview.mkdir(exist_ok=True)
        for ppm in render.glob('*.ppm'):
            png_from_ppm(ppm);shutil.copyfile(ppm.with_suffix('.png'),preview/(ppm.stem+'.png'))
        # The import fixtures are pinned to the same upstream commit as headers.
        upstream=ROOT/'tests/pes13'
        for name in ('fextendo_keyboard.c','fextendo_osk.c'):
            shutil.copyfile(upstream/name,work/name)
            exe=work/Path(name).stem
            run([*common,work/name,'-o',exe],name+'.compile')
            results[name]=run([exe],name+'.test')
        options=(upstream/'fextendo_keyboard_options.c').read_text().replace('#include "../src/runtime/fextendo_presets.h"','#include "ui.h"')
        (work/'options.c').write_text(options)
        run([*common,work/'options.c',WORK/'source/boot_font.c','-lcrypto','-lm','-o',work/'options'],'options.compile')
        options_root=root/'options';(options_root/'launcher').mkdir(parents=True)
        results['options']=run([work/'options',options_root],'options.test')
        catalog=work/'file-check';catalog.mkdir(exist_ok=True)
        digest=lambda s:hashlib.sha256(s.encode()).hexdigest()
        (catalog/'system_catalog.h').write_text('static const struct sd_check_file sd_check_files[]={{"runtime.dll",7,"'+digest('runtime')+'","'+digest('different')+'"}};\n#define SD_CHECK_FILE_COUNT 1\n')
        run(['gcc','-std=gnu11','-O1','-g','-fsanitize=address,undefined','-Wno-deprecated-declarations','-I'+str(catalog),'-I'+str(SOURCE),ROOT/'tests/launcher_check_files.c','-lcrypto','-o',work/'file-check-test'],'files.compile')
        results['files']=run([work/'file-check-test',root],'files.test')
    with tempfile.TemporaryDirectory(prefix='sd-cache-v2-') as temp:
        root=Path(temp);(root/'launcher').mkdir()
        run(['gcc','-std=gnu11','-O1','-g','-fsanitize=address,undefined','-Wno-deprecated-declarations','-I'+str(catalog),'-I'+str(SOURCE),ROOT/'tests/launcher_check_cache.c','-lcrypto','-o',work/'cache-test'],'cache.compile')
        results['cache']=run([work/'cache-test',root],'cache.test')
    include=Path('/home/blekjek/pes13-build/mesa-vulkan/install/opt/devkitpro/portlibs/switch/include')
    run(['g++','-std=gnu++17','-O1','-g','-fsanitize=address,undefined','-I'+str(include),ROOT/'tests/launcher_osk_vulkan.cpp','-pthread','-o',work/'vulkan-test'],'vulkan.compile')
    results['vulkan']=run([work/'vulkan-test'],'vulkan.test')
    run(['g++','-std=gnu++17','-O1','-g','-fsanitize=address,undefined','-I'+str(include),
         '-I/home/blekjek/sleepingdogs-lsfg-v15/native-source/wine-nx-probe/source',
         ROOT/'tests/launcher_lsfg_vulkan.cpp','-pthread','-o',work/'lsfg-model-test'],'lsfg-model.compile')
    results['lsfg_model']=run([work/'lsfg-model-test'],'lsfg-model.test')
    run(['gcc','-std=c11','-O1','-g','-fsanitize=address,undefined','-I'+str(ROOT/'src/native_dxvk_com'),ROOT/'tests/native_dxvk_compact_wire.c','-o',work/'wire-test'],'wire.compile')
    results['wire']=run([work/'wire-test'],'wire.test')
    report=dict(status='PASS',results=results,source_files={str(p.relative_to(ROOT)):sha(p) for p in SOURCE.rglob('*') if p.is_file()},
                preview_files={p.name:sha(p) for p in (LOCAL/'previews').glob('*.png')},hardware_tested=False,
                scope='Actual C UI rendering/navigation/persistence and imported keyboard under ASan/UBSan; simulated platform services. Physical Switch input/display not tested.')
    (LOCAL/'test.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()
