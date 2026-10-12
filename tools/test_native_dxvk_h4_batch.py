"""Exercise the exact 24-chunk tracker linked by the native DXVK build."""
from pathlib import Path
import json,subprocess
from build_native_dxvk_h4 import ROOT,LOCAL,sha
BASE=Path('/home/blekjek/sleepingdogs-buffer-reuse-v2')

def main():
    work=LOCAL/'batch-check';work.mkdir(parents=True,exist_ok=True)
    receipt_path=ROOT/'local/native-dxvk-probe-v1/build-horizon.json'
    native=json.loads(receipt_path.read_text());library=Path(native['library'])
    assert sha(library)==native['sha256']
    prepared_path=Path('/home/blekjek/sleepingdogs-dxvk-native-v15/prepared.json')
    assert sha(prepared_path)==native['baseline_receipt_sha256']
    prepared=json.loads(prepared_path.read_text())['source_files']
    source=library.parent.parent/'source';inputs={}
    for label,folder in [('baseline',BASE/'source'),('candidate',source)]:
        names=['src/util/util_flush.h','src/util/util_flush.cpp']
        values=[]
        for name in names:
            path=folder/name;inputs[str(path)]=sha(path)
            if label=='candidate':assert sha(path)==prepared[name]
            values.append(path.read_text())
        header,body=values
        body=body.replace('#include "util_flush.h"','#include "'+label+'.h"\n#include <algorithm>')
        body=body.replace('#include "util_string.h"\n','').replace('#include "log/log.h"\n','')
        if label=='baseline':
            header=header.replace('namespace dxvk {','namespace baseline {');body=body.replace('namespace dxvk {','namespace baseline {')
        else:assert 'chunkCount < 24u' in body and 'minPendingSubmissions = 2' in body
        (work/(label+'.h')).write_text(header,newline='\n');(work/(label+'.cpp')).write_text(body,newline='\n')
    fixture=ROOT/'tests/dxvk_batch.cpp';exe=work/'batch-check'
    command=['g++','-std=c++17','-O1','-g','-DSD_TEST_BATCH_BOUND=24','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-pie','-no-pie','-I'+str(work),str(fixture),str(work/'baseline.cpp'),str(work/'candidate.cpp'),'-o',str(exe)]
    result=subprocess.run(command,capture_output=True,text=True);(work/'compile.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr
    result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60);assert result.returncode==0,result.stderr
    assert 'bound=24' in result.stdout and 'readback=progress explicit=preserved' in result.stdout
    report=dict(status='PASS',result=result.stdout.strip(),runner_sha256=sha(__file__),
        source_files={'tests/dxvk_batch.cpp':sha(fixture)},compiled_tracker_inputs=inputs,
        native_dxvk_receipt_sha256=sha(receipt_path),native_dxvk_sha256=sha(library),
        compile_argv=command,executable_sha256=sha(exe),sanitizers=['address','undefined'],
        max_deferred_hint_chunks=24,min_pending_submissions=2,
        mandatory_flushes_preserved=True,disabled_equivalent_to_baseline=True,
        hardware_tested=False,game_fps_measured=False,
        scope='Actual pinned native tracker bodies: decision grid, stateful off-mode differential, readback progress, cost/chunk limits and submission-ID wraparound. Host fixture does not execute NVK or measure GPU queue performance.')
    (LOCAL/'native-batch.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(result.stdout.strip())
if __name__=='__main__':main()
