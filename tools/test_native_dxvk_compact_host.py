"""Reuse actual DXVK/lavapipe regression, exercising compact and legacy packets."""
from pathlib import Path
import hashlib,json
from native_dxvk_compact import ROOT

def main():
    local=ROOT/'local/native-dxvk-compact-v1';fixture=local/'host_fixture.cpp'
    text=(ROOT/'tests/native_dxvk_com_host.cpp').read_text()
    text=text.replace('"../src/','"'+str(ROOT/'src')+'/')
    text='#include "'+str(ROOT/'src/native_dxvk_com/com_compact.h')+'"\n'+text
    before='        require(wine_nx_sd_com_wow64_unix_funcs[0](packet)==0,"transport dispatch");'
    assert text.count(before)==1
    text=text.replace(before,'''        int compact=sd_com_compact_count(type,method);
        if(compact>=0){
            packet->reserved=SD_COM_COMPACT_MAGIC|(unsigned)compact;
            for(unsigned n=compact;n<16;n++)packet->args[n]=0xa5a5a5a5;
            for(unsigned n=0;n<16;n++)packet->high[n]=0xcccccccc;
        }
'''+before)
    fixture.write_text(text)
    runner=(ROOT/'tools/test_native_dxvk_h4_host.py').read_text()
    runner=runner.replace("output=ROOT/'local/native-dxvk-h4-v9'","output=ROOT/'local/native-dxvk-compact-v1'")
    runner=runner.replace("ROOT/'tests/native_dxvk_com_host.cpp'","ROOT/'local/native-dxvk-compact-v1/host_fixture.cpp'")
    runner=runner.replace("ROOT/'src/native_dxvk_com/com_native.cpp'","ROOT/'local/native-dxvk-compact-v1/source/native_dxvk_com/com_native.cpp'")
    ns={'__file__':str(ROOT/'tools/test_native_dxvk_compact_host.py'),'__name__':'compact_host_runner'}
    exec(compile(runner,str(ROOT/'tools/test_native_dxvk_h4_host.py'),'exec'),ns);ns['main']()
    report=json.loads((local/'host-test.json').read_text())
    report['compact_packets_exercised']=True
    report['candidate_sources']=json.loads((local/'build.json').read_text())['source_files']
    report['fixture_generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (local/'host-test.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
