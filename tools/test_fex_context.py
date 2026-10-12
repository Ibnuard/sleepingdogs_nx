"""Test exact x87 import against pinned code, host x87 and buffer canaries."""
from pathlib import Path
import json,shutil,subprocess
from build_fex_context import ROOT,LOCAL,WORK,BASE,PIN,sha,write_json

def main():
    LOCAL.mkdir(parents=True,exist_ok=True);work=WORK/'host';work.mkdir(parents=True,exist_ok=True)
    pin=json.loads(PIN.read_text())['debug_register_build'];sources={}
    for name in ('module_fpu.cpp','horizon_fpu.h'):
        p=BASE/'adapter'/name;assert sha(p)==pin['adapter_files'][name];sources[str(p)]=sha(p)
        shutil.copy2(p,work/name)
    old=(work/'module_fpu.cpp').read_text().replace('PES13FexImportX87','OldImport').replace('PES13FexExportX87','OldExport')
    new=old.replace('OldImport','NewImport').replace('OldExport','NewExport')
    new=new.replace('#include "horizon_fpu.h"','#include "horizon_fpu.h"\n#include "exact_x87.h"')
    new=new.replace('pes13_fex_fp::narrow(value, control)','sd_fex_context::narrow(value, control, pes13_fex_fp::narrow)')
    (work/'old.cpp').write_text(old);(work/'new.cpp').write_text(new)
    files=[ROOT/'tests/fex_context_exact.cpp',ROOT/'src/fex_context/exact_x87.h',Path(__file__)]
    reports={};commands={}
    for label,flags,args in [('sanitized',['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all'],[]),('benchmark',['-O3'],['--bench'])]:
        exe=work/label
        command=['g++','-std=c++17','-frounding-math',*flags,'-I'+str(work),'-I'+str(ROOT/'src/fex_context'),
            str(files[0]),str(work/'old.cpp'),str(work/'new.cpp'),'-o',str(exe)]
        result=subprocess.run(command,capture_output=True,text=True);(work/(label+'.compile.log')).write_text(result.stdout+result.stderr)
        assert not result.returncode,result.stderr
        result=subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=60)
        (work/(label+'.stdout')).write_text(result.stdout);(work/(label+'.stderr')).write_text(result.stderr)
        assert not result.returncode,result.stderr
        reports[label]=json.loads(result.stdout);commands[label]=command
        assert reports[label]['status']=='PASS'
    report=dict(status='PASS',results=reports,compile_commands=commands,pinned_sources=sources,
        source_files={p.relative_to(ROOT).as_posix():sha(p) for p in files},
        candidate_source_sha256=sha(WORK/'source/module_fpu.cpp'),
        scope='Host numerical/byte comparison with actual pinned serializer and x87 oracle; host benchmark excludes FEX execution, Wine and Horizon.',
        hardware_tested=False,game_fps_measured=False)
    write_json(LOCAL/'host-test.json',report);print(json.dumps(reports))
if __name__=='__main__':main()
