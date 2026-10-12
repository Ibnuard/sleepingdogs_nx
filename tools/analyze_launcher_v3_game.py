"""Analyze the preserved v3 capture without treating submissions as scanout."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = '499c25d436b6510f4b140c030526a214461381fce4b75310f23097a9b84c8d51'


def main():
    folder = ROOT / 'local/launcher-v3-recovery' / ('input-' + CAPTURE[:12])
    inputs = {p.name: {'bytes': p.stat().st_size,
                      'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
              for p in folder.iterdir() if p.is_file()}
    assert inputs['fex-runtime.log']['sha256'] == CAPTURE
    text = (folder / 'fex-runtime.log').read_text(errors='replace')
    dxvk = (folder / 'HKShip.exe_d3d11.log').read_text(errors='replace')
    windows = [dict(intervals=int(n), elapsed_us=int(us), total_presents=int(total),
                    fps=round(int(n) * 1_000_000 / int(us), 3))
               for n, us, total in re.findall(
                   r'\[SD-NDX-FPS\].*?intervals=(\d+) elapsed_us=(\d+).*?total_presents=(\d+)', text)]
    generation = [dict(window_ms=int(ms), real=int(real), generated=int(gen),
                       presented=int(presented), real_fps=round(int(real) * 1000 / int(ms), 3),
                       submitted_fps=round(int(presented) * 1000 / int(ms), 3))
                  for ms, real, gen, presented in re.findall(
                      r'\[SD-LSFG-V15\] window_ms=(\d+) real=(\d+) generated=(\d+) presented=(\d+)', text)]
    assert generation and all(w['real'] + w['generated'] == w['presented'] for w in generation)
    states = [{k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}
              for line in text.splitlines() if line.startswith('[SD-NDX-STATE]')]
    last = states[-1]
    assert last['skipped'] == sum(last[k] for k in ('cb', 'sampler', 'shader', 'fixed'))
    previous = json.loads((ROOT / 'reports/launcher-v2-game-2d5516526c0a.json').read_text())
    config = dict(re.findall(r'^info:\s+([\w.]+) = (.+)$', dxvk, re.M))
    pooled = lambda rows: round(sum(w['intervals'] for w in rows) * 1_000_000 /
                                sum(w['elapsed_us'] for w in rows), 3)
    report = dict(
        inputs=inputs, build='sleepingdogs-launcher-v3-state-v1',
        user_observation='Feels slower than the previous build; apparent maximum of 30 FPS.',
        lsfg=dict(requested=True, motion_percent=50,
                  first_generated_markers=text.count('first interpolated present submitted'),
                  windows=generation, scanout_measured=False),
        native_present_windows=windows,
        later_windows=dict(selection='After the first two 600-interval windows; scenes are not authenticated.',
                           fps=[w['fps'] for w in windows[2:]], pooled_fps=pooled(windows[2:])),
        previous_capture=dict(sha256=previous['inputs']['fex-runtime.log']['sha256'],
                              lsfg_bypassed=True,
                              later_fps=[w['fps'] for w in previous['native_present_windows'][2:]],
                              pooled_fps=pooled(previous['native_present_windows'][2:])),
        state_filter=dict(snapshots=states, last_skip_percent=round(100 * last['skipped'] / last['attempts'], 4),
                          skipped_types=['sampler'], overhead_measured=False),
        dxvk_config=config, present_mode='FIFO', resolution='1280x720',
        explicit_30_fps_limit_in_logged_config=False,
        ceiling_interpretation='The current LSFG backend submits an interpolated and a real image in FIFO for each game frame. '
                               'At 60 Hz, one FIFO image per refresh implies a steady-state real-frame ceiling near 30 FPS. '
                               'This is derived from the implementation and FIFO semantics, not a measured scanout rate or a new 30 FPS limiter.',
        stale_runtime_log=inputs['runtime.log']['sha256'] == previous['inputs']['runtime.log']['sha256'],
        qualification='Scenes and clocks are not paired. Both actual LSFG work and the broad state filter changed together. '
                      'Their individual performance costs cannot be established from this capture.',
        next_candidate='Replace the low-hit broad binding cache with synchronous inline COM argument transport; '
                       'remove native production accounting with no report consumer. Preserve saved LSFG settings '
                       'and Light 720p. Admit verified deferred-context work during Present with lifetime, '
                       'Multithread Enter and nested-call safeguards; validate the composed path before delivery.',
        next_candidate_hardware_tested=False)
    assert config['dxgi.syncInterval'] == '1' and 'Present mode: VK_PRESENT_MODE_FIFO_KHR' in dxvk
    assert not any('framerate' in k.lower() for k in config)
    out = ROOT / 'reports' / ('launcher-v3-game-' + CAPTURE[:12])
    out.mkdir(exist_ok=True)
    tokens = ('[BUILD]', '[SD-DXVK-CONFIG]', '[SD-LSFG-', '[SD-NDX-FPS]', '[SD-NDX-STATE]', '[SD-NDX-PROGRESS]')
    evidence = [line for line in text.splitlines() if any(t in line for t in tokens)]
    evidence += [line for line in dxvk.splitlines() if ' = ' in line or any(t in line for t in ('Present mode:', 'Buffer size:', 'Image count:'))]
    (out / 'evidence.txt').write_text('\n'.join(evidence) + '\n', encoding='utf-8')
    out.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('later_windows', 'previous_capture', 'stale_runtime_log')}, indent=2))
    print(f"LSFG generating windows: {len(generation)}; binding skip rate: {report['state_filter']['last_skip_percent']}%")


if __name__ == '__main__':
    main()
