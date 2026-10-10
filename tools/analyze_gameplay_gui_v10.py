"""Analyze v10 direct-sync counters, retaining overlap and clock-change limits."""
from pathlib import Path
import argparse
import hashlib
import json
import re
from port_common import ROOT, write_json
from analyze_gameplay_gui_v9 import fields, summarize


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log',type=Path)
    a=p.parse_args()
    payload=a.log.read_bytes(); digest=hashlib.sha256(payload).hexdigest()
    saved=ROOT/'local/performance-v10-gui'/digest/'fex-runtime.log'
    saved.parent.mkdir(parents=True,exist_ok=True)
    if saved.exists(): assert saved.read_bytes()==payload
    else: saved.write_bytes(payload)
    lines=payload.decode('utf-8',errors='replace').splitlines()
    assert '[SD-FEX] launch_mode=gui' in lines
    assert any('low-window-v10-direct-sync' in s for s in lines)
    rows=[]; current=frame=None; names={}; jit=[]
    for i,s in enumerate(lines,1):
        if s.startswith('[FEX3-DXVKCORE] tid='):
            if m:=re.search(r'tid=(\d+).* name=(\S+)',s): names[m[1]+'w']=m[2]
        if s.startswith('[SD-FRAME]'):
            frame=dict(line=i,**fields(s)); frame['fps']=frame['frames']*1000/frame['window_ms']
            assert abs(frame['fps']-frame['fps_x100']/100)<0.02
        if s.startswith('[SD-PERF]') and 'phase=' in s:
            current=dict(line=i,**fields(s),frame=frame,threads={},pipe={},warm={}); rows.append(current)
        if s.startswith('[FEX3-JIT] phase='):
            jit.append(dict(line=i,phase=re.search(r'phase=(\w+)',s)[1],**fields(s)))
        if current is None: continue
        if s.startswith('[THREADS]'):
            current['registered_cpu_cores']=float(re.search(r'use ([\d.]+) cores',s)[1])
            current['threads']={t+k:dict(core_mask_snapshot_core=int(c),cpu_percent=float(v))
                for t,k,c,v in re.findall(r'(\d+)([ws])@(-?\d+) ([\d.]+)%',s)}
        if s.startswith('[SERVER]'):
            current['server']=dict(requests=int(re.search(r'\] (\d+) requests',s)[1]),
                aggregate_ms=int(re.search(r'requests, (\d+) ms',s)[1]),operations={
                    n:dict(calls=int(c),avg_us=int(u),aggregate_ms=int(ms))
                    for n,c,u,ms in re.findall(r'(\w+) (\d+) avg (\d+)us (\d+)ms',s)})
        if m:=re.match(r'\[FEX3-PIPE\] (\w+) ',s): current['pipe'][m[1]]=fields(s)
        if m:=re.match(r'\[FEX3-WARM\] (\w+) ',s): current['warm'][m[1]]=fields(s)
        for tag,key in (('[SD-DIRECT-SYNC]','sync'),('[SD-PERF-IO]','io'),
                        ('[SD-SHADER-CACHE]','shader_cache'),('[FEX3-WARM] driver_cache_hits=','driver_cache')):
            if s.startswith(tag): current[key]=fields(s)
        if s.startswith('[SD-PERF]') and 'observer_us=' in s: current['observer_us']=fields(s)['observer_us']
    assert names['40w']=='dxvk-cs'
    assert [r['report'] for r in rows]==list(range(len(rows)))
    counters=('direct','pipe','direct_select','queued','sleeps','targeted','broad','completed','fallback_waits')
    for before,row in zip(rows,rows[1:]):
        assert row['frame']['window_ms']==row['window_ms']
        row['sync_delta']={k:row['sync'][k]-before['sync'][k] for k in counters}
        assert all(v>=0 for v in row['sync_delta'].values())
        n=row['sync_delta']['direct']+row['sync_delta']['pipe']
        row['direct_percent']=100*row['sync_delta']['direct']/n
    slow=[]
    for row in reversed(rows[1:]):
        if row['frame']['fps']>=30: break
        slow.append(row)
    slow.reverse(); assert slow
    summary=summarize(slow)
    summary['sync_delta']={k:sum(r['sync_delta'][k] for r in slow) for k in counters}
    direct=summary['sync_delta']['direct']; pipe=summary['sync_delta']['pipe']
    summary['direct_percent']=100*direct/(direct+pipe)
    summary['pipe_calls_per_second']=1000*pipe/summary['elapsed_ms']
    summary['server_calls_per_second']=1000*summary['server_requests']/summary['elapsed_ms']
    summary['event_op_weighted_average_us']=1000*sum(r['server']['operations']['event_op']['aggregate_ms'] for r in slow)/sum(r['server']['operations']['event_op']['calls'] for r in slow)
    phases={}
    for phase in ('dispatch_compile','compile_code','invalidate'):
        samples=[r for r in jit if r['phase']==phase and r['line']>=slow[0]['line']]
        first,last=samples[0],samples[-1]
        phases[phase]=dict(elapsed_ms=last['uptime_ms']-first['uptime_ms'],
            calls=last['calls']-first['calls'],aggregate_us=last['total_us']-first['total_us'])
    resources=[fields(s) for s in lines if s.startswith('[SD-RESOURCE]')]
    old=json.loads((ROOT/'reports/gameplay-v9-gui-performance-analysis.json').read_text())
    result=dict(status='ANALYZED',input=str(a.log),sha256=digest,bytes=len(payload),
        preserved_input=saved.relative_to(ROOT).as_posix(),
        user_reported_clocks_mhz=dict(start=dict(cpu=1728,gpu=768,ram=1600),
            middle_session=dict(cpu=1900,gpu=1150,ram=2133),change_marker=None,actual_frequencies_logged=False),
        configuration=[dict(line=i,text=s) for i,s in enumerate(lines,1) if s.startswith(
            ('[SD-FEX] launch_mode=','[SD-DXVK-CONFIG]','[SD-SYNC-MODE]','[SD-VK]')) or
            any(x in s for x in ('Setting display mode:','Present mode:','Buffer size:'))],
        selection='Trailing contiguous sub-30-FPS windows; no exact scene or clock-change markers',
        slow_segment=summary,last_three_windows=summarize(slow[-3:]),late_jit=phases,
        memory=dict(minimum_available_bytes=min(r['heap_available'] for r in resources),
            gpu_oom_max=max(fields(s)['oom'] for s in lines if s.startswith('[SD-VKMEM-STATS]'))),
        driver_cache_observed_totals={k:sum(r['driver_cache'][k] for r in rows) for k in ('driver_cache_hits','misses')},
        shader_cache_last=rows[-1]['shader_cache'],thread_names=names,intervals=rows,
        previous_capture=dict(sha256=old['sha256'],slow_segment=old['slow_segment'],controlled_comparison=False),
        limitations=[
            'Clock values are user reports; no measured frequencies, temperature or clock-change timestamp.',
            'V9 and v10 scenes, duration and clocks are not controlled; FPS differences do not establish a gain/regression.',
            'Registered CPU excludes unregistered/system threads and reports only the 12 busiest threads.',
            'Thread core masks are snapshots, not full-interval CPU residency.',
            'SERVER counts include both direct and pipe requests in v10; use SD-DIRECT-SYNC to distinguish.',
            'Select time includes concurrent real blocking; aggregate wall times are not removable overhead.',
            'Driver semaphore waits include parking/scheduling; neither GPU busy time nor per-frame critical path is measured.',
            'Compiler and driver timings can nest/overlap; do not add them as frame cost.',
            'Cache hits can include this run; zero NAK-cache scopes is not proof of no shader work.',
        ])
    write_json(ROOT/'reports/gameplay-v10-gui-performance-analysis.json',result)
    print(json.dumps({k:result[k] for k in ('sha256','slow_segment','last_three_windows','late_jit','memory','driver_cache_observed_totals','shader_cache_last')},indent=2))
    print('report fps registered_cores direct% event_us semaphore_ms fence_ms pipeline_ms sd_ms')
    for r in slow:
        print(r['report'],round(r['frame']['fps'],2),r['registered_cpu_cores'],round(r['direct_percent'],2),
            r['server']['operations']['event_op']['avg_us'],r['pipe']['semaphore_wait']['avg_us']/1000,
            r['pipe']['fence_wait']['avg_us']/1000,r['warm']['graphics_pipeline']['total_us']/1000,r['io']['sd_ms'])


if __name__=='__main__': main()
