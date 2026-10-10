"""Preserve the v13 hardware run and compare unpaired observations with v12."""
from pathlib import Path
import argparse
import hashlib
import json
import re

from port_common import ROOT, sha, write_json
from analyze_frame_diagnostics import analyze, fields
from analyze_gameplay_v11 import summarize
from analyze_gameplay_v12 import BATCH_KEYS, batch_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    payload = args.log.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    saved = ROOT / 'local/performance-v13' / digest / 'fex-runtime.log'
    saved.parent.mkdir(parents=True, exist_ok=True)
    if saved.exists():
        assert saved.read_bytes() == payload
    else:
        with saved.open('xb') as out:
            out.write(payload)
    assert sha(saved) == digest
    capture = analyze(payload)
    assert capture['status'] == 'COMPLETE'
    capture.update(sha256=digest, preserved_input=saved.relative_to(ROOT).as_posix())
    capture_path = ROOT / 'reports' / ('gameplay-v13-' + digest[:12] + '.json')
    write_json(capture_path, capture)
    frames, modes, batches, jit, provenance, pipelines = [], [], [], [], [], []
    mode = None
    for i, line in enumerate(payload.decode('utf-8', errors='replace').splitlines(), 1):
        if match := re.search(r'Setting display mode: (\d+)x(\d+)', line):
            new_mode = tuple(map(int, match.groups()))
            if new_mode != mode:
                mode = new_mode
                modes.append(dict(line=i, resolution=mode))
        if line.startswith('[SD-FRAME]'):
            frames.append(dict(line=i, resolution=mode, **fields(line)))
        if '[SD-DXVK-BATCH]' in line and 'flushes=' in line:
            row = fields(line)
            assert row['flushes'] == sum(row[k] for k in ('explicit', 'sync', 'strong', 'weak'))
            batches.append(dict(line=i, **row))
        if line.startswith('[FEX3-JIT] phase='):
            jit.append(dict(line=i, phase=re.search(r'phase=(\w+)', line)[1], **fields(line)))
        if line.startswith('[FEX3-WARM] graphics_pipeline'):
            pipelines.append(dict(line=i, **fields(line)))
        if any(s in line for s in ('[BUILD]', '[SD-VK]', 'DXVK: 3.', '[SD-SYNC-MODE]',
                                   '[FEX3-PRESET]', '[FEX3-JIT-CONFIG]', '[SD-NVK-V13]',
                                   'Type 0:', 'Type 1:', 'Type 2:', 'Discarding old cache.')):
            provenance.append(dict(line=i, text=line))
    slow = []
    for row in reversed(frames):
        if row['fps_x100'] >= 3000:
            break
        slow.append(row)
    slow.reverse()
    assert slow and batches and modes
    intervals = []
    for a, b in zip(batches, batches[1:]):
        delta = {k: b[k] - a[k] for k in BATCH_KEYS}
        assert all(v >= 0 for v in delta.values())
        intervals.append(dict(from_line=a['line'], to_line=b['line'], delta=delta))
    last = capture['final_snapshot']
    rows = [row for row in last['rows'].values() if 'frame' in row]
    assert len(rows) == 1
    row = rows[0]
    metrics = dict(capture_average_frame_ms=row['present_gap_average_ms'],
                   capture_fps=1000 / row['present_gap_average_ms'],
                   submit_thread_cpu_ms=row['frame']['thread_cpu_total_us'] / 1000,
                   submit_calls=row['stages']['vk_submit']['n'],
                   submit_wall_ms=row['stages']['vk_submit']['total_us'] / 1000,
                   submits_per_present_interval=row['stages']['vk_submit']['n'] / row['frame']['n'])
    late_jit = {}
    for phase in sorted({j['phase'] for j in jit}):
        selected = [j for j in jit if j['phase'] == phase and j['uptime_ms'] >= 200000]
        if len(selected) >= 2:
            a, b = selected[0], selected[-1]
            late_jit[phase] = dict(uptime_from_ms=a['uptime_ms'], uptime_to_ms=b['uptime_ms'],
                                  elapsed_ms=b['uptime_ms']-a['uptime_ms'],
                                  completed_wall_us=b['total_us']-a['total_us'], calls=b['calls']-a['calls'])
    baseline_path = ROOT / 'reports/gameplay-v12-performance-analysis.json'
    baseline = json.loads(baseline_path.read_text())
    result = dict(status='ANALYZED', input=str(args.log), sha256=digest,
                  preserved_input=saved.relative_to(ROOT).as_posix(), analyzer_sha256=sha(Path(__file__)),
                  capture_report=capture_path.relative_to(ROOT).as_posix(),
                  user_reported=dict(observed_fps=[17,20], remaining_slow_motion=True,
                    prior_clocks_mhz=dict(cpu=1728,gpu=768,ram=1600), clocks_reconfirmed=False),
                  log_provenance=provenance, resolution_changes=modes, all_frame_windows=frames,
                  slow_segment=summarize(slow), last_seven_windows=summarize(slow[-7:]),
                  capture_start_line=capture['start_line'], capture_end_line=last['line'],
                  capture_duration_ms=last['elapsed_ms'], capture_present_intervals=row['frame']['n'],
                  **metrics, capture_thread_waits=list(last['rows'].values()),
                  batch_counter_intervals=intervals,
                  batch_capture_inner=batch_summary(intervals,capture['start_line'],last['line']),
                  batch_last_seven_inner=batch_summary(intervals,slow[-7]['line'],slow[-1]['line']),
                  jit_after_200_seconds=late_jit, graphics_pipeline_windows=pipelines,
                  prior_v12_comparison=dict(report=baseline_path.relative_to(ROOT).as_posix(),
                    report_sha256=sha(baseline_path), paired_test=False,
                    metrics={k:dict(v12=baseline[k],v13=v) for k,v in metrics.items()}),
                  limitations=capture['limitations']+[
                    'Different scenes, cache states and possibly clocks; no causal FPS gain can be computed.',
                    'Sub-30-FPS tail is a workload heuristic, not a verified scene boundary.',
                    'The new private GPU memory type confirms v13 memory policy, but the log has no ZCULL-active marker.',
                    'The baked runtime Mesa banner predates the v13 relink; the DXVK numeric driver version omits its suffix.',
                    'Per-thread waits and compilation durations overlap and must not be subtracted from frame time.',
                    'No GPU timestamp profile of rendering passes is available.'])
    destination = ROOT / 'reports/gameplay-v13-performance-analysis.json'
    write_json(destination,result)
    print(json.dumps(dict(report=str(destination), **metrics,
                         slow_fps=result['slow_segment']['fps_weighted'],
                         last_seven_fps=result['last_seven_windows']['fps_weighted'],
                         late_jit=late_jit, batch_capture=result['batch_capture_inner']),indent=2))


if __name__ == '__main__':
    main()
