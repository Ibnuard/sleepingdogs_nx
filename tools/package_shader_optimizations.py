"""Package tested FEXTendo v9 with independent shader switches and immutable v8 rollback."""
from pathlib import Path
import argparse
import json
import zipfile
from port_common import ROOT, sha, write_json
from build_dxvk_memory import manifest
from build_shader_optimizations import V8_SHA
from sleepingdogs_shader_optimizations import BUILD, FILES
from package_named_pipe import PREFIX, archive, encode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    args=parser.parse_args()
    baseline=ROOT/'dist/sleepingdogs-fex-low-window-perf-counters.zip'
    assert sha(baseline)==V8_SHA
    with zipfile.ZipFile(baseline) as z:
        previous=json.loads(z.read('source/low-window-perf-counters/native.json'))
        entries={n:z.read(n) for n in z.namelist() if n.startswith(PREFIX)}
    out=ROOT/'dist/low-window-shader-optimizations'
    native=json.loads((out/'native.json').read_text())
    assert native['build']==BUILD and native['cpu_translator_unchanged']
    assert manifest(args.work/'native-source')==native['source_files']
    assert manifest(args.work/'fex-adapter')==native['adapter_files']==previous['adapter_files']
    for name,digest in native['build_inputs'].items():assert sha(ROOT/name)==digest,name
    changed={n for n,h in native['source_files'].items() if previous['source_files'].get(n)!=h}
    assert changed==FILES and not set(previous['source_files'])-set(native['source_files'])
    nro=out/'sleepingdogs-fex.nro'
    elf=ROOT/'local/symbols/sleepingdogs-low-window-v9.elf'
    assert sha(nro)==native['nro_sha256'] and sha(elf)==native['elf_sha256']
    reports={}
    for name in ('shaders','shader-abi','shader-binary','cpu-topology','sync-startup-binary','binary'):
        path=ROOT/'reports'/('low-window-v9-'+name+'.json')
        report=json.loads(path.read_text());assert report['status']=='PASS',name
        if 'elf_sha256' in report:assert report['elf_sha256']==native['elf_sha256'],name
        for f,digest in report.get('sources',{}).items():assert sha(ROOT/f.replace('\\','/'))==digest,(name,f)
        for f,digest in report.get('source_files',{}).items():assert native['source_files'][f]==digest,(name,f)
        reports[name]=report
    assert reports['shaders']['all_native_changes_match_overlay']
    assert reports['shader-abi']==native['shader_abi']
    assert reports['cpu-topology']['new_game']['worker_count']==4
    entries[PREFIX+nro.name]=nro.read_bytes()
    for name,payload in list(entries.items()):
        if name.endswith('.json'):
            receipt=json.loads(payload)
            if 'nro_sha256' in receipt:
                receipt.update(nro_sha256=native['nro_sha256'],additional_overlay=BUILD,hardware_tested=False)
                entries[name]=encode(receipt)
    for name in ('shader-affinity.txt','shader-cache.txt'):
        entries[PREFIX+name]=b'1\n'
    entries[PREFIX+'launcher/shader-optimizations.json']=encode(dict(build=BUILD,
        nro_sha256=native['nro_sha256'],shader_affinity=True,shader_allocation_cache=True,
        fex_port_origin=native['fex_port_origin'],performance_optimization=True,
        fps_gain_measured=False,hardware_tested=False))
    entries['README-INSTALL.txt']=(ROOT/'docs/low-window-shader-optimizations.md').read_bytes()
    prefix='source/low-window-shader-optimizations/'
    entries[prefix+'native.json']=encode(native)
    entries[prefix+'THIRD-PARTY.md']=(ROOT/'docs/PES13-THIRD-PARTY.md').read_bytes()
    entries[prefix+'COPYING.LIB']=(args.work/'native-source/COPYING.LIB').read_bytes()
    assert sha(args.work/'native-source/COPYING.LIB')==native['source_files']['COPYING.LIB']
    entries[prefix+'FEXTendo-adapter-LICENSE']=(args.work/'fex-adapter/LICENSE').read_bytes()
    for name in changed:
        entries[prefix+'native/'+name]=(args.work/'native-source'/name).read_bytes()
    # Retain the v8 fragments used by the host tests, with original receipt hashes.
    baseline_fragments=(FILES & set(previous['source_files'])) | {
        'wine-nx-probe/source/native_heap/fextendo_rust_symbols.h'}
    for name in sorted(baseline_fragments):
        path=ROOT/'local/shader-v9-v8-source'/name
        assert sha(path)==previous['source_files'][name],name
        entries[prefix+'local/shader-v9-v8-source/'+name]=path.read_bytes()
    inputs=set(native['build_inputs']) | {'tools/package_shader_optimizations.py',
        'tools/validate_shader_optimizations.py','tests/check_shader_optimizations.py',
        'tests/check_shader_binary.py','tests/shader_affinity.c','tests/shader_cache.c',
        'tests/check_perf_counters.py','tests/check_cpu_topology_binary.py',
        'tests/check_sync_startup_binary.py','tests/check_low_window_binary.py'}
    for name in inputs:entries[prefix+name]=(ROOT/name).read_bytes()
    for name,report in reports.items():entries[prefix+'reports/'+name+'.json']=encode(report)
    for name in entries:
        assert not name.endswith(('.dll','.exe','.nsp','.kip','.keys','.log'))
        assert not name.startswith(('atmosphere/','bootloader/','forwarder/'))
        if name.startswith(PREFIX):
            assert '/drive_c/' not in name
            assert name in (PREFIX+nro.name,PREFIX+'performance-counters.txt',
                PREFIX+'shader-affinity.txt',PREFIX+'shader-cache.txt') or name.endswith('.json') or name.startswith(PREFIX+'launcher/presets/performance/')
    update=archive(ROOT/'dist/sleepingdogs-fex-low-window-shader-optimizations.zip',entries)
    stage=ROOT/'dist/sleepingdogs-fex-low-window-shader-optimizations'
    for name,payload in entries.items():
        if name.startswith(PREFIX) or name=='README-INSTALL.txt':
            path=stage/name;path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():assert path.read_bytes()==payload,f'Preserve existing file: {path}'
            else:path.write_bytes(payload)
    result=dict(status='PASS',update=update,build=BUILD,nro_sha256=native['nro_sha256'],
        elf_sha256=native['elf_sha256'],changed_native_files=sorted(changed),
        baseline_sha256=V8_SHA,baseline_preserved=sha(baseline)==V8_SHA,game_files_changed=[],
        fex_and_dxvk_unchanged=True,shader_affinity_enabled=True,shader_cache_enabled=True,
        synchronization_backend_unchanged=True,hardware_tested=False,performance_optimization=True,
        fps_gain_measured=False,graphics_undefined_fixed=False,
        reports={name:sha(ROOT/'reports'/('low-window-v9-'+name+'.json')) for name in reports})
    write_json(ROOT/'reports/low-window-shader-optimizations-package.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
