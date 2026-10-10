"""Read ABI constants from an extra object compiled with the real native recipe.

The actual runtime sources/objects are never edited. This probe is not linked
or shipped. The instruction replay uses these offsets with the built ELF.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shlex
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    a = p.parse_args(); source = a.work / 'native-source'; build = a.work / 'native-build'
    directory = a.work / 'layout-probe'; directory.mkdir(exist_ok=True)
    horizon = source / 'dlls/ntdll/unix/horizon.c'
    target = 'CMakeFiles/wine-horizon-real.dir' + str(horizon) + '.obj'
    commands = subprocess.check_output(['ninja', '-t', 'commands', target], cwd=build, text=True).splitlines()
    command = next(shlex.split(c) for c in commands if ' -c ' + str(horizon) in c)
    args = []; it = iter(command)
    for item in it:
        if item in ('-o', '-c', '-MT', '-MF'): next(it)
        elif item not in ('-MD', '-MMD'): args.append(item)
    fields = {
        'object_size': 'sizeof(struct horizon_server_object)',
        'thread_type': 'HORIZON_SERVER_OBJECT_THREAD',
        'hash_size': 'HORIZON_SERVER_HANDLE_HASH_SIZE',
        **{'object_' + m: 'offsetof(struct horizon_server_object, ' + m + ')'
           for m in ('type', 'thread', 'sd_debug', 'thread_next')},
        **{'thread_' + m: 'offsetof(struct horizon_thread_state, ' + m + ')'
           for m in ('tid', 'pid', 'teb', 'started', 'terminated', 'suspend')},
        **{'handle_' + m: 'offsetof(struct horizon_server_handle_entry, ' + m + ')'
           for m in ('handle', 'object', 'hash_next')},
        'handle_size': 'sizeof(struct horizon_server_handle_entry)',
        'context_size': 'sizeof(I386_CONTEXT)',
        'teb_clientid': 'offsetof(TEB, ClientId)',
        'teb_wowoffset': 'offsetof(TEB, WowTebOffset)',
        'init_thread_start': 'offsetof(SYSTEM_DLL_INIT_BLOCK, pRtlUserThreadStart)',
    }
    probe = directory / 'probe.c'; obj = directory / 'probe.o'; raw = directory / 'layout.bin'
    probe.write_text('#include "' + str(horizon) + '"\n'
        'const unsigned long long sd_layout_probe[] = {\n' + ',\n'.join(fields.values()) + '\n};\n')
    with (directory / 'compile.log').open('w') as log:
        subprocess.run(args + ['-O0', '-c', str(probe), '-o', str(obj)], cwd=build,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objcopy', '-O', 'binary',
                    '--only-section=.rodata.sd_layout_probe', str(obj), str(raw)], check=True)
    values = struct.unpack('<' + 'Q' * len(fields), raw.read_bytes())
    result = {'layout': dict(zip(fields, values)), 'source_sha256': hashlib.sha256(horizon.read_bytes()).hexdigest(),
        'probe_sha256': hashlib.sha256(probe.read_bytes()).hexdigest(), 'command': args,
        'scope': __doc__}
    (ROOT / 'reports/thread-debug-layout.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['layout'], indent=2))

if __name__ == '__main__': main()
