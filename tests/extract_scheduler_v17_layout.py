"""Compile an unlinked ABI probe using the candidate's recorded ARM64 command.

Run under WSL after build_scheduler_v17.py. This adds no code to the runtime.
The binary test reads the object section using pyelftools on its own host.
"""
from pathlib import Path
import json
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from port_common import ROOT, sha, write_json

FIELDS = {
    'max_threads': 'NX_PROF_MAX_THREADS',
    'registry_size': 'sizeof(struct nx_prof_thread)',
    'registry_handle': 'offsetof(struct nx_prof_thread, handle)',
    'registry_tid': 'offsetof(struct nx_prof_thread, tid)',
    'registry_kind': 'offsetof(struct nx_prof_thread, kind)',
    'registry_core': 'offsetof(struct nx_prof_thread, core)',
    'registry_fixed': 'offsetof(struct nx_prof_thread, fixed)',
    'registry_teb': 'offsetof(struct nx_prof_thread, teb)',
    'dxvk_size': 'sizeof(struct fex_dxvk_slot)',
    'dxvk_active': 'offsetof(struct fex_dxvk_slot, active)',
    'shader_size': 'sizeof(struct sd_shader_slot)',
    'shader_mode': 'offsetof(struct sd_shader_slot, mode)',
    'shader_core': 'offsetof(struct sd_shader_slot, core)',
    'shader_mask': 'offsetof(struct sd_shader_slot, mask)',
    'shader_none': 'SD_SHADER_NONE',
    'shader_worker': 'SD_SHADER_WORKER',
    'shader_pipeline': 'SD_SHADER_PIPELINE',
    'shader_restore': 'SD_SHADER_RESTORE',
}


def main():
    assert sys.platform == 'linux', 'Run ABI extraction with the WSL compiler'
    receipt_path = ROOT / 'local/scheduler-v17/native.json'
    receipt = json.loads(receipt_path.read_text())
    command = receipt['compile_commands']['wine-nx-probe/source/thread_profile.c'].copy()
    production = Path(command[command.index('-c') + 1])
    work = Path('/home/blekjek/sleepingdogs-scheduler-v17/abi-test')
    work.mkdir(exist_ok=True)
    source = work / 'scheduler_layout.c'
    obj = ROOT / 'local/scheduler-v17/scheduler-layout.o'
    source.write_text('#include <stddef.h>\n#include "' + str(production) + '"\n'
        '__attribute__((used, section(".sd_v17_layout")))\n'
        'const unsigned long long sd_v17_layout[] = {\n' +
        ',\n'.join('    ' + value for value in FIELDS.values()) + '\n};\n')
    for flag, value in (('-c', source), ('-o', obj), ('-MT', obj), ('-MF', work / 'scheduler_layout.d')):
        if flag in command:
            command[command.index(flag) + 1] = str(value)
    result = subprocess.run(command, cwd=receipt['working_directory'], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (work / 'compile.log').write_text(result.stdout)
    if result.returncode:
        print(result.stdout)
        raise SystemExit(result.returncode)
    write_json(ROOT / 'local/scheduler-v17/scheduler-layout.json', dict(
        fields=list(FIELDS), expressions=FIELDS, object_sha256=sha(obj),
        production_sha256=sha(production), build_elf_sha256=receipt['elf_sha256'],
        compile_command=command, probe_sha256=sha(source), linked_into_runtime=False))
    print('PASS: scheduler ABI extracted with the recorded ARM64 compiler', flush=True)


if __name__ == '__main__':
    main()
