"""Run retained launcher/keyboard/cache/LSFG regressions against production."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'tools/test_launcher_v3.py').read_text().replace('launcher-v3','production-v1')
ns={'__name__':'production_fixture','__file__':__file__}
exec(compile(text,__file__,'exec'),ns)
if __name__=='__main__':ns['main']()
