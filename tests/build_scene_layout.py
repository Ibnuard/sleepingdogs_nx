"""Reuse the production compiler layout probe without replacing prior evidence."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'tests/build_compiler_memory_layout.py'
script=path.read_text().replace('local/compiler-memory-layout.json','local/scene-memory-layout.json')
exec(compile(script,str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
import json
assert json.loads((ROOT/'local/scene-memory-layout.json').read_text())==json.loads((ROOT/'local/compiler-memory-layout.json').read_text())
