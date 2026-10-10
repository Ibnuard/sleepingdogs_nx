"""Exercise the current native C renderer gate on the actual cumulative archive."""
from pathlib import Path
import subprocess, sys, tempfile, zipfile
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT / 'tools'))
from port_common import sha, write_json


def main():
    work = Path('/home/blekjek/sleepingdogs-streaming-memory-v1')
    native = work / 'native-source'
    base = ROOT / 'dist/sleepingdogs-fex-0.1.0-sd.zip'
    patch = ROOT / 'dist/sleepingdogs-fex-streaming-memory-fix.zip'
    prefix = 'switch/sleepingdogs-fex/'; files = {}
    for archive in (base,patch):
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if name.startswith((prefix+'launcher/renderers/',prefix+'launcher/presets/')) and name.endswith(('.dll','.conf')):
                    files[name] = z.read(name)
    with tempfile.TemporaryDirectory(dir=work,prefix='launcher-archive-') as temp:
        merged = Path(temp) / 'combined.zip'
        with zipfile.ZipFile(merged,'w') as z:
            for name,data in files.items(): z.writestr(name,data)
        run = subprocess.run([sys.executable,str(ROOT / 'tests/check_renderer_package.py'),
            '--source',str(native),'--update',str(merged),'--output',str(work / 'launcher-check')],
            capture_output=True,text=True,timeout=60)
        assert run.returncode == 0, run.stdout+run.stderr
    assert '14 archive preflight checks' in run.stdout
    assert 'unchanged renderer selection still replaces stale installed DLLs' in run.stdout
    write_json(ROOT / 'reports/streaming-launcher-check.json',{'status':'PASS',
        'patch_sha256':sha(patch),'base_sha256':sha(base),'result':run.stdout.strip(),
        'native_runtime_sha256':sha(native / 'wine-nx-probe/source/runtime.c'),
        'source_sha256':sha(Path(__file__)),'hardware_tested':False})
    print(run.stdout.strip())


if __name__ == '__main__': main()
