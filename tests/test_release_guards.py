"""Small synthetic binaries exercise release boundaries without private inputs."""
import io,json,os,stat,struct,sys,tarfile,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import release_package as pkg
import release_ci as ci
from check_release_repository import check_vendor_archive

def fixture():
    nro=bytearray(0x4200);nro[16:20]=b'NRO0';struct.pack_into('<I',nro,0x18,0x100)
    nro[0x100:0x104]=b'ASET';struct.pack_into('<QQ',nro,0x118,0x100,0x4000)
    nro[0x3260:0x3268]=b'0.1.0-p1'
    def dll(machine):
        data=bytearray(96);data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,64)
        data[64:68]=b'PE\0\0';struct.pack_into('<H',data,68,machine);return bytes(data)
    nsp=b'PFS0'+struct.pack('<III',1,6,0)+struct.pack('<QQII',0,3,0,0)+b'a.nca\0'+b'NCA'
    files={pkg.NRO:bytes(nro),pkg.NSP:nsp,pkg.PREFIX+'configuration.ini':b'production=1\n',
        pkg.PREFIX+'drive_c/windows/system32/libwow64fex.dll':dll(0xaa64),
        pkg.PREFIX+'drive_c/windows/system32/ntdll.dll':dll(0xaa64),
        pkg.PREFIX+'drive_c/windows/syswow64/ntdll.dll':dll(0x14c),
        pkg.PREFIX+'drive_c/SleepingDogs/sdndx4.dll':dll(0x14c),
        pkg.PREFIX+'share/wine/nls/locale.nls':b'NLS'}
    lock=dict(runtime_version='0.1.0-p1',files={n:pkg.sha(d) for n,d in files.items()},
              forwarder_ncas={'a.nca':pkg.sha(b'NCA')},source_fingerprints={})
    return files,lock

class ReleasePackage(unittest.TestCase):
    def test_valid_payload_and_architecture(self):
        files,lock=fixture();self.assertTrue(pkg.validate_payload(files,lock)['no_game_data'])
        n=pkg.PREFIX+'drive_c/windows/system32/ntdll.dll'
        files[n]=files[pkg.PREFIX+'drive_c/windows/syswow64/ntdll.dll'];lock['files'][n]=pkg.sha(files[n])
        with self.assertRaisesRegex(ValueError,'architecture'):pkg.validate_payload(files,lock)

    def test_game_private_payloads_even_if_added_to_inventory(self):
        for name in ('drive_c/SleepingDogs/HKShip.exe','drive_c/SleepingDogs/Data/a.bin',
                     'drive_c/SleepingDogs/World.BIG','drive_c/SleepingDogs/UserOptions.dat',
                     'launcher/lossless.dll','drive_c/windows/syswow64/LosslessScaling.dll',
                     'lsfg/lsfg-3.1.sdp','launcher/lsfg.txt'):
            with self.subTest(name=name):
                files,lock=fixture();name=pkg.PREFIX+name;files[name]=b'PRIVATE';lock['files'][name]=pkg.sha(b'PRIVATE')
                with self.assertRaises(ValueError):pkg.validate_payload(files,lock)
        for name in ('lossless.dll','source/a/Lossless.dll','source/shaders.sdp','licenses/a.exe','source/prod.keys'):
            with self.assertRaises(ValueError):pkg.validate_path(name)

    def test_paths(self):
        for name in ('../a','/a','C:/a','x/../a','x\\a','./a','a//b',''):
            with self.subTest(name=name),self.assertRaises(ValueError):pkg.safe_name(name)

    def test_inventory_version_and_forwarder(self):
        files,lock=fixture()
        lock['files'][pkg.NRO]='0'*64
        with self.assertRaisesRegex(ValueError,'inventory'):pkg.validate_payload(files,lock)
        lock['files'][pkg.NRO]=pkg.sha(files[pkg.NRO]);lock['runtime_version']='0.1.1'
        with self.assertRaisesRegex(ValueError,'version'):pkg.validate_payload(files,lock)
        lock['runtime_version']='0.1.0-p1';lock['forwarder_ncas']['a.nca']='0'*64
        with self.assertRaisesRegex(ValueError,'Forwarder'):pkg.validate_payload(files,lock)
        with self.assertRaises(ValueError):pkg.pfs_files(b'PFS0'+struct.pack('<III',1001,0,0))

    def test_archive_sha_manifest_duplicates_symlinks(self):
        files,lock=fixture();files['runtime-manifest.json']=pkg.encoded({'files':lock['files']})
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'runtime.zip';pkg.write_zip(path,files);lock['sha256']=pkg.sha(path.read_bytes())
            self.assertEqual(len(pkg.read_runtime(path,lock)),len(files)-1)
            lock['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'SHA256'):pkg.read_runtime(path,lock)
            for special in ('duplicate','symlink','manifest'):
                target=Path(d)/(special+'.zip')
                with zipfile.ZipFile(target,'w') as z:
                    for n,data in files.items():z.writestr(n,b'{}' if special=='manifest' and n=='runtime-manifest.json' else data)
                    if special=='duplicate':z.writestr(pkg.NRO.upper(),b'OTHER')
                    if special=='symlink':
                        info=zipfile.ZipInfo('source/link');info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'/private')
                lock['sha256']=pkg.sha(target.read_bytes())
                with self.assertRaises((ValueError,KeyError)):pkg.read_runtime(target,lock)

    def test_source_mismatch(self):
        with patch.object(pkg,'fingerprints',return_value={'src/x.c':'new'}):
            with self.assertRaisesRegex(ValueError,'sources changed'):pkg.verify_sources({'source_fingerprints':{'src/x.c':'old'}})

    def test_nested_vendor_archive_payloads(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('dxvk/x32/d3d11.dll','dxvk/x32/lossless.dll','game/HKShip.exe','data/world.big','lsfg/pack.sdp'):
                target=Path(d)/'vendor.tar.gz'
                with tarfile.open(target,'w:gz') as archive:
                    member=tarfile.TarInfo(name);member.size=4;archive.addfile(member,io.BytesIO(b'MZxx'))
                if name.endswith('d3d11.dll'):check_vendor_archive(target)
                else:
                    with self.subTest(name=name),self.assertRaises(ValueError):check_vendor_archive(target)

    def test_artifact_assembly_and_second_job_validation(self):
        files,lock=fixture();files['runtime-manifest.json']=pkg.encoded({'files':lock['files']})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'release').mkdir();(root/'release/README.txt').write_text('Install your own game')
            archive=root/'runtime.zip';pkg.write_zip(archive,files);lock['sha256']=pkg.sha(archive.read_bytes())
            (root/'release/runtime-lock.json').write_bytes(pkg.encoded(lock));out=root/'out';commit='a'*40
            with patch.object(pkg,'ROOT',root),patch.object(pkg,'verify_sources'):
                pkg.assemble(archive,out,'v0.1.0-r1',commit)
                self.assertEqual(ci.validate_assets(out,'v0.1.0-r1',commit)['source_commit'],commit)
                (out/'sleepingdogs-fex.nro').write_bytes(b'corrupt')
                with self.assertRaisesRegex(ValueError,'checksum'):ci.validate_assets(out,'v0.1.0-r1',commit)

