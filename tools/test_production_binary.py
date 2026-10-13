"""Audit linked production ARM64 startup and loader symbols."""
from pathlib import Path
import argparse
import json,re
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'tools/test_launcher_v2_binary.py').read_text().replace('local/launcher-v2','local/production-v1')
ns={'__name__':'production_binary','__file__':__file__}
exec(compile(text,__file__,'exec'),ns)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build-dir',type=Path,default=ROOT/'local/production-v1')
    args=p.parse_args();ns['LOCAL']=args.build_dir;ns['main']()
    build=json.loads((args.build_dir/'build.json').read_text())
    if build.get('startup_defaults_embedded'):
        header=(ROOT/'src/launcher/startup_config_data.h').read_text()
        nro=(args.build_dir/'sleepingdogs-fex.nro').read_bytes()
        for symbol in ('config_json','dummys_bson'):
            match=re.search(r'static const unsigned char sd_startup_'+symbol+r'\[\]=\{(.*?)\};',header,re.S)
            assert match,symbol
            payload=bytes(int(b,16) for b in re.findall(r'0x([0-9a-f]{2})',match[1]))
            assert payload and payload in nro,symbol
        for name in (b'config.json\0',b'dummys.bson\0',b'local\0'):assert name in nro,name
        report_path=args.build_dir/'binary-test.json';report=json.loads(report_path.read_text())
        report['startup_default_payloads_present_in_nro']=True
        report_path.write_text(json.dumps(report,indent=2)+'\n')
        print('PASS: startup defaults present in actual NRO; zero-byte local filename retained')
