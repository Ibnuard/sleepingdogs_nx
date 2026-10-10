"""Rerun the C renderer gate against the scene build and final cumulative ZIP."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'tests/check_streaming_launcher.py'
script=path.read_text().replace('sleepingdogs-streaming-memory-v1','sleepingdogs-scene-memory-v1')
script=script.replace('sleepingdogs-fex-streaming-memory-fix.zip','sleepingdogs-fex-scene-memory-fix.zip')
script=script.replace('reports/streaming-launcher-check.json','reports/scene-launcher-check.json')
exec(compile(script,str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