class ReleaseTransport(unittest.TestCase):
    def test_stable_version_and_legacy_revision(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'release').mkdir();output=root/'outputs'
            for runtime,expected in (('0.1.1','v0.1.1'),('0.1.0-p1','v0.1.0-r7')):
                (root/'release/runtime-lock.json').write_text(json.dumps({'runtime_version':runtime}))
                output.write_text('')
                with patch.object(ci,'ROOT',root),patch.object(ci,'merged_commit',return_value='b'*40),\
                    patch.dict(os.environ,{'GITHUB_RUN_NUMBER':'7','GITHUB_OUTPUT':str(output)}):ci.version()
                self.assertEqual(output.read_text(),'version='+expected+'\ncommit='+'b'*40+'\n')

    def test_only_closed_merged_main_same_repository(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'event.json'
            good={'action':'closed','pull_request':{'merged':True,'merge_commit_sha':'b'*40,
                'base':{'ref':'main','repo':{'full_name':'owner/repo'}}}}
            def run(event,eventname='pull_request_target'):
                path.write_text(json.dumps(event))
                with patch.dict(os.environ,{'GITHUB_EVENT_PATH':str(path),'GITHUB_EVENT_NAME':eventname,
                    'GITHUB_REPOSITORY':'owner/repo'}):return ci.merged_commit()
            self.assertEqual(run(good),'b'*40)
            for eventname in ('pull_request','push','workflow_dispatch'):
                with self.assertRaises(ValueError):run(good,eventname)
            for key,value in (('merged',False),('merge_commit_sha','HEAD'),('base',{'ref':'dev'})):
                bad=json.loads(json.dumps(good));bad['pull_request'][key]=value
                with self.assertRaises(ValueError):run(bad)
            bad=json.loads(json.dumps(good));bad['pull_request']['base']['repo']['full_name']='other/repo'
            with self.assertRaises(ValueError):run(bad)

    def test_published_assets_are_immutable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'asset').write_bytes(b'NEW');calls=[]
            def gh(*args,**kwargs):
                calls.append((args,kwargs));route=args[1]
                if '/git/matching-refs/' in route:return [{'ref':'refs/tags/v0.1.0-r1','object':{'sha':'c'*40,'type':'commit'}}]
                if '/releases?' in route:return [[{'tag_name':'v0.1.0-r1','draft':False,'assets':[{'name':'asset','digest':'sha256:'+pkg.sha(b'OLD')}]}]]
                raise AssertionError('Unexpected GitHub mutation')
            with patch.dict(os.environ,{'GITHUB_REPOSITORY':'owner/repo'}),patch.object(ci,'gh',side_effect=gh),\
                patch.object(ci,'validate_assets',return_value={}),patch.object(ci.subprocess,'run') as run:
                with self.assertRaisesRegex(ValueError,'differs from rerun'):ci.publish(root,'v0.1.0-r1','c'*40)
                run.assert_not_called();self.assertTrue(all('--method' not in args for args,_ in calls))

if __name__=='__main__':unittest.main()
