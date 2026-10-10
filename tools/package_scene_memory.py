"""Package a verified two-workspace NRO/FEX pair with all earlier fixes."""
from pathlib import Path
import argparse,json,shutil,tempfile,zipfile
from port_common import ROOT,sha,write_json
from package_named_pipe import PREFIX,archive,encode
from build_gpu_pressure import FILES,ADAPTER_FILES
from build_dxvk_memory import manifest
from sleepingdogs_scene_memory import apply_native,apply_fex,NATIVE_MARKER,FEX_MARKER,RESERVE_BYTES

REPORTS=('scene-host-check','scene-native-binary-check','scene-gate-binary-check',
         'scene-decoder-binary-check','scene-debug-regression')
SOURCES=('tools/sleepingdogs_scene_memory.py','tools/build_scene_memory.py','tools/package_scene_memory.py',
    'tools/analyze_scene_memory.py','tools/sleepingdogs_overlay.py','tools/build_launcher.py','tools/verify_package.py',
    'tests/scene_memory_host.cpp','tests/check_scene_memory_host.py','tests/check_scene_native_binary.py',
    'tests/check_gpu_budget_binary.py','tests/native_heap_binary.py','tests/check_scene_fex_binary.py',
    'tests/check_compiler_decoder_binary.py','tests/check_compiler_gate_binary.py','tests/build_scene_layout.py',
    'tests/build_compiler_memory_layout.py','tests/compiler_memory_layout.cpp','tests/check_fex_debug_binary.py',
    'tests/check_scene_memory_package.py','tests/check_scene_launcher.py','tests/check_streaming_launcher.py',
    'tests/check_renderer_package.py','docs/scene-memory-fix.md','reports/scene-memory-analysis.json','README.md','LICENSE')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-scene-memory-v1'))
    work=p.parse_args().work;out=ROOT/'dist/scene-memory-fix'
    native=json.loads((out/'native.json').read_text());fex=json.loads((out/'fex.json').read_text())
    assert sha(out/'sleepingdogs-fex.nro')==native['nro_sha256']
    assert sha(out/'libwow64fex.dll')==fex['dll_sha256']
    assert sha(ROOT/'local/symbols/sleepingdogs-scene-memory.elf')==native['elf_sha256']
    assert NATIVE_MARKER.encode() in (out/'sleepingdogs-fex.nro').read_bytes()
    assert FEX_MARKER.encode() in (out/'libwow64fex.dll').read_bytes()
    assert sha(ROOT/'tools/sleepingdogs_scene_memory.py')==fex['inputs']['patch_sha256']
    assert sha(ROOT/'tools/build_scene_memory.py')==fex['inputs']['builder_sha256']
    for field,folder in (('source_files','native-source'),('adapter_files','fex-adapter')):
        for n,digest in native[field].items():assert sha(work/folder/n)==digest,n
    assert manifest(work/'fex/source')==fex['source_files']
    assert manifest(work/'fex/adapter')==fex['adapter_files']
    prior=ROOT/'dist/sleepingdogs-fex-gpu-pressure-fix.zip'
    assert sha(prior)=='5e638baccba90ea1a62a7542753b810602c422a60e7865af01c4de5bc9ef8e6b'
    with zipfile.ZipFile(prior) as z:
        old={n:z.read(n) for n in z.namelist() if n not in ('README.txt','SHA256SUMS.txt')}
    previous=json.loads(old['source/gpu-pressure-fix/native.json'])
    base=Path('/home/blekjek/sleepingdogs-gpu-pressure-v1')
    old_fex=Path('/home/blekjek/sleepingdogs-compiler-memory-v2/fex')
    assert manifest(old_fex/'source')==fex['inputs']['source']
    assert manifest(old_fex/'adapter')==fex['inputs']['adapter']
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);ns=root/'native';na=root/'native-adapter';na.mkdir()
        for n in FILES:
            src=base/'native-source'/n;assert sha(src)==previous['source_files'][n]
            dst=ns/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        for n in ADAPTER_FILES:
            src=base/'fex-adapter'/n;assert sha(src)==previous['adapter_files'][n];shutil.copy2(src,na/n)
        apply_native(ns,na)
        for n in FILES:assert sha(ns/n)==native['source_files'][n],n
        for n in ADAPTER_FILES:assert sha(na/n)==native['adapter_files'][n],n
        fs=root/'fex';fa=root/'fex-adapter';fa.mkdir()
        for n in fex['source_changes']:
            dst=fs/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old_fex/'source'/n,dst)
        for n in fex['adapter_changes']:shutil.copy2(old_fex/'adapter'/n,fa/n)
        apply_fex(fs,fa)
        for n,digest in fex['source_changes'].items():assert sha(fs/n)==digest,n
        for n,digest in fex['adapter_changes'].items():assert sha(fa/n)==digest,n
    assert set(fex['source_changes'])=={'Source/Windows/WOW64/Module.cpp'}
    assert set(fex['adapter_changes'])=={'sd_fex_workspace.h'}
    # No other FEX source or adapter file may change outside that reconstruction.
    for field,original,allowed in (('source_files','source',fex['source_changes']),('adapter_files','adapter',fex['adapter_changes'])):
        assert set(fex[field])==set(fex['inputs'][original])
        for n,digest in fex[field].items():
            if n not in allowed:assert digest==fex['inputs'][original][n],n
    checks={}
    for name in REPORTS:
        report=json.loads((ROOT/'reports'/(name+'.json')).read_text())
        if name=='scene-debug-regression':assert report['actual_dll_emitter_cases']==67
        else:assert report['status']=='PASS',name
        if 'dll_sha256' in report:assert report['dll_sha256']==fex['dll_sha256'],name
        for n,digest in report.get('sources',{}).items():assert sha(ROOT/n)==digest,n
        checks[name]=report
    assert checks['scene-native-binary-check']['native_elf_sha256']==native['elf_sha256']
    assert checks['scene-native-binary-check']['previous_native_elf_sha256']==previous['elf_sha256']
    assert checks['scene-host-check']['header_sha256']==fex['adapter_files']['sd_fex_workspace.h']
    assert checks['scene-host-check']['pool_source_sha256']==fex['source_files']['FEXCore/include/FEXCore/Utils/ThreadPoolAllocator.h']
    entries=dict(old);nro=PREFIX+'sleepingdogs-fex.nro';dll=PREFIX+'drive_c/windows/system32/libwow64fex.dll'
    changed={nro,dll};entries[nro]=(out/'sleepingdogs-fex.nro').read_bytes();entries[dll]=(out/'libwow64fex.dll').read_bytes()
    for name in ('direct-arena-fix','first-fault-trace','named-pipe-fix','dep-policy-fix','debug-cache-fix',
        'thread-debug-fix','memory-budget-fix','compiler-memory-fix','gpu-budget-fix','streaming-memory-fix','gpu-pressure-fix'):
        key=PREFIX+'launcher/'+name+'.json';receipt=json.loads(entries[key])
        receipt['nro_sha256']=native['nro_sha256'];receipt['additional_overlay']='launcher/scene-memory-fix.json'
        if name=='compiler-memory-fix':
            receipt.update(build='sleepingdogs-compiler-memory-v2',dll_sha256=fex['dll_sha256'],compile_slots=2,
                scratch_reserve_bytes=RESERVE_BYTES,previous_nro_sha256=previous['nro_sha256'],
                previous_dll_sha256=fex['previous_dll_sha256'])
        entries[key]=encode(receipt);changed.add(key)
    policy=json.loads(old[PREFIX+'launcher/fex-memory-policy.json'])
    policy.update(sha256=fex['dll_sha256'],previous_sha256=fex['previous_dll_sha256'],debug_register_build=fex,
        scene_memory_build='launcher/scene-memory-fix.json')
    for name,receipt in (('fex-memory-policy',policy),('fex-debug-fix',fex)):
        key=PREFIX+'launcher/'+name+'.json';entries[key]=encode(receipt);changed.add(key)
    entries[PREFIX+'launcher/scene-memory-fix.json']=encode({'build':'sleepingdogs-scene-memory-v1',
        'nro_sha256':native['nro_sha256'],'dll_sha256':fex['dll_sha256'],'compile_slots':2,
        'scratch_reserve_bytes':RESERVE_BYTES,'profile':'fastest','hardware_tested':False})
    entries['README.txt']='''Sleeping Dogs FEXTendo - scene memory v1

1. Tutup Sleeping Dogs/FEXTendo sepenuhnya dari HOME.
2. Salin SELURUH folder switch dari ZIP ini ke root SD PALING AKHIR.
   NRO dan drive_c/windows/system32/libwow64fex.dll wajib diperbarui bersama.
3. NSP GPU-budget yang dipakai sekarang tetap; tidak perlu install ulang.
   Untuk instalasi dari basis lama, install NSP dalam forwarder sekali.
4. Pilih DXVK 3.1.1, Launch Debug, lalu New Game menuju adegan 3D.

Penanda pasangan baru:
[SD-COMPILER-MEM] native=v2 decoder_reserve_kib=64 ir_reserve_mib=16 pairs=2
[SD-COMPILER-MEM] fex=v2 compile_slots=2 decoder=instruction-limit ir_mib=16

Log terakhir kehabisan backing memori saat alokasi GPU 1 MiB. Pool GPU hampir
penuh walaupun patch peminjaman cadangan sudah aktif. Compiler sekarang memakai
dua pasangan buffer terlindungi; kompilasi berikutnya menunggu. Cadangan turun
32,125 MiB. Ukuran IR/decoder dan profil Fastest tetap; kompilasi awal/loading
bisa lebih lambat. Perbaikan ini menambah ruang, belum membuktikan semua adegan
3D muat. Uji host, ARM64 dan paket lulus; gameplay perlu diuji di Switch.

Semua patch sebelumnya disertakan. Data game, save dan preferensi tidak dimuat
dalam update. Kirim fex-runtime.log dan crash.log terbaru jika masih gagal.
Rollback: sleepingdogs-fex-scene-memory-rollback.zip; salin seluruh switch
saat aplikasi tertutup untuk mengembalikan NRO dan FEX sebelumnya bersama.
'''.encode()
    folder='source/scene-memory-fix/'
    for n in SOURCES:entries[folder+n]=(ROOT/n).read_bytes()
    for name in REPORTS:entries[folder+'reports/'+name+'.json']=encode(checks[name])
    for name in ('fex_alloc.py','fex_memory.py','fex_lookup.py','fex_scratch.py'):
        entries[folder+'reference/pes13-nx/tests/'+name]=(ROOT.parent/'pes13-nx/tests'/name).read_bytes()
    entries[folder+'layout.json']=(ROOT/'local/scene-memory-layout.json').read_bytes()
    entries[folder+'native.json']=encode(native);entries[folder+'fex.json']=encode(fex)
    for n in FILES:entries[folder+'native/'+n]=(work/'native-source'/n).read_bytes()
    for n in ADAPTER_FILES:entries[folder+'native-adapter/'+n]=(work/'fex-adapter'/n).read_bytes()
    for n in fex['source_changes']:entries[folder+'fex/'+n]=(work/'fex/source'/n).read_bytes()
    for n in fex['adapter_files']:entries[folder+'adapter/'+n]=(work/'fex/adapter'/n).read_bytes()
    for n,data in old.items():
        if n not in changed:assert entries[n]==data,n
    fw=json.loads(old['forwarder/build.json'])
    for n in entries:
        if n.lower().endswith('.dll') and n!=dll:assert entries[n]==old[n],n
        if n.lower().endswith('.nsp'):assert n=='forwarder/'+fw['nsp'] and entries[n]==old[n]
        assert not n.lower().endswith(('.log','.keys','.exe','.big','.bix'))
        assert Path(n).name not in {'configuration.ini','fex-mode.txt','UserOptions.dat','selected.txt','renderer-choice.txt'}
    rollback={n:old[n] for n in changed}
    rollback[PREFIX+'launcher/scene-memory-fix.json']=encode({'rolled_back':True})
    rollback['README.txt']=b'Close FEXTendo from HOME and copy the entire switch folder. Restores previous GPU-pressure NRO and four-workspace FEX together. Keep current NSP.\n'
    report=archive(ROOT/'dist/sleepingdogs-fex-scene-memory-fix.zip',entries)
    report['rollback']=archive(ROOT/'dist/sleepingdogs-fex-scene-memory-rollback.zip',rollback)
    report.update(status='PASS',source_reconstruction='PASS',prior_payloads_preserved=True,
        nro_sha256=native['nro_sha256'],dll_sha256=fex['dll_sha256'],
        other_dlls_unchanged=True,forwarder_unchanged=fw['sha256'],hardware_tested=False)
    write_json(ROOT/'reports/scene-package.json',report)
    # Future normal builds use this exact matching pair; previous vendors stay pinned.
    shutil.copy2(out/'libwow64fex.dll',ROOT/'vendor/fex/libwow64fex-sd-scene.dll')
    write_json(ROOT/'vendor/fex/libwow64fex-sd-scene.json',policy)
    print(json.dumps({k:report[k] for k in ('path','sha256','bytes','files')}))

if __name__=='__main__':main()
