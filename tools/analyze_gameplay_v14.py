"""Preserve v14 hardware evidence, including the incomplete cache invalidation."""
from pathlib import Path
import argparse
import hashlib
import json
import re
from port_common import ROOT,sha,write_json
from analyze_frame_diagnostics import analyze,fields
from analyze_gameplay_v11 import summarize


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);a=p.parse_args()
    data=a.log.read_bytes();digest=hashlib.sha256(data).hexdigest()
    saved=ROOT/'local/performance-v14'/digest/'fex-runtime.log';saved.parent.mkdir(parents=True,exist_ok=True)
    if saved.exists():assert saved.read_bytes()==data
    else:
        with saved.open('xb') as out:out.write(data)
    capture=analyze(data);assert capture['status']=='COMPLETE'
    capture.update(sha256=digest,preserved_input=saved.relative_to(ROOT).as_posix())
    dest=ROOT/'reports'/('gameplay-v14-'+digest[:12]+'.json');write_json(dest,capture)
    frames=[];markers=[];cache=[];jit=[];modes=[];shader_cache=[];cpu=[];oom=[];warm=[]
    for i,s in enumerate(data.decode(errors='replace').splitlines(),1):
        if s.startswith('[SD-FRAME]'):frames.append(dict(line=i,**fields(s)))
        if s.startswith('[SD-NVK-V14]'):markers.append(dict(line=i,text=s))
        if s.startswith('[FEX3-WARM] driver_cache_hits='):cache.append(dict(line=i,**fields(s)))
        if s.startswith('[FEX3-WARM] graphics_pipeline'):warm.append(dict(line=i,**fields(s)))
        if s.startswith('[SD-SHADER-CACHE]'):shader_cache.append(dict(line=i,**fields(s)))
        if s.startswith('[FEX3-JIT] phase='):jit.append(dict(line=i,phase=re.search(r'phase=(\w+)',s)[1],**fields(s)))
        if m:=re.search(r'Setting display mode: (\d+)x(\d+)',s):modes.append(dict(line=i,resolution=list(map(int,m.groups()))))
        if s.startswith('[SD-VKMEM-STATS]'):oom.append(dict(line=i,**fields(s)))
        if s.startswith('[THREADS]') and (m:=re.search(r'use ([\d.]+) cores',s)):cpu.append(dict(line=i,cores=float(m[1])))
    assert any('shader compiler SM53' in r['text'] for r in markers)
    tail=[]
    for r in reversed(frames):
        if r['fps_x100']>=3000:break
        tail.append(r)
    tail.reverse();assert len(tail)>7
    last=capture['final_snapshot'];present=[r for r in last['rows'].values() if 'frame' in r]
    assert len(present)==1;present=present[0];f=present['frame'];stage=present['stages']['vk_submit']
    late={}
    for phase in ('compile_code','dispatch_compile','invalidate'):
        rows=[r for r in jit if r['phase']==phase and r['uptime_ms']>=200000]
        if len(rows)>1:
            first,end=rows[0],rows[-1]
            late[phase]=dict(elapsed_ms=end['uptime_ms']-first['uptime_ms'],
                completed_wall_us=end['total_us']-first['total_us'],calls=end['calls']-first['calls'])
    previous=ROOT/'reports/gameplay-v13-performance-analysis.json';v13=json.loads(previous.read_text())
    result=dict(status='ANALYZED',input=str(a.log),sha256=digest,analyzer_sha256=sha(Path(__file__)),
        preserved_input=saved.relative_to(ROOT).as_posix(),capture_report=dest.relative_to(ROOT).as_posix(),
        user_reported=dict(peak_fps=24,typical_fps=[15,17],clocks_reconfirmed=False,paired_scene=False),
        capture_fps=1000/present['present_gap_average_ms'],capture_average_frame_ms=present['present_gap_average_ms'],
        capture_duration_ms=last['elapsed_ms'],capture_present_intervals=f['n'],
        submits_per_present_interval=stage['n']/f['n'],submit_calls=stage['n'],submit_wall_ms=stage['total_us']/1000,
        present_thread_cpu_ms=f['thread_cpu_total_us']/1000,
        resolution_records=modes,markers=markers,all_frame_windows=frames,
        slow_tail=summarize(tail),tail_excluding_first_transition=summarize(tail[1:]),last_seven=summarize(tail[-7:]),
        driver_cache_hits=sum(r['driver_cache_hits'] for r in cache),driver_cache_misses=sum(r['misses'] for r in cache),
        completed_nak_compile_scopes_max=max((r['completed'] for r in shader_cache),default=None),
        compiled_shader_marker_count=sum('shader=' in r['text'] for r in markers),
        zcull_active_marker_count=sum('ZCULL active=' in r['text'] for r in markers),
        graphics_pipeline_windows=warm,jit_after_200_seconds=late,cpu_samples=cpu,
        max_vulkan_oom_counter=max((r['oom'] for r in oom),default=None),
        prior_v13=dict(report=previous.relative_to(ROOT).as_posix(),sha256=sha(previous),
            capture_fps=v13['capture_fps'],capture_frame_ms=v13['capture_average_frame_ms'],paired_test=False),
        interpretation='v14 is installed, but its retained nvk_instance object still uses v13 driver_build_sha for the Mesa disk-cache namespace. The newer pipelineCacheUUID alone does not isolate that cache. All hits and zero NAK compile scopes are consistent with reuse; the log cannot date individual cached binaries.',
        limitations=capture['limitations']+[
            'Tail selection below 30 FPS is a workload heuristic; scene identity is unverified.',
            'The first tail window may span a scene transition and is also reported separately.',
            'Ten-second window averages cannot validate or disprove an instantaneous 24 FPS peak.',
            'Cache hits are intervals; NAK completed scopes are cumulative and must not be summed.',
            'No controlled v13/v14 comparison, cache-file contents or hardware render-pass timings.'])
    write_json(ROOT/'reports/gameplay-v14-performance-analysis.json',result)
    keys=('capture_fps','capture_average_frame_ms','submits_per_present_interval','submit_wall_ms',
          'driver_cache_hits','driver_cache_misses','completed_nak_compile_scopes_max','zcull_active_marker_count')
    print(json.dumps({**{k:result[k] for k in keys},'tail_fps_excluding_transition':result['tail_excluding_first_transition']['fps_weighted'],
        'last_seven_fps':result['last_seven']['fps_weighted'],'late_jit':late},indent=2))


if __name__=='__main__':main()
