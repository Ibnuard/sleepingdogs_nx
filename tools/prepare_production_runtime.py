"""Freeze tested local production inputs for portable GitHub packaging.

Run in the prepared WSL workspace. Never copy the game directory or live SD.
Only catalog-pinned modules, Wine data, presets and named settings are inputs.
"""
from pathlib import Path
import argparse,json
from release_package import (ROOT,PREFIX,NRO,NSP,SOURCE_TOOLS,sha,encoded,
    fingerprints,write_zip,validate_payload,pfs_files,read_runtime)

LOCAL=ROOT/'local/production-v1'
BASE=ROOT/'dist/sd-launcher-v4-update'
FULL=ROOT/'local/buffer-reuse-validate-uzpwmdes/switch/sleepingdogs-fex'
WORK=Path('/home/blekjek/sleepingdogs-production-v1')
FORWARDER=Path('/home/blekjek/sleepingdogs-fxtmem-forwarder-v1')

def checked(path,digest):
    data=path.read_bytes()
    if sha(data)!=digest:raise ValueError('Changed input: '+str(path))
    return data

def prepare(output):
    build=json.loads((LOCAL/'build.json').read_text())
    reports={n:json.loads((LOCAL/n).read_text()) for n in ('policy-test.json','test.json','binary-test.json')}
    if any(r['status']!='PASS' for r in reports.values()):raise ValueError('Production tests must pass')
    for name in ('policy-test.json','binary-test.json'):
        if reports[name]['nro_sha256']!=build['nro_sha256']:raise ValueError('Stale production test')
    if reports['policy-test.json']['generated_sources']!=build['generated_sources']:
        raise ValueError('Stale production policy test')
    if reports['binary-test.json']['elf_sha256']!=build['elf_sha256']:
        raise ValueError('Stale linked-binary test')
    for name,digest in reports['test.json']['source_files'].items():checked(ROOT/name,digest)
    for name,digest in reports['policy-test.json']['sources'].items():checked(ROOT/name,digest)
    for group in ('source_files','scripts'):
        for name,digest in build[group].items():checked(ROOT/name,digest)
    checked(Path(build['elf']),build['elf_sha256'])
    files={NRO:checked(LOCAL/'sleepingdogs-fex.nro',build['nro_sha256'])}
    catalog=json.loads(checked(LOCAL/'catalog.json',build['catalog_sha256']))
    for item in catalog:
        files[PREFIX+item['path']]=checked(Path(item['source']),item['sha256'])
    # The previous delivery's inventory pins all reused presets and notices.
    sums=checked(BASE/'SHA256SUMS.txt','c4f15d5ab2a568459d587e950a14674f888daa503cf6680ec4471b6becc3e91f')
    for line in sums.decode().splitlines():
        digest,name=line.split('  ',1)
        if (name.startswith(('licenses/','source/')) or
            (name.startswith(PREFIX+'launcher/') and name.endswith('/dxvk.conf'))):
            files[name]=checked(BASE/name,digest)
    # These are Wine locale tables/fonts, never files from drive_c/SleepingDogs.
    for p in (FULL/'share/wine').rglob('*'):
        if p.is_file():files[PREFIX+p.relative_to(FULL).as_posix()]=p.read_bytes()
    for name in ('controller-gamepad.txt','controller-keyboard.txt','fex_auto_core3',
                 'fex_dxvk_balance','fex_fast_api','fex_polling','fex_short_trace_off'):
        files[PREFIX+name]=(FULL/name).read_bytes()
    files[PREFIX+'configuration.ini']=(ROOT/'config/configuration.ini').read_bytes()
    files[PREFIX+'run-native-com-test.txt']=b'0\n'
    files[PREFIX+'launcher/renderer-choice.txt']=b'2\n'
    files[PREFIX+'launcher/debug-launch.txt']=b'0\n'
    for name in ('d3d9.dll','d3d11.dll','dxgi.dll','sdndx4.dll','dxvk.conf'):
        files[PREFIX+'drive_c/SleepingDogs/'+name]=files[PREFIX+'launcher/renderers/dxvk-native-h4/'+name]
    files[PREFIX+'drive_c/dxvk/d3d9.dll']=files[PREFIX+'launcher/renderers/dxvk-3.1.1/d3d9.dll']
    files[PREFIX+'drive_c/SleepingDogs/COPY-YOUR-GAME-HERE.txt']=b'Copy your own original x86 Sleeping Dogs PC installation here. Keep the supplied renderer DLLs and dxvk.conf. Definitive Edition is unsupported.\n'
    for name in ('LICENSE','THIRD_PARTY.md'):files[name]=(ROOT/name).read_bytes()
    forwarder=json.loads((ROOT/'reports/forwarder-memory-v1.json').read_text())
    files[NSP]=checked(FORWARDER/'hacbrewpack_nsp/059a3db219b42000.nsp',
        'f893d51849443ae6da59925aeec8659f68e94b15347d8528ce56412fbad52598')
    files['evidence/forwarder.json']=encoded(forwarder)
    # Matching generated units, adapters, build recipes and their exact receipts.
    for name,digest in build['generated_sources'].items():
        files['source/generated/production/'+name]=checked(WORK/name,digest)
    inline=ROOT/'local/native-dxvk-inline-v1'
    inline_build=json.loads((inline/'build.json').read_text())
    for name,digest in inline_build['source_files'].items():
        files['source/generated/inline/'+name]=checked(inline/name,digest)
    for name in SOURCE_TOOLS+('prepare_production_runtime.py','release_package.py','test_production.py',
                             'test_production_launcher.py','test_production_binary.py'):
        files['source/tools/'+name]=(ROOT/'tools'/name).read_bytes()
    for p in (ROOT/'src').rglob('*'):
        if p.is_file():files['source/'+p.relative_to(ROOT).as_posix()]=p.read_bytes()
    for p in (FORWARDER/'source').rglob('*'):
        if p.is_file():files['source/forwarder/'+p.relative_to(FORWARDER/'source').as_posix()]=p.read_bytes()
    for p in (ROOT/'vendor').rglob('*'):
        if p.is_file() and any(x in p.name.upper() for x in ('LICENSE','COPYING','NOTICE')):
            files['licenses/'+p.relative_to(ROOT).as_posix()]=p.read_bytes()
    for name in ('build.json','policy-test.json','test.json','binary-test.json','catalog.json'):
        files['evidence/production/'+name]=(LOCAL/name).read_bytes()
    files['evidence/inline-build.json']=(inline/'build.json').read_bytes()
    files['evidence/launcher-v4-validation.json']=(ROOT/'reports/launcher-v4-validation.json').read_bytes()
    files[PREFIX+'launcher/build-production.json']=encoded(dict(version=build['version'],
        nro_sha256=build['nro_sha256'],normal_logs=False,explicit_debug=True))
    lock=dict(schema=1,tag='runtime-production-v1',asset=output.name,runtime_version=build['version'],
        files={n:sha(d) for n,d in sorted(files.items())},source_fingerprints=fingerprints(),
        forwarder_ncas={n:sha(d) for n,d in pfs_files(files[NSP]).items()})
    checks=validate_payload(files,lock)
    files['runtime-manifest.json']=encoded(dict(kind='production-v1',files=lock['files']))
    output.parent.mkdir(parents=True,exist_ok=True);write_zip(output,files)
    lock['sha256']=sha(output.read_bytes());read_runtime(output,lock)
    (ROOT/'release').mkdir(exist_ok=True)
    (ROOT/'release/runtime-lock.json').write_bytes(encoded(lock))
    summary=dict(status='PASS',runtime_sha256=lock['sha256'],runtime_bytes=output.stat().st_size,
        **checks,policy=reports['policy-test.json']['results'],saved_lsfg_preserved=True,
        last_played_independent=True,explicit_debug_supported=True)
    (ROOT/'reports/production-v1-validation.json').write_bytes(encoded(summary))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    prepare(p.parse_args().output)
