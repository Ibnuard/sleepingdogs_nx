"""Finish the NSP-only folder after packed-ABI and ARM64 validation."""
from pathlib import Path
import argparse
import json
import shutil
from port_common import ROOT, sha, write_json


def copy_checked(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == source.read_bytes(), f'Preserve existing file: {target}'
    else:
        shutil.copy2(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    out = ROOT/'dist/sleepingdogs-fex-fextendo-memory-v1'
    fw = json.loads((out/'forwarder/build.json').read_text())
    test = json.loads((ROOT/'reports/forwarder-memory-v1.json').read_text())
    assert test['status'] == 'PASS' and test['abi'] == fw['memory_abi'] == 'fxtmem-v1'
    assert fw['title_id'] == '059a3db219b42000'
    assert test['nsp_sha256'] == fw['sha256'] == sha(out/'forwarder'/fw['nsp'])
    assert test['elf_sha256'] == fw['elf_sha256'] == sha(args.work/'forwarder.elf')
    assert test['builder_sha256'] == fw['builder_sha256'] == sha(ROOT/'forwarder/build_forwarder.py')
    assert test['test_sha256'] == sha(ROOT/'tests/check_forwarder_memory_v1.py')
    assert test['harness_sha256'] == sha(ROOT/'tests/check_forwarder_startup_binary.py')
    assert test['exefs_added_only'] == ['fxtmem'] and test['npdm_assets_target_unchanged']
    for name, digest in test['source_files'].items():
        assert digest == fw['source_files'][name] == sha(args.work/'source'/name)
        copy_checked(args.work/'source'/name, out/'source/compiled'/name)
    for name in ('forwarder.elf', 'exefs/main.npdm', 'exefs/fxtmem'):
        copy_checked(args.work/name, out/'source/built'/name)
    for name in ('forwarder/build_forwarder.py', 'forwarder/hbl/base.json',
                 'tools/package_forwarder_memory_v1.py', 'tools/port_common.py',
                 'tools/sleepingdogs_gpu_budget.py', 'tools/f1_overlay.py',
                 'tests/check_forwarder_memory_v1.py', 'tests/check_forwarder_startup_binary.py',
                 'docs/forwarder-memory-v1.md', 'reports/forwarder-memory-v1.json'):
        copy_checked(ROOT/name, out/'source'/name)
    copy_checked(ROOT/'docs/forwarder-memory-v1.md', out/'INSTALL.txt')
    write_json(out/'package.json', dict(
        status='PASS', abi='fxtmem-v1', title_id=fw['title_id'], target=fw['target'],
        nsp='forwarder/'+fw['nsp'], nsp_sha256=fw['sha256'],
        tested_nro_sha256=test['nro_sha256'], hardware_tested=False,
        runtime_changed=False, forwarder_machine_code_unchanged=True,
        exefs_added_only=['fxtmem'], same_title_replacement=True,
        reboot_required_on_active_fextendo_memory_v1=False,
        boot_entry='FEXTendo Memory v1 TEST', freeze_fixed=False))
    files = [p for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS.txt']
    for path in files:
        name = path.relative_to(out).as_posix()
        assert not name.startswith(('switch/', 'atmosphere/', 'bootloader/'))
        assert path.suffix.lower() not in ('.keys', '.kip', '.nro', '.dll', '.log')
    (out/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(out).as_posix()}\n' for p in files))
    for line in (out/'SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert sha(out/name) == digest
    print(f'PASS NSP-only package: {fw["nsp"]}; {len(files)} files verified')


if __name__ == '__main__':
    main()
