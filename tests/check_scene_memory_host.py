"""Sanitize two-workspace scheduling with actual FEX pools and compiler permits."""
from pathlib import Path
import argparse,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-scene-memory-v1'))
a=p.parse_args();fex=a.work/'fex';source=fex/'source';out=a.work/'host-check';out.mkdir(exist_ok=True)
command=['g++','-std=c++20','-O1','-g','-pthread','-DASSERTIONS_ENABLED=1','-DFMT_HEADER_ONLY',
    '-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-pie','-no-pie',
    '-I'+str(source/'FEXCore/include'),'-I'+str(source/'External/fmt/include'),
    '-I'+str(source/'FEXHeaderUtils'),'-I'+str(fex/'adapter'),
    str(ROOT/'tests/scene_memory_host.cpp'),'-o',str(out/'scene-memory')]
with (out/'scene-compile.log').open('w') as log:
    subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,TMPDIR=str(out)))
result=subprocess.check_output([str(out/'scene-memory')],text=True,timeout=60)
write_json(ROOT/'reports/scene-host-check.json',{'status':'PASS','sanitizers':['address','undefined'],
    'results':result.splitlines(),'threads':32,'paired_compiler_lifetimes':8000,'permits':2,
    'pool_source_sha256':sha(source/'FEXCore/include/FEXCore/Utils/ThreadPoolAllocator.h'),
    'header_sha256':sha(fex/'adapter/sd_fex_workspace.h'),
    'sources':{n:sha(ROOT/n) for n in ('tests/scene_memory_host.cpp','tests/check_scene_memory_host.py')},
    'scope':'Production pools/permits with POSIX heap; not a Horizon scheduler test','hardware_tested':False})
print(result)
