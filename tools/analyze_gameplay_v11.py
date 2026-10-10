"""Preserve resolution and observer provenance in the v11 gameplay analysis."""
from pathlib import Path
import argparse
import json
import re
from port_common import ROOT, sha, write_json
from analyze_frame_diagnostics import analyze, fields


def summarize(rows):
    elapsed = sum(r['window_ms'] for r in rows)
    frames = sum(r['frames'] for r in rows)
    return dict(windows=len(rows), window_ms=elapsed, frames=frames,
                fps_weighted=frames*1000/elapsed if elapsed else None,
                fps_min=min((r['fps_x100']/100 for r in rows), default=None),
                fps_max=max((r['fps_x100']/100 for r in rows), default=None), rows=rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', type=Path)
    a = p.parse_args()
    payload = a.log.read_bytes(); digest = sha(a.log)
    capture = analyze(payload)
    lines = payload.decode('utf-8', errors='replace').splitlines()
    frames, changes, cpu = [], [], []
    mode = None; changed_in_window = False
    for i,s in enumerate(lines, 1):
        if m := re.search(r'Setting display mode: (\d+)x(\d+)', s):
            new_mode = tuple(map(int, m.groups()))
            if new_mode != mode:
                mode = new_mode; changed_in_window = True
                changes.append(dict(line=i, resolution=list(mode)))
        if s.startswith('[SD-FRAME]'):
            frames.append(dict(line=i, resolution=mode, resolution_changed_in_window=changed_in_window,
                               **fields(s)))
            changed_in_window = False
        if s.startswith('[THREADS]') and (m := re.search(r'use ([\d.]+) cores', s)):
            cpu.append(dict(line=i, registered_cores=float(m[1]),
                            threads={t+k:float(v) for t,k,v in re.findall(r'(\d+)([ws])@-?\d+ ([\d.]+)%',s)}))
    slow = []
    for row in reversed(frames):
        if row['fps_x100'] >= 3000: break
        slow.append(row)
    slow.reverse()
    assert capture['status'] == 'COMPLETE' and slow
    last = capture['final_snapshot']
    presenting = [r for r in last['rows'].values() if 'frame' in r]
    assert len(presenting) == 1
    presenting = presenting[0]; n = presenting['frame']['n']
    by_resolution = {f'{w}x{h}':summarize([r for r in slow if r['resolution'] == (w,h)
                                        and not r['resolution_changed_in_window']])
                     for w,h in ((1280,720),(960,540))}
    capture_res = [c for c in changes if c['line'] <= capture['start_line']][-1]['resolution']
    result = dict(status='ANALYZED', sha256=digest, input=str(a.log),
        user_reported=dict(overlay='Status Monitor / Tesla', device='OLED handheld',
            clocks_mhz=dict(cpu=1728,gpu=768,ram=1600), observed_fps=[11,20],
            observed_gpu_load_peak_percent=99, observed_ram_traffic_gb_per_sec=6,
            same_position_and_camera_confirmed=False, measured_by_log=False),
        resolution_changes=changes, slow_segment=summarize(slow), by_resolution=by_resolution,
        capture_resolution=capture_res, capture_start_line=capture['start_line'],
        capture_end_line=last['line'], capture_duration_ms=last['elapsed_ms'],
        capture_average_frame_ms=presenting['present_gap_average_ms'],
        capture_fps=1000/presenting['present_gap_average_ms'],
        submit_thread_cpu_ms=presenting['frame']['thread_cpu_total_us']/1000,
        submit_calls=presenting['stages']['vk_submit']['n'],
        submit_wall_ms=presenting['stages']['vk_submit']['total_us']/1000,
        submits_per_present_interval=presenting['stages']['vk_submit']['n']/n,
        registered_cpu_samples=[r for r in cpu if r['line'] >= slow[0]['line']],
        limitations=capture['limitations']+[
            'Sub-30-FPS windows are a workload heuristic, not verified gameplay/scene markers.',
            'The resolution-transition window is excluded from per-resolution aggregates.',
            '720p/540p scene and camera are uncontrolled; this is not a paired resolution benchmark.',
            'The 30-second per-thread capture ended before the switch to 540p.',
            'User overlay readings are not recorded in the log; 6 GB/s is traffic, not 6 GB allocated RAM.',
            'Registered CPU utilization excludes unregistered/system threads.',
            'No measured FPS gain from batching is available.'])
    write_json(ROOT/'reports/gameplay-v11-performance-analysis.json', result)
    print(json.dumps({k:result[k] for k in ('capture_fps','capture_average_frame_ms','submit_thread_cpu_ms',
        'submit_wall_ms','submits_per_present_interval')}, indent=2))
    print(json.dumps({k:{n:v for n,v in s.items() if n != 'rows'} for k,s in by_resolution.items()},indent=2))


if __name__ == '__main__': main()
