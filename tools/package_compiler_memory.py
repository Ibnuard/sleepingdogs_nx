"""Package the tested NRO/FEX pair over the cumulative memory-budget patch."""
from pathlib import Path
import argparse
import json
import shutil
import tempfile
import zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode, PREFIX
from build_memory_budget import FILES, ADAPTER_FILES
from sleepingdogs_compiler_memory import apply_native, apply_fex

REPORTS = ('compiler-memory-host-check', 'compiler-decoder-binary-check',
           'compiler-reserve-binary-check', 'compiler-gate-binary-check', 'compiler-debug-regression')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-compiler-memory-v2'))
    a = p.parse_args(); work = a.work
    previous_native = Path('/home/blekjek/sleepingdogs-memory-budget-v1')
    previous_fex = Path('/home/blekjek/sleepingdogs-fex-debug-v1')
    out = ROOT / 'dist/compiler-memory-fix'
    native = json.loads((out / 'native.json').read_text()); fex = json.loads((out / 'fex.json').read_text())
    assert sha(out / 'sleepingdogs-fex.nro') == native['nro_sha256']
    assert sha(out / 'libwow64fex.dll') == fex['dll_sha256']
    for names, base in (('source_files', work / 'native-source'), ('adapter_files', work / 'fex-adapter')):
        for n, digest in native[names].items(): assert sha(base / n) == digest, n
    for n, digest in fex['source_changes'].items(): assert sha(work / 'fex/source' / n) == digest, n
    for n, digest in fex['adapter_files'].items(): assert sha(work / 'fex/adapter' / n) == digest, n
    for n, digest in fex['inputs']['local'].items(): assert sha(ROOT / n) == digest, n
    for name in REPORTS:
        report = json.loads((ROOT / 'reports' / (name + '.json')).read_text())
        if name == 'compiler-debug-regression': assert report['actual_dll_emitter_cases'] == 67
        else: assert report['status'] == 'PASS', name
        if 'dll_sha256' in report: assert report['dll_sha256'] == fex['dll_sha256'], name
        if name == 'compiler-reserve-binary-check': assert report['after']['elf_sha256'] == native['elf_sha256']
        for n, digest in report.get('sources', {}).items(): assert sha(ROOT / n) == digest, n
    prior = ROOT / 'dist/sleepingdogs-fex-memory-budget-fix.zip'
    assert sha(prior) == '19dfeb58885977aefa76b0253783ffea937bcaf0321959d270416d9ebf3031e5'
    with zipfile.ZipFile(prior) as z:
        old = {n:z.read(n) for n in z.namelist() if n not in ('README.txt','SHA256SUMS.txt')}
    old_native = json.loads(old['source/memory-budget-fix/native.json'])
    old_fex = json.loads(old['source/fex-debug-fix/build.json'])
    fex_names = set(fex['source_changes']) | {n.removeprefix('generated/fex/') for n in
        fex['inputs']['approved'] if n.startswith('generated/fex/')}
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp); ns, na = base / 'native', base / 'native-adapter'
        na.mkdir()
        for n in FILES:
            original = previous_native / 'native-source' / n
            assert sha(original) == old_native['source_files'][n], n
            target = ns / n; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(original,target)
        for n in ADAPTER_FILES:
            original = previous_native / 'fex-adapter' / n
            assert sha(original) == old_native['adapter_files'][n], n
            shutil.copy2(original,na/n)
        apply_native(ns, na)
        for n in FILES: assert sha(ns/n) == native['source_files'][n], n
        for n in ADAPTER_FILES: assert sha(na/n) == native['adapter_files'][n], n
        fs, fa = base / 'fex', base / 'adapter'; fa.mkdir()
        for n in fex_names:
            original = previous_fex / 'source' / n
            expected = old_fex['source_changes'].get(n) or old_fex['inputs']['approved'].get('generated/fex/'+n)
            if expected: assert sha(original) == expected, n
            target = fs/n; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(original,target)
        for n,digest in old_fex['adapter_files'].items():
            assert sha(previous_fex/'adapter'/n)==digest,n
            shutil.copy2(previous_fex/'adapter'/n, fa/n)
        apply_fex(fs,fa)
        for n in fex_names: assert sha(fs/n)==sha(work/'fex/source'/n),n
        for n,digest in fex['adapter_files'].items(): assert sha(fa/n)==digest,n
    entries = dict(old)
    nro_key = PREFIX+'sleepingdogs-fex.nro'; dll_key=PREFIX+'drive_c/windows/system32/libwow64fex.dll'
    changed = {nro_key,dll_key}
    entries[nro_key]=(out/'sleepingdogs-fex.nro').read_bytes()
    entries[dll_key]=(out/'libwow64fex.dll').read_bytes()
    for name in ('direct-arena-fix','first-fault-trace','named-pipe-fix','dep-policy-fix',
                 'debug-cache-fix','thread-debug-fix','memory-budget-fix'):
        key=PREFIX+'launcher/'+name+'.json'; receipt=json.loads(entries[key])
        receipt['nro_sha256']=native['nro_sha256']; receipt['additional_overlay']='launcher/compiler-memory-fix.json'
        entries[key]=encode(receipt); changed.add(key)
    policy=json.loads(entries[PREFIX+'launcher/fex-memory-policy.json'])
    policy.update(sha256=fex['dll_sha256'],previous_sha256=fex['previous_dll_sha256'],
                  debug_register_build=fex, compiler_memory_build='launcher/compiler-memory-fix.json')
    for name,receipt in (('fex-memory-policy',policy),('fex-debug-fix',fex)):
        key=PREFIX+'launcher/'+name+'.json'; entries[key]=encode(receipt); changed.add(key)
    paired={'build':'sleepingdogs-compiler-memory-v1','nro_sha256':native['nro_sha256'],'dll_sha256':fex['dll_sha256'],
            'compile_slots':4,'scratch_reserve_bytes':67371008,'decoder_reserve_bytes':65536,'ir_reserve_bytes':16777216,
            'previous_nro_sha256':old_native['nro_sha256'],'previous_dll_sha256':fex['previous_dll_sha256'],
            'hardware_tested':False}
    entries[PREFIX+'launcher/compiler-memory-fix.json']=encode(paired)
    entries['README.txt']='''Sleeping Dogs FEXTendo - compiler memory fix v1

1. Tutup Sleeping Dogs/FEXTendo sepenuhnya dari HOME.
2. Timpa SELURUH folder switch dari ZIP ini ke root SD, paling akhir setelah paket basis/ready.
   Wajib salin NRO DAN drive_c/windows/system32/libwow64fex.dll bersama.
3. Buka forwarder Sleeping Dogs yang sama; NSP tidak perlu diinstall ulang.
4. Pilih Launch Debug. Cari kedua penanda:
   [SD-COMPILER-MEM] native=v1 decoder_reserve_kib=64 ir_reserve_mib=16 pairs=4
   [SD-COMPILER-MEM] fex=v1 compile_slots=4 decoder=instruction-limit ir_mib=16

Empat buffer IR kini dilindungi dengan batas empat kompilasi yang berlangsung bersamaan.
Kompilasi berikutnya menunggu slot; thread game dan empat core tetap tersedia.
Decoder menyesuaikan kapasitas dengan batas instruksi (500 pada Fastest: 64 KiB).
Cadangan native berkurang 31,75 MiB; kapasitas IR tetap 16 MiB per buffer.
Semua perbaikan sebelumnya disertakan. Fastest tetap. File game/save/settings tidak ditimpa.
Uji host, decoder/kompilasi ARM64, allocator NRO, dan integritas paket lulus.
Boot/menu/gameplay masih perlu diuji di Switch. Jika gagal, kirim fex-runtime.log dan crash.log terbaru.
Rollback: sleepingdogs-fex-compiler-memory-rollback.zip memulihkan pasangan memory-budget v1.
'''.encode()
    folder='source/compiler-memory-fix/'
    files=('src/sd_fex_workspace.h','tools/sleepingdogs_compiler_memory.py','tools/build_compiler_memory.py',
        'tools/package_compiler_memory.py','tools/sleepingdogs_overlay.py','tools/build_launcher.py','tools/verify_package.py',
        'tests/compiler_memory_host.cpp','tests/check_compiler_memory_host.py','tests/compiler_memory_layout.cpp',
        'tests/build_compiler_memory_layout.py','tests/check_compiler_decoder_binary.py','tests/check_compiler_gate_binary.py',
        'tests/check_compiler_reserve_binary.py','tests/native_heap_binary.py','tests/check_fex_debug_binary.py',
        'tests/check_compiler_memory_package.py',
        'reports/compiler-memory-analysis.json','docs/compiler-memory-fix.md','LICENSE')
    for n in files: entries[folder+n]=(ROOT/n).read_bytes()
    for name in REPORTS: entries[folder+'reports/'+name+'.json']=(ROOT/'reports'/(name+'.json')).read_bytes()
    # Preserve the exact shared NT/PE test harness dependencies for reproducibility.
    for name in ('fex_alloc.py','fex_memory.py','fex_lookup.py','fex_scratch.py'):
        entries[folder+'reference/pes13-nx/tests/'+name]=(ROOT.parent/'pes13-nx/tests'/name).read_bytes()
    entries[folder+'layout.json']=(ROOT/'local/compiler-memory-layout.json').read_bytes()
    entries[folder+'native.json']=encode(native); entries[folder+'fex.json']=encode(fex)
    for n in FILES: entries[folder+'native/'+n]=(work/'native-source'/n).read_bytes()
    for n in ADAPTER_FILES: entries[folder+'native-adapter/'+n]=(work/'fex-adapter'/n).read_bytes()
    for n in fex_names: entries[folder+'fex/'+n]=(work/'fex/source'/n).read_bytes()
    for n in fex['adapter_files']: entries[folder+'adapter/'+n]=(work/'fex/adapter'/n).read_bytes()
    for n,data in old.items():
        if n not in changed: assert entries[n]==data,n
    for n in entries:
        assert not n.lower().endswith(('.log','.keys','.nsp','.exe','.big','.bix'))
        assert Path(n).name not in {'configuration.ini','fex-mode.txt','UserOptions.dat','selected.txt','renderer-choice.txt'}
        assert '/drive_c/SleepingDogs/' not in n
    report=archive(ROOT/'dist/sleepingdogs-fex-compiler-memory-fix.zip',entries)
    rollback={n:old[n] for n in changed}
    rollback[PREFIX+'launcher/compiler-memory-fix.json']=encode({'rolled_back':True})
    rollback['README.txt']=b'Close FEXTendo from HOME; overwrite the complete switch folder. Restores both memory-budget v1 NRO and previous FEX DLL.\n'
    report['rollback']=archive(ROOT/'dist/sleepingdogs-fex-compiler-memory-rollback.zip',rollback)
    report.update(status='PASS',source_reconstruction='PASS',prior_payloads_preserved=True,
                  nro_sha256=native['nro_sha256'],dll_sha256=fex['dll_sha256'],hardware_tested=False,game_boot_confirmed=False)
    write_json(ROOT/'reports/compiler-memory-package.json',report)
    shutil.copy2(out/'libwow64fex.dll',ROOT/'vendor/fex/libwow64fex-sd-compiler.dll')
    write_json(ROOT/'vendor/fex/libwow64fex-sd-compiler.json',policy)
    print(json.dumps({k:report[k] for k in ('path','sha256','bytes','files','nro_sha256','dll_sha256')}))

if __name__=='__main__': main()
