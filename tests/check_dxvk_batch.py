"""Differential tests of the actual DXVK flush tracker, with ASan/UBSan."""
from pathlib import Path
import argparse
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from port_common import sha, write_json
from build_dxvk_batch import BASE, WORK, prepare


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, default=WORK)
    work = p.parse_args().work
    baseline, prepared, changed = prepare(work)
    checks = work/'checks'; checks.mkdir(exist_ok=True)
    for label, source in [('baseline', BASE/'source'), ('candidate', work/'source')]:
        header = (source/'src/util/util_flush.h').read_text()
        cpp = (source/'src/util/util_flush.cpp').read_text()
        # Only remove unused Windows logging/string headers so these exact
        # function bodies can run under host sanitizers; no algorithm rewrite.
        cpp = cpp.replace('#include "util_flush.h"', '#include "'+label+'.h"\n#include <algorithm>')
        cpp = cpp.replace('#include "util_string.h"\n', '').replace('#include "log/log.h"\n', '')
        if label == 'baseline':
            header = header.replace('namespace dxvk {', 'namespace baseline {')
            cpp = cpp.replace('namespace dxvk {', 'namespace baseline {')
        (checks/(label+'.h')).write_text(header)
        (checks/(label+'.cpp')).write_text(cpp)
    exe = checks/'batch-test'
    with (checks/'compile.log').open('w') as log:
        subprocess.run(['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined',
                        '-fno-sanitize-recover=all','-fno-pie','-no-pie',
                        '-I'+str(checks),str(ROOT/'tests/dxvk_batch.cpp'),
                        str(checks/'baseline.cpp'),str(checks/'candidate.cpp'),'-o',str(exe)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    result = subprocess.check_output([str(exe)], text=True, timeout=60).strip()
    write_json(ROOT/'reports/dxvk-batch-host.json', dict(status='PASS', result=result,
        sanitizers=['address','undefined'], hardware_tested=False,
        candidate_sources=changed,
        baseline_tracker_sources={n:baseline['source_files'][n] for n in
                                  ('src/util/util_flush.h','src/util/util_flush.cpp')},
        sources={n:sha(ROOT/n) for n in ('tests/check_dxvk_batch.py','tests/dxvk_batch.cpp',
                                       'tools/sleepingdogs_dxvk_batch.py','tools/build_dxvk_batch.py')}))
    print(result, flush=True)


if __name__ == '__main__': main()
