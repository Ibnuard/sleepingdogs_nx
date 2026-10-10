"""Exercise actual v11 launch gate and profile/HUD merge on the staged update."""
from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from port_common import sha, write_json
from build_dxvk_memory import manifest


def main():
    native = Path('/home/blekjek/sleepingdogs-low-window-v1/native-source/wine-nx-probe/source')
    stage = ROOT/'dist/sleepingdogs-fex-low-window-submit-batching/switch/sleepingdogs-fex'
    work = Path('/home/blekjek/sleepingdogs-dxvk-batch-v1/checks')
    receipt = json.loads((ROOT/'dist/low-window-frame-diagnostics/native.json').read_text())
    for n in ('runtime.c','f1_dx_hud.h'):
        assert sha(native/n) == receipt['source_files']['wine-nx-probe/source/'+n]
    spec = importlib.util.spec_from_file_location('preflight', ROOT/'vendor/f1-tools/check_renderer_package.py')
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    source = (native/'runtime.c').read_text()
    begin = source.index('#ifndef FEXTENDO_PRESETS_H')
    end = source.index('\n#endif', source.index('#ifndef FEXTENDO_RENDERERS_H'))+len('\n#endif')
    cpp, exe = work/'batch-launcher.c', work/'batch-launcher'
    cpp.write_text(base.PREAMBLE+source[begin:end]+'\n'+(ROOT/'tests/dxvk_batch_launcher.c').read_text())
    with (work/'launcher-compile.log').open('w') as log:
        subprocess.run(['cc','-std=c11','-O1','-g','-D_POSIX_C_SOURCE=200809L',
                        '-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-pie','-no-pie',
                        '-I'+str(native),str(cpp),'-o',str(exe)],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
    files = manifest(stage)
    # Update users already have this renderer validation config. Seed only
    # that missing baseline file; all updated DLLs and Performance come from stage.
    base_config = ROOT/'local/buffer-reuse-validate-uzpwmdes/switch/sleepingdogs-fex/launcher/renderers/dxvk-3.1.1/dxvk.conf'
    with tempfile.TemporaryDirectory(prefix='batch-launch-',dir=work) as temp:
        root=Path(temp)
        for n in files:
            if n.startswith(('launcher/renderers/','launcher/presets/')) and n.endswith(('.dll','.conf')):
                target=root/n; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(stage/n,target)
        shutil.copy2(base_config,root/'launcher/renderers/dxvk-3.1.1/dxvk.conf')
        result=subprocess.check_output([str(exe),str(root)],text=True,timeout=60).strip()
    assert manifest(stage) == files
    write_json(ROOT/'reports/dxvk-batch-launcher.json', dict(status='PASS', result=result,
        staged_runtime_files=files, base_renderer_config_sha256=sha(base_config),
        native_source_sha256=sha(native/'runtime.c'), nro_sha256=receipt['nro_sha256'],
        sanitizers=['address','undefined'], hardware_tested=False,
        sources={n:sha(ROOT/n) for n in ('tests/check_dxvk_batch_launcher.py','tests/dxvk_batch_launcher.c',
                                       'vendor/f1-tools/check_renderer_package.py')}))
    print(result,flush=True)


if __name__ == '__main__': main()
