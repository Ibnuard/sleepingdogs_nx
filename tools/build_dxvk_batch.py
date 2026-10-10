"""Build the isolated v12 DXVK experiment; preserve v11 NRO and SDK."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from sleepingdogs_dxvk_batch import apply, BUILD, FILES, MARKER

BASE = Path('/home/blekjek/sleepingdogs-buffer-reuse-v2')
WORK = Path('/home/blekjek/sleepingdogs-dxvk-batch-v1')
INPUTS = ('tools/build_dxvk_batch.py', 'tools/sleepingdogs_dxvk_batch.py')


def prepare(work):
    prior = json.loads((BASE/'prepared.json').read_text())
    vendor = json.loads((ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.json').read_text())
    baseline = dict(source_files=prior['source_files'], commit=vendor['source']['commit'])
    for n,h in vendor['source_changes'].items(): assert baseline['source_files'][n] == h, n
    assert manifest(BASE/'source') == baseline['source_files']
    inputs = dict(base_source=baseline['source_files'],
                  files={n:sha(ROOT/n) for n in INPUTS},
                  cross_sha256=sha(BASE/'cross-x32.txt'),
                  base_receipt_sha256=sha(BASE/'prepared.json'),
                  base_vendor_sha256=sha(ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.json'))
    work.mkdir(parents=True, exist_ok=True)
    source, stamp = work/'source', work/'prepared.json'
    if not stamp.exists():
        assert not source.exists(), 'Use a fresh work directory'
        shutil.copytree(BASE/'source', source, symlinks=True)
        apply(source)
        shutil.copy2(BASE/'cross-x32.txt', work/'cross-x32.txt')
        write_json(stamp, dict(inputs=inputs, source_files=manifest(source)))
    prepared = json.loads(stamp.read_text())
    assert inputs == prepared['inputs']
    assert manifest(source) == prepared['source_files']
    changed = {n:h for n,h in prepared['source_files'].items()
               if inputs['base_source'].get(n) != h}
    assert set(changed) == FILES
    assert set(inputs['base_source']) <= set(prepared['source_files'])
    return baseline, prepared, changed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=WORK)
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--prepare-only', action='store_true')
    a = p.parse_args()
    baseline, prepared, changed = prepare(a.work)
    if a.prepare_only:
        print('Prepared isolated source:', a.work, flush=True)
        return
    tests = json.loads((ROOT/'reports/dxvk-batch-host.json').read_text())
    assert tests['status'] == 'PASS'
    for n,h in tests['sources'].items(): assert sha(ROOT/n) == h, n
    for n,h in tests['candidate_sources'].items(): assert prepared['source_files'][n] == h, n
    tc = Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64')
    shaders = Path('/home/blekjek/f1-dxvk-small-chunks/shader-tools/usr/bin')
    env = dict(os.environ, PATH=str(tc/'bin')+os.pathsep+str(shaders)+os.pathsep+os.environ['PATH'])
    build, source = a.work/'build-x32', a.work/'source'
    print('Compiling isolated DXVK; native runtime and shared SDK unchanged', flush=True)
    with (a.work/'build.log').open('a') as log:
        if not (build/'build.ninja').exists():
            subprocess.run(['meson','setup',str(build),str(source),'--cross-file',str(a.work/'cross-x32.txt'),
                            '--buildtype=release','-Denable_d3d10=false','-Db_lto=false'],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['ninja','-C',str(build),'-j',str(a.jobs)], env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    out = ROOT/'dist/dxvk-batch'; stage = out/'x32'; stage.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in ('d3d9','d3d11','dxgi'):
        dll = build/'src'/name/(name+'.dll')
        shutil.copy2(dll, out/dll.name)
        subprocess.run([str(tc/'bin/llvm-strip'),'--strip-debug','-o',str(stage/dll.name),str(dll)], check=True)
        assert b'-sdbatch1' in (stage/dll.name).read_bytes()
        files[dll.name] = dict(sha256=sha(stage/dll.name), bytes=(stage/dll.name).stat().st_size,
                              raw_sha256=sha(dll))
    assert MARKER.encode() in (stage/'d3d11.dll').read_bytes()
    assert manifest(source) == prepared['source_files']
    assert manifest(BASE/'source') == baseline['source_files']
    write_json(out/'build.json', dict(build=BUILD, commit=baseline['commit'], inputs=prepared['inputs'],
        source_files=prepared['source_files'], changed=changed, files=files,
        hardware_tested=False, fps_gain_measured=False, native_runtime_unchanged=True,
        option='d3d11.sdSubmissionBatching', default_enabled=False,
        max_deferred_hint_chunks=12, min_pending_submissions=2,
        barriers_unchanged=True, required_flushes_unchanged=True, allocation_limits_unchanged=True))
    print('Built', BUILD, json.dumps(files), flush=True)


if __name__ == '__main__': main()
