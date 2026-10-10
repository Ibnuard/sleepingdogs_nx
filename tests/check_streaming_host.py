"""ASan/UBSan against exact native helpers and DXVK allocation functions."""
from pathlib import Path
import os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
WORK=Path('/home/blekjek/sleepingdogs-streaming-memory-v1')


def function(text,signature):
    start=text.index(signature);end=text.index('\n  }',start)+4
    return text[start:end]


def main():
    out=WORK/'host-check';out.mkdir(exist_ok=True)
    native=WORK/'native-source/wine-nx-probe/source'
    flags=['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-pie','-no-pie']
    exe=out/'gpu'
    subprocess.run(['cc','-std=gnu11','-pthread',*flags,'-I'+str(native),ROOT/'tests/streaming_gpu.c','-o',exe],check=True)
    checks=[subprocess.check_output([exe],text=True).strip()];print(checks[-1],flush=True)
    sources={}
    for label,source in [('baseline',Path('/home/blekjek/sleepingdogs-dxvk-memory-v2/source')),('candidate',WORK/'dxvk/source')]:
        memory=(source/'src/dxvk/dxvk_memory.cpp').read_text();header=(source/'src/dxvk/dxvk_memory.h').read_text()
        start=header.index('  struct DxvkMemoryPool {');pool=header[start:header.index('\n  };',start)+5]
        includes=out/(label+'-include');includes.mkdir(exist_ok=True)
        for name in ('dxvk_allocator.h','dxvk_allocator.cpp'):
            text=(source/'src/dxvk'/name).read_text().replace('#include "../util/util_env.h"',
                '#include "'+str(source/'src/util/util_bit.h')+'"\nnamespace dxvk::env { constexpr bool is32BitHostPlatform(){return true;} }')
            for n in ('util_bit.h','util_likely.h'):text=text.replace('../util/'+n,str(source/'src/util'/n))
            (includes/name).write_text(text)
        cpp=(ROOT/'tests/streaming_dxvk.cpp').read_text().replace('/* ACTUAL_POOL */',pool)
        for token,sig in [('ACTUAL_ALLOCATE','  Rc<DxvkResourceAllocation> DxvkMemoryAllocator::allocateMemory('),
                          ('ACTUAL_CHUNK','  bool DxvkMemoryAllocator::allocateChunkInPool(')]:
            cpp=cpp.replace('/* '+token+' */',function(memory,sig))
        file=out/(label+'.cpp');file.write_text(cpp);exe=out/label
        subprocess.run(['g++','-std=c++20',*flags,'-I'+str(includes),file,includes/'dxvk_allocator.cpp','-o',exe,
                        *(['-DBASELINE'] if label=='baseline' else [])],check=True)
        checks.append(subprocess.check_output([exe],text=True).strip());print(label+': '+checks[-1],flush=True)
        sources[label]={n:sha(source/n) for n in ('src/dxvk/dxvk_memory.cpp','src/dxvk/dxvk_allocator.cpp')}
    write_json(ROOT/'reports/streaming-host-check.json',{'status':'PASS','checks':checks,'sanitizers':['address','undefined'],
        'compiled_dxvk':sources,'compiled_native':{n:sha(native/n) for n in ('f1_gpu_arena.h','sd_gpu_stream.h')},
        'sources':{n:sha(ROOT/n) for n in ('tests/check_streaming_host.py','tests/streaming_gpu.c','tests/streaming_dxvk.cpp')},
        'scope':'Actual allocation functions/page allocator and native arena; Vulkan allocation, resource destructor and kernel boundaries modeled.',
        'hardware_tested':False})


if __name__=='__main__':main()
