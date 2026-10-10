"""Package a cumulative low-window update and the exact previous runtime rollback."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile,subprocess,sys
from port_common import ROOT,sha,write_json
from package_named_pipe import PREFIX,archive,encode
from build_low_window import BASE_ZIP_SHA,ZIP
from build_dxvk_memory import manifest
from dxvk_runtime import release_files

def digest(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    p.add_argument('--ini',type=Path,default=Path('/mnt/d/Dev/Personal/UNDANGAN/hekate_ipl.ini'))
    p.add_argument('--hoc',type=Path,default=Path('/mnt/d/Dev/Personal/UNDANGAN/hoc.kip'))
    a=p.parse_args();out=ROOT/'dist/low-window-fix';work=a.work
    assert sha(ZIP)==BASE_ZIP_SHA
    native=json.loads((out/'native.json').read_text());boot=json.loads((out/'boot/build.json').read_text())
    fw=json.loads((out/'forwarder/build.json').read_text())
    assert native['nro_sha256']==sha(out/'sleepingdogs-fex.nro')==fw['nro_sha256']
    assert sha(ROOT/'local/symbols/sleepingdogs-low-window.elf')==native['elf_sha256']
    assert native['source_files']==manifest(work/'native-source')
    for name,h in native['build_inputs'].items():assert sha(ROOT/name)==h,name
    assert native['adapter_files']==manifest(work/'fex-adapter')
    for name,h in boot['files'].items():assert sha(out/'boot'/name)==h,name
    assert sha(a.hoc)==boot['hoc_input_sha256']
    assert sha(out/'forwarder'/fw['nsp'])==fw['sha256'] and fw['packed_payload_verified']
    assert fw['address_space']=='39-bit low-window' and fw['title_id']=='059a3db219b42000'
    assert fw['system_resource_bytes']==16777216
    checks={}
    for name in ('low-window-arena-full','low-window-binary','low-window-boot'):
        j=json.loads((ROOT/'reports'/f'{name}.json').read_text());assert j['status']=='PASS'
        if 'elf_sha256' in j:assert j['elf_sha256']==native['elf_sha256']
        for n,h in j.get('source_files',{}).items():assert sha(work/'native-source'/n)==h,n
        for key in ('tests','sources'):
            for n,h in j.get(key,{}).items():assert sha(ROOT/n)==h,n
        checks[name]=j
    with zipfile.ZipFile(ZIP) as z:old={n:z.read(n) for n in z.namelist() if not n.endswith('/') and n!='SHA256SUMS.txt'}
    entries=dict(old);rollback={}
    nro_name=PREFIX+'sleepingdogs-fex.nro';rollback[nro_name]=old[nro_name];entries[nro_name]=(out/'sleepingdogs-fex.nro').read_bytes()
    changed=[]
    for name,data in list(entries.items()):
        if name.startswith(PREFIX+'launcher/') and name.endswith('.json') and '/presets/' not in name:
            j=json.loads(data);touched=False
            for key in ('nro_sha256',):
                if key in j:j[key]=native['nro_sha256'];touched=True
            for key in ('forwarder_sha256','compatible_forwarder_sha256'):
                if key in j:j[key]=fw['sha256'];touched=True
            if touched:
                j['additional_overlay']='sleepingdogs-low-window-v1';j['hardware_tested']=False
                if name.endswith('/direct-arena-fix.json'):
                    j['virtual_alias_bytes']=1048576000;j['arena_mode']='high backing / low guest alias'
                rollback[name]=data;entries[name]=encode(j);changed.append(name)
    entries[PREFIX+'launcher/low-window-fix.json']=encode({
        'build':native['build'],'nro_sha256':native['nro_sha256'],'forwarder_sha256':fw['sha256'],
        'address_space_bits':39,'kernel_required':'AMS 1.11.2 low-window','hoc':'2.5.1 (user CUST preserved)',
        'guest_base':'0x30000000','arena_bytes':1048576000,'fex_profile':'fastest','hardware_tested':False})
    for name in list(entries):
        if name.startswith('forwarder/'):
            rollback[name]=entries.pop(name)
    for path in sorted((out/'forwarder').rglob('*')):
        if path.is_file():entries['forwarder/'+path.relative_to(out/'forwarder').as_posix()]=path.read_bytes()
    entries['atmosphere/sleepingdogs-low-window/mesosphere.bin']=(out/'boot/mesosphere-low-window.bin').read_bytes()
    entries['atmosphere/sleepingdogs-low-window/loader-hoc.kip']=(out/'boot/loader-hoc-low-window.kip').read_bytes()
    ini=a.ini.read_bytes();text=ini.decode('utf-8-sig')
    # Derive only the existing EMUMMC entry; never alter SYSNAND/Stock/global settings.
    start=text.index('[CFW (EMUMMC)]');tail=text[start:].splitlines();lines=[]
    for line in tail[1:]:
        if line.startswith('[') or line.startswith('{'):break
        if line.strip():lines.append(line.strip())
    assert 'pkg3=atmosphere/package3' in lines and 'emummcforce=1' in lines
    assert lines.count('kip1=atmosphere/kips/hoc.kip')==1
    newlines=[]
    for line in lines:
        if line=='kip1=atmosphere/kips/hoc.kip':line='kip1=atmosphere/sleepingdogs-low-window/loader-hoc.kip'
        newlines.append(line)
        if line=='pkg3=atmosphere/package3':newlines.append('kernel=atmosphere/sleepingdogs-low-window/mesosphere.bin')
    entry='[CFW EMUMMC SD Low Window]\n'+'\n'.join(newlines)+'\n'
    entries['bootloader/ini/sleepingdogs-low-window.ini']=entry.encode()
    assert 'bootloader/hekate_ipl.ini' not in entries
    assert 'atmosphere/kips/hoc.kip' not in entries
    entries['README-INSTALL.txt']=(ROOT/'docs/low-window-fix.md').read_bytes()
    rollback['README-ROLLBACK.txt']=('Copy switch/, reinstall forwarder/FEXTendo-SleepingDogs-32bit.nsp, then reboot using the ORIGINAL CFW (EMUMMC) Hekate entry. Game/save files are not included or overwritten. Original boot files were never replaced; backup-input is reference only.\n').encode()
    rollback['backup-input/hekate_ipl.ini']=ini;rollback['backup-input/hoc.kip']=a.hoc.read_bytes()
    # Historical receipts in source/ stay historical. New source/ contains the actual overlay/build proof.
    source_prefix='source/low-window-fix/'
    for path in sorted((out/'boot').iterdir()):
        if path.is_file():entries[source_prefix+'boot/'+path.name]=path.read_bytes()
    for tree,files in checks['low-window-boot']['compiled_source_changes'].items():
        for name,h in files.items():
            path=work/tree/name;assert sha(path)==h
            entries[source_prefix+'boot-source/'+tree+'/'+name]=path.read_bytes()
    for path in sorted((work/'atmosphere-hoc/stratosphere/loader/source').rglob('*')):
        if path.is_file():
            entries[source_prefix+'boot-source/atmosphere-hoc/stratosphere/loader/source/'+
                path.relative_to(work/'atmosphere-hoc/stratosphere/loader/source').as_posix()]=path.read_bytes()
    entries[source_prefix+'boot-source/hoc-2.5.1-version.patch']=(work/'hoc-2.5.1-version.patch').read_bytes()
    entries[source_prefix+'native.json']=encode(native)
    entries[source_prefix+'inputs.json']=encode({'base_zip_sha256':BASE_ZIP_SHA,'hekate_ipl_sha256':digest(ini),
        'hoc_input_sha256':sha(a.hoc),'old_nro_sha256':digest(old[nro_name]),'native_unchanged_profile':'fastest'})
    for name in native['source_changes']:entries[source_prefix+'native/'+name]=(work/'native-source'/name).read_bytes()
    for path in sorted((work/'forwarder-final/source').iterdir()):
        if path.is_file():entries[source_prefix+'forwarder-source/'+path.name]=path.read_bytes()
    local_files=['tools/build_low_window.py','tools/build_low_window_boot.py','tools/package_low_window.py',
        'tools/f1_base_build.py','forwarder/build_forwarder.py','tests/check_low_window_arena.py',
        'tests/check_low_window_binary.py','tests/check_low_window_boot.py','tests/low_window_arena_boundary.inc',
        'tests/direct_arena.c','docs/low-window-fix.md']
    local_files += [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/low_window').glob('*') if p.is_file()]
    for name in local_files:entries[source_prefix+name]=(ROOT/name).read_bytes()
    for name,j in checks.items():entries[source_prefix+'reports/'+name+'.json']=encode(j)
    # Every existing DLL, preset, runtime ancillary file and FEX policy is byte-identical.
    permitted=set(changed+[nro_name])|{n for n in old if n.startswith('forwarder/')}|{'README-INSTALL.txt'}
    for name,data in old.items():
        if name not in permitted:assert entries[name]==data,name
    for name in entries:
        assert '\\' not in name and not name.startswith('/') and '..' not in Path(name).parts
        assert not name.lower().endswith(('.keys','crash.log','fex-runtime.log'))
        if name.startswith(PREFIX+'drive_c/SleepingDogs/'):
            assert name in old and entries[name]==old[name],name
    update=ROOT/'dist/sleepingdogs-fex-low-window-fix.zip'
    report={'update':archive(update,entries),'rollback':archive(ROOT/'dist/sleepingdogs-fex-low-window-rollback.zip',rollback),
        'nro_sha256':native['nro_sha256'],'forwarder_sha256':fw['sha256'],'boot':boot,
        'changed_existing_files':sorted(permitted),'baseline_payload_preserved':True,'hardware_tested':False}
    # This is a cumulative update, not the original full installation. Recreate
    # unchanged base renderer files from their pinned release archives. Require
    # the old shipped metadata to authenticate every pre-existing byte.
    fixtures={};existing={}
    with zipfile.ZipFile(update) as z:
        for name in z.namelist():
            if name.startswith((PREFIX+'launcher/renderers/',PREFIX+'launcher/presets/')):
                fixtures[name]=z.read(name)
    releases=json.loads(old[PREFIX+'launcher/dxvk-releases.json'])
    for renderer,files in release_files().items():
        for name,data in files.items():
            assert digest(data)==releases[renderer]['dlls'][name]
            target=PREFIX+'launcher/renderers/'+renderer+'/'+name
            if target in fixtures:assert fixtures[target]==data
            else:fixtures[target]=data;existing[target]=digest(data)
    merged=work/'launcher-installed-fixture.zip'
    with zipfile.ZipFile(merged,'w') as z:
        for name,data in fixtures.items():z.writestr(name,data)
    # Run the real C gate on final update bytes plus the authenticated base DLLs.
    run=subprocess.run([sys.executable,str(ROOT/'tests/check_renderer_package.py'),'--source',str(work/'native-source'),
        '--update',str(merged),'--output',str(work/'launcher-check')],text=True,capture_output=True,timeout=90)
    (out/'launcher-check.txt').write_text(run.stdout+run.stderr)
    assert run.returncode==0,run.stdout+run.stderr
    report['launcher_check']=run.stdout.strip();report['pre_existing_renderer_files']=existing;report['status']='PASS'
    write_json(ROOT/'reports/low-window-package.json',report)
    print(json.dumps({k:report[k] for k in ('status','update','rollback','launcher_check')},indent=2))

if __name__=='__main__':main()
