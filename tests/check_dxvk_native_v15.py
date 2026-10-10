"""Test actual v15 tracker against unchanged DXVK with bounded hint deferral."""
from pathlib import Path
import subprocess,sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_dxvk_native_v15 import BASE,WORK
from port_common import sha,write_json

def main():
    source=WORK/'source';original=Path('/home/blekjek/sleepingdogs-buffer-reuse-v2/source')
    checks=WORK/'checks';checks.mkdir(exist_ok=True)
    for label,path in [('baseline',original),('candidate',source)]:
        h=(path/'src/util/util_flush.h').read_text()
        cpp=(path/'src/util/util_flush.cpp').read_text()
        cpp=cpp.replace('#include "util_flush.h"','#include "'+label+'.h"\n#include <algorithm>')
        cpp=cpp.replace('#include "util_string.h"\n','').replace('#include "log/log.h"\n','')
        if label=='baseline':
            h=h.replace('namespace dxvk {','namespace baseline {');cpp=cpp.replace('namespace dxvk {','namespace baseline {')
        (checks/(label+'.h')).write_text(h);(checks/(label+'.cpp')).write_text(cpp)
    fixture=(ROOT/'tests/dxvk_batch.cpp').read_text()
    for old,new in [('chunks >= 12','chunks >= 24'),('bounded by 12','bounded by 24'),
        ('i < 12','i < 24'),('== 11','== 23'),('StrongHint, 12','StrongHint, 24'),
        ('notifyFlush(12, 11)','notifyFlush(24, 11)'),('StrongHint, 15','StrongHint, 27'),('bound=12','bound=24')]:
        assert old in fixture,old;fixture=fixture.replace(old,new)
    (checks/'fixture.cpp').write_text(fixture)
    exe=checks/'check'
    subprocess.run(['c++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',
        '-fno-pie','-no-pie','-I'+str(checks),str(checks/'fixture.cpp'),str(checks/'baseline.cpp'),
        str(checks/'candidate.cpp'),'-o',str(exe)],check=True)
    result=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
    print(result.stdout)
    # The v15 guest change has no ABI/header/barrier changes compared with v12.
    prepared=json.loads((WORK/'prepared.json').read_text())
    write_json(ROOT/'reports/dxvk-native-v15-host-check.json',dict(status='PASS',output=result.stdout,
        candidate_sources=prepared['changes'],source_sha256=sha(source/'src/util/util_flush.cpp'),
        estimated_cost_limit=1500,hardware_tested=False,fps_gain_measured=False))

if __name__=='__main__':main()
