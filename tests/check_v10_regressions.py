"""Run existing compiled regressions against v10 without replacing v9 reports."""
from pathlib import Path
import gc
import importlib
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
elf=ROOT/'local/symbols/sleepingdogs-low-window-v10.elf'
for module, report in (('check_direct_sync_binary',None),
        ('check_cpu_topology_binary','cpu-topology'),
        ('check_sync_startup_binary','sync-startup-binary'),
        ('check_low_window_binary','binary'),('check_shader_binary','shader-binary')):
    m=importlib.import_module(module)
    sys.argv=[module,'--elf',str(elf)]
    if module=='check_shader_binary':
        original=m.write_json
        def redirected(path,value):
            assert path==ROOT/'reports/low-window-v9-shader-binary.json'
            return original(ROOT/'reports/low-window-v10-shader-binary.json',value)
        m.write_json=redirected
    elif report:
        sys.argv.extend(['--report',str(ROOT/'reports'/('low-window-v10-'+report+'.json'))])
    print('Checking',module,flush=True)
    m.main()
    gc.collect()
