"""Package the cumulative DEP bridge, preserving every other tested runtime payload."""
from pathlib import Path
import argparse
import json
import tempfile
import zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode, PREFIX
from build_dep_fix import NATIVE_FILES, WOW_FILES
from sleepingdogs_named_pipe import apply as apply_pipes
from sleepingdogs_fault_trace import apply as apply_faults
from wow64_dep_fix import apply as apply_dep


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-dep-v1'))
    p.add_argument('--memory-work',type=Path,default=Path('/home/blekjek/sleepingdogs-direct-arena-v2'))
    p.add_argument('--context-work',type=Path,default=Path('/home/blekjek/sleepingdogs-wow64-context-v1'))
    a=p.parse_args(); out=ROOT/'dist/dep-policy-fix'
    native=json.loads((out/'native.json').read_text())
    wow=json.loads((out/'wow64.json').read_text())
    assert sha(out/'sleepingdogs-fex.nro')==native['nro_sha256']
    assert sha(out/'wow64.dll')==wow['dll_sha256']
    for component, receipt, sub in (('native',native,'native-source'),('wow64',wow,'source')):
        for n,d in receipt['source_files'].items(): assert sha(a.work/component/sub/n)==d,n
    for report in ('dep-bridge-host-check','dep-bridge-binary-check','fex-dep-binary-check','first-fault-host-check'):
        test=json.loads((ROOT/'reports'/f'{report}.json').read_text())
        assert test['status']=='PASS'
        for n,d in test.get('sources',{}).items(): assert sha(ROOT/n)==d,n
        if report=='dep-bridge-binary-check': assert test['dll_sha256']==wow['dll_sha256']
        if report=='fex-dep-binary-check': assert test['dll_sha256']==sha(ROOT/'vendor/fex/libwow64fex-sd-debug.dll')
    oldzip=ROOT/'dist/sleepingdogs-fex-named-pipe-fix.zip'
    assert sha(oldzip)=='469f507e1290f20300587f7320abd659ebb2f6427eaa8331f78abe70d0a9036f'
    with zipfile.ZipFile(oldzip) as z:
        previous={n:z.read(n) for n in z.namelist() if n not in ('README.txt','SHA256SUMS.txt')}
    # Recreate every modified compilation unit from the prior source layers.
    with tempfile.TemporaryDirectory() as tmp:
        expected=Path(tmp)
        seed=('dlls/ntdll/unix/horizon.c','dlls/ntdll/unix/file.c',
              'dlls/ntdll/unix/signal_arm64.c','wine-nx-probe/source/runtime.c','wine-nx-probe/source/f1_crash.c')
        for n in seed:
            dest=expected/n; dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((a.memory_work/'native-source'/n).read_bytes())
        apply_pipes(expected); apply_faults(expected)
        checked=tuple(dict.fromkeys(seed+NATIVE_FILES+('dlls/ntdll/unix/sd_named_pipe.h','dlls/ntdll/unix/sd_named_pipe.inc')))
        for n in checked:
            assert (expected/n).read_bytes()==(a.work/'native/native-source'/n).read_bytes(),n
        for n in WOW_FILES:
            if n.endswith('sd_wow64_dep.inc'):continue
            dest=expected/n; dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((a.context_work/'source'/n).read_bytes())
        apply_dep(expected)
        for n in WOW_FILES: assert (expected/n).read_bytes()==(a.work/'wow64/source'/n).read_bytes(),n
    old_build=json.loads(previous['source/named-pipe-fix/build.json'])
    for n,d in old_build['memory_sources_unchanged'].items(): assert sha(a.work/'native/native-source'/n)==d,n
    source_check={'compiled_native_and_wow64_overlay_reconstruction':'PASS',
                  'memory_sources_unchanged':old_build['memory_sources_unchanged']}
    write_json(ROOT/'reports/dep-source-check.json',source_check)
    entries=dict(previous)
    changed={PREFIX+'sleepingdogs-fex.nro',PREFIX+'drive_c/windows/system32/wow64.dll',
             *(PREFIX+'launcher/'+n+'.json' for n in ('wow64-context-fix','direct-arena-fix','first-fault-trace','named-pipe-fix'))}
    entries[PREFIX+'sleepingdogs-fex.nro']=(out/'sleepingdogs-fex.nro').read_bytes()
    entries[PREFIX+'drive_c/windows/system32/wow64.dll']=(out/'wow64.dll').read_bytes()
    entries[PREFIX+'launcher/wow64-context-fix.json']=encode(wow)
    for name in ('direct-arena-fix','named-pipe-fix','first-fault-trace'):
        key=PREFIX+'launcher/'+name+'.json'; rec=json.loads(entries[key])
        rec['nro_sha256']=native['nro_sha256']; rec['additional_overlay']='launcher/dep-policy-fix.json'
        if name=='first-fault-trace':
            rec.update(build='sleepingdogs-post-frame-fault-v2',max_guest_snapshots=4,
                skip_debug_exceptions=True,code_bytes=64,source_files=native['source_files'])
        entries[key]=encode(rec)
    dep={'build':'sleepingdogs-wow64-dep-notification-v1','nro_sha256':native['nro_sha256'],
        'wow64_sha256':wow['dll_sha256'],'policy_forced':False,'fex_profile':'fastest (unchanged)',
        'fex_dll_unchanged':True,'hardware_tested':False,'game_boot_confirmed':False,
        'evidence':'Wine disables DEP for HKShip.exe, but the prior WoW64 DLL never notified the FEX export.',
        'log_capture':'First four non-debug exceptions, instruction bytes; first snapshot persisted to crash.log.'}
    entries[PREFIX+'launcher/dep-policy-fix.json']=encode(dep)
    entries['README.txt']='''Sleeping Dogs FEXTendo - DEP policy bridge v1

1. Tutup Sleeping Dogs/FEXTendo dari HOME.
2. Salin SELURUH folder switch dari ZIP ini ke root SD, timpa file lama.
3. Buka forwarder Sleeping Dogs yang sama; tidak perlu install ulang NSP.
4. Pilih Launch Debug. Cari [SD-DEP] change flags=00000002 backend notified
   dan [SD-FIRSTFAULT] build=v2 di fex-runtime.log.
5. Jika masih freeze/crash, kirim fex-runtime.log DAN crash.log terbaru dari
   switch/sleepingdogs-fex/ setelah percobaan itu.

Log sebelumnya sudah mencapai present 1-4, lalu guest execution fault pada heap.
Wine menonaktifkan DEP untuk HKShip.exe, tetapi WoW64 lama tidak menyampaikan
perubahan tersebut ke FEX. Patch menghubungkan notifikasi kebijakan yang sudah
diterima Wine, termasuk sinkronisasi saat startup; tidak memaksa DEP mati.
Pencatatan fault kini melewati breakpoint normal dan menyimpan byte di EIP.

Kumulatif: seluruh perbaikan named pipe, breakpoint FEX, arena, WoW64 self-context
dan renderer sebelumnya tetap. Fastest tetap; game/save/pilihan launcher tidak
ditimpa. Pasang patch ini PALING AKHIR setelah paket basis/ready.

Uji host dan build bukan bukti boot/menu/gameplay di Switch. Penyebab heap jump
belum terlihat di log lama; patch memperbaiki celah kebijakan yang terbukti dan
menyiapkan bukti fault pertama jika ada kendala lanjutan.
Rollback: sleepingdogs-fex-dep-policy-rollback.zip mengembalikan runtime named-pipe.
'''.encode()
    folder='source/dep-policy-fix/'
    files=('src/sd_wow64_dep.inc','src/sd_fault_trace.inc','src/sd_fault_io.inc','src/sd_fault_wine_log.h',
        'tools/wow64_dep_fix.py','tools/wow64_context_fix.py','tools/sleepingdogs_fault_trace.py',
        'tools/build_dep_fix.py','tools/package_dep_fix.py','tools/build_launcher.py','tools/verify_package.py',
        'tests/dep_bridge.c','tests/check_dep_bridge.py','tests/check_dep_bridge_binary.py',
        'tests/check_fex_dep_binary.py',
        'tests/fault_trace.c','tests/check_fault_trace.py',
        'reports/dep-bridge-host-check.json','reports/dep-bridge-binary-check.json',
        'reports/fex-dep-binary-check.json',
        'reports/first-fault-host-check.json','reports/dep-fault-analysis.json','docs/dep-policy-fix.md','LICENSE')
    for n in files: entries[folder+n]=(ROOT/n).read_bytes()
    entries[folder+'native.json']=encode(native); entries[folder+'wow64.json']=encode(wow)
    entries[folder+'source-check.json']=encode(source_check)
    for component, sub, names in (('native','native-source',NATIVE_FILES),('wow64','source',WOW_FILES)):
        for n in names: entries[folder+'generated/'+component+'/'+n]=(a.work/component/sub/n).read_bytes()
    for n,data in previous.items():
        if n not in changed: assert entries[n]==data,n
    for n in entries:
        assert not n.lower().endswith(('.log','.keys','.nsp','.exe','.big','.bix'))
        assert Path(n).name not in {'configuration.ini','fex-mode.txt','UserOptions.dat','selected.txt','renderer-choice.txt'}
        assert '/drive_c/SleepingDogs/' not in n
    report=archive(ROOT/'dist/sleepingdogs-fex-dep-policy-fix.zip',entries)
    rollback={n:previous[n] for n in changed}
    rollback[PREFIX+'launcher/dep-policy-fix.json']=encode({'rolled_back':True})
    rollback['README.txt']=b'Close FEXTendo from HOME, then overwrite switch/ on SD. Restores the named-pipe runtime.\n'
    report['rollback']=archive(ROOT/'dist/sleepingdogs-fex-dep-policy-rollback.zip',rollback)
    report.update(cumulative=True,checksums_verified=True,prior_payloads_preserved=True,
        source_reconstruction='PASS',memory_sources_unchanged=True,
        nro_sha256=native['nro_sha256'],wow64_sha256=wow['dll_sha256'],hardware_tested=False,game_boot_confirmed=False)
    write_json(ROOT/'reports/dep-policy-package.json',report); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
