"""Package v12's DXVK-only experiment and a complete renderer rollback."""
from pathlib import Path
import argparse
import gzip
import hashlib
import io
import json
import tarfile
import tempfile
import zipfile
from port_common import ROOT, sha, write_json
from package_named_pipe import PREFIX, archive, encode
from package_dxvk_memory import interfaces
from package_streaming_memory import executable_sections
from build_dxvk_memory import manifest
from sleepingdogs_dxvk_batch import apply, BUILD, FILES, OPTION

V11_SHA = 'f753ec3e8b716facbce7740851ffee1c1344e559a4a5aa13bb0979cf5b968cf1'
NRO_SHA = '91cce20983b88834d9652deb9f5225ec431c300a0440e34370766f9372ecd7d8'
NAME = 'sleepingdogs-fex-low-window-submit-batching'
PERFORMANCE = PREFIX+'launcher/presets/performance/dxvk-3.1.1/dxvk.conf'
SOURCES = ('tools/sleepingdogs_dxvk_batch.py','tools/build_dxvk_batch.py',
           'tools/package_dxvk_batch.py','tools/analyze_gameplay_v11.py',
           'tests/check_dxvk_batch.py','tests/dxvk_batch.cpp',
           'tests/check_dxvk_batch_binary.py','tests/check_wow64_context_binary.py',
           'tests/check_dxvk_batch_launcher.py','tests/dxvk_batch_launcher.c',
           'vendor/f1-tools/check_renderer_package.py','docs/low-window-submit-batching.md',
           'vendor/dxvk/DXVK-LICENSE','vendor/dxvk/dxvk-3.1.1-sdrecycle1.json')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-dxvk-batch-v1'))
    p.add_argument('--stage-only',action='store_true')
    a=p.parse_args(); out=ROOT/'dist/dxvk-batch'
    baseline=ROOT/'dist/sleepingdogs-fex-low-window-frame-diagnostics.zip'
    assert sha(baseline)==V11_SHA
    with zipfile.ZipFile(baseline) as z:
        assert z.testzip() is None
        old={n:z.read(n) for n in z.namelist() if n.startswith((PREFIX,'source/'))}
    assert hashlib.sha256(old[PREFIX+'sleepingdogs-fex.nro']).hexdigest()==NRO_SHA
    build=json.loads((out/'build.json').read_text())
    assert build['build']==BUILD and manifest(a.work/'source')==build['source_files']
    previous=a.work.parent/'sleepingdogs-buffer-reuse-v2'
    assert manifest(previous/'source')==build['inputs']['base_source']
    for n,h in build['inputs']['files'].items(): assert sha(ROOT/n)==h,n
    assert set(build['changed'])==FILES
    with tempfile.TemporaryDirectory(prefix='sd-batch-source-') as temp:
        source=Path(temp)
        for n in FILES:
            target=source/n; target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((previous/'source'/n).read_bytes())
        apply(source)
        for n in FILES: assert sha(source/n)==build['changed'][n],n
    vendor=json.loads((ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.json').read_text())
    old_archive=ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.tar.gz'
    assert sha(old_archive)==vendor['archive_sha256']
    with tarfile.open(old_archive) as tar:
        old_dlls={n:tar.extractfile('dxvk-3.1.1-sdrecycle1/x32/'+n).read() for n in vendor['files']}
    entries=dict(old); rollback={}; managed=set(); checks={}; dlls={}
    for n,data in old_dlls.items():
        assert hashlib.sha256(data).hexdigest()==vendor['files'][n]['sha256']
        candidate=(out/'x32'/n).read_bytes(); raw=(out/n).read_bytes()
        assert hashlib.sha256(candidate).hexdigest()==build['files'][n]['sha256']
        assert hashlib.sha256(raw).hexdigest()==build['files'][n]['raw_sha256']
        assert interfaces(candidate)==interfaces(data),n
        assert executable_sections(candidate)==executable_sections(raw),n
        checks[n]=dict(sha256=build['files'][n]['sha256'],interfaces_unchanged=True,
                       stripped_executable_sections_identical=True)
        dlls[n]=candidate
        targets=['launcher/renderers/dxvk-3.1.1/'+n,'drive_c/SleepingDogs/'+n]
        if n=='d3d9.dll': targets.append('drive_c/dxvk/d3d9.dll')
        for relative in targets:
            key=PREFIX+relative; entries[key]=candidate; rollback[key]=data; managed.add(key)
    # Stable archive identity for the launcher receipt, without changing the
    # global renderer selector or any pinned earlier build inputs.
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for n,data in sorted(dlls.items()):
            info=tarfile.TarInfo('dxvk-3.1.1-sdbatch1/x32/'+n)
            info.size=len(data); info.mode=0o644; tar.addfile(info,io.BytesIO(data))
    payload=gzip.compress(buffer.getvalue(),compresslevel=6,mtime=0)
    renderer_archive=out/'dxvk-3.1.1-sdbatch1.tar.gz'; renderer_archive.write_bytes(payload)
    receipts_path=ROOT/'local/buffer-reuse-validate-uzpwmdes/switch/sleepingdogs-fex/launcher/dxvk-releases.json'
    old_receipts=json.loads(receipts_path.read_bytes())
    assert old_receipts['dxvk-3.1.1']['dlls']=={n:m['sha256'] for n,m in vendor['files'].items()}
    receipts=dict(old_receipts)
    receipts['dxvk-3.1.1']=dict(build=BUILD,url='https://github.com/doitsujin/dxvk/tree/'+build['commit'],
        archive_sha256=sha(renderer_archive),dlls={n:m['sha256'] for n,m in build['files'].items()},
        patch=dict(build=BUILD,option=OPTION,hardware_tested=False,fps_gain_measured=False))
    receipt_key=PREFIX+'launcher/dxvk-releases.json'
    entries[receipt_key]=encode(receipts); rollback[receipt_key]=encode(old_receipts)
    assert OPTION.encode() not in old[PERFORMANCE]
    entries[PERFORMANCE]=old[PERFORMANCE]+b'\n# Sleeping Dogs v12: optional small-hint submission batching\n'+(OPTION+' = True\n').encode()
    rollback[PERFORMANCE]=old[PERFORMANCE]
    mode_key=PREFIX+'launcher/dxvk-submit-batching.json'
    entries[mode_key]=encode(dict(build=BUILD,nro_sha256=NRO_SHA,option=OPTION,performance_enabled=True,
        dlls={n:m['sha256'] for n,m in build['files'].items()},target_resolution=[1280,720],
        hardware_tested=False,fps_gain_measured=False,native_runtime='unchanged v11'))
    rollback[mode_key]=encode(dict(build='sleepingdogs-dxvk-sdrecycle1',rolled_back=True,option_active=False))
    entries['README-INSTALL.txt']=(ROOT/'docs/low-window-submit-batching.md').read_bytes()
    allowed=managed|{receipt_key,PERFORMANCE,mode_key}
    for n,data in entries.items():
        if n.startswith(PREFIX) and n not in allowed: assert data==old[n],n
        if '/drive_c/' in n: assert n in managed,n
        assert not n.lower().endswith(('.exe','.log','.keys','.nsp','.kip','.big','.bix'))
        if n.endswith('.dll'): assert n in managed,n
    stage=ROOT/'dist'/NAME
    staged={}
    for n,data in entries.items():
        if not (n.startswith(PREFIX) or n=='README-INSTALL.txt'): continue
        target=stage/n; target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists(): assert target.read_bytes()==data,('staged file changed',n)
        else: target.write_bytes(data)
        if n.startswith(PREFIX): staged[n.removeprefix(PREFIX)]=hashlib.sha256(data).hexdigest()
    if a.stage_only:
        print('STAGED',stage,flush=True)
        return
    reports={}
    for name in ('host','binary','launcher'):
        report=json.loads((ROOT/'reports'/('dxvk-batch-'+name+'.json')).read_text())
        assert report['status']=='PASS'
        for n,h in report['sources'].items(): assert sha(ROOT/n)==h,n
        reports[name]=report
    assert reports['host']['candidate_sources']==build['changed']
    assert reports['binary']['dll_sha256']==build['files']['d3d11.dll']['sha256']
    assert reports['launcher']['staged_runtime_files']==staged
    assert reports['launcher']['nro_sha256']==NRO_SHA
    folder='source/dxvk-submit-batching/'
    for n in SOURCES: entries[folder+n]=(ROOT/n).read_bytes()
    entries[folder+'build.json']=encode(build)
    for n in FILES:
        entries[folder+'dxvk/'+n]=(a.work/'source'/n).read_bytes()
        entries[folder+'dxvk-base/'+n]=(previous/'source'/n).read_bytes()
    for n,report in reports.items(): entries[folder+'reports/'+n+'.json']=encode(report)
    entries[folder+'reports/gameplay-v11.json']=(ROOT/'reports/gameplay-v11-performance-analysis.json').read_bytes()
    rollback['README-INSTALL.txt']=b'Close FEXTendo from HOME. Copy the entire switch folder to the SD root and overwrite. Restores the sdrecycle1 DXVK DLL set and the v11 Performance preset. The v11 NRO, game files, saves and forwarder are unchanged.\n'
    rollback[folder+'DXVK-LICENSE']=(ROOT/'vendor/dxvk/DXVK-LICENSE').read_bytes()
    update=archive(ROOT/'dist'/(NAME+'.zip'),entries)
    undo=archive(ROOT/'dist'/(NAME+'-rollback.zip'),rollback)
    result=dict(status='PASS',build=BUILD,update=update,rollback=undo,interfaces=checks,
        baseline_zip_sha256=V11_SHA,baseline_preserved=sha(baseline)==V11_SHA,nro_sha256=NRO_SHA,
        native_runtime_unchanged=True,fex_adapter_unchanged=True,shared_sdk_unchanged=True,
        game_files_changed=[],managed_dll_copies=len(managed),target_resolution=[1280,720],
        performance_enabled=True,hardware_tested=False,fps_gain_measured=False,
        reports={n:sha(ROOT/'reports'/('dxvk-batch-'+n+'.json')) for n in reports})
    write_json(ROOT/'reports/dxvk-batch-package.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__ == '__main__': main()
