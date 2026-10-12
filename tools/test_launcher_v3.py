"""Run unchanged launcher regressions plus the corrected present-mode policy."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local/launcher-v3'
WORK=Path('/home/blekjek/sleepingdogs-launcher-v3')
def main():
    text=(ROOT/'tools/test_launcher_v2.py').read_text().replace("local/launcher-v2","local/launcher-v3").replace('sleepingdogs-launcher-v2','sleepingdogs-launcher-v3')
    ns={'__name__':'v3_fixture','__file__':__file__};exec(compile(text,__file__,'exec'),ns);ns['main']()
    exe=WORK/'tests/lsfg-policy'
    ns['run'](['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined',
        '-I'+str(ROOT/'src/launcher'),'-I/home/blekjek/pes13-build/mesa-switch/include',ROOT/'tests/lsfg_present_policy.cpp','-o',exe],'lsfg-policy.compile')
    output=ns['run']([exe],'lsfg-policy.test')
    report=json.loads((LOCAL/'test.json').read_text());report['results']['present_policy']=output
    (LOCAL/'test.json').write_text(json.dumps(report,indent=2)+'\n');print(output)
if __name__=='__main__':main()
