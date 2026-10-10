"""Exercise inherited ARM64 guards after relinking the Vulkan driver."""
from pathlib import Path
import gc
import importlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'),str(ROOT/'tests')]
from port_common import sha,write_json


def main():
    elf = ROOT/'local/symbols/sleepingdogs-low-window-v13.elf'
    native = json.loads((ROOT/'dist/low-window-mesa-backport/native.json').read_text())
    assert sha(elf) == native['elf_sha256']
    checks = {}
    import check_v11_binary as diag
    old = diag.write_json
    diag.write_json = lambda path,value: old(ROOT/'reports/low-window-v13-diagnostic-binary.json',value)
    try: diag.diagnostics(elf)
    finally: diag.write_json = old
    checks['diagnostic-binary'] = sha(ROOT/'reports/low-window-v13-diagnostic-binary.json')
    gc.collect()
    for module,label in (('check_direct_sync_binary','direct-sync-binary'),
                         ('check_low_window_binary','binary'),
                         ('check_shader_binary','shader-binary')):
        m=importlib.import_module(module); writer=m.write_json
        m.write_json=lambda path,value,_writer=writer,_label=label: _writer(
            ROOT/'reports'/('low-window-v13-'+_label+'.json'),value)
        sys.argv=[module,'--elf',str(elf)]
        print('Checking',module,flush=True)
        try: m.main()
        finally: m.write_json=writer
        path=ROOT/'reports'/('low-window-v13-'+label+'.json')
        report=json.loads(path.read_text())
        assert report['status']=='PASS' and report['elf_sha256']==sha(elf)
        checks[label]=sha(path)
        gc.collect()
    sources={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in (
        Path(__file__),ROOT/'tests/check_v11_binary.py',ROOT/'tests/check_direct_sync_binary.py',
        ROOT/'tests/check_low_window_binary.py',ROOT/'tests/check_shader_binary.py')}
    write_json(ROOT/'reports/low-window-v13-runtime-binary.json',dict(status='PASS',
        elf_sha256=sha(elf),reports=checks,sources=sources,hardware_tested=False))
    print('PASS v13 linked ARM64 regression checks',flush=True)


if __name__=='__main__': main()
