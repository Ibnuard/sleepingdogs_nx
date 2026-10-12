"""Audit linked production ARM64 startup and loader symbols."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'tools/test_launcher_v2_binary.py').read_text().replace('local/launcher-v2','local/production-v1')
ns={'__name__':'production_binary','__file__':__file__}
exec(compile(text,__file__,'exec'),ns)
if __name__=='__main__':ns['main']()
