"""Strip debug-only sections, retain COFF symbols, and pin the renderer archive."""
from pathlib import Path
import gzip
import io
import json
import subprocess
import tarfile
from port_common import ROOT,sha,write_json
from sleepingdogs_dxvk_memory import COMMIT,MARKER


def main():
    out=ROOT/'dist/dxvk-memory-fix'
    build=json.loads((out/'build.json').read_text())
    base=json.loads((ROOT/'vendor/dxvk/dxvk-3.1.1-f1mem2.json').read_text())
    assert build['commit']==COMMIT
    assert build['inputs']['patch_sha256']==sha(ROOT/'tools/sleepingdogs_dxvk_memory.py')
    strip=Path('/home/blekjek/pes13-build/toolchains/llvm-mingw-20260505-ucrt-ubuntu-22.04-x86_64/bin/llvm-strip')
    stage=out/'x32';stage.mkdir(exist_ok=True)
    files={}
    for name,meta in build['files'].items():
        assert sha(out/name)==meta['sha256']
        subprocess.run([str(strip),'--strip-debug','-o',str(stage/name),str(out/name)],check=True)
        assert MARKER.encode() in (stage/name).read_bytes()
        files[name]={'sha256':sha(stage/name),'bytes':(stage/name).stat().st_size}
    archive=ROOT/'vendor/dxvk/dxvk-3.1.1-sdmem1.tar.gz'
    with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as compressed:
        with tarfile.open(fileobj=compressed,mode='w') as tar:
            for name in files:
                data=(stage/name).read_bytes();info=tarfile.TarInfo('dxvk-3.1.1-sdmem1/x32/'+name)
                info.size=len(data);info.mode=0o644;tar.addfile(info,io.BytesIO(data))
    receipt={'build':'sleepingdogs-dxvk-sdmem1','source':{'commit':COMMIT,
        'patch_sha256':sha(ROOT/'tools/sleepingdogs_dxvk_memory.py'),
        'base_patch_sha256':sha(ROOT/'tools/dxvk_compact_chunks.py'),
        'small_patch_sha256':sha(ROOT/'tools/dxvk_small_chunks.py')},
        'source_changes':build['changed'],'files':files,'archive_sha256':sha(archive),
        'upstream_archive_sha256':base['upstream_archive_sha256'],
        'previous_archive_sha256':base['archive_sha256'],'dependencies':base['dependencies'],
        'strip':{'flags':['--strip-debug'],'tool_sha256':sha(strip),'raw_files':build['files']},
        'pool_cap_bytes':2097152,'resource_sizes_unchanged':True,'hardware_tested':False,
        'note':'Sleeping Dogs: 2 MiB ordinary chunk cap; larger resources receive their full aligned size; deferred MapBuffer handles allocation failure.'}
    write_json(out/'staged.json',receipt)
    write_json(ROOT/'vendor/dxvk/dxvk-3.1.1-sdmem1.json',receipt)
    print(json.dumps({'files':files,'archive':sha(archive)}))


if __name__=='__main__':main()
