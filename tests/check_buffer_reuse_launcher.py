"""Apply the existing C launcher gate checks to the unchanged scene-memory NRO."""
from pathlib import Path
source = Path(__file__).with_name('check_streaming_launcher.py').read_text()
source = source.replace('/home/blekjek/sleepingdogs-streaming-memory-v1', '/home/blekjek/sleepingdogs-scene-memory-v1')
source = source.replace('dist/sleepingdogs-fex-streaming-memory-fix.zip', 'dist/sleepingdogs-fex-buffer-reuse-fix.zip')
source = source.replace('reports/streaming-launcher-check.json', 'reports/buffer-reuse-launcher-check.json')
exec(compile(source, str(Path(__file__)), 'exec'))
