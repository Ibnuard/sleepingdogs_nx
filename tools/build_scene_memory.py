"""Build a source-pinned two-workspace FEX/native pair without changing Fastest."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from port_common import ROOT,DEFAULT_GAME,GAME_EXE,sha,write_json
from build_launcher import prepare,build_nro
from build_gpu_pressure import FILES,ADAPTER_FILES
from sleepingdogs_fault_trace import apply as apply_faults
from sleepingdogs_scene_memory import apply_fex,FEX_MARKER,NATIVE_MARKER,RESERVE_BYTES
from build_dxvk_memory import manifest


def native(work,out,jobs):
    source,metadata=prepare(work,DEFAULT_GAME/GAME_EXE)
    stamp=work/'fault-prepared.json'
    if not stamp.exists():
        apply_faults(source);write_json(stamp,{n:sha(source/n) for n in FILES})
    for n,digest in json.loads(stamp.read_text()).items():assert sha(source/n)==digest,n
    elf,nro=build_nro(work,source,Path('/home/blekjek/pes13-build'),jobs)
    for marker in (NATIVE_MARKER.encode(),b'[SD-GPU-PRESSURE] v1',b'fastest'):
        assert marker in nro.read_bytes(),marker
    shutil.copy2(nro,out/nro.name);shutil.copy2(elf,ROOT/'local/symbols/sleepingdogs-scene-memory.elf')
    write_json(out/'native.json',{'build':'sleepingdogs-scene-memory-v1','nro_sha256':sha(nro),'elf_sha256':sha(elf),
        'game':metadata,'scratch_reserve_bytes':RESERVE_BYTES,'compile_slots':2,
        'source_files':{n:sha(source/n) for n in FILES},
        'adapter_files':{n:sha(work/'fex-adapter'/n) for n in ADAPTER_FILES},
        'prepared':json.loads((work/'sleepingdogs-prepared.json').read_text()),'hardware_tested':False})
    print('Scene memory native:',sha(nro),flush=True)


def fex(work,out,jobs):
    previous=Path('/home/blekjek/sleepingdogs-compiler-memory-v2/fex')
    old=json.loads((ROOT/'dist/compiler-memory-fix/fex.json').read_text())
    for n,digest in old['source_changes'].items():assert sha(previous/'source'/n)==digest,n
    for n,digest in old['adapter_files'].items():assert sha(previous/'adapter'/n)==digest,n
    identity={'source':manifest(previous/'source'),'adapter':manifest(previous/'adapter'),
        'patch_sha256':sha(ROOT/'tools/sleepingdogs_scene_memory.py'),'builder_sha256':sha(Path(__file__))}
    folder=work/'fex';folder.mkdir(exist_ok=True);source=folder/'source';adapter=folder/'adapter'
    stamp=folder/'prepared.json'
    if not stamp.exists():
        assert not source.exists(),'Use a fresh work tree'
        shutil.copytree(previous/'source',source,symlinks=True)
        shutil.copytree(previous/'adapter',adapter)
        apply_fex(source,adapter)
        write_json(stamp,{'inputs':identity,'source':manifest(source),'adapter':manifest(adapter)})
    prepared=json.loads(stamp.read_text());assert prepared['inputs']==identity
    assert prepared['source']==manifest(source) and prepared['adapter']==manifest(adapter)
    changes={n:h for n,h in prepared['source'].items() if identity['source'].get(n)!=h}
    adapter_changes={n:h for n,h in prepared['adapter'].items() if identity['adapter'].get(n)!=h}
    assert set(changes)=={'Source/Windows/WOW64/Module.cpp'}
    assert set(adapter_changes)=={'sd_fex_workspace.h'}
    dep=Path('/home/blekjek/pes13-build');tc=dep/'toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64'
    build=folder/'build';temp=folder/'tmp';temp.mkdir(exist_ok=True)
    env=dict(os.environ,PATH=str(tc/'bin')+os.pathsep+os.environ['PATH'],TMPDIR=str(temp))
    with (folder/'build.log').open('a') as log:
        if not (build/'build.ninja').exists():
            subprocess.run(['cmake','-S',str(source),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
                '-DCMAKE_TOOLCHAIN_FILE='+str(source/'Data/CMake/toolchain_mingw.cmake'),'-DMINGW_TRIPLE=aarch64-w64-mingw32',
                '-DENABLE_LTO=OFF','-DBUILD_TESTING=OFF','-DENABLE_JEMALLOC_GLIBC_ALLOC=OFF','-DENABLE_ASSERTIONS=OFF',
                '-DENABLE_CCACHE=OFF','-DENABLE_OFFLINE_TELEMETRY=OFF','-DENABLE_GDB_SYMBOLS=OFF','-DRANGES_NATIVE=OFF',
                '-DTUNE_CPU=cortex-a57','-DTUNE_ARCH=armv8-a','-DOVERRIDE_VERSION=sleepingdogs-fex-scene1',
                '-DOVERRIDE_HASH='+old['inputs']['pin'],'-DPES13_HORIZON_DIR='+str(adapter)],
                env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['cmake','--build',str(build),'--target','wow64fex','-j',str(jobs)],
            env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    dll=build/'Bin/libwow64fex.dll';assert FEX_MARKER.encode() in dll.read_bytes()
    shutil.copy2(dll,out/dll.name)
    write_json(out/'fex.json',{'build':'sleepingdogs-compiler-memory-v2','inputs':identity,
        'source_files':prepared['source'],'adapter_files':prepared['adapter'],'source_changes':changes,'adapter_changes':adapter_changes,
        'dll_sha256':sha(dll),'dll_bytes':dll.stat().st_size,'previous_dll_sha256':old['dll_sha256'],
        'compile_slots':2,'ir_bytes_unchanged':16777216,'decoder_default_bytes':65536,'profile':'fastest (unchanged)',
        'hardware_tested':False})
    print('Scene memory FEX:',sha(dll),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-scene-memory-v1'))
    p.add_argument('--component',choices=('native','fex'),required=True);p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args();work=a.work.resolve();work.mkdir(exist_ok=True,parents=True)
    out=ROOT/'dist/scene-memory-fix';out.mkdir(exist_ok=True)
    (native if a.component=='native' else fex)(work,out,a.jobs)


if __name__=='__main__':main()
