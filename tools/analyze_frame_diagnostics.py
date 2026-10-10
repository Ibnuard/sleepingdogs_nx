"""Summarize v11 per-thread capture without adding overlapping wall times."""
from pathlib import Path
import argparse
import hashlib
import re
from port_common import ROOT, write_json

def fields(line):
    return {k:int(v) for k,v in re.findall(r'\b(\w+)=(-?\d+)(?=[\s;,]|$)',line)}

def analyze(payload):
    capture=None; maps={}; frame_windows=[]
    for line_no,line in enumerate(payload.decode('utf-8',errors='replace').splitlines(),1):
        if line.startswith('[SD-DIAG-MAP]'):
            v=fields(line); kind=re.search(r'kind=(\w)',line)
            if kind and 'handle' in v and 'tid' in v:
                label=str(v['tid'])+kind[1]
                maps.setdefault(v['handle'],set()).add(label)
        elif line.startswith('[SD-DIAG] phase='):
            phase=re.search(r'phase=(\w+)',line)[1]
            if phase=='start':
                capture=dict(start_line=line_no,**fields(line),snapshots=[])
                frame_windows=[]
            elif capture and phase in ('sample','complete'):
                values=fields(line)
                values['reported_rows']=values.pop('rows',0)
                capture['snapshots'].append(dict(line=line_no,phase=phase,**values,rows={}))
        elif capture and line.startswith('[SD-FRAME]'):
            frame_windows.append(dict(line=line_no,**fields(line)))
        elif capture and capture['snapshots'] and line.startswith(('[SD-DIAG-WAIT]','[SD-DIAG-FRAME]')):
            values=fields(line)
            if not {'row','handle'}<=set(values): continue
            row=capture['snapshots'][-1]['rows'].setdefault(values['row'],dict(handle=values['handle'],stages={}))
            assert row['handle']==values['handle'],'Row identity changed within capture'
            if line.startswith('[SD-DIAG-FRAME]'): row['frame']=values
            else:
                stage=re.search(r'stage=(\w+)',line)
                if stage: row['stages'][stage[1]]=values
    if not capture or not capture['snapshots']:
        return dict(status='NO_CAPTURE' if not capture else 'STARTED_NO_REPORT',capture=capture,
                    note='No completed diagnostic report; no per-thread performance inference.')
    last=capture['snapshots'][-1]
    last['missing_rows']=max(0,last['reported_rows']-len(last['rows']))
    for row in last['rows'].values():
        labels=sorted(maps.get(row['handle'],()))
        row['observed_thread_labels']=labels
        row['mapping_unambiguous']=len(labels)==1
        if frame:=row.get('frame'):
            n=frame['n']; cpu_n=frame['cpu_valid_n']
            row['present_gap_average_ms']=frame['gap_total_us']/n/1000 if n else None
            row['presenting_thread_cpu_average_ms']=frame['thread_cpu_total_us']/cpu_n/1000 if cpu_n else None
            row['cpu_tick_coverage']=cpu_n/n if n else None
    return dict(status='COMPLETE' if last['phase']=='complete' and not last['missing_rows'] else 'PARTIAL',
        start_line=capture['start_line'],final_snapshot=last,snapshots=capture['snapshots'],
        subsequent_frame_windows=frame_windows,
        limitations=[
            'Each snapshot is cumulative; use only the latest snapshot or differences, never sum snapshots.',
            'Different thread durations overlap; Wine and Vulkan totals are not removable frame cost.',
            'Thread mappings are observed snapshots; exited or recycled handles may be missing or ambiguous.',
            'Present CPU ticks cover only that thread, and invalid CPU intervals are excluded.',
            'Only calls wholly inside the capture are counted; live snapshots may see partial updates.',
            'No GPU timestamps, measured clocks or temperatures. No definitive CPU/GPU bottleneck verdict.'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log',type=Path)
    a=p.parse_args()
    data=a.log.read_bytes(); digest=hashlib.sha256(data).hexdigest()
    dest=ROOT/'local/performance-v11'/digest/'fex-runtime.log'
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists(): assert dest.read_bytes()==data
    else: dest.write_bytes(data)
    result=analyze(data)
    result.update(input=str(a.log),sha256=digest,preserved_input=dest.relative_to(ROOT).as_posix())
    path=ROOT/'reports'/('gameplay-v11-'+digest[:12]+'.json')
    write_json(path,result)
    print(result['status'],path,flush=True)

if __name__=='__main__': main()
