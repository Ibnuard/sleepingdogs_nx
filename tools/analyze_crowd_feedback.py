"""Analyze a post-v14.1 report without inferring the installed build from cache hits."""
from pathlib import Path
import argparse
import hashlib
import json
import re
from port_common import ROOT,sha,write_json
from analyze_frame_diagnostics import analyze,fields
from analyze_gameplay_v11 import summarize


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log',type=Path)
    args=parser.parse_args()
    data=args.log.read_bytes();digest=hashlib.sha256(data).hexdigest()
    preserved=ROOT/'local/performance-feedback'/digest/'fex-runtime.log'
    preserved.parent.mkdir(parents=True,exist_ok=True)
    if preserved.exists():assert preserved.read_bytes()==data
    else:
        with preserved.open('xb') as f:f.write(data)
    capture=analyze(data)
    assert capture['status']=='COMPLETE'
    lines=data.decode(errors='replace').splitlines()
    frames=[];cache=[];jit=[];nak=[];oom=[];markers=[];modes=[];cpu=[];io=[]
    for line,s in enumerate(lines,1):
        row=dict(line=line,**fields(s))
        if s.startswith('[SD-FRAME]'):frames.append(row)
        if s.startswith('[FEX3-WARM] driver_cache_hits='):cache.append(row)
        if s.startswith('[FEX3-JIT] phase='):jit.append(dict(phase=re.search(r'phase=(\w+)',s)[1],**row))
        if s.startswith('[SD-SHADER-CACHE]'):nak.append(row)
        if s.startswith('[SD-VKMEM-STATS]'):oom.append(row)
        if s.startswith('[SD-NVK-'):markers.append(dict(line=line,text=s))
        if s.startswith('[SD-PERF-IO]'):io.append(row)
        if s.startswith('[THREADS]') and (m:=re.search(r'use ([\d.]+) cores',s)):
            cpu.append(dict(line=line,registered_cores=float(m[1])))
        if m:=re.search(r'Setting display mode: (\d+)x(\d+)',s):
            modes.append(dict(line=line,resolution=list(map(int,m.groups()))))
    slow=[]
    for r in reversed(frames):
        if r['fps_x100']>=3000:break
        slow.append(r)
    slow.reverse()
    last=capture['final_snapshot']
    presenting=[r for r in last['rows'].values() if 'frame' in r]
    assert len(presenting)==1
    p=presenting[0];intervals=p['frame']['n']
    late={}
    for phase in ('compile_code','dispatch_compile','invalidate'):
        rows=[r for r in jit if r['phase']==phase and r['uptime_ms']>=200000]
        if len(rows)>1:
            a,b=rows[0],rows[-1]
            late[phase]=dict(elapsed_ms=b['uptime_ms']-a['uptime_ms'],
                calls=b['calls']-a['calls'],completed_wall_us=b['total_us']-a['total_us'])
    marker141=[r for r in markers if r['text'].startswith('[SD-NVK-V14.1]')]
    report=dict(status='ANALYZED',sha256=digest,input=str(args.log),
        preserved_input=preserved.relative_to(ROOT).as_posix(),analyzer_sha256=sha(Path(__file__)),
        user_reported=dict(frequent_fps=20,crowded_scene_fps=[11,14],
            cache_fix_copied_and_closed_from_HOME=True,measured_clocks_available=False),
        runtime_identity=dict(v141_marker_count=len(marker141),markers=markers,
            installed_nro_sha256=None,verified_v141=False if not marker141 else True,
            conclusion='Installation was confirmed by user, but the v14.1 marker is absent. '
                       'No conclusion that the wrong build is installed from this absence alone. '
                       'The NRO actually stored on the SD is needed to resolve the discrepancy.'),
        resolutions=modes,capture_fps=1000/p['present_gap_average_ms'],
        capture_average_frame_ms=p['present_gap_average_ms'],capture_duration_ms=last['elapsed_ms'],
        present_thread_cpu_ms=p['frame']['thread_cpu_total_us']/1000,
        submits_per_present_interval=p['stages']['vk_submit']['n']/intervals,
        submit_wall_ms=p['stages']['vk_submit']['total_us']/1000,
        slow_tail=summarize(slow),tail_without_first_transition=summarize(slow[1:]),
        last_seven=summarize(slow[-7:]),registered_cpu_samples=cpu,
        driver_cache_hits=sum(r['driver_cache_hits'] for r in cache),
        driver_cache_misses=sum(r['misses'] for r in cache),
        max_completed_nak_compiles=max((r['completed'] for r in nak),default=None),
        max_vulkan_oom=max((r['oom'] for r in oom),default=None),
        jit_after_200_seconds=late,io_intervals=io,capture=capture,
        limitations=capture['limitations']+[
            'The final sub-30-FPS segment is a workload heuristic, not an identified scene.',
            'Ten-second FPS windows do not validate or disprove instantaneous HUD readings.',
            'Zero NAK compilation is normal with a warm cache and does not identify its build.',
            'The build marker discrepancy cannot be resolved by trusting the filename or directory.',
            'Scene density sensitivity alone does not distinguish CPU scene work, draw dispatch or GPU geometry/shading.',
            'No measured performance gain or installed-build verdict from comparison with previous unpaired logs.'])
    dest=ROOT/'reports'/('crowd-feedback-'+digest[:12]+'.json')
    write_json(dest,report)
    print(json.dumps({k:report[k] for k in ('capture_fps','capture_average_frame_ms',
        'submit_wall_ms','submits_per_present_interval','driver_cache_hits',
        'driver_cache_misses','max_completed_nak_compiles','max_vulkan_oom','jit_after_200_seconds')},indent=2))
    print('last7',report['last_seven']['fps_weighted'],'report',dest)


if __name__=='__main__':main()
