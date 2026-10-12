"""Preserve the user capture and distinguish requested LSFG from generated frames."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def main():
    local=ROOT/'local/launcher-v3/input-2d5516526c0a'
    text=(local/'fex-runtime.log').read_text(errors='replace')
    evidence={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in local.iterdir() if p.is_file()}
    assert evidence['fex-runtime.log']['sha256']=='2d5516526c0acf48a4956a98498512edeb96a752f8777b1d763eccdecda415e1'
    lines=[s for s in text.splitlines() if any(t in s for t in ('[SD-NDX-FPS]','[SD-NDX-PROGRESS]','[SD-NDX-WIRE]','[SD-LSFG-NATIVE]'))]
    windows=[dict(intervals=int(n),elapsed_us=int(us),total_presents=int(total),fps=round(int(n)*1000000/int(us),3))
        for n,us,total in re.findall(r'\[SD-NDX-FPS\].*?intervals=(\d+) elapsed_us=(\d+).*?total_presents=(\d+)',text)]
    contexts={}
    for tid,obj in re.findall(r'\[SD-NDX-ACTIVE\].*?thread=(\w+).*?interface=14 method=\d+ object=(\w+)',text):
        contexts.setdefault(obj,set()).add(tid)
    report=dict(inputs=evidence,build='sleepingdogs-launcher-v2-native-h4-v9',lsfg_requested=True,
        lsfg_attached=True,per_present_mode_bypasses=text.count('generation bypassed: per-present mode override'),
        generated_frame_markers=text.count('first interpolated present submitted'),
        initialized_markers=text.count('2x initialized'),
        native_present_windows=windows,
        native_fps_gameplay_600_frame_windows=[w['fps'] for w in windows[2:]],
        sampled_context_threads={obj:sorted(tids) for obj,tids in contexts.items()},
        qualification='Unpaired scene-dependent windows; not evidence of a regression or measured speedup. runtime.log is the old H4 v3 COM self-test.',
        optimization='25 independent binding setters filtered in PE32; no draws, resource hazards, Map copies or resolution change.',
        switch_fps_measured_for_candidate=False)
    out=ROOT/'reports/launcher-v2-game-2d5516526c0a';out.mkdir(exist_ok=True)
    (out/'evidence.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out.with_suffix('.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
