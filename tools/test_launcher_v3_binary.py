"""Reuse the actual linked ARM64 heap/loader audit for the v3 output."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    text=(ROOT/'tools/test_launcher_v2_binary.py').read_text().replace("local/launcher-v2","local/launcher-v3")
    ns={'__name__':'v3_binary','__file__':__file__};exec(compile(text,__file__,'exec'),ns);ns['main']()
if __name__=='__main__':main()
