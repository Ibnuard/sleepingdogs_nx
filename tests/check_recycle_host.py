"""Sanitize production DXVK dispatch/free/cache functions, with Vulkan modeled."""
from pathlib import Path
import argparse,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
def function(text,sig):
    start=text.index(sig);return text[start:text.index('\n  }',start)+4]
def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-buffer-reuse-v2'))
    work=p.parse_args().work;out=work/'checks';out.mkdir(exist_ok=True);results={}
    candidate=work/'source';candidate_header=(candidate/'src/dxvk/dxvk_memory.h').read_text()
    start=candidate_header.index('    // Global bound, not per memory type.')
    members=candidate_header[start:candidate_header.index('    void freeDeviceMemory(',start)]
    start=candidate_header.index('  enum class DxvkAllocationFlag');flags=candidate_header[start:candidate_header.index('\n  };',start)+5]
    for label,source in [('baseline',Path('/home/blekjek/sleepingdogs-streaming-memory-v1/dxvk/source')),('candidate',candidate)]:
        memory=(source/'src/dxvk/dxvk_memory.cpp').read_text();header=(source/'src/dxvk/dxvk_memory.h').read_text()
        include=out/(label+'-include');include.mkdir(exist_ok=True)
        for name in ('dxvk_allocator.h','dxvk_allocator.cpp'):
            text=(source/'src/dxvk'/name).read_text().replace('#include "../util/util_env.h"',
                '#include "'+str(source/'src/util/util_bit.h')+'"\nnamespace dxvk::env { constexpr bool is32BitHostPlatform(){return true;} }')
            for n in ('util_bit.h','util_likely.h'):text=text.replace('../util/'+n,str(source/'src/util'/n))
            (include/name).write_text(text)
        text=(ROOT/'tests/recycle_dxvk.cpp').read_text()
        start=header.index('  struct DxvkMemoryPool {');pool=header[start:header.index('\n  };',start)+5]
        for token,value in [('ACTUAL_POOL',pool),('ACTUAL_FLAGS',flags),('ACTUAL_CACHE_MEMBERS',members),
            ('ACTUAL_CACHE',(candidate/'src/dxvk/sd_dxvk_recycle.inc').read_text())]:text=text.replace('/* '+token+' */',value)
        funcs={'ACTUAL_ALLOCATE':'  Rc<DxvkResourceAllocation> DxvkMemoryAllocator::allocateMemory(',
            'ACTUAL_CHUNK':'  bool DxvkMemoryAllocator::allocateChunkInPool(',
            'ACTUAL_CREATE_DEDICATED':'  DxvkResourceAllocation* DxvkMemoryAllocator::createAllocation(\n          DxvkMemoryType&       type,\n    const DxvkDeviceMemory&',
            'ACTUAL_CREATE_POOLED':'  DxvkResourceAllocation* DxvkMemoryAllocator::createAllocation(\n          DxvkMemoryType&       type,\n          DxvkMemoryPool&',
            'ACTUAL_FREE':'  void DxvkMemoryAllocator::freeAllocation(',
            'ACTUAL_TRIM':'  void DxvkMemoryAllocator::freeEmptyChunksInHeap('}
        for token,sig in funcs.items():text=text.replace('/* '+token+' */',function(memory,sig))
        cpp=out/(label+'.cpp');cpp.write_text(text);exe=out/label
        command=['g++','-std=c++20','-O1','-g','-pthread','-fsanitize=address,undefined','-fno-sanitize-recover=all',
            '-fno-pie','-no-pie','-I'+str(include),'-I'+str(source/'src/util'),str(cpp),str(include/'dxvk_allocator.cpp'),'-o',str(exe)]
        if label=='baseline':command.append('-DBASELINE')
        with (out/(label+'-compile.log')).open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        result=subprocess.check_output([str(exe)],text=True,timeout=60);print(result,flush=True)
        results[label]={'result':result.strip(),'compiled_sources':{n:sha(source/n) for n in ('src/dxvk/dxvk_memory.cpp','src/dxvk/dxvk_allocator.cpp')}}
    write_json(ROOT/'reports/recycle-host-check.json',{'status':'PASS','results':results,'sanitizers':['address','undefined'],
        'helper_sha256':sha(candidate/'src/dxvk/sd_dxvk_recycle.inc'),
        'sources':{n:sha(ROOT/n) for n in ('tests/recycle_dxvk.cpp','tests/check_recycle_host.py','src/sd_dxvk_recycle.inc')},
        'scope':__doc__,'hardware_tested':False})
if __name__=='__main__':main()
