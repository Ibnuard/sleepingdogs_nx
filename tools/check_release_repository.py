"""Fail CI if tracked files contain private/game payloads or stale runtime code."""
import json,subprocess,tarfile
from pathlib import PurePosixPath
from release_package import ROOT,forbidden,verify_sources,sha,safe_name

def check_vendor_archive(path):
    with tarfile.open(path,'r:gz') as archive:
        seen=set()
        for item in archive:
            p=safe_name(item.name);key=item.name.lower()
            if key in seen or item.issym() or item.islnk():raise ValueError('Unsafe vendor archive member')
            seen.add(key)
            if item.isdir():continue
            if (not item.isfile() or item.size>64*1024*1024 or forbidden(item.name) or
                p.name not in ('d3d8.dll','d3d9.dll','d3d10core.dll','d3d11.dll','dxgi.dll')):
                raise ValueError('Private or unexpected vendor archive member: '+item.name)
            if archive.extractfile(item).read(2)!=b'MZ':raise ValueError('Invalid vendor PE')

def check():
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    vendor=json.loads((ROOT/'release/public-vendor-lock.json').read_text())
    bad=[]
    for name in filter(None,names):
        p=PurePosixPath(name)
        # Retained textual probe evidence is not a runtime payload or a live log.
        if name.startswith('reports/') and p.name in ('stdout.txt','stderr.txt'):
            (ROOT/name).read_text(encoding='utf-8')
            continue
        if name in vendor:
            if sha((ROOT/name).read_bytes())!=vendor[name]:raise ValueError('Changed approved vendor input: '+name)
            if name.endswith('.tar.gz'):check_vendor_archive(ROOT/name)
            continue
        if (forbidden(name) or p.suffix.lower() in ('.nro','.nsp','.dll','.7z') or
            p.suffix.lower() in ('.gz','.tar','.xz','.dat','.bin') or
            name.lower().startswith(('drive_c/','switch/','dist/','local/'))):bad.append(name)
    if bad:raise ValueError('Non-source/private payload tracked: '+', '.join(bad))
    lock=json.loads((ROOT/'release/runtime-lock.json').read_text())
    verify_sources(lock)
    print('PASS: source/vendor inventory excludes game/private payloads; runtime source fingerprints match')

if __name__=='__main__':check()
