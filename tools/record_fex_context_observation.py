"""Archive the supplied FEX-context-v1 gameplay observation without A/B claims."""
from pathlib import Path
import json,re,shutil
from port_common import ROOT,sha,write_json

def fields(line):return {k:int(v) for k,v in re.findall(r'(\w+)=(\d+)\b',line)}
def main():
    report=ROOT/'reports/native-dxvk-h4-game-29bfb67e08e1.json'
    capture=json.loads(report.read_text());evidence=report.with_suffix('')
    runtime=(evidence/'runtime.txt').read_text()
    assert capture['build']=='native-dxvk-h4-v9' and all(capture['validation'].values())
    assert '[SD-FEX-CONTEXT] v1 exact x87 import;' in runtime
    assert '[SD-GAME-QUALITY] mode=Light720p resolution=1280x720' in runtime
    windows=[fields(x) for x in runtime.splitlines() if x.startswith('[SD-NDX-FPS]')]
    for w in windows:w['present_fps']=w['intervals']*1e6/w['elapsed_us']
    progress=[fields(x) for x in runtime.splitlines() if x.startswith('[SD-NDX-PROGRESS] calls=')]
    a,b=[(a,b) for a,b in zip(progress,progress[1:]) if a['maps']==b['maps']==0 and b['presents']>a['presents']][-1]
    delta={k:b[k]-a[k] for k in ('calls','draws','presents','copy_bytes','failures')}
    auxiliary=evidence/'supplied-com-runtime.txt'
    supplied=Path('C:/Users/Administrator/Pictures/pesnx/SD/runtime.log')
    expected='4d42441ed2ce578f2e22d7c9f15c3891c7842f490e89da3a58834907377c7331'
    if supplied.exists():
        assert sha(supplied)==expected
        shutil.copyfile(supplied,auxiliary)
    assert sha(auxiliary)==expected
    old=json.loads((ROOT/'reports/native-dxvk-h4-v9-gameplay-observation.json').read_text())
    result=dict(status='FEX_CONTEXT_V1_GAME_ROUTE_OBSERVED',capture_report=report.relative_to(ROOT).as_posix(),
        capture_report_sha256=sha(report),evidence={p.name:dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
            for p in (evidence/'runtime.txt',evidence/'dxvk.txt',auxiliary)},
        fex_context_v1_marker=True,resolution=[1280,720],quality='Light720p',
        user_feedback='Slight improvement; ordinary views 20-23 FPS, crowded views still around 16, peak 30 only with a wall/narrow view.',
        requested_target='Improve real crowded-scene FPS toward 20+ while retaining 720p.',
        last_five_present_windows=windows[-5:],
        last_five_pooled_fps=sum(w['intervals'] for w in windows[-5:])*1e6/sum(w['elapsed_us'] for w in windows[-5:]),
        previous_v9_last_five_pooled_fps=old['last_five_pooled_fps'],
        compared_scenes_and_clocks_authenticated=False,clean_exit_confirmed=False,fresh_com_confirmed=False,
        auxiliary_runtime='Byte-identical old v3 COM runtime; not a fresh self-test.',
        zero_active_maps_at_endpoints_interval=dict(start=a,end=b,delta=delta,
            calls_per_present=delta['calls']/delta['presents'],draws_per_present=delta['draws']/delta['presents'],
            copy_bytes_per_present=delta['copy_bytes']/delta['presents']),
        next_candidate='Guest-local reference ownership to remove avoidable FEX/Wine/native round trips, with counters and a reproduced v9 proxy rollback.',
        limitations=['Present windows are not labeled fixed-scene A/B benchmarks.',
            'Similar pooled FPS neither measures the optimization in isolation nor contradicts subjective scene-specific improvement.',
            'Sampled progress is biased toward critical methods; it cannot estimate AddRef/Release frequency.',
            'Calls per frame and low total GPU/CPU utilization do not identify a proven bottleneck.'],
        recorder_sha256=sha(__file__))
    write_json(ROOT/'reports/fex-context-v1-gameplay-observation.json',result)
    print(json.dumps({k:result[k] for k in ('status','last_five_pooled_fps','previous_v9_last_five_pooled_fps','fresh_com_confirmed')}))
if __name__=='__main__':main()
