"""Reuse the pinned v2 build recipe in isolated v3 directories."""
from pathlib import Path
from launcher_v3_overlay import ROOT,lsfg_overlay,replace

def recipe():
    text=(ROOT/'tools/build_launcher_v2.py').read_text()
    text=text.replace('from launcher_v2_overlay import','from launcher_v3_overlay import')
    text=text.replace('launcher-v2','launcher-v3').replace('0.1.0-l2','0.1.0-l3')
    text=text.replace('native-dxvk-compact-v1','native-dxvk-state-v1')
    text=text.replace('a03a58b6023a7b74ff0d96d0460ce247715fa1210b6f6d02428f206908541344',
                      '3d2154bb29f4735e8d6818deeb95c2b9554dc3e7177780199a15cdb7514bd3dd')
    text=replace(text,"    save(overlay/'lsfg.cpp',backend)","    save(overlay/'lsfg.cpp',lsfg_overlay(backend))")
    text=text.replace("ROOT/'tools/launcher_v2_overlay.py',ROOT/'tools/launcher_v1_overlay.py'",
        "ROOT/'tools/launcher_v3_overlay.py',ROOT/'tools/launcher_v2_overlay.py',ROOT/'tools/launcher_v1_overlay.py',ROOT/'tools/build_launcher_v2.py'")
    text=text.replace("ROOT/'tools/native_dxvk_compact.py'","ROOT/'tools/native_dxvk_compact.py',ROOT/'tools/native_dxvk_state.py',ROOT/'tools/build_native_dxvk_state.py'")
    namespace={'__name__':'launcher_v3_recipe','__file__':__file__,'lsfg_overlay':lsfg_overlay}
    exec(compile(text,str(ROOT/'tools/build_launcher_v2.py'),'exec'),namespace)
    return namespace
if __name__=='__main__':recipe()['main']()
