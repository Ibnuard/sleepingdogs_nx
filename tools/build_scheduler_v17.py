"""Reproduce v16 then rebuild the isolated Wine scheduler A/B candidate."""
from pathlib import Path
import json
import shlex
import shutil
import struct
import subprocess
from port_common import ROOT, sha, write_json
from build_lsfg_native import run

WORK = Path('/home/blekjek/sleepingdogs-scheduler-v17')
NATIVE = WORK / 'native-source'
DEST = ROOT / 'local/scheduler-v17'
SOURCES = ('dlls/ntdll/unix/horizon.c', 'dlls/ntdll/unix/thread.c',
           'wine-nx-probe/source/runtime.c', 'wine-nx-probe/source/thread_profile.c')


def main():
    previous = json.loads((ROOT / 'local/sync-notify-v16/native.json').read_text())
    prepared = json.loads((WORK / 'prepared.json').read_text())
    for name, digest in prepared['files'].items():
        assert sha(NATIVE / name) == digest, name
    cwd = Path(previous['working_directory'])
    out, objects = WORK / 'runtime', WORK / 'objects'
    for p in (out, objects, DEST):
        p.mkdir(parents=True, exist_ok=True)
    original = previous['link_argv']
    inputs = {}
    for arg in original[1:]:
        if not arg.startswith('-') and arg.endswith(('.obj', '.o', '.a')):
            p = (cwd / arg).resolve()
            inputs[str(p)] = sha(p)
    baseline = out / 'baseline/wine-nx-runtime.elf'
    baseline.parent.mkdir(exist_ok=True)
    cmd = original.copy()
    cmd[cmd.index('-o') + 1] = str(baseline)
    cmd = ['-Wl,-Map=' + str(out / 'baseline.map') if x.startswith('-Wl,-Map=') else x for x in cmd]
    run(cmd, cwd, out / 'baseline.log')
    assert sha(baseline) == previous['elf_sha256'], 'v16 inputs changed; stop before packaging'
    print('PASS: delivered v16 ELF reproduced exactly', flush=True)
    changed, commands = {}, {}
    for source in SOURCES:
        filename = Path(source).name
        matches = [x for x in original if x.endswith('/' + filename + '.obj')]
        assert len(matches) == 1, (source, matches)
        old = matches[0]
        if source in previous['compile_commands']:
            argv = previous['compile_commands'][source].copy()
        else:
            raw = subprocess.check_output(['ninja', '-t', 'commands', old], cwd=cwd, text=True).splitlines()[-1]
            argv = shlex.split(raw)
        obj = objects / (filename + '.obj')
        new, i = [], 0
        while i < len(argv):
            if argv[i] in ('-c', '-o', '-MF', '-MT'):
                flag = argv[i]
                value = NATIVE / source if flag == '-c' else obj.with_suffix('.d') if flag == '-MF' else obj
                new.extend((flag, str(value)))
                i += 2
            else:
                new.append(argv[i])
                i += 1
        new[1:1] = ['-I' + str(NATIVE / 'wine-nx-probe/source')]
        run(new, cwd, out / (filename + '.compile.log'))
        changed[old], commands[source] = str(obj), new
        print('Compiled', source, flush=True)
    candidate = out / 'candidate/wine-nx-runtime.elf'
    candidate.parent.mkdir(exist_ok=True)
    cmd = [changed.get(x, x) for x in original]
    cmd[cmd.index('-o') + 1] = str(candidate)
    cmd = ['-Wl,-Map=' + str(out / 'candidate.map') if x.startswith('-Wl,-Map=') else x for x in cmd]
    run(cmd, cwd, out / 'candidate.log')
    for path, digest in inputs.items():
        assert sha(path) == digest, ('link input changed', path)
    for name, digest in prepared['files'].items():
        assert sha(NATIVE / name) == digest, ('source changed', name)
    baseline_nro = ROOT / 'local/sync-notify-v16/sleepingdogs-fex.nro'
    assert sha(baseline_nro) == previous['nro_sha256']
    data = baseline_nro.read_bytes()
    size = struct.unpack_from('<I', data, 0x18)[0]
    assert data[size:size + 4] == b'ASET'
    io, il, no, nl, ro, rl = struct.unpack_from('<6Q', data, size + 8)
    assert not rl
    (out / 'icon.jpg').write_bytes(data[size + io:size + io + il])
    nacp = bytearray(data[size + no:size + no + nl])
    nacp[0x3060:0x3070] = b'0.1.0-v17-sched'.ljust(16, b'\0')
    (out / 'app.nacp').write_bytes(nacp)
    nro = DEST / 'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro', str(candidate), str(nro),
        '--icon=' + str(out / 'icon.jpg'), '--nacp=' + str(out / 'app.nacp')], check=True)
    shutil.copy2(candidate, ROOT / 'local/symbols/sleepingdogs-scheduler-v17.elf')
    shutil.copy2(WORK / 'prepared.json', DEST / 'prepared.json')
    shutil.copy2(WORK / 'v17.patch', DEST / 'v17.patch')
    write_json(DEST / 'native.json', dict(status='BUILT', build='sleepingdogs-v17-scheduler',
        nro_sha256=sha(nro), elf_sha256=sha(candidate), baseline_reproduced=True,
        baseline_elf_sha256=sha(baseline), baseline_nro_sha256=previous['nro_sha256'],
        driver_cache_id=previous['driver_cache_id'],
        driver_library_sha256=previous['driver_library_sha256'],
        backend_library_sha256=previous['backend_library_sha256'],
        link_argv=cmd, working_directory=str(cwd), inputs=inputs,
        changed_objects=changed, compile_commands=commands,
        fex_engine_unchanged=True, dxvk_unchanged=True, mesa_unchanged=True, lsfg_unchanged=True,
        scheduler_changed=True, hardware_tested=False, fps_gain_measured=False))
    print('BUILT', sha(nro), flush=True)


if __name__ == '__main__':
    main()
