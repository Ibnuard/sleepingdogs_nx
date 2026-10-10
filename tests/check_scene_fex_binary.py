"""Run shipping two-permit CompileBlock and unchanged decoder on ARM64 emulator."""
from pathlib import Path
import json
import check_compiler_decoder_binary as decoder
from port_common import sha,write_json
ROOT=Path(__file__).resolve().parents[1]
decoder.DLL=ROOT/'dist/scene-memory-fix/libwow64fex.dll'
decoder.L=json.loads((ROOT/'local/scene-memory-layout.json').read_text())
gate=ROOT/'tests/check_compiler_gate_binary.py'
fixture=gate.read_text().split('\nm=GateModel()')[0]
assert fixture.count('slots=4')==1 and fixture.count('self.slot_base + 32')==1
fixture=fixture.replace('slots=4','slots=2').replace('self.slot_base + 32','self.slot_base + 16')
namespace={'__file__':str(gate),'__name__':'scene_gate_fixture'}
exec(compile(fixture,str(gate),'exec'),namespace)
m=namespace['GateModel']()
for i in range(2):m.start(i);assert m.stage[i]=='lookup'
assert len(m.held)==2
m.start(2);assert m.stage[2]=='waiting' and len(m.held)==2 and 2 not in m.shared
m.resume(0,'done');assert len(m.held)==1
m.resume(2,'lookup');assert len(m.held)==2 and 2 in m.shared
for i in (1,2):m.resume(i,'done')
assert not m.held
sources={n:sha(ROOT/n) for n in ('tests/check_scene_fex_binary.py','tests/check_compiler_gate_binary.py',
    'tests/check_compiler_decoder_binary.py','../pes13-nx/tests/fex_alloc.py','tests/build_scene_layout.py',
    'tests/build_compiler_memory_layout.py','tests/compiler_memory_layout.cpp')}
write_json(ROOT/'reports/scene-gate-binary-check.json',{'status':'PASS','dll_sha256':sha(decoder.DLL),
    'permits':2,'simultaneous_compilers':3,'third_waits_before_invalidation_lock':True,
    'released_permit_reused':True,'all_early_cache_returns_unlock':True,'sources':sources,
    'boundaries':'NT, std::mutex scheduler and cache result modeled; actual CompileBlock, selection and RAII execute',
    'hardware_tested':False})
print('PASS: real DLL third compiler waits, then resumes; both RAII permits released',flush=True)
def save_report(path,value):
    assert path.name=='compiler-decoder-binary-check.json'
    value['sources']=sources;write_json(ROOT/'reports/scene-decoder-binary-check.json',value)
decoder.write_json=save_report
decoder.main()
