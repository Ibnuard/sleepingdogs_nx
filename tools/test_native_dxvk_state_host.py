"""Run the native DXVK image/resource regression against the state-v1 bridge."""
from pathlib import Path
from native_dxvk_state import ROOT
def main():
    text=(ROOT/'tools/test_native_dxvk_compact_host.py').read_text().replace('native-dxvk-compact-v1','native-dxvk-state-v1')
    ns={'__name__':'state_host_fixture','__file__':__file__}
    exec(compile(text,__file__,'exec'),ns);ns['main']()
if __name__=='__main__':main()
