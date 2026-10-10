"""Preserve and analyze the user's v7 Performance run without guessing scene markers."""
from pathlib import Path
import argparse
import json
import re
from port_common import ROOT, sha, write_json


def fields(line):
    return {k: int(v) for k, v in re.findall(r'\b(\w+)=(-?\d+)(?=\s|$)', line)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    dest = ROOT / 'local/performance-v7/fex-runtime.log'
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = args.log.read_bytes()
    if dest.exists():
        assert dest.read_bytes() == payload, 'Preserve the previous input log'
    else:
        dest.write_bytes(payload)
    lines = payload.decode('utf-8', errors='replace').splitlines()
    frames = [dict(line=i, **fields(s)) for i, s in enumerate(lines, 1) if s.startswith('[SD-FRAME]')]
    assert frames and all(row['window_ms'] > 0 for row in frames)
    slow = []
    for row in reversed(frames):
        if row['fps_x100'] >= 3000:
            break
        slow.append(row)
    slow.reverse()
    assert slow, 'No trailing sub-30-FPS segment in this input'
    elapsed = sum(row['window_ms'] for row in slow)
    count = sum(row['frames'] for row in slow)
    fps = count * 1000 / elapsed
    present = sum(row['present_avg_us'] * row['frames'] for row in slow) / count
    jit = {}
    for phase in ('dispatch_compile', 'compile_code', 'invalidate'):
        rows = [fields(s) for s in lines if s.startswith('[FEX3-JIT] phase=' + phase + ' ')]
        late = [row for row in rows if row['uptime_ms'] >= 90000]
        if len(late) > 1:
            a, b = late[0], late[-1]
            jit[phase] = dict(window_ms=b['uptime_ms']-a['uptime_ms'],
                              calls=b['calls']-a['calls'], total_us=b['total_us']-a['total_us'],
                              explanation='Aggregate elapsed call time, may overlap across threads; not CPU utilization')
    heaps = [fields(s)['heap_available'] for s in lines if s.startswith('[SD-RESOURCE]')]
    gpu = [fields(s) for s in lines if s.startswith('[SD-VKMEM-STATS]')]
    config = [s for s in lines if s.startswith('[SD-DXVK-CONFIG]')]
    assert any('profile=performance renderer=dxvk-3.1.1 hud=FPS' in s for s in config)
    assert any('[SD-FEX] launch_mode=gui' in s for s in lines)
    assert any('VK_PRESENT_MODE_IMMEDIATE_KHR' in s for s in lines)
    result = dict(status='PASS', log_sha256=sha(dest), log_bytes=len(payload),
        input=str(args.log), preserved_input='local/performance-v7/fex-runtime.log',
        hardware_user_reported='OLED handheld; CPU 1728 / GPU 768 / RAM 1600 MHz',
        user_report='Performance, lowest in-game detail, observed 16-20 FPS; 540p not yet tried',
        launch='normal GUI', config=config, display_mode='1280x720@60',
        final_swapchain='1292x732 scaled to 1280x720', present_mode='IMMEDIATE',
        selection='Trailing contiguous logged windows below 30 FPS; inferred slow segment, no scene/menu markers',
        slow_segment=dict(windows=len(slow), elapsed_ms=elapsed, frames=count,
            fps_weighted=fps, fps_min=min(r['fps_x100']/100 for r in slow),
            fps_max=max(r['fps_x100']/100 for r in slow),
            frame_average_ms=1000/fps, present_average_ms=present/1000,
            present_share_percent=present*fps/10000,
            errors=sum(r['errors'] for r in slow), rows=slow),
        all_frame_windows=frames, late_jit=jit,
        memory=dict(minimum_heap_available_bytes=min(heaps),
                    maximum_gpu_oom=max(r['oom'] for r in gpu)),
        limitations=['Not a controlled comparison with v6 or 540p.',
            'Low Present duration does not exclude GPU waits in other calls.',
            'No per-thread CPU, driver-wait or pipeline compiler interval reports in this normal v7 run.',
            'DisplaySettings.xml content and applied advanced options are not present in the log.',
            'No evidence yet that a software change reaches stable 30 FPS.'])
    write_json(ROOT/'reports/gameplay-v7-performance-analysis.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('all_frame_windows','slow_segment')}, indent=2))
    print(json.dumps({k:v for k,v in result['slow_segment'].items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
