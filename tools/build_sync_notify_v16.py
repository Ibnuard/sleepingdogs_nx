"""Reproduce v15, compile only horizon.c/runtime.c, then link an isolated v16."""
from pathlib import Path
import json
import shlex
import shutil
import struct
import subprocess
from port_common import ROOT, sha, write_json
from build_lsfg_native import run
from prepare_sync_notify_v16 import WORK, NATIVE

DEST = ROOT / 'local/sync-notify-v16'


def main():
    previous = json.loads((ROOT / 'local/lsfg-native-v15/native.json').read_text())
    prepared = json.loads((WORK / 'prepared.json').read_text())
    for name, digest in prepared['files'].items():
        assert sha(NATIVE / name) == digest, name
    cwd = Path(previous['working_directory'])
    out = WORK / 'runtime'
    objects = WORK / 'objects'
    for p in (out, objects, DEST):
        p.mkdir(parents=True, exist_ok=True)
    original = previous['link_argv']
    inputs = {}
    for arg in original[1:]:
        if not arg.startswith('-') and arg.endswith(('.obj', '.o', '.a')):
            p = (cwd / arg).resolve()
            inputs[str(p)] = sha(p)
    # switch.specs embeds the output basename in .nx-module-name. Preserve it
    # as well as the inputs when reproducing the delivered ELF byte-for-byte.
    baseline = out / 'baseline/wine-nx-runtime.elf'
    baseline.parent.mkdir(exist_ok=True)
    cmd = original.copy()
    cmd[cmd.index('-o') + 1] = str(baseline)
    cmd = ['-Wl,-Map=' + str(out / 'baseline.map') if x.startswith('-Wl,-Map=') else x for x in cmd]
    run(cmd, cwd, out / 'baseline.log')
    assert sha(baseline) == previous['elf_sha256'], 'v15 inputs changed; do not package'
    print('PASS: v15 baseline ELF reproduced exactly', flush=True)

    changed, commands = {}, {}
    horizon_obj = next(x for x in original if x.endswith('/horizon.c.obj'))
    runtime_obj = previous['changed_objects']['CMakeFiles/wine-nx-runtime.dir/source/runtime.c.obj']
    for old, source in ((horizon_obj, 'dlls/ntdll/unix/horizon.c'),
                        (runtime_obj, 'wine-nx-probe/source/runtime.c')):
        if source.endswith('/horizon.c'):
            raw = subprocess.check_output(['ninja', '-t', 'commands', old], cwd=cwd, text=True).splitlines()[-1]
            argv = shlex.split(raw)
        else:
            argv = previous['compile_commands'][source].copy()
        obj = objects / (Path(source).name + '.obj')
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
        run(new, cwd, out / (Path(source).name + '.compile.log'))
        changed[old], commands[source] = str(obj), new
        print('Compiled', source, flush=True)
    candidate = out / 'candidate/wine-nx-runtime.elf'
    candidate.parent.mkdir(exist_ok=True)
    cmd = [changed.get(x, x) for x in original]
    cmd[cmd.index('-o') + 1] = str(candidate)
    cmd = ['-Wl,-Map=' + str(out / 'candidate.map') if x.startswith('-Wl,-Map=') else x for x in cmd]
    run(cmd, cwd, out / 'candidate.log')
    for path, digest in inputs.items():
        assert sha(path) == digest, ('input changed', path)
    for name, digest in prepared['files'].items():
        assert sha(NATIVE / name) == digest, ('source changed', name)

    old_nro = (ROOT / 'local/lsfg-native-v15/sleepingdogs-fex.nro').read_bytes()
    assert sha(ROOT / 'local/lsfg-native-v15/sleepingdogs-fex.nro') == previous['nro_sha256']
    size = struct.unpack_from('<I', old_nro, 0x18)[0]
    assert old_nro[size:size + 4] == b'ASET'
    io, il, no, nl, ro, rl = struct.unpack_from('<6Q', old_nro, size + 8)
    assert not rl
    (out / 'icon.jpg').write_bytes(old_nro[size + io:size + io + il])
    nacp = bytearray(old_nro[size + no:size + no + nl])
    nacp[0x3060:0x3070] = b'0.1.0-v16-sync'.ljust(16, b'\0')
    (out / 'app.nacp').write_bytes(nacp)
    nro = DEST / 'sleepingdogs-fex.nro'
    subprocess.run(['/opt/devkitpro/tools/bin/elf2nro', str(candidate), str(nro),
        '--icon=' + str(out / 'icon.jpg'), '--nacp=' + str(out / 'app.nacp')], check=True)
    shutil.copy2(candidate, ROOT / 'local/symbols/sleepingdogs-sync-v16.elf')
    shutil.copy2(WORK / 'prepared.json', DEST / 'prepared.json')
    shutil.copy2(WORK / 'v16.patch', DEST / 'v16.patch')
    write_json(DEST / 'native.json', dict(status='BUILT', build='sleepingdogs-v16-sync-notify',
        nro_sha256=sha(nro), elf_sha256=sha(candidate), baseline_reproduced=True,
        baseline_elf_sha256=sha(baseline), baseline_nro_sha256=previous['nro_sha256'],
        driver_cache_id=previous['driver_cache_id'],
        driver_library_sha256=previous['driver_library_sha256'],
        backend_library_sha256=previous['backend_library_sha256'],
        link_argv=cmd, working_directory=str(cwd), inputs=inputs,
        changed_objects=changed, compile_commands=commands,
        fex_unchanged=True, dxvk_unchanged=True, mesa_unchanged=True, lsfg_unchanged=True,
        hardware_tested=False, fps_gain_measured=False))
    print('BUILT', sha(nro), flush=True)


if __name__ == '__main__':
    main()
