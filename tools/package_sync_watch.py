"""Package the bounded semaphore observer and restore the requested Fastest mode."""
from pathlib import Path
import argparse
import json
import zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import archive, encode, PREFIX
from build_dxvk_memory import manifest

BASE_SHA='7d6f58a6ec01e053807d6093b52eceb7f13c737949c9290d0516a213aaf24094'
EXPECTED={'wine-nx-probe/source/runtime.c','dlls/ntdll/unix/signal_arm64.c',
          'dlls/ntdll/unix/sync.c','wine-nx-probe/source/sd_sync_watch.h',
          'wine-nx-probe/source/sd_sync_watch.inc','wine-nx-probe/source/sd_sync_bridge.inc'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    args=parser.parse_args()
    out=ROOT/'dist/low-window-sync-watch'
    native=json.loads((out/'native.json').read_text())
    assert native['build']=='sleepingdogs-low-window-v4-sync-watch'
    assert native['sync_watch'] and native['profile']=='fastest'
    assert native['source_files']==manifest(args.work/'native-source')
    assert native['adapter_files']==manifest(args.work/'fex-adapter')
    for name,digest in native['build_inputs'].items(): assert sha(ROOT/name)==digest,name
    nro=out/'sleepingdogs-fex.nro';elf=ROOT/'local/symbols/sleepingdogs-low-window-v4.elf'
    assert sha(nro)==native['nro_sha256'] and sha(elf)==native['elf_sha256']
    data=nro.read_bytes()
    for marker in (b'low-window-v4-sync-watch',b'[SD-SYNC] v1',b'[SD-SYNC-OBJECT]',
                   b'[SD-WATCH] v3',b'[SD-INIT] v2',b'[SD-LOWVA] v1',b'fastest'):
        assert marker in data,marker
    base=ROOT/'dist/sleepingdogs-fex-low-window-loading-watch.zip'
    assert sha(base)==BASE_SHA
    with zipfile.ZipFile(base) as z:
        previous=json.loads(z.read('source/low-window-loading-watch/native.json'))
        old_runtime={name:z.read(name) for name in z.namelist() if name.startswith(PREFIX)}
    assert native['adapter_files']==previous['adapter_files']
    assert not set(previous['source_files'])-set(native['source_files'])
    changes={name for name,digest in native['source_files'].items() if previous['source_files'].get(name)!=digest}
    assert changes==EXPECTED,sorted(changes)
    # Verify host-tested source is exactly the include compiled in the NRO.
    for name in ('sd_sync_watch.h','sd_sync_watch.inc','sd_sync_bridge.inc'):
        assert sha(ROOT/'src/low_window'/name)==native['source_files']['wine-nx-probe/source/'+name]
    reports={}
    for name in ('low-window-sync-watch','low-window-sync-guest-frame','low-window-v4-loading-watch',
                 'low-window-v4-launch-order','low-window-v4-binary','low-window-v4-admission-binary'):
        report=json.loads((ROOT/'reports'/f'{name}.json').read_text())
        assert report['status']=='PASS'
        if 'elf_sha256' in report: assert report['elf_sha256']==native['elf_sha256']
        for file,digest in report.get('source_files',{}).items():
            relative=file if '/' in file else 'wine-nx-probe/source/'+file
            assert native['source_files'][relative]==digest,(name,file)
        for file,digest in report.get('sources',{}).items(): assert sha(ROOT/file)==digest,(name,file)
        reports[name]=report
    for name,test in (('low-window-sync-guest-frame','check_sync_guest_frame.py'),
                      ('low-window-v4-launch-order','check_launch_order.py'),
                      ('low-window-v4-admission-binary','check_launch_memory_binary.py')):
        assert reports[name]['test_sha256']==sha(ROOT/'tests'/test)
    assert reports['low-window-v4-admission-binary']['harness_sha256']==sha(ROOT/'tests/check_low_window_binary.py')
    assert sha(ROOT.parent/'Sleeping Dogs/HKShip.exe')==reports['low-window-sync-guest-frame']['game_sha256']
    kernelbase=ROOT.parent/'pes13-nx/local/production-input-fix/approved/switch/pes13-fex/drive_c/windows/syswow64/kernelbase.dll'
    assert sha(kernelbase)==reports['low-window-sync-guest-frame']['kernelbase_sha256']
    compatible=json.loads((ROOT/'dist/low-window-startup-fix/forwarder/build.json').read_text())
    assert compatible['sha256']==sha(ROOT/'dist/low-window-startup-fix/forwarder'/compatible['nsp'])

    entries={PREFIX+nro.name:data,PREFIX+'launcher/fex-mode.txt':b'fastest\n',
             'README-INSTALL.txt':(ROOT/'docs/low-window-sync-watch.md').read_bytes()}
    for name,payload in old_runtime.items():
        if not name.endswith('.json'): continue
        receipt=json.loads(payload)
        if 'nro_sha256' not in receipt: continue
        receipt['nro_sha256']=native['nro_sha256'];receipt['additional_overlay']=native['build']
        receipt['hardware_tested']=False
        if 'profile' in receipt: receipt['profile']='fastest'
        entries[name]=encode(receipt)
    entries[PREFIX+'launcher/sync-watch.json']=encode({
        'build':native['build'],'nro_sha256':native['nro_sha256'],'profile':'fastest',
        'diagnostic_only':True,'debug_window_seconds':600,'hardware_tested':False,
        'compatible_forwarder_sha256':compatible['sha256'],
        'reason':'Fast/TSO did not remove the same-handle loading stall; capture lifecycle and object evidence'})
    source='source/low-window-sync-watch/'
    entries[source+'native.json']=encode(native)
    for name in changes: entries[source+'native/'+name]=(args.work/'native-source'/name).read_bytes()
    for name in ('tools/build_low_window.py','tools/low_window_loading.py','tools/low_window_sync.py',
                 'tools/package_sync_watch.py','tools/analyze_sync_comparison.py','tools/port_common.py',
                 'tools/f1_base_build.py','tools/f1_overlay.py','tools/build_dxvk_memory.py','tools/package_named_pipe.py',
                 'tests/check_sync_watch.py','tests/sync_watch.c','tests/check_sync_guest_frame.py',
                 'tests/check_loading_watch.py','tests/loading_watch.c','tests/check_launch_order.py',
                 'tests/check_low_window_binary.py','tests/check_launch_memory_binary.py',
                 'reports/low-window-sync-comparison.json','docs/low-window-sync-watch.md','LICENSE'):
        entries[source+name]=(ROOT/name).read_bytes()
    for name in native['build_inputs']:
        entries[source+name]=(ROOT/name).read_bytes()
    for name,report in reports.items(): entries[source+'reports/'+name+'.json']=encode(report)
    for name in entries:
        assert not name.startswith(('atmosphere/','bootloader/','forwarder/'))
        assert '/drive_c/' not in name and not name.endswith(('.dll','.nsp','.kip','.keys','.log','.exe'))
        if name.startswith(PREFIX):
            assert name in (PREFIX+nro.name,PREFIX+'launcher/fex-mode.txt') or (name.startswith(PREFIX+'launcher/') and name.endswith('.json'))
    update=archive(ROOT/'dist/sleepingdogs-fex-low-window-sync-watch.zip',entries)
    rollback=dict(old_runtime)
    rollback[PREFIX+'launcher/fex-mode.txt']=b'fastest\n'
    rollback[PREFIX+'launcher/sync-watch.json']=encode({'rolled_back':True,'nro_sha256':previous['nro_sha256'],'profile':'fastest'})
    rollback['README.txt']=b'Tutup game dari HOME, lalu timpa switch/ ke root SD. Kembali ke NRO low-window v3 dengan profil fastest. Tidak perlu NSP/reboot.\n'
    restore=archive(ROOT/'dist/sleepingdogs-fex-low-window-sync-watch-rollback.zip',rollback)
    stage=ROOT/'dist/sleepingdogs-fex-low-window-sync-watch'
    for name,payload in entries.items():
        if not name.startswith(PREFIX) and name!='README-INSTALL.txt': continue
        path=stage/name;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists(): assert path.read_bytes()==payload,f'Preserve existing extracted file: {path}'
        else: path.write_bytes(payload)
    result=dict(status='PASS',update=update,rollback=restore,nro_sha256=native['nro_sha256'],
                elf_sha256=native['elf_sha256'],changed_native_files=sorted(changes),profile='fastest',
                fex_adapter_unchanged=True,baseline_preserved=sha(base)==BASE_SHA,
                compatible_forwarder_sha256=compatible['sha256'],diagnostic_only=True,
                hardware_tested=False,freeze_fixed=False)
    write_json(ROOT/'reports/low-window-sync-watch-package.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
