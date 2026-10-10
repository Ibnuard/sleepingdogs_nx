"""Build bounded, opt-in v15 batching using the already proven DXVK/FEX ABI."""
from pathlib import Path
import os,json,shutil,subprocess
from port_common import ROOT,sha,write_json
from build_dxvk_memory import manifest
BASE=Path('/home/blekjek/sleepingdogs-dxvk-batch-v1')
WORK=Path('/home/blekjek/sleepingdogs-dxvk-native-v15')
DEST=ROOT/'local/dxvk-native-v15'
FILES={'src/util/util_flush.cpp','src/d3d11/d3d11_context_imm.cpp','version.h.in'}

def prepare():
    prior=json.loads((BASE/'prepared.json').read_text())
    assert manifest(BASE/'source')==prior['source_files']
    WORK.mkdir(exist_ok=True)
    if not (WORK/'source').exists():shutil.copytree(BASE/'source',WORK/'source',symlinks=True)
    # Each edited file is restored from the pinned v12 input on every prepare.
    for rel in FILES:
        text=(BASE/'source'/rel).read_text()
        if rel.endswith('util_flush.cpp'):
            assert text.count('chunkCount < 12u')==1
            text=text.replace('chunkCount < 12u','chunkCount < 24u')
            text=text.replace('batch only small automatic hints','batch bounded automatic hints')
        elif rel.endswith('d3d11_context_imm.cpp'):
            text=text.replace('[SD-DXVK-BATCH] v1','[SD-DXVK-BATCH] v2')
            text=text.replace('hint_chunks=12','hint_chunks=24')
        else:text=text.replace('-sdbatch1','-sdbatch2')
        (WORK/'source'/rel).write_text(text)
    shutil.copy2(BASE/'cross-x32.txt',WORK/'cross-x32.txt')
    candidate=manifest(WORK/'source')
    assert {n for n,h in candidate.items() if prior['source_files'].get(n)!=h}==FILES
    write_json(WORK/'prepared.json',dict(baseline=prior['source_files'],source_files=candidate,
        changes={n:candidate[n] for n in sorted(FILES)}))
    return candidate

def main():
    candidate=prepare()
    tc=Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64')
    shaders=Path('/home/blekjek/f1-dxvk-small-chunks/shader-tools/usr/bin')
    env=dict(os.environ,PATH=str(tc/'bin')+os.pathsep+str(shaders)+os.pathsep+os.environ['PATH'])
    build=WORK/'build-x32'
    with (WORK/'build.log').open('w') as log:
        if not (build/'build.ninja').exists():
            subprocess.run(['meson','setup',str(build),str(WORK/'source'),'--cross-file',str(WORK/'cross-x32.txt'),
                '--buildtype=release','-Denable_d3d10=false','-Db_lto=false'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['ninja','-C',str(build),'-j4'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    DEST.mkdir(exist_ok=True);files={}
    for name in ('d3d9','d3d11','dxgi'):
        source=build/'src'/name/(name+'.dll');output=DEST/source.name
        subprocess.run([str(tc/'bin/llvm-strip'),'--strip-debug','-o',str(output),str(source)],check=True)
        files[output.name]=dict(sha256=sha(output),bytes=output.stat().st_size)
        assert b'-sdbatch2' in output.read_bytes()
    assert b'[SD-DXVK-BATCH] v2' in (DEST/'d3d11.dll').read_bytes()
    assert manifest(WORK/'source')==candidate
    write_json(DEST/'build.json',dict(status='BUILT',files=files,source_files=candidate,
        changes={n:candidate[n] for n in sorted(FILES)},
        option='d3d11.sdSubmissionBatching',max_deferred_hint_chunks=24,min_pending_submissions=2,
        present_map_query_flushes_unchanged=True,barriers_unchanged=True,cost_limit_unchanged=True,
        fex_unchanged=True,hardware_tested=False,fps_gain_measured=False))
    print('BUILT DXVK 3.1.1-sdbatch2',files,flush=True)

if __name__=='__main__':main()
