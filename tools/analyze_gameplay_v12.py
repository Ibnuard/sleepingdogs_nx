"""Preserve and summarize the v12 run; comparisons are observational, not paired."""
from pathlib import Path
import argparse
import hashlib
import json
import re

from port_common import ROOT, sha, write_json
from analyze_frame_diagnostics import analyze, fields
from analyze_gameplay_v11 import summarize


BATCH_KEYS = ('flushes', 'explicit', 'sync', 'strong', 'weak', 'deferred_hints')


def batch_summary(intervals, start_line, end_line):
    """Only difference endpoints wholly inside these log-line boundaries."""
    rows = [r for r in intervals if r['from_line'] >= start_line and r['to_line'] <= end_line]
    totals = {k: sum(r['delta'][k] for r in rows) for k in BATCH_KEYS}
    return dict(requested_start_line=start_line, requested_end_line=end_line,
                measured_start_line=rows[0]['from_line'] if rows else None,
                measured_end_line=rows[-1]['to_line'] if rows else None,
                intervals=len(rows), totals=totals,
                flush_class_percent={k: 100 * totals[k] / totals['flushes'] if totals['flushes'] else None
                                     for k in ('explicit', 'sync', 'strong', 'weak')},
                note='Inner cumulative-counter endpoints only; not the entire time window. '
                     'deferred_hints counts requests, not eliminated submissions.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    payload = args.log.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    saved = ROOT / 'local/performance-v12' / digest / 'fex-runtime.log'
    saved.parent.mkdir(parents=True, exist_ok=True)
    if saved.exists():
        assert saved.read_bytes() == payload, 'Preserved log differs'
    else:
        with saved.open('xb') as out:
            out.write(payload)
    assert sha(saved) == digest

    capture = analyze(payload)
    assert capture['status'] == 'COMPLETE'
    capture.update(input=str(args.log), sha256=digest, preserved_input=saved.relative_to(ROOT).as_posix())
    capture_path = ROOT / 'reports' / ('gameplay-v12-' + digest[:12] + '.json')
    write_json(capture_path, capture)
    lines = payload.decode('utf-8', errors='replace').splitlines()
    frames, changes, cpu, batches, jit, provenance = [], [], [], [], [], []
    mode = None
    changed_in_window = False
    for i, line in enumerate(lines, 1):
        if match := re.search(r'Setting display mode: (\d+)x(\d+)', line):
            new_mode = tuple(map(int, match.groups()))
            if new_mode != mode:
                mode = new_mode
                changed_in_window = True
                changes.append(dict(line=i, resolution=list(mode)))
        if line.startswith('[SD-FRAME]'):
            frames.append(dict(line=i, resolution=mode, resolution_changed_in_window=changed_in_window,
                               **fields(line)))
            changed_in_window = False
        if line.startswith('[THREADS]') and (match := re.search(r'use ([\d.]+) cores', line)):
            cpu.append(dict(line=i, registered_cores=float(match[1]),
                            threads={t + k: float(v) for t, k, v in
                                     re.findall(r'(\d+)([ws])@-?\d+ ([\d.]+)%', line)}))
        if '[SD-DXVK-BATCH]' in line and 'flushes=' in line:
            values = fields(line)
            assert values.get('enabled') == 1
            assert all(k in values for k in BATCH_KEYS)
            assert values['flushes'] == sum(values[k] for k in ('explicit', 'sync', 'strong', 'weak'))
            batches.append(dict(line=i, **values))
        if line.startswith('[FEX3-JIT] phase='):
            phase = re.search(r'phase=(\w+)', line)[1]
            jit.append(dict(line=i, phase=phase, **fields(line)))
        if any(marker in line for marker in ('[BUILD]', '[SD-VK]', 'DXVK: 3.',
                                             '[SD-SYNC-MODE]', '[FEX3-PRESET]',
                                             '[FEX3-JIT-CONFIG]', 'Discarding old cache.',
                                             'hint_chunks=')):
            provenance.append(dict(line=i, text=line))

    assert batches and any('DXVK: 3.1.1-sdbatch1' in row['text'] for row in provenance)
    intervals = []
    for previous, current in zip(batches, batches[1:]):
        delta = {k: current[k] - previous[k] for k in BATCH_KEYS}
        assert all(value >= 0 for value in delta.values()), 'Counter reset or non-monotonic log'
        assert delta['flushes'] == sum(delta[k] for k in ('explicit', 'sync', 'strong', 'weak'))
        intervals.append(dict(from_line=previous['line'], to_line=current['line'], delta=delta))
    slow = []
    for row in reversed(frames):
        if row['fps_x100'] >= 3000:
            break
        slow.append(row)
    slow.reverse()
    assert slow
    last = capture['final_snapshot']
    presenting = [row for row in last['rows'].values() if 'frame' in row]
    assert len(presenting) == 1
    presenting = presenting[0]
    count = presenting['frame']['n']
    capture_modes = [row for row in changes if row['line'] <= capture['start_line']]
    assert capture_modes
    capture_res = capture_modes[-1]['resolution']
    capture_resolution_changes = [row for row in changes if capture['start_line'] < row['line'] <= last['line']]
    by_resolution = {f'{w}x{h}': summarize([row for row in slow if row['resolution'] == (w, h)
                                         and not row['resolution_changed_in_window']])
                     for w, h in sorted({tuple(row['resolution']) for row in changes})}
    baseline_path = ROOT / 'reports/gameplay-v11-performance-analysis.json'
    baseline = json.loads(baseline_path.read_text())
    late_jit = {}
    for phase in sorted({row['phase'] for row in jit}):
        selected = [row for row in jit if row['phase'] == phase and row['uptime_ms'] >= 200000]
        if len(selected) >= 2:
            first, final = selected[0], selected[-1]
            elapsed = final['uptime_ms'] - first['uptime_ms']
            late_jit[phase] = dict(from_line=first['line'], to_line=final['line'],
                                  uptime_from_ms=first['uptime_ms'], uptime_to_ms=final['uptime_ms'],
                                  elapsed_ms=elapsed, calls=final['calls'] - first['calls'],
                                  completed_wall_us=final['total_us'] - first['total_us'],
                                  note='Completed calls; phase durations may overlap/nest and are not CPU ticks.')
    metrics = dict(capture_average_frame_ms=presenting['present_gap_average_ms'],
                   capture_fps=1000 / presenting['present_gap_average_ms'],
                   submit_thread_cpu_ms=presenting['frame']['thread_cpu_total_us'] / 1000,
                   submit_calls=presenting['stages']['vk_submit']['n'],
                   submit_wall_ms=presenting['stages']['vk_submit']['total_us'] / 1000,
                   submits_per_present_interval=presenting['stages']['vk_submit']['n'] / count)
    result = dict(status='ANALYZED', sha256=digest, input=str(args.log),
        preserved_input=saved.relative_to(ROOT).as_posix(), capture_report=capture_path.relative_to(ROOT).as_posix(),
        analyzer_sha256=sha(Path(__file__)),
        user_reported=dict(device='OLED handheld', previous_typical_fps=[11,14],
            latest_more_frequent_fps=[16,19], target_resolution=[1280,720], target_fps=30,
            prior_clocks_mhz=dict(cpu=1728,gpu=768,ram=1600),
            clocks_reconfirmed_for_this_log=False, same_position_and_camera_confirmed=False,
            measured_by_log=False),
        log_provenance=provenance, resolution_changes=changes, all_frame_windows=frames,
        slow_segment=summarize(slow), last_seven_windows=summarize(slow[-7:]), by_resolution=by_resolution,
        capture_resolution=capture_res, capture_resolution_changes=capture_resolution_changes,
        capture_start_line=capture['start_line'], capture_end_line=last['line'],
        capture_duration_ms=last['elapsed_ms'], capture_present_intervals=count, **metrics,
        capture_thread_waits=[dict(handle=row['handle'], labels=row.get('observed_thread_labels', []),
                                   stages=row['stages']) for row in last['rows'].values()],
        batch_counter_snapshots=batches, batch_counter_intervals=intervals,
        batch_capture_inner=batch_summary(intervals, capture['start_line'], last['line']),
        batch_slow_inner=batch_summary(intervals, slow[0]['line'], slow[-1]['line']),
        batch_last_seven_inner=batch_summary(intervals, slow[-7]['line'], slow[-1]['line']),
        jit_after_200_seconds=late_jit,
        registered_cpu_samples=[row for row in cpu if row['line'] >= slow[0]['line']],
        prior_v11_comparison=dict(report=baseline_path.relative_to(ROOT).as_posix(),
            report_sha256=sha(baseline_path), log_sha256=baseline['sha256'], paired_test=False,
            capture_resolution=baseline['capture_resolution'],
            metrics={key: dict(v11=baseline[key], v12=value, difference=value-baseline[key])
                     for key,value in metrics.items()},
            note='Observed runs differ in scene, timing, cache state and potentially clocks; '
                 'these differences do not establish a causal speedup.'),
        limitations=capture['limitations'] + [
            'Sub-30-FPS windows are a workload heuristic, not verified gameplay or scene markers.',
            'The resolution-transition window is excluded from per-resolution aggregates.',
            'The run changes from 540p to 720p; resolution comparisons are not controlled.',
            'DXVK discarded the prior version shader cache; late compilation counters must be checked separately.',
            'Batch deltas use only fully enclosed snapshot endpoints, so they under-cover their enclosing frame windows.',
            'Deferred hints are attempted flush requests, not a count of saved GPU submissions.',
            'Registered CPU utilization excludes unregistered and system threads.',
            'Wine and Vulkan waits overlap across threads and cannot simply be subtracted from frame time.',
            'User clocks are from the previous report and have not been reconfirmed for this run.'])
    destination = ROOT / 'reports/gameplay-v12-performance-analysis.json'
    write_json(destination, result)
    print(json.dumps(dict(report=str(destination), sha256=digest, **metrics,
                         batch_slow_inner=result['batch_slow_inner']), indent=2))


if __name__ == '__main__':
    main()
