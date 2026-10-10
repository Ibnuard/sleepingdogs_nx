"""Preserve and inspect the v9 Debug capture; do not treat it as a controlled benchmark."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import re

from port_common import ROOT, write_json


def fields(line):
    return {k: int(v) for k, v in re.findall(r"\b(\w+)=(-?\d+)(?=\s|$)", line)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    payload = args.log.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    preserved = ROOT / "local/performance-v9-debug" / digest / "fex-runtime.log"
    preserved.parent.mkdir(parents=True, exist_ok=True)
    if preserved.exists():
        assert preserved.read_bytes() == payload, "Preserve earlier evidence"
    else:
        preserved.write_bytes(payload)
    lines = payload.decode("utf-8", errors="replace").splitlines()
    tags = Counter(m.group() for s in lines if (m := re.match(r"\[[^]]+\]", s)))
    frames = [dict(line=i, **fields(s)) for i, s in enumerate(lines, 1)
              if s.startswith("[SD-FRAME]")]
    assert frames and all(r["window_ms"] > 0 for r in frames)
    assert all(abs(r["frames"] * 1000 / r["window_ms"] - r["fps_x100"] / 100) < 0.02
               for r in frames)
    slow = []
    for row in reversed(frames):
        if row["fps_x100"] >= 3000:
            break
        slow.append(row)
    slow.reverse()
    assert slow
    first_line = slow[0]["line"]
    elapsed = sum(r["window_ms"] for r in slow)
    count = sum(r["frames"] for r in slow)
    jit = {}
    for phase in ("dispatch_compile", "compile_code", "invalidate"):
        rows = [dict(line=i, **fields(s)) for i, s in enumerate(lines, 1)
                if i >= first_line and s.startswith("[FEX3-JIT] phase=" + phase + " ")]
        if len(rows) >= 2:
            a, b = rows[0], rows[-1]
            jit[phase] = dict(first=a, last=b,
                elapsed_ms=b["uptime_ms"] - a["uptime_ms"],
                calls=b["calls"] - a["calls"],
                aggregate_elapsed_us=b["total_us"] - a["total_us"])
    pipeline = []
    heartbeat = None
    for i, s in enumerate(lines, 1):
        if s.startswith("[SD-LOAD]"):
            heartbeat = dict(line=i, **fields(s))
        match = re.match(r"\[FEX3-PIPE\] (\w+) ", s)
        if i >= first_line and match:
            pipeline.append(dict(line=i, heartbeat=heartbeat, phase=match[1], **fields(s)))
    progress = [dict(line=i, **fields(s)) for i, s in enumerate(lines, 1)
                if i >= first_line and s.startswith("[SD-PROGRESS]")]
    io = None
    if len(progress) >= 2:
        a, b = progress[0], progress[-1]
        io = dict(first=a, last=b, delta={k: b[k] - a[k] for k in
                  ("reads", "sd_reads", "cache_hits", "sd_ms", "syscalls")})
    heaps = [dict(line=i, **fields(s)) for i, s in enumerate(lines, 1)
             if s.startswith("[SD-RESOURCE]")]
    gpu = [fields(s) for s in lines if s.startswith("[SD-VKMEM-STATS]")]
    def evidence(prefix):
        return [dict(line=i, text=s) for i, s in enumerate(lines, 1) if s.startswith(prefix)]
    assert "[SD-FEX] launch_mode=debug" in lines
    assert any("low-window-v9-shader-optimizations" in s for s in lines)
    result = dict(
        status="ANALYZED", input=str(args.log), sha256=digest, bytes=len(payload),
        preserved_input=str(preserved.relative_to(ROOT)),
        configuration=evidence("[SD-FEX] launch_mode=") + evidence("[SD-VK]") +
            evidence("[SD-DXVK-CONFIG]") + evidence("[SD-SHADER]") + evidence("[SD-PERF]"),
        display=[dict(line=i, text=s) for i, s in enumerate(lines, 1)
                 if "Setting display mode:" in s or "Buffer size:" in s or "Present mode:" in s],
        tag_counts=dict(tags.most_common()),
        slow_segment=dict(
            selection="Trailing contiguous sub-30-FPS logged windows; scene/loading boundaries unknown",
            windows=len(slow), elapsed_ms=elapsed, frames=count,
            weighted_fps=count * 1000 / elapsed, mean_frame_ms=elapsed / count,
            minimum_window_fps=min(r["frames"] * 1000 / r["window_ms"] for r in slow),
            maximum_window_fps=max(r["frames"] * 1000 / r["window_ms"] for r in slow),
            mean_present_ms=sum(r["present_avg_us"] * r["frames"] for r in slow) / count / 1000,
            errors=sum(r["errors"] for r in slow), rows=slow),
        frame_windows=frames, late_jit=jit, late_driver_intervals=pipeline,
        late_io_counter_delta=io,
        memory=dict(minimum_heap_available=min(heaps, key=lambda r: r["heap_available"]),
                    maximum_gpu_oom=max(r["oom"] for r in gpu)),
        limitations=[
            "Launch Debug adds syscall instrumentation, thread snapshots and verbose Wine logging; overhead unmeasured.",
            "No normal-launch per-thread/server/pipeline-compiler/cache-hit interval reports in this capture.",
            "No controlled comparison with v7, v9 toggles off, or 960x540; no hardware clock readings in log.",
            "Driver wait durations include blocking and scheduling and can overlap across threads; not GPU execution times.",
            "Dispatch compilation includes nested compile_code; do not add them or treat them as CPU utilization.",
            "SD-CALL calls counters cover all calls of a thread, not just the last displayed syscall name.",
            "Frame summaries cannot recover individual frame times or 1% lows.",
            "Shader features enabled at startup do not quantify their performance benefit.",
        ])
    destination = ROOT / "reports/gameplay-v9-debug-performance-analysis.json"
    write_json(destination, result)
    print(json.dumps(dict(report=str(destination), sha256=digest,
          slow_segment={k: v for k, v in result["slow_segment"].items() if k != "rows"},
          memory=result["memory"], late_io=io), indent=2))


if __name__ == "__main__":
    main()
