"""Compare the preserved Fastest and Fast device sessions; no hardware emulation."""
import json
import re
from port_common import ROOT, sha, write_json


def read_session(relative, digest):
    path=ROOT/relative
    assert sha(path)==digest
    lines=path.read_text(encoding='utf-8').splitlines()
    progress=[]; waits=[]; seconds=0
    for number,line in enumerate(lines,1):
        found=re.match(r'\[SD-LOAD\] v1 t=(\d+)s presents=(\d+) delta=(\d+) present_seen=(\d+) age_ms=(\d+) present_errors=(\d+)',line)
        if found:
            seconds,count,delta,seen,age,errors=map(int,found.groups())
            progress.append(dict(line=number,seconds=seconds,presents=count,age_ms=age,errors=errors))
        if re.match(r'\[SD-CALL\] tid=(4|72) NtWaitForSingleObject ',line) and 'a0=6d4ffff0 a1=0 a2=0 ' in line:
            waits.append(dict(line=number,seconds=seconds,text=line))
    final_count=progress[-1]['presents']
    plateau=[r for r in progress if r['presents']==final_count]
    assert len(plateau)>=3 and waits
    return dict(log_sha256=digest,bytes=path.stat().st_size,
                profile=next(s for s in lines if s.startswith('[SD-FEX-MODE]')),
                tso=next(s for s in lines if s.startswith('[FEX3-PRESET]')),
                plateau_first=plateau[0],plateau_last=plateau[-1],
                wait_samples=waits,
                invalid_status_directly_sampled=any('status=c0000008' in w['text'] for w in waits),
                frozen_stacks=[next(s for s in reversed(lines) if s.startswith(f'[SD-STACK] tid={tid}w round=0 ') and 'guest= bb6f3b bb7c6a bb7e31' in s) for tid in (4,72)],
                last_heap_available_bytes=int(re.search(r'heap_available=(\d+)',next(s for s in reversed(lines) if s.startswith('[SD-RESOURCE]'))).group(1)),
                vkmem=next(s for s in reversed(lines) if s.startswith('[SD-VKMEM-STATS]')))


if __name__=='__main__':
    result=dict(
        fastest=read_session('local/loading-freeze-v3/fex-runtime.log','bc83d378715f4e3284feeff39ffea08fda92f74b661605d7e5b8a63a0791b7f3'),
        fast=read_session('local/loading-freeze-v3-fast/fex-runtime.log','5a6918b09c9794a78efe26ed4a4b4a494760ff2f1afe03bca63691328fd12c0b'),
        user_observation='Fast is slower and still freezes',
        conclusion='Enabling all three TSO options did not remove the observed stall: same high-valued handle and game wait stacks. Restore Fastest and collect lifecycle/object evidence.',
        qualification='The Fast log samples only entered states for these busy waits; STATUS_INVALID_HANDLE was directly observed in the previous Fastest session. The new hook records the first actual invalid return.',
        hardware_freeze_fixed=False)
    write_json(ROOT/'reports/low-window-sync-comparison.json',result)
    print(json.dumps({n:{k:result[n][k] for k in ('plateau_first','plateau_last','invalid_status_directly_sampled','last_heap_available_bytes')} for n in ('fastest','fast')},indent=2))
