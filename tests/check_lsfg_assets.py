"""Validate converted SPIR-V bindings and the actual C++ pack reader."""
from pathlib import Path
import json, re, struct, subprocess, sys, os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from port_common import sha,write_json
from build_lsfg_backend import WORK

def main():
    report=json.loads((ROOT/'reports/lsfg-shader-conversion.json').read_text())
    registry=(WORK/'backend/lsfg-vk-backend/src/extraction/shader_registry.cpp').read_text()
    expected={256:(5,1,1,2)}
    for perf,part in enumerate(registry.split('#define PERF true')):
        for m in re.finditer(r'SHADER\((\d+), (\d+), (\d+), (\d+), (\d+)\)',part):
            rid,sampled,storage,buffers,samplers=map(int,m.groups())
            expected[rid+23*perf]=(sampled,storage,buffers,samplers)
    assert len(expected)==45
    for record in report['records']:
        rid=record['dll_resource'];a,b,c,d=expected[rid]
        assert record['bindings']==sorted([*range(c),*range(16,16+d),*range(32,32+a),*range(48,48+b)]),rid
        assert set(record['capabilities'])<={1,50,56,5345},rid
        subprocess.run(['spirv-val','--target-env','vulkan1.3',str(ROOT/f'local/lsfg-shaders-v15/{rid}.spv')],check=True)
    # Exercise the same reader compiled into the Switch binary, under sanitizers.
    source=WORK/'check-pack.cpp';source.write_text('''#include "sd_lsfg_pack.hpp"
#include <iostream>
int main(int n,char** v){try{auto data=sd_lsfg_read_pack(v[1]);return data.size()==45?0:2;}
catch(const std::exception& e){std::cerr<<e.what()<<"\\n";return 1;}}
''')
    exe=WORK/'check-pack'
    subprocess.run(['c++','-std=c++20','-O1','-g','-fsanitize=address,undefined',
        '-fno-sanitize-recover=all','-I'+str(ROOT/'tools'),str(source),'-o',str(exe)],check=True)
    original=(ROOT/'local/lsfg-shaders-v15/lsfg-3.1.sdp').read_bytes()
    cases={'valid':original,'empty':b'', 'truncated':original[:-1], 'wrong-version':original[:8]+b'\x02'+original[9:],
        'corrupt-shader':original[:200]+bytes([original[200]^1])+original[201:],
        'excess-data':original+b'\0','huge-shader':original[:52]+b'\xff'*4+original[56:]}
    results={}
    for name,data in cases.items():
        path=WORK/(name+'.sdp');path.write_bytes(data)
        p=subprocess.run([str(exe),str(path)],capture_output=True,text=True)
        assert p.returncode==(0 if name=='valid' else 1),(name,p.stdout,p.stderr)
        assert 'Sanitizer' not in p.stderr,p.stderr
        results[name]=p.stderr.strip() or 'accepted'
    write_json(ROOT/'reports/lsfg-assets-check.json',dict(status='PASS',shader_count=45,
        bindings_match_actual_backend=True,spirv_validation='Vulkan 1.3',reader_cases=results,
        pack_sha256=sha(ROOT/'local/lsfg-shaders-v15/lsfg-3.1.sdp'),hardware_tested=False))
    print('PASS: 45 SPIR-V shaders, exact backend bindings, 7 pack-reader cases')

if __name__=='__main__':main()
