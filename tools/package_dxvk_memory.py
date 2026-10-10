"""Cumulative renderer update and rollback, with explicit managed-DLL allowlist."""
from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import zipfile
import pefile
from port_common import ROOT,sha,write_json
from package_named_pipe import PREFIX,archive,encode
from sleepingdogs_dxvk_memory import apply,FILES
from dxvk_runtime import release_files,effective_release


def interfaces(data):
    pe=pefile.PE(data=data)
    assert pe.FILE_HEADER.Machine==0x14c
    return {'imports':{d.dll.decode():sorted((i.name or str(i.ordinal).encode()).decode() for i in d.imports)
                       for d in pe.DIRECTORY_ENTRY_IMPORT},
            'exports':sorted((s.ordinal,(s.name or b'').decode()) for s in pe.DIRECTORY_ENTRY_EXPORT.symbols)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-dxvk-memory-v2'))
    args=parser.parse_args();work=args.work
    out=ROOT/'dist/dxvk-memory-fix';native=ROOT/'dist/compiler-memory-fix'
    build=json.loads((out/'build.json').read_text());staged=json.loads((out/'staged.json').read_text())
    assert sha(ROOT/'tools/build_dxvk_memory.py')==build['inputs']['builder_sha256']
    assert sha(ROOT/'tools/sleepingdogs_dxvk_memory.py')==build['inputs']['patch_sha256']
    previous_source=Path('/home/blekjek/f1-dxvk-compact-chunks/source')
    with tempfile.TemporaryDirectory() as temp:
        reconstruction=Path(temp)
        for n in FILES:
            assert sha(previous_source/n)==build['inputs']['base'][n],n
            p=reconstruction/n;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((previous_source/n).read_bytes())
        apply(reconstruction)
        for n in FILES:
            assert sha(reconstruction/n)==build['changed'][n]==sha(work/'source'/n),n
    tests={}
    for name in ('dxvk-memory-host-check','dxvk-map-binary-check'):
        report=json.loads((ROOT/'reports'/(name+'.json')).read_text())
        assert report['status']=='PASS'
        for n,digest in report['sources'].items():assert sha(ROOT/n)==digest,n
        tests[name]=report
    assert tests['dxvk-map-binary-check']['dll_sha256']==staged['files']['d3d11.dll']['sha256']
    previous=ROOT/'dist/sleepingdogs-fex-compiler-memory-fix.zip'
    assert sha(previous)=='b8266ff9853f5d2368fdb5fc07df551f7399f259e5d4c1aaf4a227f93dd82dbf'
    with zipfile.ZipFile(previous) as z:
        old={n:z.read(n) for n in z.namelist() if n not in ('README.txt','SHA256SUMS.txt')}
    # The prior cumulative runtime does not carry renderer binaries. Retrieve
    # these from its pinned original archive, never from the user's game folder.
    import tarfile
    baseline=json.loads((ROOT/'vendor/dxvk/dxvk-3.1.1-f1mem2.json').read_text())
    with tarfile.open(ROOT/'vendor/dxvk/dxvk-3.1.1-f1mem2.tar.gz') as tar:
        old_dlls={n:tar.extractfile('dxvk-3.1.1-f1mem2/x32/'+n).read() for n in baseline['files']}
    current=release_files()['dxvk-3.1.1'];entries=dict(old);rollback={};changed=set()
    managed=set()
    interface_report={}
    for name,data in current.items():
        assert hashlib.sha256(data).hexdigest()==staged['files'][name]['sha256']
        assert hashlib.sha256(old_dlls[name]).hexdigest()==baseline['files'][name]['sha256']
        assert interfaces(data)==interfaces(old_dlls[name]),name
        interface_report[name]={'imports_exports_unchanged':True,'sha256':staged['files'][name]['sha256']}
        targets=['launcher/renderers/dxvk-3.1.1/'+name,'drive_c/SleepingDogs/'+name]
        if name=='d3d9.dll':targets.append('drive_c/dxvk/d3d9.dll')
        for relative in targets:
            key=PREFIX+relative;entries[key]=data;rollback[key]=old_dlls[name]
            changed.add(key);managed.add(key)
    key=PREFIX+'launcher/dxvk-releases.json'
    if key in old:previous_receipt=old[key]
    else:
        with zipfile.ZipFile(ROOT/'dist/sleepingdogs-fex-0.1.0-sd.zip') as z:previous_receipt=z.read(key)
    receipts=json.loads(previous_receipt)
    assert receipts['dxvk-3.1.1']['dlls']=={n:m['sha256'] for n,m in baseline['files'].items()}
    release=effective_release('dxvk-3.1.1')
    receipts['dxvk-3.1.1']={'url':release['url'],'archive_sha256':release['sha256'],
                           'dlls':{n:m['sha256'] for n,m in staged['files'].items()},'patch':staged}
    entries[key]=encode(receipts);rollback[key]=previous_receipt;changed.add(key)
    entries[PREFIX+'launcher/dxvk-memory-fix.json']=encode(staged)
    rollback[PREFIX+'launcher/dxvk-memory-fix.json']=encode({'rolled_back':True})
    entries['README.txt']='''Sleeping Dogs FEXTendo - DXVK memory fix v1

1. Tutup Sleeping Dogs/FEXTendo sepenuhnya dari HOME.
2. Timpa SELURUH folder switch dari ZIP ini ke root SD, paling akhir setelah paket basis/ready.
   Salin DLL pada drive_c/SleepingDogs DAN launcher/renderers/dxvk-3.1.1.
3. Buka forwarder Sleeping Dogs yang sama. Pilih DXVK 3.1.1 dan Launch Debug.
4. Pastikan log memuat [SD-DXVK-MEM] v1 pool cap=2 MiB.

Log terakhir sudah mencapai logo; kemudian alokasi buffer grafis 5 MiB gagal.
Cadangan DXVK biasa kini dibatasi 2 MiB. Resource lebih besar tetap mendapat
ukuran penuh yang dibulatkan ke halaman, sehingga buffer 5 MiB memakai 5 MiB.
Deferred Map mengembalikan error jika alokasi gagal, tanpa membaca pointer NULL.
Semua perbaikan sebelumnya termasuk; FEX tetap Fastest. NSP tidak perlu diinstall ulang.
Data asli game, save, dan pengaturan pengguna tidak ditimpa. Tiga DLL DXVK adalah
file runtime yang dikelola port ini dan memang diperbarui.

Uji host dan instruksi DLL lulus. Masuk menu/gameplay masih perlu diuji di Switch.
Jika gagal, kirim fex-runtime.log dan crash.log terbaru.
Rollback renderer: sleepingdogs-fex-dxvk-memory-rollback.zip, salin switch/ saat aplikasi tertutup.
'''.encode()
    rollback['README.txt']=b'Close FEXTendo from HOME; copy the whole switch folder. Restores the prior DXVK f1mem2 DLLs in both managed locations. Keeps the compiler/native fixes.\n'
    source='source/dxvk-memory-fix/'
    for n in ('tools/sleepingdogs_dxvk_memory.py','tools/build_dxvk_memory.py','tools/stage_dxvk_memory.py',
              'tools/package_dxvk_memory.py','tools/dxvk_runtime.py','tools/verify_package.py',
              'tests/dxvk_memory.cpp','tests/dxvk_deferred_map.cpp','tests/check_dxvk_memory_host.py',
              'tests/check_dxvk_map_binary.py','tests/check_wow64_context_binary.py','tools/port_common.py',
              'tests/check_dxvk_memory_package.py','tests/check_dxvk_memory_launcher.py',
              'tests/check_renderer_package.py','vendor/f1-tools/check_renderer_package.py',
              'reports/dxvk-memory-analysis.json','docs/dxvk-memory-fix.md',
              'vendor/dxvk/DXVK-LICENSE','vendor/dxvk/dxvk-3.1.1-f1mem2.json',
              'tools/dxvk_compact_chunks.py','tools/dxvk_small_chunks.py'):
        entries[source+n]=(ROOT/n).read_bytes()
    for name in tests:entries[source+'reports/'+name+'.json']=(ROOT/'reports'/(name+'.json')).read_bytes()
    for n in FILES:
        entries[source+'patched/'+n]=(work/'source'/n).read_bytes()
        entries[source+'base/'+n]=(previous_source/n).read_bytes()
    for name in ('build.json','staged.json'):entries[source+name]=(out/name).read_bytes()
    for name,data in old.items():
        if name not in changed:assert entries[name]==data,name
    for name in entries:
        if '/drive_c/SleepingDogs/' in name:assert name in managed,name
        assert not name.lower().endswith(('.log','.keys','.nsp','.exe','.big','.bix'))
        assert Path(name).name not in {'configuration.ini','fex-mode.txt','UserOptions.dat','selected.txt','renderer-choice.txt'}
    report=archive(ROOT/'dist/sleepingdogs-fex-dxvk-memory-fix.zip',entries)
    report['rollback']=archive(ROOT/'dist/sleepingdogs-fex-dxvk-memory-rollback.zip',rollback)
    report.update(status='PASS',source_reconstruction='PASS',prior_payloads_preserved=True,
                  interfaces=interface_report,native_nro_unchanged=hashlib.sha256(entries[PREFIX+'sleepingdogs-fex.nro']).hexdigest(),
                  fex_unchanged=hashlib.sha256(entries[PREFIX+'drive_c/windows/system32/libwow64fex.dll']).hexdigest(),
                  original_game_excluded=True,hardware_tested=False)
    write_json(ROOT/'reports/dxvk-memory-package.json',report)
    print(json.dumps({k:report[k] for k in ('path','sha256','bytes','files')}))


if __name__=='__main__':main()
