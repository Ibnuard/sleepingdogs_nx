"""Build production v1 from the pinned launcher-v4 ELF/link inputs in WSL."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess

from production_overlay import ROOT, runtime, checker, logger, horizon_present

WORK=Path('/home/blekjek/sleepingdogs-production-v1')
LOCAL=ROOT/'local/production-v1'
BASE=ROOT/'local/launcher-v4'
OLDWORK=Path('/home/blekjek/sleepingdogs-launcher-v4')
VERSION='0.1.0-p1'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(data,newline='\n')
def run(args,name,cwd):
    with (WORK/(name+'.log')).open('w') as out:
        result=subprocess.run([str(x) for x in args],cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(name+': '+(WORK/(name+'.log')).read_text()[-9000:])


def prepare():
    LOCAL.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    old=json.loads((BASE/'build.json').read_text())
    assert old['nro_sha256']=='c7c8b5a4def6b89f2dac4fe47f280b06008cfe634a4543d8a4b95a7b8f442c76'
    assert sha(BASE/'sleepingdogs-fex.nro')==old['nro_sha256'] and sha(old['elf'])==old['elf_sha256']
    for name,digest in old['generated_sources'].items():assert sha(OLDWORK/name)==digest,name
    cwd=Path(old['working_directory'])
    inputs={str((cwd/a).resolve()):sha(cwd/a) for a in old['link_argv'] if a.endswith(('.obj','.o','.a'))}
    pin=LOCAL/'baseline-inputs.json'
    if pin.exists():assert json.loads(pin.read_text())==inputs,'Baseline objects changed'
    else:save(pin,json.dumps(inputs,indent=2)+'\n')
    source=WORK/'source';shutil.copytree(OLDWORK/'source',source,dirs_exist_ok=True)
    (WORK/'objects').mkdir(exist_ok=True)
    save(source/'runtime.c',runtime((OLDWORK/'source/runtime.c').read_text()))
    save(source/'checker_runtime.h',checker((ROOT/'src/launcher/checker_runtime.h').read_text()))
    save(source/'com_horizon.cpp',horizon_present((OLDWORK/'source/com_horizon.cpp').read_text()))
    for p in (ROOT/'src/production').glob('*.h'):shutil.copyfile(p,source/p.name)
    catalog=json.loads((BASE/'catalog.json').read_text())
    catalog=[e for e in catalog if not e['path'].startswith('lsfg/')]
    save(LOCAL/'catalog.json',json.dumps(catalog,indent=2)+'\n')
    generated=(OLDWORK/'source/system_catalog.h').read_text()
    generated='\n'.join(line for line in generated.splitlines() if '"lsfg/' not in line)+'\n'
    key=hashlib.sha256((generated+sha(source/'runtime.c')+sha(source/'checker_runtime.h')).encode()).hexdigest()
    generated=generated[:generated.index('#define SD_CHECK_CACHE_BUILD')]+f'#define SD_CHECK_CACHE_BUILD "{key}"\n'
    save(source/'system_catalog.h',generated)
    commands={};replacements={}
    for name in ('runtime','com_horizon'):
        command=[x.replace(str(OLDWORK),str(WORK)) for x in old['compile_commands'][name]]
        command.insert(1,'-I'+str(source))
        commands[name]=command
        replacements[old['compile_commands'][name][old['compile_commands'][name].index('-o')+1]]=command[command.index('-o')+1]
    dxvk=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1')
    item=next(x for x in json.loads((dxvk/'build-horizon/compile_commands.json').read_text()) if x['file'].endswith('/log.cpp'))
    original=Path(item['file']);save(source/'dxvk-log.cpp',logger(original.read_text()))
    command=shlex.split(item['command']);command[command.index('-c')+1]=str(source/'dxvk-log.cpp')
    command[command.index('-o')+1]=str(WORK/'objects/dxvk-log.o')
    command.insert(1,'-I'+str(original.parent));commands['dxvk-log']=command
    link=[replacements.get(a,a) for a in old['link_argv']]
    elf=WORK/'sleepingdogs-production-v1.elf';link[link.index('-o')+1]=str(elf)
    link=[('-Wl,-Map='+str(WORK/'production.map') if x.startswith('-Wl,-Map=') else x) for x in link]
    # Resolve every Logger method before the archive; the old logging object is
    # then not pulled in. No renderer/driver code or archive is modified.
    index=next(i for i,x in enumerate(link) if x.endswith('/libsd_native_dxvk_com.a'))
    link.insert(index,str(WORK/'objects/dxvk-log.o'))
    record=dict(build='production-v1',version=VERSION,baseline_nro_sha256=old['nro_sha256'],
                baseline_build_sha256=sha(BASE/'build.json'),inputs=inputs,
                generated_sources={p.relative_to(WORK).as_posix():sha(p) for p in source.rglob('*') if p.is_file()},
                source_files={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'src/production').glob('*.h')},
                scripts={p.relative_to(ROOT).as_posix():sha(p) for p in (Path(__file__),ROOT/'tools/production_overlay.py')},
                logger_input=dict(path=str(original),sha256=sha(original)),
                compile_commands=commands,link_argv=link,working_directory=str(cwd),elf=str(elf),
                catalog_sha256=sha(LOCAL/'catalog.json'),saved_lsfg_preserved=True,
                normal_logs=False,explicit_debug_supported=True,hardware_tested=False)
    save(LOCAL/'prepared.json',json.dumps(record,indent=2)+'\n');return record


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    assert os.name=='posix';os.environ.setdefault('DEVKITPRO','/opt/devkitpro')
    record=prepare()
    if args.prepare_only:print('Prepared production-v1');return
    for name,command in record['compile_commands'].items():
        print('Compiling',name,flush=True);run(command,name,record['working_directory'])
    print('Linking production-v1',flush=True);run(record['link_argv'],'link',record['working_directory'])
    nacp=WORK/'production.nacp';nro=WORK/'sleepingdogs-fex.nro'
    run(['/opt/devkitpro/tools/bin/nacptool','--create','Sleeping Dogs - FEXTendo','AndroSwitch Project',VERSION,nacp],'nacp',WORK)
    run(['/opt/devkitpro/tools/bin/elf2nro',record['elf'],nro,'--nacp='+str(nacp)],'nro',WORK)
    shutil.copy2(nro,LOCAL/nro.name)
    record.update(status='BUILT',nro_sha256=sha(nro),elf_sha256=sha(record['elf']),nro_bytes=nro.stat().st_size)
    save(LOCAL/'build.json',json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('status','version','nro_sha256','nro_bytes')}),flush=True)


if __name__=='__main__':main()
