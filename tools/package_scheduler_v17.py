"""Package the verified scheduler candidate and exact delivered v16 rollback."""
from pathlib import Path
import json
import zipfile
from port_common import ROOT, sha, write_json
from prepare_scheduler_v17 import NATIVE
from package_native_v15 import archive, digest, encode

PREFIX = 'switch/sleepingdogs-fex/'
SOURCE = 'source/scheduler-v17/'
NAME = 'sleepingdogs-fex-v17-scheduler-update'
OLD_ZIP = '0cc99376998f6348a0a9198975a34c4a4080388649dbe3acf417f0dcafe2e61b'
OLD_NRO = 'f7e753c8fb43406feabce65dee329efc9416eebd6962220a4e31ccf4f8ae3a7d'
OLD_ELF = '63eb8b35356d35275a896aca86fe3eed8d154605a1afbee06226eb76cef21311'
REPORTS = ('scheduler-v17-host-check.json', 'scheduler-v17-binary.json',
    'scheduler-v17-native-check.json', 'sched-v17-diagnostic-binary.json',
    'sched-v17-direct-sync-binary.json', 'sched-v17-low-window-binary.json',
    'sched-v17-shader-binary.json')


def main():
    baseline = ROOT / 'dist/sleepingdogs-fex-v16-sync-notify-update.zip'
    assert sha(baseline) == OLD_ZIP
    with zipfile.ZipFile(baseline) as z:
        assert z.testzip() is None
        original = {n: z.read(n) for n in z.namelist() if n.startswith((PREFIX, 'source/'))}
    assert digest(original[PREFIX + 'sleepingdogs-fex.nro']) == OLD_NRO
    local = ROOT / 'local/scheduler-v17'
    native = json.loads((local / 'native.json').read_text())
    prepared = json.loads((local / 'prepared.json').read_text())
    assert native['baseline_reproduced'] and native['baseline_nro_sha256'] == OLD_NRO
    assert native['baseline_elf_sha256'] == OLD_ELF
    assert all(native[k] for k in ('fex_engine_unchanged', 'dxvk_unchanged', 'mesa_unchanged', 'lsfg_unchanged'))
    for name, expected in native['inputs'].items():
        assert sha(name) == expected, name
    for name, expected in prepared['files'].items():
        assert sha(NATIVE / name) == expected, name
    nro = local / 'sleepingdogs-fex.nro'
    assert sha(nro) == native['nro_sha256']
    assert sha(ROOT / 'local/symbols/sleepingdogs-scheduler-v17.elf') == native['elf_sha256']
    reports = {n: json.loads((ROOT / 'reports' / n).read_text()) for n in REPORTS}
    assert all(r['status'] == 'PASS' for r in reports.values())
    assert reports['scheduler-v17-host-check.json']['source_files'] == prepared['files']
    for name in REPORTS[1:]:
        assert reports[name]['elf_sha256'] == native['elf_sha256'], name
    assert reports['scheduler-v17-native-check.json']['nro_sha256'] == native['nro_sha256']

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
    identity = PREFIX + 'launcher/scheduler-v17.json'
    entries[identity] = encode(dict(build=native['build'], nro_sha256=native['nro_sha256'],
        inherited_build='sleepingdogs-v16-sync-notify', target_resolution=[1280, 720],
        default_auto_affinity=True, setting='auto-affinity.txt',
        automatic_allowed_mask='granted process mask & 7',
        driver_cache_id=native['driver_cache_id'], fex_origin='own pes13-fex-derived port',
        hardware_tested=False, fps_gain_measured=False))
    rollback[identity] = encode(dict(build='sleepingdogs-v16-sync-notify', rolled_back=True,
        nro_sha256=OLD_NRO, automatic_affinity_available=False))
    changed.append(identity)

    for name in prepared['files']:
        entries[SOURCE + 'native/' + name] = (NATIVE / name).read_bytes()
    files = ('tools/prepare_scheduler_v17.py', 'tools/build_scheduler_v17.py',
        'tools/package_scheduler_v17.py', 'src/low_window/sd_auto_affinity_v17.h',
        'tests/check_scheduler_v17.py', 'tests/check_scheduler_v17_binary.py',
        'tests/extract_scheduler_v17_layout.py',
        'tests/shader_affinity.c', 'tests/check_lsfg_native_binary.py',
        'docs/scheduler-v17.md')
    for name in files:
        entries[SOURCE + name] = (ROOT / name).read_bytes()
    for name in ('native.json', 'prepared.json', 'v17.patch', 'scheduler-layout.json', 'scheduler-layout.o'):
        entries[SOURCE + name] = (local / name).read_bytes()
    for name in REPORTS:
        entries[SOURCE + 'reports/' + name] = (ROOT / 'reports' / name).read_bytes()
    entries[SOURCE + 'reports/latest-v16-log-analysis.json'] = (
        ROOT / 'reports/gameplay-v11-614bd031fb35.json').read_bytes()
    entries['README-INSTALL.txt'] = b'''Sleeping Dogs FEXTendo v17 - native automatic-affinity candidate

Close FEXTendo completely from HOME. Merge the entire switch folder into the SD
root. Preferences, saves and game data are not included. Keep 1280x720, the same
clocks and graphics settings. Set LSFG OFF for the native FPS comparison.

Confirm runtime 0.1.0-v17-scheduler and:
[SD-SCHED-V17] mode=auto coremask=process&7 periodic=1
Ordinary automatic threads may use application cores 0-2; explicit masks and
shader/core3 helper policies remain protected. Renderer and FEX engine unchanged.

To compare the previous policy with this NRO, create
switch/sleepingdogs-fex/auto-affinity.txt containing 0 and a newline, fully close
from HOME and relaunch. The startup marker becomes mode=v16-pinned.
Delete the file or set 1 to enable again. Save each fex-runtime.log before the
next session. Compare a warmed matching crowded route and camera.

Host and ARM64 checks pass. Hardware improvement is unmeasured; no 30 FPS claim.
Rollback-v16 restores the exact previous NRO and affected metadata.
Details: source/scheduler-v17/docs/scheduler-v17.md
'''
    rollback['README-INSTALL.txt'] = b'''Close FEXTendo completely from HOME.
Merge this switch folder into the SD root to restore the exact delivered v16 NRO
and affected metadata. v16 ignores auto-affinity.txt. Preferences and saves are
not included. No renderer changes are required.
'''
    runtime = {n: d for n, d in entries.items() if n.startswith(PREFIX)}
    assert all(n in changed or d == original[n] for n, d in runtime.items())
    assert not any(n.endswith('.txt') for n in runtime), 'Unexpected preference overwrite'
    restored = dict(runtime)
    restored.update({n: d for n, d in rollback.items() if n.startswith(PREFIX)})
    assert all(restored[n] == d for n, d in original.items() if n.startswith(PREFIX))
    update = archive(ROOT / 'dist' / (NAME + '.zip'), entries)
    undo = archive(ROOT / 'dist/sleepingdogs-fex-v17-rollback-v16.zip', rollback)
    staged = ROOT / 'dist' / NAME
    for name, data in runtime.items():
        dest = staged / name
        assert dest.resolve().is_relative_to(staged.resolve())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    write_json(ROOT / 'reports/scheduler-v17-package.json', dict(status='PASS',
        build=native['build'], update=update, rollback=undo, nro_sha256=native['nro_sha256'],
        elf_sha256=native['elf_sha256'], baseline_preserved=True, rollback_restores_v16=True,
        runtime_changed=changed, preference_files_included=False, hardware_tested=False,
        fps_gain_measured=False, test_reports={n: sha(ROOT / 'reports' / n) for n in REPORTS},
        runtime_files={n: digest(d) for n, d in runtime.items()}))
    print(json.dumps(dict(status='PASS', update=update, rollback=undo), indent=2), flush=True)


if __name__ == '__main__':
    main()
