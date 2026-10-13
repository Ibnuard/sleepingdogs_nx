"""Portable distribution CI: pinned runtime, exact inventory, no game/LSFG payload."""
from pathlib import Path, PurePosixPath
import argparse,hashlib,json,re,stat,struct,zipfile

ROOT=Path(__file__).resolve().parents[1]
PREFIX='switch/sleepingdogs-fex/'
NRO=PREFIX+'sleepingdogs-fex.nro'
NSP='FEXTendo-SleepingDogs-39bit-FEXTendoMemory-v1.nsp'
SOURCE_TOOLS=('build_production.py','production_overlay.py','build_launcher_v4.py','launcher_v4_overlay.py',
    'launcher_v4_runtime.py','build_launcher_v2.py','launcher_v3_overlay.py','launcher_v2_overlay.py',
    'launcher_v1_overlay.py','native_dxvk_compact.py','native_dxvk_inline.py','build_native_dxvk_inline.py',
    'native_dxvk_present_overlap.py','build_startup_config.py')

def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(data):return (json.dumps(data,indent=2,sort_keys=True)+'\n').encode()
def safe_name(name):
    p=PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or p.as_posix()!=name.rstrip('/'):
        raise ValueError('Unsafe archive path: '+name)
    return p

def fingerprints(root=ROOT):
    paths=[p for p in (root/'src').rglob('*') if p.is_file() and p.suffix.lower() not in ('.md','.pyc')]
    paths += [root/'tools'/n for n in SOURCE_TOOLS]
    return {p.relative_to(root).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n')) for p in sorted(paths)}

def verify_sources(lock,root=ROOT):
    if fingerprints(root)!=lock['source_fingerprints']:
        raise ValueError('Runtime sources changed: rebuild the production input and refresh its lock')

def forbidden(name):
    low=name.lower();p=safe_name(name)
    return (p.suffix.lower() in ('.exe','.big','.bix','.sdp','.keys','.log','.rar','.zip') or
            low.endswith(('/lossless.dll','/losslessscaling.dll')) or
            ('lossless' in p.name.lower() and p.suffix.lower()=='.dll') or
            p.name.lower() in ('prod.keys','title.keys','stdout.txt','stderr.txt','stdin.txt','useroptions.dat') or
            any(x in p.parts for x in ('__pycache__','.git')))

def validate_path(name):
    if forbidden(name):raise ValueError('Forbidden distributed payload: '+name)
    p=safe_name(name)
    if name==NSP or name in ('LICENSE','THIRD_PARTY.md','README.txt'):return
    if name.startswith(('source/','evidence/','licenses/')):
        if p.suffix.lower() in ('.dll','.nro','.nsp','.dat','.bin','.elf','.o','.obj','.a'):
            raise ValueError('Unexpected binary in source/evidence: '+name)
        return
    if not name.startswith(PREFIX):raise ValueError('Unknown package root: '+name)
    path=name[len(PREFIX):]
    if path=='sleepingdogs-fex.nro':return
    if path.startswith('drive_c/SleepingDogs/'):
        if path.removeprefix('drive_c/SleepingDogs/') not in {
            'd3d9.dll','d3d11.dll','dxgi.dll','sdndx4.dll','dxvk.conf','HKShip.wine-nx.txt','COPY-YOUR-GAME-HERE.txt'}:
            raise ValueError('Game data is never a release input: '+name)
        return
    if path.startswith('drive_c/windows/') and p.suffix.lower()=='.dll':return
    if path=='drive_c/dxvk/d3d9.dll':return
    if path.startswith('share/wine/') and p.suffix.lower() in ('.nls','.ttf','.fon','.inf'):return
    if path.startswith('launcher/renderers/') and p.name in ('d3d9.dll','d3d11.dll','dxgi.dll','sdndx4.dll','dxvk.conf'):return
    if path.startswith('launcher/presets/') and p.name=='dxvk.conf':return
    if path.startswith('launcher/') and '/' not in path[len('launcher/'):] and p.name in {
        'background-music.bin','background.rgba','blur.rgba','buttons.rgba','credits-icon.rgba','font.bin',
        'gamepad.rgba','icon.rgba','logo.rgba','settings-icon.rgba','timestamp-font.bin','wordmark.rgba',
        'nro-icon.jpg','renderer-choice.txt','debug-launch.txt','build-production.json','fex-mode.txt'}:return
    if '/' not in path and path in {
        'configuration.ini','production.txt','run-native-com-test.txt','run-guest-tests.txt',
        'controller-gamepad.txt','controller-keyboard.txt','fex_auto_core3','fex_dxvk_balance','fex_fast_api',
        'fex_polling','fex_short_trace_off','auto-affinity.txt','shader-affinity.txt','shader-cache.txt',
        'apc-wake.txt','sync-notify.txt','sync-mode.txt','native-dxvk-batch.txt'}:return
    raise ValueError('File is not on the public runtime allowlist: '+name)

def pfs_files(blob):
    if blob[:4]!=b'PFS0':raise ValueError('Invalid PFS0')
    count,strings=struct.unpack_from('<II',blob,4)
    if count>1000:raise ValueError('Invalid PFS count')
    start=16+24*count;payload=start+strings;result={}
    if payload>len(blob):raise ValueError('Truncated PFS')
    for i in range(count):
        off,size,nameoff,_=struct.unpack_from('<QQII',blob,16+24*i)
        if nameoff>=strings or payload+off+size>len(blob):raise ValueError('Invalid PFS member')
        end=blob.find(b'\0',start+nameoff,payload)
        if end<0:raise ValueError('Invalid PFS name')
        name=blob[start+nameoff:end].decode();safe_name(name)
        if name in result:raise ValueError('Duplicate PFS member')
        result[name]=blob[payload+off:payload+off+size]
    return result

def validate_payload(files,lock):
    for name in files:validate_path(name)
    for name in (NRO,NSP,PREFIX+'configuration.ini',PREFIX+'drive_c/windows/system32/libwow64fex.dll',
                 PREFIX+'drive_c/windows/system32/ntdll.dll',PREFIX+'drive_c/windows/syswow64/ntdll.dll',
                 PREFIX+'drive_c/SleepingDogs/sdndx4.dll',PREFIX+'share/wine/nls/locale.nls'):
        if name not in files:raise ValueError('Missing runtime file: '+name)
    if {n:sha(d) for n,d in files.items()}!=lock['files']:raise ValueError('Runtime inventory/hash mismatch')
    nro=files[NRO]
    if nro[16:20]!=b'NRO0':raise ValueError('Not an NRO')
    assets=struct.unpack_from('<I',nro,0x18)[0]
    if nro[assets:assets+4]!=b'ASET':raise ValueError('Missing NRO metadata')
    off,size=struct.unpack_from('<QQ',nro,assets+24)
    nacp=nro[assets+off:assets+off+size]
    if len(nacp)!=0x4000 or nacp[0x3060:0x3070].split(b'\0')[0].decode()!=lock['runtime_version']:
        raise ValueError('NRO version differs from pinned runtime')
    ncas=pfs_files(files[NSP]);expected=lock['forwarder_ncas']
    if {n:sha(d) for n,d in ncas.items()}!=expected:raise ValueError('Forwarder contents differ')
    for name,data in files.items():
        if name.endswith('.dll'):
            if data[:2]!=b'MZ' or len(data)<64:raise ValueError('Invalid runtime DLL: '+name)
            pe=struct.unpack_from('<I',data,0x3c)[0]
            if pe+24>len(data) or data[pe:pe+4]!=b'PE\0\0':raise ValueError('Invalid PE: '+name)
            machine=struct.unpack_from('<H',data,pe+4)[0]
            target=0xaa64 if '/windows/system32/' in name else 0x14c
            if machine!=target:raise ValueError('Wrong DLL architecture: '+name)
    return dict(files=len(files),nro_sha256=sha(nro),forwarder_sha256=sha(files[NSP]),
                no_game_data=True,no_lossless_dll=True,no_proprietary_shader_pack=True,
                normal_logs=False,hardware_tested=False)

def read_runtime(path,lock):
    if sha(path.read_bytes())!=lock['sha256']:raise ValueError('Runtime archive SHA256 mismatch')
    files={};lower=set();total=0
    with zipfile.ZipFile(path) as z:
        for item in z.infolist():
            safe_name(item.filename);total+=item.file_size
            if (item.is_dir() or item.filename.lower() in lower or stat.S_ISLNK(item.external_attr>>16)
                or item.file_size>128*1024*1024 or total>1024*1024*1024):raise ValueError('Unsafe runtime member')
            lower.add(item.filename.lower());files[item.filename]=z.read(item)
    manifest=json.loads(files.pop('runtime-manifest.json'))
    if manifest['files']!=lock['files']:raise ValueError('Embedded runtime manifest differs')
    validate_payload(files,lock);return files

def write_zip(path,files):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in sorted(files.items()):
            safe_name(name);item=zipfile.ZipInfo(name,(2026,1,1,0,0,0))
            item.external_attr=(stat.S_IFREG|0o644)<<16;item.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(item,data)

def assemble(runtime,output,version,commit,lock_path=None,folder_only=False):
    if not re.fullmatch(r'v?\d+\.\d+\.\d+(?:-[a-z0-9]+)*',version):raise ValueError('Invalid release version')
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Invalid source commit')
    lock=json.loads((lock_path or ROOT/'release/runtime-lock.json').read_text());verify_sources(lock)
    files=read_runtime(runtime,lock);checks=validate_payload(files,lock)
    files['README.txt']=(ROOT/'release/README.txt').read_bytes()
    manifest=dict(package_version=version,source_commit=commit,runtime_version=lock['runtime_version'],
                  runtime_sha256=lock['sha256'],checks=checks,files={n:sha(d) for n,d in sorted(files.items())})
    files['manifest.json']=encoded(manifest);output.mkdir(parents=True,exist_ok=False)
    if folder_only:
        for name,data in files.items():
            dest=output/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    else:
        archive=output/f'SleepingDogs-FEXTendo-{version}-sd.zip';write_zip(archive,files)
        with zipfile.ZipFile(archive) as z:
            if z.testzip() or any(sha(z.read(n))!=d for n,d in manifest['files'].items()):raise ValueError('Final ZIP differs')
        (output/'sleepingdogs-fex.nro').write_bytes(files[NRO]);(output/NSP).write_bytes(files[NSP])
        (output/'manifest.json').write_bytes(files['manifest.json'])
    items=sorted(p for p in output.rglob('*') if p.is_file())
    (output/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.relative_to(output).as_posix()+'\n' for p in items))
    print(json.dumps(dict(status='PASS',path=str(output),**checks),indent=2))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--version',required=True);p.add_argument('--commit',required=True);p.add_argument('--folder-only',action='store_true')
    a=p.parse_args();assemble(a.runtime,a.output,a.version,a.commit,folder_only=a.folder_only)
