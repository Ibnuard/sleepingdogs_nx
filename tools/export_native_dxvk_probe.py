"""Export checked native-DXVK probe receipts and its source adaptation patch.

This exports development evidence and a static archive, not a Switch NRO.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=Path('/home/blekjek/sleepingdogs-dxvk-arm64-v1'))
    parser.add_argument('--source', type=Path, default=Path('/home/blekjek/sleepingdogs-dxvk-native-v15/source'))
    args = parser.parse_args()
    evidence = ROOT/'local/native-dxvk-probe-v1'
    receipts = {label: json.loads((evidence/name).read_text()) for label, name in
                [('host', 'build-host.json'), ('horizon', 'build-horizon.json'), ('test', 'host-test.json')]}
    for target in ('host', 'horizon'):
        receipt = receipts[target]
        assert receipt['status'] == 'BUILT' and not receipt['game_integration']
        assert not receipt['hardware_tested'] and not receipt['fps_gain_measured']
        assert sha(receipt['library']) == receipt['sha256']
        assert sha(ROOT/'tools/build_native_dxvk_probe.py') == receipt['builder_sha256']
        for name, digest in receipt['probe_sources'].items():
            assert sha(ROOT/name) == digest, name
    test = receipts['test']
    assert test['status'] == 'PASS' and test['draw_pixels_verified'] == 1280*720
    assert test['present_calls'] == 60 and test['buffer_bytes_verified'] == 1024
    assert sha(args.work/'build-host/sd_native_dxvk_host_probe') == test['executable_sha256']
    assert sha(evidence/'build-host.json') == test['build_receipt_sha256']
    assert sha(ROOT/'tools/test_native_dxvk_probe.py') == test['runner_sha256']
    assert sha(evidence/'host-stderr.log') == test['stderr_sha256']
    inputs = json.loads((ROOT/'vendor/dxvk/native-probe-v1-inputs.json').read_text())
    patches = receipts['horizon']['adapted_files']
    assert patches == receipts['host']['adapted_files']
    for name, digest in inputs['source_files'].items():
        assert sha(args.source/name) == digest, name
        assert sha(args.work/'source'/name) == patches.get(name, digest), name
    patch = ''.join(''.join(difflib.unified_diff(
        (args.source/name).read_text().splitlines(keepends=True),
        (args.work/'source'/name).read_text().splitlines(keepends=True),
        fromfile='a/'+name, tofile='b/'+name)) for name in sorted(patches))
    (ROOT/'vendor/dxvk/native-probe-v1.patch').write_text(patch, newline='\n')
    for label, receipt in receipts.items():
        (ROOT/f'reports/native-dxvk-probe-v1-{label}.json').write_text(json.dumps(receipt,indent=2)+'\n')
    # Text log is evidence only; it contains no game input or credentials.
    shutil.copy2(evidence/'host-stderr.log', ROOT/'reports/native-dxvk-probe-v1-host-log.txt')
    shutil.copy2(receipts['horizon']['library'], evidence/'libsd_native_dxvk-arm64.a')
    print(json.dumps(dict(status='PASS', receipts_exported=3, pinned_source_files=len(inputs['source_files']),
                          adapted_source_files=len(patches), archive_bytes=(evidence/'libsd_native_dxvk-arm64.a').stat().st_size,
                          game_integration=False, hardware_tested=False, fps_gain_measured=False),indent=2))


if __name__ == '__main__':
    main()
