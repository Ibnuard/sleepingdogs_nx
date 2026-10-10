"""Derive x86 replay offsets from the exact production DXVK compiler command."""
from pathlib import Path
import argparse,json,shlex,struct,subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-buffer-reuse-v2'))
work=p.parse_args().work
(work/'checks').mkdir(exist_ok=True)
entry=next(c for c in json.loads((work/'build-x32/compile_commands.json').read_text()) if c['file'].endswith('/dxvk_memory.cpp'))
flags=shlex.split(entry['command'])
for opt in ('-o','-c','-MF','-MT','-MQ'):
    if opt in flags:i=flags.index(opt);del flags[i:i+2]
flags=[v for v in flags if v not in ('-MD','-MMD')]
obj=work/'checks/layout.obj'
flags+=['-fno-access-control','-Wno-invalid-offset-of','-c',str(ROOT/'tests/recycle_layout.cpp'),'-o',str(obj)]
with (work/'checks/layout-compile.log').open('w') as log:subprocess.run(flags,cwd=entry['directory'],stdout=log,stderr=subprocess.STDOUT,check=True)
data=obj.read_bytes();machine,count=struct.unpack_from('<HH',data);assert machine==0x14c
optional=struct.unpack_from('<H',data,16)[0]
for i in range(count):
    at=20+optional+i*40
    if data[at:at+8].rstrip(b'\0')==b'.sdmeta':
        size,offset=struct.unpack_from('<II',data,at+16);values=struct.unpack_from('<'+'I'*(size//4),data,offset);break
else:raise RuntimeError('No metadata')
names=('allocator_size cache cache_bytes hits types type_masks type_size type_heap type_stats type_usage heap_size heap_types heap_index stats_allocated stats_used '
       'allocation_size count flags cookie memory size map buffer image kmt_local kmt_global sparse type allocator views '
       'info_size info_cookie info_properties info_mode req_size req_bytes req_alignment req_types device_memory_size info_handle').split()
assert len(names)==len(values)
target=ROOT/'local/recycle-layout.json';target.write_text(json.dumps(dict(zip(names,values)),indent=2)+'\n');print(target)
