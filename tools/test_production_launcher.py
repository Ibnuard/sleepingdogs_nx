"""Run retained launcher/keyboard/cache/LSFG regressions against production."""
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'tools/test_launcher_v3.py').read_text().replace('launcher-v3','production-v1')
ns={'__name__':'production_fixture','__file__':__file__}
exec(compile(text,__file__,'exec'),ns)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build-dir',type=Path,default=ROOT/'local/production-v1')
    p.add_argument('--work',type=Path,default=Path('/home/blekjek/sleepingdogs-production-v1'))
    args=p.parse_args()
    text=text.replace('sleepingdogs-production-v1',str(args.work.name)).replace('local/production-v1',args.build_dir.relative_to(ROOT).as_posix())
    ns={'__name__':'production_fixture','__file__':__file__}
    exec(compile(text,__file__,'exec'),ns);ns['main']()
