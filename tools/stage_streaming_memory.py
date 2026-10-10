"""Pin the new stripped renderer set; preserve all prior release archives."""
from pathlib import Path
import gzip,io,json,tarfile
from port_common import ROOT,sha,write_json


def main():
    out=ROOT/'dist/streaming-memory-fix';build=json.loads((out/'dxvk.json').read_text())
    previous=json.loads((ROOT/'vendor/dxvk/dxvk-3.1.1-sdmem1.json').read_text())
    assert build['inputs']['patch_sha256']==sha(ROOT/'tools/sleepingdogs_streaming_memory.py')
    files={n:{k:v for k,v in m.items() if k!='raw_sha256'} for n,m in build['files'].items()}
    archive=ROOT/'vendor/dxvk/dxvk-3.1.1-sdstream1.tar.gz'
    with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as gz:
        with tarfile.open(fileobj=gz,mode='w') as tar:
            for name,meta in files.items():
                p=out/'x32'/name;assert sha(p)==meta['sha256']
                data=p.read_bytes();info=tarfile.TarInfo('dxvk-3.1.1-sdstream1/x32/'+name)
                info.size=len(data);info.mode=0o644;tar.addfile(info,io.BytesIO(data))
    source=dict(previous['source']);source['sdmem1_patch_sha256']=source['patch_sha256']
    source['patch_sha256']=sha(ROOT/'tools/sleepingdogs_streaming_memory.py')
    receipt={'build':'sleepingdogs-dxvk-sdstream1','source':source,'source_changes':build['changed'],
        'files':files,'archive_sha256':sha(archive),'upstream_archive_sha256':previous['upstream_archive_sha256'],
        'previous_archive_sha256':previous['archive_sha256'],'dependencies':previous['dependencies'],
        'pool_cap_bytes':2097152,'dedicated_mapped_threshold_bytes':2097152,'resource_sizes_unchanged':True,
        'hardware_tested':False,'note':'Large mapped resources own their backing until the final reference; small allocations stay in separate chunks.'}
    write_json(out/'staged.json',receipt);write_json(ROOT/'vendor/dxvk/dxvk-3.1.1-sdstream1.json',receipt)
    print(json.dumps({'archive_sha256':sha(archive),'files':files}))


if __name__=='__main__':main()
