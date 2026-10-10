"""Build the pinned DXVK stream-reuse variant without changing NRO/FEX."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from port_common import ROOT,sha,write_json
from build_dxvk_memory import manifest
from sleepingdogs_dxvk_recycle import apply,FILES,MARKER

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-buffer-reuse-v2'))
    p.add_argument('--jobs',type=int,default=4);a=p.parse_args();work=a.work.resolve();work.mkdir(parents=True,exist_ok=True)
    previous=Path('/home/blekjek/sleepingdogs-streaming-memory-v1/dxvk')
    baseline=json.loads((ROOT/'dist/streaming-memory-fix/dxvk.json').read_text())
    assert manifest(previous/'source')==baseline['source_files']
    source=work/'source';build=work/'build-x32';stamp=work/'prepared.json'
    inputs={'base':baseline['source_files'],'patch_sha256':sha(ROOT/'tools/sleepingdogs_dxvk_recycle.py'),
        'helper_sha256':sha(ROOT/'src/sd_dxvk_recycle.inc'),'builder_sha256':sha(Path(__file__)),
        'cross_sha256':sha(previous/'cross-x32.txt')}
    if not stamp.exists():
        assert not source.exists(),'Use a fresh work directory'
        shutil.copytree(previous/'source',source,symlinks=True);apply(source)
        shutil.copy2(previous/'cross-x32.txt',work/'cross-x32.txt')
        write_json(stamp,{'inputs':inputs,'source_files':manifest(source)})
    prepared=json.loads(stamp.read_text());assert prepared['inputs']==inputs
    assert manifest(source)==prepared['source_files']
    changed={n:h for n,h in prepared['source_files'].items() if inputs['base'].get(n)!=h}
    assert set(changed)==set(FILES)
    tc=Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64')
    shaders=Path('/home/blekjek/f1-dxvk-small-chunks/shader-tools/usr/bin')
    env=dict(os.environ,PATH=str(tc/'bin')+os.pathsep+str(shaders)+os.pathsep+os.environ['PATH'])
    with (work/'build.log').open('a') as log:
        if not (build/'build.ninja').exists():
            subprocess.run(['meson','setup',str(build),str(source),'--cross-file',str(work/'cross-x32.txt'),
                '--buildtype=release','-Denable_d3d10=false','-Db_lto=false'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['ninja','-C',str(build),'-j',str(a.jobs)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    out=ROOT/'dist/buffer-reuse-fix';stage=out/'x32';stage.mkdir(parents=True,exist_ok=True);files={}
    for name in ('d3d9','d3d11','dxgi'):
        dll=build/'src'/name/(name+'.dll');shutil.copy2(dll,out/dll.name)
        subprocess.run([str(tc/'bin/llvm-strip'),'--strip-debug','-o',str(stage/dll.name),str(dll)],check=True)
        assert MARKER.encode() in (stage/dll.name).read_bytes()
        files[dll.name]={'sha256':sha(stage/dll.name),'bytes':(stage/dll.name).stat().st_size,'raw_sha256':sha(dll)}
    write_json(out/'build.json',{'build':'sleepingdogs-dxvk-sdrecycle1','commit':baseline['commit'],
        'inputs':inputs,'source_files':prepared['source_files'],'changed':changed,'files':files,
        'max_idle_bytes':16777216,'max_idle_count':4,'resource_sizes_unchanged':True,'hardware_tested':False})
    print(json.dumps(files),flush=True)

if __name__=='__main__':main()
