"""Compile an unlinked ABI probe with the candidate's recorded ARM64 recipe.

Only this test probe and its object are written. The production translation
unit, runtime object, and linked ELF remain unchanged.
"""
from pathlib import Path
import json
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from port_common import ROOT, sha, write_json


FIELDS = {
    'waiter_size': 'sizeof(struct sd_sync_waiter)',
    **{'waiter_' + member: 'offsetof(struct sd_sync_waiter, ' + member + ')'
       for member in ('next', 'connection', 'request', 'data', 'data_size',
                      'count', 'status', 'queued', 'notified', 'completed', 'condition')},
    'connection_size': 'sizeof(struct horizon_server_connection)',
    'connection_thread': 'offsetof(struct horizon_server_connection, thread)',
    'object_size': 'sizeof(struct horizon_server_object)',
    'condition_size': 'sizeof(pthread_cond_t)',
    'legacy_waiter_size': 'sizeof(struct pes27_waiter)',
    **{'legacy_waiter_' + member: 'offsetof(struct pes27_waiter, ' + member + ')'
       for member in ('next', 'interest', 'condition')},
    'legacy_interest_size': 'sizeof(struct pes27_interest)',
    **{'legacy_interest_' + member: 'offsetof(struct pes27_interest, ' + member + ')'
       for member in ('handles', 'count', 'broad', 'thread')},
    'router_size': 'sizeof(struct pes27_router)',
    **{'router_' + member: 'offsetof(struct pes27_router, ' + member + ')'
       for member in ('head', 'notices', 'broad_notices', 'candidates',
                      'notified', 'filtered', 'sleeps')},
    'apc_counter_bytes': 'sizeof(sd_apc_notify_counts)',
    'sync_counter_bytes': 'sizeof(sd_sync_counts)',
}


def main():
    assert sys.platform == 'linux', 'Run ABI extraction under WSL'
    destination = ROOT / 'local/apc-v18'
    receipt = json.loads((destination / 'native.json').read_text())
    prepared = json.loads((destination / 'prepared.json').read_text())
    command = receipt['compile_commands']['dlls/ntdll/unix/horizon.c'].copy()
    production = Path(command[command.index('-c') + 1])
    assert sha(production) == prepared['files']['dlls/ntdll/unix/horizon.c']
    dependencies = {}
    for name in ('horizon.c', 'sd_apc_notify_v18.h', 'sd_sync_queue.h',
                 'sd_sync_state.h', 'sd_sync_router.h', 'sd_sync_legacy_wait.h'):
        item = production.parent / name
        digest = sha(item)
        assert digest == prepared['files']['dlls/ntdll/unix/' + name], name
        dependencies[str(item)] = digest
    source = destination / 'apc-layout.c'
    obj = destination / 'apc-layout.o'
    source.write_text('#include <stddef.h>\n#include "' + str(production) + '"\n'
        '__attribute__((used, section(".sd_v18_apc_layout"), aligned(8)))\n'
        'const unsigned long long sd_v18_apc_layout[] = {\n' +
        ',\n'.join('    ' + value for value in FIELDS.values()) + '\n};\n')
    for flag, value in (('-c', source), ('-o', obj), ('-MT', obj),
                        ('-MF', destination / 'apc-layout.d')):
        if flag in command:
            command[command.index(flag) + 1] = str(value)
    result = subprocess.run(command, cwd=receipt['working_directory'], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (destination / 'apc-layout.log').write_text(result.stdout)
    if result.returncode:
        print(result.stdout)
        raise SystemExit(result.returncode)
    for path, digest in dependencies.items():
        assert sha(Path(path)) == digest, ('production changed', path)
    elf = ROOT / 'local/symbols/sleepingdogs-apc-v18.elf'
    assert sha(elf) == receipt['elf_sha256']
    disassembly = destination / 'apc-notifier-disassembly.txt'
    objdump = Path(command[0]).with_name('aarch64-none-elf-objdump')
    disassembly.write_text(subprocess.check_output([
        str(objdump), '-d', '--disassemble=sd_sync_signal_apc_locked', str(elf)], text=True))
    production_lines = production.read_text().splitlines()
    call_lines = [i for i, line in enumerate(production_lines)
                  if 'sd_sync_signal_apc_locked(' in line]
    assert len(call_lines) == 1, 'Review caller preconditions if callsites change'
    call_line = call_lines[0]
    source_evidence = destination / 'apc-notifier-caller.txt'
    source_evidence.write_text('\n'.join(
        f'{i + 1}: {production_lines[i]}'
        for i in range(max(0, call_line - 30), min(len(production_lines), call_line + 10))) + '\n')
    write_json(destination / 'apc-layout.json', dict(
        fields=list(FIELDS), expressions=FIELDS, object_sha256=sha(obj),
        production_sha256=sha(production), production_dependencies=dependencies,
        build_elf_sha256=receipt['elf_sha256'], compile_command=command,
        probe_sha256=sha(source), linked_into_runtime=False,
        caller_line=call_line + 1, caller_count=len(call_lines),
        disassembly_sha256=sha(disassembly), caller_evidence_sha256=sha(source_evidence)))
    print('PASS: APC ABI extracted with the candidate ARM64 compiler', flush=True)


if __name__ == '__main__':
    main()
