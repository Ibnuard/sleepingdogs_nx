"""Record the supplied v9 capture without treating workload counts as timing."""
from pathlib import Path
import json,re,shutil
from port_common import ROOT,sha,write_json

def fields(line):return {k:int(v) for k,v in re.findall(r'(\w+)=(\d+)\b',line)}
def main():
    report=ROOT/'reports/native-dxvk-h4-game-71534a073915.json';capture=json.loads(report.read_text())
    evidence=ROOT/'reports/native-dxvk-h4-game-71534a073915'
    runtime=(evidence/'runtime.txt').read_text();dxvk=(evidence/'dxvk.txt').read_text()
    assert capture['build']=='native-dxvk-h4-v9' and all(capture['validation'].values())
    windows=[fields(x) for x in runtime.splitlines() if x.startswith('[SD-NDX-FPS]')]
    for w in windows:w['present_fps']=w['intervals']*1e6/w['elapsed_us']
    progress=[fields(x) for x in runtime.splitlines() if x.startswith('[SD-NDX-PROGRESS] calls=')]
    pairs=[(a,b) for a,b in zip(progress,progress[1:]) if a['maps']==b['maps']==0 and b['presents']>a['presents']]
    a,b=pairs[-1];delta={k:b[k]-a[k] for k in ('calls','draws','presents','copy_bytes','failures')}
    old=ROOT/'reports/native-dxvk-h4-v8.1-light-observation.json';old_report=json.loads(old.read_text())
    old_game=json.loads((ROOT/old_report['game_capture_report']).read_text())
    old_windows=old_game['native_present_windows'][-5:]
    # Recompute directly from raw archived windows so report field names do
    # not determine the evidence arithmetic.
    old_text=(ROOT/old_report['evidence']['runtime']['path']).read_text()
    old_windows=[fields(x) for x in old_text.splitlines() if x.startswith('[SD-NDX-FPS]')][-5:]
    pooled=lambda rows:sum(x['intervals'] for x in rows)*1e6/sum(x['elapsed_us'] for x in rows)
    auxiliary=evidence/'supplied-com-runtime.txt'
    supplied=Path('C:/Users/Administrator/Pictures/pesnx/SD/DF/runtime.log')
    if supplied.exists():
        assert sha(supplied)=='4d42441ed2ce578f2e22d7c9f15c3891c7842f490e89da3a58834907377c7331'
        shutil.copyfile(supplied,auxiliary)
    assert sha(auxiliary)=='4d42441ed2ce578f2e22d7c9f15c3891c7842f490e89da3a58834907377c7331'
    result=dict(status='V9_GAME_ROUTE_OBSERVED_NO_MEANINGFUL_GAIN_REPORTED',capture_report=report.relative_to(ROOT).as_posix(),
        capture_report_sha256=sha(report),evidence={p.name:dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
        for p in (evidence/'runtime.txt',evidence/'dxvk.txt',auxiliary)},
        user_feedback='masih blm ada kenaikan signifikan sih',resolution=[1280,720],quality='Light720p',
        last_five_present_windows=windows[-5:],last_five_pooled_fps=pooled(windows[-5:]),v81_last_five_pooled_fps=pooled(old_windows),
        compared_scenes_and_clocks_authenticated=False,clean_exit_confirmed=False,fresh_v9_com_confirmed=False,
        auxiliary_runtime='Byte-identical previously supplied v3 COM runtime; does not validate this v9 self-test.',
        zero_active_maps_at_endpoints_interval=dict(start=a,end=b,delta=delta,
            calls_per_present=delta['calls']/delta['presents'],draws_per_present=delta['draws']/delta['presents'],
            copy_bytes_per_present=delta['copy_bytes']/delta['presents']),
        map_counters=fields(next(x for x in reversed(runtime.splitlines()) if x.startswith('[SD-NDX-MAP]'))),
        batching=fields(next(x for x in reversed(dxvk.splitlines()) if '[SD-DXVK-BATCH]' in x)),
        scheduler='v17 automatic application cores; native DXVK host workers outside guest registry',
        existing_fex_settings='fastest x87=64 scalar/vector/memcpy TSO=0 multiblock=1 smc=mtrack; QPC/delay fast gateway active',
        limitations=['Present windows can contain menu/loading and are not labeled same-scene A/B.',
            'Deferred hints are requests, not eliminated GPU submissions.',
            'COM snapshots favor critical calls; apparent CreateSamplerState prevalence is not a frequency or CPU profile.',
            'Compile totals contain nested scopes and do not measure translated game execution.',
            'Call/copy counts do not identify a bottleneck or quantify potential FPS gain.'],
        recorder_sha256=sha(__file__))
    write_json(ROOT/'reports/native-dxvk-h4-v9-gameplay-observation.json',result)
    print(json.dumps({k:result[k] for k in ('status','last_five_pooled_fps','v81_last_five_pooled_fps','fresh_v9_com_confirmed')}))
if __name__=='__main__':main()
