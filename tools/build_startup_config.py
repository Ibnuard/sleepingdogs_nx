"""Rebuild the tested production runtime with embedded startup repair (0.1.1)."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
from production_overlay import ROOT

LOCAL=ROOT/'local/startup-config-v011'
WORK=Path('/home/blekjek/sleepingdogs-startup-config-v011')
BASE=ROOT/'local/production-v1'
OLDWORK=Path('/home/blekjek/sleepingdogs-production-v1')
VERSION='0.1.1'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value,newline='\n')
def run(command,name,cwd):
    with (WORK/(name+'.log')).open('w') as output:
        result=subprocess.run([str(a) for a in command],cwd=cwd,stdout=output,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError((WORK/(name+'.log')).read_text()[-7000:])

def main():
    assert os.name=='posix';os.environ.setdefault('DEVKITPRO','/opt/devkitpro')
    LOCAL.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    old=json.loads((BASE/'build.json').read_text())
    assert old['nro_sha256']=='e6169af1a3ead1aeaf53c0ee9c70f8e322cc70a4d6f9a26bc765ea24ddc734b3'
    assert sha(BASE/'sleepingdogs-fex.nro')==old['nro_sha256']
    for name,digest in old['generated_sources'].items():assert sha(OLDWORK/name)==digest,name
    for name,digest in old['inputs'].items():assert sha(name)==digest,name
    source=WORK/'source';shutil.copytree(OLDWORK/'source',source,dirs_exist_ok=True)
    (WORK/'objects').mkdir(exist_ok=True)
    for name in ('system_check.h','startup_config.h','startup_config_data.h'):
        shutil.copyfile(ROOT/'src/launcher'/name,source/name)
    runtime=(source/'runtime.c').read_text()
    runtime=runtime.replace('0.1.0-production.1','0.1.1').replace('sleepingdogs-production-v1','sleepingdogs-production-v0.1.1')
    old_line='        if(ready&&!wine_nx_f1_prepare_threads(thread_error,sizeof(thread_error))){'
    assert runtime.count(old_line)==1
    runtime=runtime.replace(old_line,
        '        if(ready&&!sd_startup_config_restore(RUNTIME_DIR,thread_error,sizeof(thread_error))){\n'
        '            ready=0;launch_error=thread_error;log_line("[SD-STARTUP-CONFIG] %s",thread_error);\n'
        '        }\n'+old_line,1)
    save(source/'runtime.c',runtime)
    # Cache identity changes with all headers involved in startup validation.
    catalog_source=(source/'system_catalog.h').read_text()
    key=hashlib.sha256((catalog_source+runtime+''.join(sha(source/n) for n in
        ('system_check.h','startup_config.h','startup_config_data.h'))).encode()).hexdigest()
    catalog_source=catalog_source[:catalog_source.index('#define SD_CHECK_CACHE_BUILD')]+f'#define SD_CHECK_CACHE_BUILD "{key}"\n'
    save(source/'system_catalog.h',catalog_source)
    shutil.copyfile(BASE/'catalog.json',LOCAL/'catalog.json')
    command=[a.replace(str(OLDWORK),str(WORK)) for a in old['compile_commands']['runtime']]
    before=old['compile_commands']['runtime'];obj=command[command.index('-o')+1]
    cwd=Path(old['working_directory'])
    run(command,'runtime',cwd)
    link=[obj if a==before[before.index('-o')+1] else a for a in old['link_argv']]
    elf=WORK/'sleepingdogs-v0.1.1.elf';link[link.index('-o')+1]=str(elf)
    link=[('-Wl,-Map='+str(WORK/'release.map') if a.startswith('-Wl,-Map=') else a) for a in link]
    # Reused native Present/logger objects preserve the production quiet policy.
    run(link,'link',cwd)
    nacp=WORK/'release.nacp';nro=WORK/'sleepingdogs-fex.nro'
    run(['/opt/devkitpro/tools/bin/nacptool','--create','Sleeping Dogs - FEXTendo','AndroSwitch Project',VERSION,nacp],'nacp',WORK)
    run(['/opt/devkitpro/tools/bin/elf2nro',elf,nro,'--nacp='+str(nacp)],'nro',WORK)
    shutil.copy2(nro,LOCAL/nro.name)
    inputs={str((cwd/a).resolve()):sha(cwd/a) for a in link if a.endswith(('.obj','.o','.a'))}
    record=dict(build='startup-config-v011',version=VERSION,baseline_nro_sha256=old['nro_sha256'],
        baseline_build_sha256=sha(BASE/'build.json'),inputs=inputs,
        generated_sources={p.relative_to(WORK).as_posix():sha(p) for p in source.rglob('*') if p.is_file()},
        source_files={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'src/production').glob('*.h')},
        scripts={p.relative_to(ROOT).as_posix():sha(p) for p in (Path(__file__),ROOT/'tools/production_overlay.py')},
        compile_commands={'runtime':command},link_argv=link,working_directory=str(cwd),elf=str(elf),
        catalog_sha256=sha(LOCAL/'catalog.json'),status='BUILT',nro_sha256=sha(nro),
        elf_sha256=sha(elf),nro_bytes=nro.stat().st_size,normal_logs=False,explicit_debug_supported=True,
        startup_defaults_embedded=True,restore_missing_only=True,hardware_tested=False)
    save(LOCAL/'build.json',json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('status','version','nro_sha256','nro_bytes')}))

if __name__=='__main__':main()
