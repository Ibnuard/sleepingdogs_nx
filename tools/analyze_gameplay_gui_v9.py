"""Analyze the normal-launch v9 interval capture without inferring a frame critical path."""
from pathlib import Path
import argparse
import hashlib
import json
import re

from port_common import ROOT, write_json


def fields(line):
    return {k: int(v) for k, v in re.findall(r"\b(\w+)=(-?\d+)(?=[\s;,]|$)", line)}


def summarize(rows):
    elapsed = sum(r["frame"]["window_ms"] for r in rows)
    frames = sum(r["frame"]["frames"] for r in rows)
    return dict(reports=[r["report"] for r in rows], elapsed_ms=elapsed, frames=frames,
        fps=frames * 1000 / elapsed, frame_ms=elapsed / frames,
        min_window_fps=min(r["frame"]["fps"] for r in rows),
        max_window_fps=max(r["frame"]["fps"] for r in rows),
        registered_cpu_cores_min=min(r["registered_cpu_cores"] for r in rows),
        registered_cpu_cores_max=max(r["registered_cpu_cores"] for r in rows),
        main_thread_percent_min=min(r["threads"]["4w"]["cpu_percent"] for r in rows),
        main_thread_percent_max=max(r["threads"]["4w"]["cpu_percent"] for r in rows),
        dxvk_cs_percent_min=min(r["threads"]["40w"]["cpu_percent"] for r in rows),
        dxvk_cs_percent_max=max(r["threads"]["40w"]["cpu_percent"] for r in rows),
        graphics_pipeline_calls=sum(r["warm"]["graphics_pipeline"]["n"] for r in rows),
        graphics_pipeline_aggregate_us=sum(r["warm"]["graphics_pipeline"]["total_us"] for r in rows),
        driver_cache_get_aggregate_us=sum(r["warm"]["driver_cache_get"]["total_us"] for r in rows),
        server_requests=sum(r["server"]["requests"] for r in rows),
        sd_read_aggregate_ms=sum(r["io"]["sd_ms"] for r in rows),
        observer_aggregate_us=sum(r["observer_us"] for r in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    payload = args.log.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    preserved = ROOT / "local/performance-v9-gui" / digest / "fex-runtime.log"
    preserved.parent.mkdir(parents=True, exist_ok=True)
    if preserved.exists():
        assert preserved.read_bytes() == payload
    else:
        preserved.write_bytes(payload)
    lines = payload.decode("utf-8", errors="replace").splitlines()
    assert "[SD-FEX] launch_mode=gui" in lines
    assert any("low-window-v9-shader-optimizations" in s for s in lines)
    blocks = []
    current = frame = None
    names = {}
    jit = []
    for i, s in enumerate(lines, 1):
        if s.startswith("[FEX3-DXVKCORE] tid="):
            m = re.search(r"tid=(\d+).* name=(\S+)", s)
            if m:
                names[m[1] + "w"] = m[2]
        if s.startswith("[SD-FRAME]"):
            frame = dict(line=i, **fields(s))
            frame["fps"] = frame["frames"] * 1000 / frame["window_ms"]
            assert abs(frame["fps"] - frame["fps_x100"] / 100) < 0.02
        if s.startswith("[SD-PERF]") and "phase=" in s:
            current = dict(line=i, **fields(s), frame=frame, threads={}, pipe={}, warm={})
            blocks.append(current)
        if s.startswith("[FEX3-JIT] phase="):
            jit.append(dict(line=i, phase=re.search(r"phase=(\w+)", s)[1], **fields(s)))
        if current is None:
            continue
        if s.startswith("[THREADS]"):
            current["registered_cpu_cores"] = float(re.search(r"use ([\d.]+) cores", s)[1])
            current["threads"] = {
                t + kind: dict(core_mask_snapshot_core=int(core), cpu_percent=float(p))
                for t, kind, core, p in re.findall(r"(\d+)([ws])@(-?\d+) ([\d.]+)%", s)}
        if s.startswith("[SERVER]"):
            current["server"] = dict(
                requests=int(re.search(r"\] (\d+) requests", s)[1]),
                aggregate_ms=int(re.search(r"requests, (\d+) ms", s)[1]),
                operations={n: dict(calls=int(c), avg_us=int(u), aggregate_ms=int(ms))
                            for n, c, u, ms in re.findall(r"(\w+) (\d+) avg (\d+)us (\d+)ms", s)})
        if m := re.match(r"\[FEX3-PIPE\] (\w+) ", s):
            current["pipe"][m[1]] = fields(s)
        if m := re.match(r"\[FEX3-WARM\] (\w+) ", s):
            current["warm"][m[1]] = fields(s)
        if s.startswith("[FEX3-WARM] driver_cache_hits="):
            current["driver_cache"] = fields(s)
        if s.startswith("[SD-SHADER-CACHE]"):
            current["shader_allocation_cache"] = fields(s)
        if s.startswith("[SD-PERF-IO]"):
            current["io"] = fields(s)
        if s.startswith("[SD-PERF]") and "observer_us=" in s:
            current["observer_us"] = fields(s)["observer_us"]
    assert names["40w"] == "dxvk-cs"
    assert [b["report"] for b in blocks] == list(range(len(blocks)))
    assert all(b["frame"]["window_ms"] == b["window_ms"] for b in blocks[1:])
    slow = []
    for b in reversed(blocks[1:]):
        if b["frame"]["fps"] >= 30:
            break
        slow.append(b)
    slow.reverse()
    assert slow
    phase_delta = {}
    for phase in ("dispatch_compile", "compile_code", "invalidate"):
        rows = [r for r in jit if r["phase"] == phase and r["line"] >= slow[0]["line"]]
        if len(rows) >= 2:
            a, b = rows[0], rows[-1]
            phase_delta[phase] = dict(first=a, last=b,
                elapsed_ms=b["uptime_ms"] - a["uptime_ms"],
                calls=b["calls"] - a["calls"], aggregate_us=b["total_us"] - a["total_us"])
    resources = [dict(line=i, **fields(s)) for i, s in enumerate(lines, 1) if s.startswith("[SD-RESOURCE]")]
    result = dict(status="ANALYZED", input=str(args.log), sha256=digest, bytes=len(payload),
        preserved_input=str(preserved.relative_to(ROOT)),
        user_observation="FPS drop occurred while changing area/scene, not a fixed-camera idle test",
        configuration=[dict(line=i, text=s) for i, s in enumerate(lines, 1)
                       if s.startswith(("[SD-FEX] launch_mode=", "[SD-VK]", "[SD-DXVK-CONFIG]", "[SD-SHADER]"))
                       or "Setting display mode:" in s or "Buffer size:" in s],
        selection="Trailing contiguous sub-30-FPS windows; no exact scene markers",
        slow_segment=summarize(slow), last_three_windows=summarize(slow[-3:]),
        driver_cache_observed_totals={k: sum(b["driver_cache"][k] for b in blocks)
                                      for k in ("driver_cache_hits", "misses")},
        shader_allocation_cache_last=blocks[-1]["shader_allocation_cache"],
        memory=dict(minimum_available_bytes=min(r["heap_available"] for r in resources),
                    last_resource=resources[-1],
                    max_gpu_oom=max(fields(s)["oom"] for s in lines if s.startswith("[SD-VKMEM-STATS]"))),
        late_jit=phase_delta, thread_names=names, intervals=blocks,
        limitations=[
            "No controlled scene comparison with Debug, v7, shader switches off, or 960x540.",
            "No current temperature, CPU/GPU frequency or GPU busy-time measurements.",
            "Registered thread CPU excludes unregistered/system threads. Only the top 12 are printed.",
            "Thread core masks are end-of-interval snapshots, not per-core residency for the full interval.",
            "The first SERVER report includes startup and must not be treated as a steady interval.",
            "SERVER select time includes real blocking; concurrent waits sum above wall time and are not all removable overhead.",
            "Driver/server/compiler timings can overlap or nest; do not add them as frame cost or CPU usage.",
            "Cache-hit and timed-call counts are read independently and can differ slightly during active calls.",
            "Zero completed NAK allocation-cache scopes does not prove all possible shader compilation paths were idle.",
            "Observer wall time divided by interval does not measure its FPS impact.",
            "Frame summaries cannot establish 1% lows or distinguish GPU, CPU execution, and ready-queue latency.",
        ])
    dest = ROOT / "reports/gameplay-v9-gui-performance-analysis.json"
    write_json(dest, result)
    print(json.dumps({k: v for k, v in result.items() if k not in
          ("intervals", "late_jit", "limitations", "configuration", "thread_names")}, indent=2))
    print("report fps registered_cores main% dxvk_cs% semaphore_ms fence_ms pipeline_ms sd_ms observer_ms")
    for b in slow:
        print(b["report"], round(b["frame"]["fps"], 2), b["registered_cpu_cores"],
            b["threads"]["4w"]["cpu_percent"], b["threads"]["40w"]["cpu_percent"],
            b["pipe"]["semaphore_wait"]["avg_us"] / 1000,
            b["pipe"]["fence_wait"]["avg_us"] / 1000,
            b["warm"]["graphics_pipeline"]["total_us"] / 1000,
            b["io"]["sd_ms"], b["observer_us"] / 1000)


if __name__ == "__main__":
    main()
