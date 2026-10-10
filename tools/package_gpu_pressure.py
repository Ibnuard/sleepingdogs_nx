"""Cumulative native reserve correction; keep the tested renderer/FEX/NSP bytes."""
from pathlib import Path
import argparse,hashlib,json,shutil,tempfile,zipfile
from port_common import ROOT,sha,write_json
from package_named_pipe import PREFIX,archive,encode
from build_gpu_pressure import FILES,ADAPTER_FILES
from sleepingdogs_gpu_pressure import apply,MARKER


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-gpu-pressure-v1'))
    work=p.parse_args().work;out=ROOT/'dist/gpu-pressure-fix'
    native=json.loads((out/'native.json').read_text())
    assert sha(out/'sleepingdogs-fex.nro')==native['nro_sha256']
    assert sha(ROOT/'local/symbols/sleepingdogs-gpu-pressure.elf')==native['elf_sha256']
    assert sha(ROOT/'tools/sleepingdogs_gpu_pressure.py')==native['patch_sha256']
    assert sha(ROOT/'tools/build_gpu_pressure.py')==native['builder_sha256']
    assert MARKER.encode() in (out/'sleepingdogs-fex.nro').read_bytes()
    for field,folder in (('source_files','native-source'),('adapter_files','fex-adapter')):
        for n,digest in native[field].items():assert sha(work/folder/n)==digest,n
    prior=ROOT/'dist/sleepingdogs-fex-streaming-memory-fix.zip'
    assert sha(prior)=='7b546ff9d5aa70823f5e86dfc20b2480ad41037b57e54d8cf527546e6762d917'
    with zipfile.ZipFile(prior) as z:
        old={n:z.read(n) for n in z.namelist() if n not in ('README.txt','SHA256SUMS.txt')}
    previous=json.loads(old['source/streaming-memory-fix/native.json'])
    base=Path('/home/blekjek/sleepingdogs-streaming-memory-v1')
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)
        for n,digest in previous['source_files'].items():
            src=base/'native-source'/n;assert sha(src)==digest,n
            dst=source/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        apply(source)
        for n in FILES:assert sha(source/n)==native['source_files'][n],n
    for n in ADAPTER_FILES:assert sha(base/'fex-adapter'/n)==native['adapter_files'][n],n
    checks={}
    for name in ('gpu-pressure-host-check','gpu-pressure-binary-check'):
        check=json.loads((ROOT/'reports'/(name+'.json')).read_text());assert check['status']=='PASS'
        for n,digest in check['sources'].items():assert sha(ROOT/n)==digest,n
        checks[name]=check
    assert checks['gpu-pressure-binary-check']['native_elf_sha256']==native['elf_sha256']
    assert checks['gpu-pressure-binary-check']['previous_native_elf_sha256']==previous['elf_sha256']
    for n,digest in checks['gpu-pressure-host-check']['compiled_native'].items():
        assert sha(work/'native-source/wine-nx-probe/source'/n)==digest,n
    entries=dict(old);changed={PREFIX+'sleepingdogs-fex.nro'}
    entries[PREFIX+'sleepingdogs-fex.nro']=(out/'sleepingdogs-fex.nro').read_bytes()
    for name in ('direct-arena-fix','first-fault-trace','named-pipe-fix','dep-policy-fix','debug-cache-fix',
                 'thread-debug-fix','memory-budget-fix','compiler-memory-fix','gpu-budget-fix','streaming-memory-fix'):
        key=PREFIX+'launcher/'+name+'.json';receipt=json.loads(entries[key])
        receipt['nro_sha256']=native['nro_sha256'];receipt['additional_overlay']='launcher/gpu-pressure-fix.json'
        entries[key]=encode(receipt);changed.add(key)
    renderers=json.loads(old[PREFIX+'launcher/dxvk-releases.json'])
    fw=json.loads(old['forwarder/build.json'])
    assert fw['sha256']=='222269d0bc876b970a1a82a82890223909dd6811776232041e7b8966c4756781'
    pressure={k:native[k] for k in ('build','nro_sha256','gpu_preallocation_bytes','reserve_is_soft','hardware_tested')}
    pressure.update(dxvk_dlls=renderers['dxvk-3.1.1']['dlls'],compatible_forwarder_sha256=fw['sha256'])
    entries[PREFIX+'launcher/gpu-pressure-fix.json']=encode(pressure)
    entries['README.txt']='''Sleeping Dogs FEXTendo - GPU pressure recovery v1

1. Tutup Sleeping Dogs/FEXTendo sepenuhnya dari HOME.
2. Timpa SELURUH folder switch dari ZIP ini ke root SD PALING AKHIR.
3. NSP GPU-budget sebelumnya tetap dipakai; TIDAK perlu install ulang.
   Untuk instalasi baru dari basis lama, install NSP dalam forwarder sekali.
4. Pilih DXVK 3.1.1, Launch Debug, lalu coba New Game menuju adegan 3D.

Penanda baru:
[SD-GPU-PRESSURE] v1 soft_reserve=1; reuse idle GPU space before OOM

Log terakhir masih menyisakan sekitar 17 MiB di pool GPU, tetapi aturan
cadangan 16 MiB menolak alokasi kecil saat blok terbesar tinggal 9 MiB.
Koreksi ini memakai ruang kosong itu ketika jalur heap biasa sudah gagal.
Alokasi aktif tidak dipindah atau dibuang; ukuran resource tetap penuh.
Total jatah proses dan pool tidak bertambah. FEX tetap Fastest. DXVK, Wine/FEX
DLL, forwarder, game, save dan pengaturan pengguna tetap seperti sebelumnya.
Semua update sebelumnya disertakan; ZIP tidak memuat data asli game.

Pengujian host, binari ARM64 dan paket lulus. Gameplay Switch belum diuji.
Jika masih crash, kirim fex-runtime.log dan crash.log terbaru.
Rollback: sleepingdogs-fex-gpu-pressure-rollback.zip; salin seluruh switch
saat aplikasi tertutup. Mengembalikan NRO streaming sebelumnya. NSP tetap sama.
'''.encode()
    folder='source/gpu-pressure-fix/'
    for n in ('src/sd_gpu_pressure.h','tools/sleepingdogs_gpu_pressure.py','tools/build_gpu_pressure.py',
        'tools/package_gpu_pressure.py','tools/analyze_gpu_pressure.py','tools/sleepingdogs_overlay.py',
        'tools/build_launcher.py','tools/verify_package.py','tests/gpu_pressure.c','tests/check_gpu_pressure_host.py',
        'tests/check_gpu_pressure_binary.py','tests/check_gpu_pressure_package.py','tests/check_gpu_budget_binary.py',
        'tests/native_heap_binary.py','docs/gpu-pressure-fix.md','reports/gpu-pressure-analysis.json','LICENSE'):
        entries[folder+n]=(ROOT/n).read_bytes()
    for name,check in checks.items():entries[folder+'reports/'+name+'.json']=encode(check)
    entries[folder+'native.json']=encode(native)
    for n in FILES:entries[folder+'native/'+n]=(work/'native-source'/n).read_bytes()
    for n in ADAPTER_FILES:entries[folder+'adapter/'+n]=(work/'fex-adapter'/n).read_bytes()
    # The launcher gate and renderer files are unchanged; retain its exact test
    # evidence rather than presenting a new run against unchanged code.
    gate=json.loads((ROOT/'reports/streaming-launcher-check.json').read_text())
    assert gate['status']=='PASS' and gate['patch_sha256']==sha(prior)
    assert sha(work/'native-source/wine-nx-probe/source/runtime.c')==gate['native_runtime_sha256']
    entries[folder+'reports/inherited-launcher-check.json']=encode(gate)
    for n,data in old.items():
        if n not in changed:assert entries[n]==data,n
    for n in entries:
        if n.lower().endswith('.dll'):assert entries[n]==old[n],n
        if n.lower().endswith('.nsp'):assert n=='forwarder/'+fw['nsp'] and entries[n]==old[n]
        assert not n.lower().endswith(('.log','.keys','.exe','.big','.bix'))
        assert Path(n).name not in {'configuration.ini','fex-mode.txt','UserOptions.dat','selected.txt','renderer-choice.txt'}
    rollback={n:old[n] for n in changed}
    rollback[PREFIX+'launcher/gpu-pressure-fix.json']=encode({'rolled_back':True})
    rollback['README.txt']=b'Close FEXTendo from HOME and copy the complete switch folder. Restores the previous streaming-memory NRO and receipts. Keep DXVK sdstream1 and the current GPU-budget NSP.\n'
    report=archive(ROOT/'dist/sleepingdogs-fex-gpu-pressure-fix.zip',entries)
    report['rollback']=archive(ROOT/'dist/sleepingdogs-fex-gpu-pressure-rollback.zip',rollback)
    report.update(status='PASS',source_reconstruction='PASS',prior_payloads_preserved=True,
        nro_sha256=native['nro_sha256'],dlls_unchanged=True,forwarder_unchanged=fw['sha256'],
        inherited_launcher_gate='Identical runtime.c and renderer/preset payloads to the validated streaming archive',
        hardware_tested=False)
    write_json(ROOT/'reports/gpu-pressure-package.json',report)
    print(json.dumps({k:report[k] for k in ('path','sha256','bytes','files')}))


if __name__=='__main__':main()
