"""ASan/UBSan checks of the shipped and candidate DXVK allocator source."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from port_common import sha, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-dxvk-memory-v2'))
    args = parser.parse_args(); work = args.work
    output = work / 'checks'; output.mkdir(exist_ok=True)
    results = {}
    for label, source in [('baseline', Path('/home/blekjek/f1-dxvk-compact-chunks/source')),
                          ('candidate', work / 'source')]:
        memory = (source / 'src/dxvk/dxvk_memory.cpp').read_text()
        header = (source / 'src/dxvk/dxvk_memory.h').read_text()
        start = memory.index('  bool DxvkMemoryAllocator::allocateChunkInPool(')
        end = memory.index('\n  }', start) + 4
        function = memory[start:end]
        start = header.index('  struct DxvkMemoryPool {')
        pool = header[start:header.index('\n  };', start)+5]
        includes = output / (label + '-includes'); includes.mkdir(exist_ok=True)
        # Only replace transitive platform includes. Allocator implementation
        # and every constant remain the pinned production code.
        for name in ('dxvk_allocator.h','dxvk_allocator.cpp'):
            text = (source / 'src/dxvk' / name).read_text()
            text = text.replace('#include "../util/util_env.h"',
                '#include "'+str(source / 'src/util/util_bit.h')+'"\n'
                'namespace dxvk::env { constexpr bool is32BitHostPlatform() { return sizeof(void*)==4; } }')
            for utility in ('util_bit.h','util_likely.h'):
                text = text.replace('../util/'+utility, str(source / 'src/util' / utility))
            (includes / name).write_text(text)
        text = (ROOT / 'tests/dxvk_memory.cpp').read_text()
        text = text.replace('/* ACTUAL_DXVK_MEMORY_POOL */',pool).replace('/* ACTUAL_ALLOCATE_CHUNK */',function)
        cpp, exe = output / (label+'.cpp'), output / label
        cpp.write_text(text)
        cmd = ['g++','-std=c++20','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-pie','-no-pie',
               '-I'+str(includes),str(cpp),str(includes/'dxvk_allocator.cpp'),'-o',str(exe)]
        if label == 'baseline':cmd += ['-DBASELINE']
        subprocess.run(cmd,check=True)
        run = subprocess.check_output([str(exe)],text=True)
        results[label] = {'output':run.strip(), 'function_sha256':hashlib.sha256(function.encode()).hexdigest(),
                         'page_allocator_sha256':sha(source/'src/dxvk/dxvk_allocator.cpp')}
    # Prove the old deferred Map dereferences a missing allocation, and that
    # both new callers correctly handle the same allocation failure.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    map_results = {}
    for label, source in [('baseline', Path('/home/blekjek/f1-dxvk-compact-chunks/source')),
                          ('candidate', work / 'source')]:
        original = (source / 'src/d3d11/d3d11_context_def.cpp').read_text()
        text = (ROOT / 'tests/dxvk_deferred_map.cpp').read_text()
        for token, name, result in [('ACTUAL_MAP_BUFFER','MapBuffer','HRESULT'),
                                    ('ACTUAL_UPDATE_BUFFER','UpdateMappedBuffer','void')]:
            start = original.index('  '+result+' D3D11DeferredContext::'+name+'(')
            function = original[start:original.index('\n  }',start)+4]
            text = text.replace('/* '+token+' */',function)
        cpp,exe=output/(label+'-map.cpp'),output/(label+'-map')
        cpp.write_text(text)
        subprocess.run(['g++','-std=c++20','-O1','-g','-fsanitize=address,undefined',
            '-fno-sanitize-recover=all','-fno-pie','-no-pie',str(cpp),'-o',str(exe)],check=True)
        run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=20)
        if label=='baseline':
            assert run.returncode!=0 and 'null pointer' in run.stderr,run
            map_results[label]='Reproduced null pointer on failed resource allocation under UBSan'
        else:
            assert run.returncode==0,run
            map_results[label]=run.stdout.strip()
    write_json(ROOT / 'reports/dxvk-memory-host-check.json', {'status':'PASS','results':results,'deferred_map':map_results,
        'sources':{n:sha(ROOT/n) for n in ('tools/sleepingdogs_dxvk_memory.py','tests/dxvk_memory.cpp','tests/dxvk_deferred_map.cpp','tests/check_dxvk_memory_host.py')},
        'limits':'Vulkan allocation and mapping modeled; pressure workload synthetic; no hardware boot claim.'})
    print(json.dumps(results))


if __name__ == '__main__': main()
