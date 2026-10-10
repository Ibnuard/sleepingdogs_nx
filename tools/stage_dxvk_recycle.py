"""Pin the stripped reuse renderer set without replacing older vendors."""
import gzip,io,json,tarfile
from port_common import ROOT,sha,write_json

def main():
    out=ROOT/'dist/buffer-reuse-fix';build=json.loads((out/'build.json').read_text())
    previous=json.loads((ROOT/'vendor/dxvk/dxvk-3.1.1-sdstream1.json').read_text())
    assert build['inputs']['patch_sha256']==sha(ROOT/'tools/sleepingdogs_dxvk_recycle.py')
    assert build['inputs']['helper_sha256']==sha(ROOT/'src/sd_dxvk_recycle.inc')
    files={n:{k:v for k,v in meta.items() if k!='raw_sha256'} for n,meta in build['files'].items()}
    archive=ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.tar.gz'
    with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as gz:
        with tarfile.open(fileobj=gz,mode='w') as tar:
            for name,meta in files.items():
                p=out/'x32'/name;assert sha(p)==meta['sha256'];data=p.read_bytes()
                info=tarfile.TarInfo('dxvk-3.1.1-sdrecycle1/x32/'+name);info.size=len(data);info.mode=0o644;tar.addfile(info,io.BytesIO(data))
    source=dict(previous['source']);source['sdstream1_patch_sha256']=source['patch_sha256']
    source['patch_sha256']=build['inputs']['patch_sha256'];source['helper_sha256']=build['inputs']['helper_sha256']
    receipt={'build':'sleepingdogs-dxvk-sdrecycle1','source':source,'source_changes':build['changed'],'files':files,
        'archive_sha256':sha(archive),'upstream_archive_sha256':previous['upstream_archive_sha256'],
        'previous_archive_sha256':previous['archive_sha256'],'dependencies':previous['dependencies'],
        'pool_cap_bytes':2097152,'dedicated_mapped_threshold_bytes':2097152,'resource_sizes_unchanged':True,
        'max_idle_bytes':16777216,'max_idle_count':4,'retired_only':True,'hardware_tested':False}
    write_json(out/'staged.json',receipt);write_json(ROOT/'vendor/dxvk/dxvk-3.1.1-sdrecycle1.json',receipt)
    print(json.dumps({'archive_sha256':sha(archive),'files':files}))
if __name__=='__main__':main()
