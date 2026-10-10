"""Package verified v16 plus exact v15 rollback without changing preferences."""
from pathlib import Path
import json
import zipfile
from port_common import ROOT, sha, write_json
from prepare_sync_notify_v16 import WORK, NATIVE
from package_native_v15 import archive, digest, encode

PREFIX = 'switch/sleepingdogs-fex/'
SOURCE = 'source/sync-notify-v16/'
NAME = 'sleepingdogs-fex-v16-sync-notify-update'
OLD_ZIP = 'd744dfafe7364cdb6a28e3943f1e3eb9a31dbee0b1fc03a5d00d55c9b5ece3f4'
OLD_NRO = '916343e32fdc0dfe53f0a38d2fc7911c935018d2f3e9cfac77c87b322006739a'
REPORTS = ('sync-notify-v16-host.json', 'sync-notify-v16-binary.json',
    'sync-v16-native-check.json', 'sync-v16-diagnostic-binary.json',
    'sync-v16-direct-sync-binary.json', 'sync-v16-low-window-binary.json',
    'sync-v16-shader-binary.json')


def main():
    baseline = ROOT / 'dist/sleepingdogs-fex-v15-native-lsfg-update.zip'
    assert sha(baseline) == OLD_ZIP
    with zipfile.ZipFile(baseline) as z:
        assert z.testzip() is None
        original = {n: z.read(n) for n in z.namelist() if n.startswith((PREFIX, 'source/'))}
    assert digest(original[PREFIX + 'sleepingdogs-fex.nro']) == OLD_NRO
    local = ROOT / 'local/sync-notify-v16'
    native = json.loads((local / 'native.json').read_text())
    prepared = json.loads((local / 'prepared.json').read_text())
    assert native['baseline_reproduced'] and native['baseline_nro_sha256'] == OLD_NRO
    assert native['baseline_elf_sha256'] == '28affbe1a66ce6bf293582e7e00aaddb5c4c1063d866216a7a70de264dbb1a2c'
    assert all(native[k] for k in ('fex_unchanged', 'dxvk_unchanged', 'mesa_unchanged', 'lsfg_unchanged'))
    for name, expected in native['inputs'].items():
        assert sha(name) == expected, name
    for name, expected in prepared['files'].items():
        assert sha(NATIVE / name) == expected, name
    nro = local / 'sleepingdogs-fex.nro'
    assert sha(nro) == native['nro_sha256']
    assert sha(ROOT / 'local/symbols/sleepingdogs-sync-v16.elf') == native['elf_sha256']
    reports = {n: json.loads((ROOT / 'reports' / n).read_text()) for n in REPORTS}
    assert all(r['status'] == 'PASS' for r in reports.values())
    assert reports['sync-notify-v16-host.json']['source_files'] == prepared['files']
    for name in REPORTS[1:]:
        assert reports[name]['elf_sha256'] == native['elf_sha256'], name
    assert reports['sync-v16-native-check.json']['nro_sha256'] == native['nro_sha256']

    entries = dict(original)
    rollback = {PREFIX + nro.name: original[PREFIX + nro.name]}
    entries[PREFIX + nro.name] = nro.read_bytes()
    changed = [PREFIX + nro.name]
    for name, data in original.items():
        if not name.startswith(PREFIX) or not name.endswith('.json'):
            continue
        obj = json.loads(data)
        if obj.get('nro_sha256') == OLD_NRO:
            obj.update(nro_sha256=native['nro_sha256'], additional_overlay=native['build'],
                       hardware_tested=False, fps_gain_measured=False)
            entries[name] = encode(obj)
            rollback[name] = data
            changed.append(name)
    identity = PREFIX + 'launcher/native-v16-sync-notify.json'
    entries[identity] = encode(dict(build=native['build'], nro_sha256=native['nro_sha256'],
        inherited_build='sleepingdogs-v15-native-lsfg', target_resolution=[1280, 720],
        default_filter=True, effective_in_sync_mode=2,
        filter_setting='sync-notify-filter.txt', driver_cache_id=native['driver_cache_id'],
        fex_origin='own pes13-fex-derived port', hardware_tested=False, fps_gain_measured=False))
    rollback[identity] = encode(dict(build='sleepingdogs-v15-native-lsfg', rolled_back=True,
        nro_sha256=OLD_NRO, filter_available=False))
    changed.append(identity)

    for name in prepared['files']:
        entries[SOURCE + 'native/' + name] = (NATIVE / name).read_bytes()
    files = ('tools/prepare_sync_notify_v16.py', 'tools/build_sync_notify_v16.py',
        'tools/package_sync_notify_v16.py', 'src/low_window/sd_sync_notify_v16.h',
        'tests/check_sync_notify_v16.py', 'tests/sync_notify_v16_cases.c',
        'tests/check_sync_notify_v16_binary.py', 'tests/check_lsfg_native_binary.py',
        'docs/sync-notify-v16.md')
    for name in files:
        entries[SOURCE + name] = (ROOT / name).read_bytes()
    for name in ('native.json', 'prepared.json', 'v16.patch'):
        entries[SOURCE + name] = (local / name).read_bytes()
    for name in REPORTS:
        entries[SOURCE + 'reports/' + name] = (ROOT / 'reports' / name).read_bytes()
    entries[SOURCE + 'reports/latest-v15-log-analysis.json'] = (
        ROOT / 'reports/gameplay-v11-1de314d6e7b8.json').read_bytes()
    entries['README-INSTALL.txt'] = b'''Sleeping Dogs FEXTendo v16 - native Wine notification candidate

Close FEXTendo completely from HOME. Merge the entire switch folder into the SD
root. Runtime dependencies are the v15 files; user preferences and saves are not
included. Keep 1280x720 and your existing graphics/profile/clock settings.

For native comparison set LSFG OFF. Both Stable and Performance were already
reported equally slow; this candidate does not rely on switching that profile.
Confirm runtime 0.1.0-v16-sync-notify and [SD-SYNC-V16] filter=1 active=1.

To compare with the previous wake route using this same NRO, create
switch/sleepingdogs-fex/sync-notify-filter.txt containing 0 and a newline, then
fully close and relaunch. Delete it or set 1 to enable the filter again.
Save each fex-runtime.log before launching the next session overwrites it.
Compare a warmed, matching crowded route/camera with the same clocks.

Host and ARM64 checks pass. Switch performance remains unmeasured; 30 FPS is not
promised. queued_candidates_skipped is not saved milliseconds or actual wakes.
The rollback-v15 ZIP restores the exact previous v15 NRO and metadata.
Details: source/sync-notify-v16/docs/sync-notify-v16.md
'''
    rollback['README-INSTALL.txt'] = b'''Close FEXTendo completely from HOME.
Merge this switch folder into the SD root to restore the exact delivered v15 NRO
and its modified runtime metadata. Renderer DLLs, LSFG, game files, preferences
and saves need no change. v15 ignores sync-notify-filter.txt if present.
'''

    runtime = {n: d for n, d in entries.items() if n.startswith(PREFIX)}
    assert all(n in changed or d == original[n] for n, d in runtime.items())
    assert not any(n.endswith('.txt') for n in runtime), 'Unexpected preference overwrite'
    restored = dict(runtime)
    restored.update({n: d for n, d in rollback.items() if n.startswith(PREFIX)})
    assert all(restored[n] == d for n, d in original.items() if n.startswith(PREFIX))
    update = archive(ROOT / 'dist' / (NAME + '.zip'), entries)
    undo = archive(ROOT / 'dist/sleepingdogs-fex-v16-rollback-v15.zip', rollback)
    staged = ROOT / 'dist' / NAME
    for name, data in runtime.items():
        dest = staged / name
        assert dest.resolve().is_relative_to(staged.resolve())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    write_json(ROOT / 'reports/sync-notify-v16-package.json', dict(status='PASS',
        build=native['build'], update=update, rollback=undo, nro_sha256=native['nro_sha256'],
        elf_sha256=native['elf_sha256'], baseline_preserved=True, rollback_restores_v15=True,
        runtime_changed=changed, preference_files_included=False, hardware_tested=False,
        fps_gain_measured=False, test_reports={n: sha(ROOT / 'reports' / n) for n in REPORTS},
        runtime_files={n: digest(d) for n, d in runtime.items()}))
    print(json.dumps(dict(status='PASS', update=update, rollback=undo), indent=2), flush=True)


if __name__ == '__main__':
    main()
