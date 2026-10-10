"""Build isolated AMS 1.11.2 / HOC 2.5.1 low-window components under WSL."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, urllib.request, zipfile, re
from port_common import ROOT, sha, write_json

AMS_REV = '5388824be146a89619e8d641acd64599cf1c5f62'
HOC_RELEASE = 'a6f1732e1d96577a8009d47c9b98e018080f3fe7'
HOC_LOADER = 'd9906a794c6015a892c60744d520faf793d22549'
AUTORUN = 'cbb0e4e6e7fa7f47f328d92441f51bfb507f266f'
TITLE_ID = '0x059A3DB219B42000'
AUDIT = ROOT / 'local/autorun-memory-audit/horizon-wine'

def run(*cmd, **kw):
    return subprocess.run(list(map(str, cmd)), check=True, **kw)

def revision(folder):
    return subprocess.check_output(['git', '-C', str(folder), 'rev-parse', 'HEAD'], text=True).strip()

def fetch(url, dest):
    if not dest.exists():
        with urllib.request.urlopen(url, timeout=90) as r: dest.write_bytes(r.read())

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-low-window-v1'))
    p.add_argument('--hoc', type=Path, default=Path('/mnt/d/Dev/Personal/UNDANGAN/hoc.kip'))
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args(); work=a.work; work.mkdir(parents=True, exist_ok=True)
    out=ROOT/'dist/low-window-fix/boot'; out.mkdir(parents=True, exist_ok=True)
    ams=work/'atmosphere'; hoc=work/'hoc'; hocams=work/'atmosphere-hoc'
    if not ams.exists(): run('git','clone','--depth','1','--branch','1.11.2','https://github.com/Atmosphere-NX/Atmosphere.git',ams)
    assert revision(ams)==AMS_REV
    patch=(AUDIT/'mesosphere/low-window.patch').read_text()
    old='return program_id == UINT64_C(0x0548EABB35576000);'
    assert patch.count(old)==1
    patch=patch.replace(old, 'return program_id == UINT64_C(0x0548EABB35576000) || program_id == UINT64_C('+TITLE_ID+');')
    patchfile=work/'sleepingdogs-low-window.patch'; patchfile.write_text(patch)
    if not (work/'ams-patched.json').exists():
        run('git','-C',ams,'apply','--check',patchfile)
        run('git','-C',ams,'apply',patchfile)
        write_json(work/'ams-patched.json',{'base':AMS_REV,'patch_sha256':sha(patchfile)})
    run('git','-C',ams,'apply','--reverse','--check',patchfile)
    if not hoc.exists(): run('git','clone','--depth','40','--branch','2.5.1','https://github.com/Horizon-OC/Horizon-OC.git',hoc)
    assert subprocess.check_output(['git','-C',str(hoc),'rev-parse','2.5.1'],text=True).strip()==HOC_RELEASE
    if revision(hoc)!=HOC_LOADER:
        run('git','-C',hoc,'fetch','--depth','1','origin',HOC_LOADER)
        run('git','-C',hoc,'checkout','--detach',HOC_LOADER)
    assert revision(hoc)==HOC_LOADER
    versionpatch=work/'hoc-2.5.1-version.patch'
    fetch(f'https://raw.githubusercontent.com/autorunhq/autorun/{AUTORUN}/horizon-wine/mesosphere/hoc-2.5.1-version.patch',versionpatch)
    if not (work/'hoc-patched.json').exists():
        run('git','-C',hoc,'apply','--check',versionpatch)
        run('git','-C',hoc,'apply',versionpatch)
        write_json(work/'hoc-patched.json',{'base':HOC_LOADER,'version_patch':sha(versionpatch)})
    run('git','-C',hoc,'apply','--reverse','--check',versionpatch)
    if not hocams.exists():
        run('git','clone','--local',ams,hocams)
        run('git','-C',hocams,'apply',patchfile)
        shutil.copytree(hoc/'Source/Atmosphere/stratosphere/loader',hocams/'stratosphere/loader',dirs_exist_ok=True)
        run('git','-C',hocams,'apply','--check',AUDIT/'mesosphere/hoc-low-window.patch')
        run('git','-C',hocams,'apply',AUDIT/'mesosphere/hoc-low-window.patch')
    env=dict(os.environ, DEVKITPRO='/opt/devkitpro',DEVKITA64='/opt/devkitpro/devkitA64',
             DEVKITARM='/opt/devkitpro/devkitARM',TMPDIR=str(work),TMP=str(work),TEMP=str(work))
    for tree,target in ((ams,'mesosphere'),(ams,'stratosphere/loader'),(hocams,'stratosphere/loader')):
        logfile=work/('boot-'+tree.name+'-'+target.replace('/','-')+'.log')
        print('Building',tree.name,target,flush=True)
        with logfile.open('w') as log: run('make','-s','-C',tree/target,'-j'+str(a.jobs),env=env,stdout=log,stderr=subprocess.STDOUT)
    build=Path('out/nintendo_nx_arm64_armv8a/release')
    # HOC's editable CUST must be uncompressed, matching the supplied KIP.
    elf=hocams/'stratosphere/loader'/build/'loader.elf'
    hactool=work/'hactool'
    if not hactool.exists():run('git','clone','--depth','1','--branch','1.4.0','https://github.com/SciresM/hactool.git',hactool)
    assert revision(hactool)=='3121a5bf08cd81d3a99719feb2cab3b60767afd5'
    if not (hactool/'hactool').exists():
        shutil.copy2(hactool/'config.mk.template',hactool/'config.mk')
        run('make','-s','-C',hactool,'CC=cc','-j'+str(a.jobs))
    kip=out/'loader-hoc-low-window.kip'
    run(hactool/'hactool','-t','kip1','--uncompressed='+str(kip),
        hocams/'stratosphere/loader'/build/'loader.kip',stdout=subprocess.DEVNULL)
    data=bytearray(kip.read_bytes())
    assert data[:4]==b'KIP1' and not data[31]&7, 'Need uncompressed HOC KIP'
    symbol=subprocess.check_output(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-nm','-S','--demangle',str(elf)],text=True)
    sizes=re.findall(r'^[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+\S\s+ams::ldr::hoc::C$',symbol,re.M)
    assert len(sizes)==1; size=int(sizes[0],16)
    off=data.find(b'CUST',256); assert off>=256 and data.find(b'CUST',off+4)==-1
    releasezip=work/'hoc-2.5.1.zip'
    fetch('https://github.com/Horizon-OC/Horizon-OC/releases/download/2.5.1/dist.zip',releasezip)
    assert sha(releasezip)=='48a57eef49032cbae615074676df4a5fb017aff40be3f45734a158d5b19ffa00'
    with zipfile.ZipFile(releasezip) as z: released=z.read('atmosphere/kips/hoc.kip')
    user=a.hoc.read_bytes(); roff=released.find(b'CUST',256); uoff=user.find(b'CUST',256)
    assert uoff==roff and roff>=256 and len(user)==len(released)
    assert user[:uoff+12]==released[:roff+12] and user[uoff+size:]==released[roff+size:], 'User HOC differs outside settings'
    assert data[off:off+size]==released[roff:roff+size], 'Source CUST ABI/defaults differ from release'
    data[off:off+size]=user[uoff:uoff+size]; kip.write_bytes(data)
    shutil.copy2(ams/'mesosphere'/build/'mesosphere.bin',out/'mesosphere-low-window.bin')
    shutil.copy2(ams/'stratosphere/loader'/build/'loader.kip',out/'loader-stock-low-window.kip')
    shutil.copy2(patchfile,out/patchfile.name)
    shutil.copy2(ams/'LICENSE',out/'LICENSE.Atmosphere'); shutil.copy2(hoc/'LICENSE',out/'LICENSE.HOC')
    write_json(out/'build.json',{'ams_revision':AMS_REV,'hoc_release':HOC_RELEASE,'hoc_source':HOC_LOADER,
        'autorun_revision':AUTORUN,'title_ids':['0548eabb35576000','059a3db219b42000'],
        'hos':'22.5.0','ams':'1.11.2','hoc':'2.5.1','hoc_input_sha256':sha(a.hoc),
        'hoc_settings_offset_original':uoff,'hoc_settings_offset_patched':off,'hoc_settings_bytes':size,
        'hoc_settings_sha256':hashlib.sha256(user[uoff:uoff+size]).hexdigest(),
        'files':{f.name:sha(f) for f in out.iterdir() if f.is_file() and f.name!='build.json'},'hardware_tested':False})
    print('Boot components built; HOC configuration preserved byte for byte.',flush=True)

if __name__=='__main__': main()
