"""Extract the v3 loading stall evidence without changing the game or runtime."""
from pathlib import Path
import argparse
import bisect
import json
import re
import shutil

from port_common import ROOT, sha, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, default=ROOT / 'dist/sleepingdogs-fex-low-window-loading-watch/fex-runtime.log')
    args = parser.parse_args()
    expected = 'bc83d378715f4e3284feeff39ffea08fda92f74b661605d7e5b8a63a0791b7f3'
    assert sha(args.log) == expected, 'This analysis is pinned to the supplied v3 session'
    saved = ROOT / 'local/loading-freeze-v3/fex-runtime.log'
    saved.parent.mkdir(parents=True, exist_ok=True)
    if saved.exists():
        assert sha(saved) == expected
    else:
        shutil.copy2(args.log, saved)
    lines = saved.read_text(encoding='utf-8').splitlines()

    presents, waits, pipes, resources, stacks = [], [], [], [], []
    seconds = None
    for number, line in enumerate(lines, 1):
        match = re.match(r'\[SD-LOAD\] v1 t=(\d+)s presents=(\d+) delta=(\d+) present_seen=(\d+) age_ms=(\d+) present_errors=(\d+)', line)
        if match:
            seconds, count, delta, seen, age, errors = map(int, match.groups())
            presents.append(dict(line=number, seconds=seconds, count=count, delta=delta, seen=seen, age_ms=age, errors=errors))
        match = re.match(r'\[SD-CALL\] tid=(4|72) NtWaitForSingleObject (entered|returned) age_ms=(\d+) status=([0-9a-f]+) calls=(\d+)/(\d+) a0=6d4ffff0 a1=0 a2=0 ', line)
        if match:
            tid, state, age, status, completed, calls = match.groups()
            waits.append(dict(line=number, seconds=seconds, tid=int(tid), state=state, status=status,
                              age_ms=int(age), completed=int(completed), total_calls=int(calls)))
        if line.startswith('[FEX3-PIPE] ') and ' n=' in line:
            phase, count = re.search(r'\[FEX3-PIPE\] (\w+) n=(\d+)', line).groups()
            pipes.append(dict(line=number, seconds=seconds, phase=phase, completed_calls=int(count)))
        if line.startswith('[SD-RESOURCE] '):
            resources.append(dict(line=number, **{k: int(v) for k, v in re.findall(r'(heap_available|free_threads)=(\d+)', line)}))
        if re.match(r'\[SD-STACK\] tid=(4|72)w round=0 ', line) and 'guest= bb6f3b bb7c6a bb7e31' in line:
            stacks.append(dict(line=number, text=line))

    plateau = [p for p in presents if p['seconds'] >= 115]
    assert len(plateau) >= 10 and all(p['count'] == 3441 and p['errors'] == 0 for p in plateau)
    assert all(p['completed_calls'] == 0 for p in pipes if p['seconds'] >= 130 and p['phase'] != 'shared_clock_gap')
    threads = {}
    for tid in (4, 72):
        rows = [w for w in waits if w['tid'] == tid]
        assert len(rows) >= 10 and any(w['status'] == 'c0000008' for w in rows)
        assert rows[-1]['total_calls'] > rows[0]['total_calls'] + 10000000
        threads[str(tid)] = dict(first=rows[0], last=rows[-1],
                                call_growth=rows[-1]['total_calls'] - rows[0]['total_calls'],
                                invalid_handle_returns_observed=sum(w['status'] == 'c0000008' for w in rows))

    # Resolve native samples using exactly the shipped ELF, never a later build.
    from elftools.elf.elffile import ELFFile
    elf_path = ROOT / 'local/symbols/sleepingdogs-low-window-v3.elf'
    assert sha(elf_path) == '7749eebcd8f222f88c060013e03840fb86ac9ce220d598dc920717c72663e47c'
    with elf_path.open('rb') as f:
        symbols = list(ELFFile(f).get_section_by_name('.symtab').iter_symbols())
        observer_symbol = next(s['st_value'] for s in symbols if s.name == 'wine_nx_f1_thread_snapshot')
        functions = sorted((s['st_value'], s['st_size'], s.name) for s in symbols
                           if s['st_info']['type'] == 'STT_FUNC' and s['st_size'])
    observer = int(re.search(r'observer=([0-9a-f]+);', '\n'.join(lines)).group(1), 16)
    runtime_base = observer - observer_symbol
    addresses = [s[0] for s in functions]
    for stack in stacks:
        native = stack['text'].split('native=')[1].split('guest=')[0].split()
        resolved = []
        for address in native:
            offset = int(address, 16) - runtime_base
            index = bisect.bisect_right(addresses, offset) - 1
            if index >= 0:
                start, size, name = functions[index]
                if offset < start + size:
                    resolved.append(f'{name}+0x{offset-start:x}')
                    continue
            resolved.append(f'unresolved:{address}')
        stack['native_symbols'] = resolved

    # Static inspection of the original executable: no patched file or mock
    # result is used as evidence that the runtime has been fixed.
    import pefile
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    game = ROOT.parent / 'Sleeping Dogs/HKShip.exe'
    game_hash = sha(game)
    assert game_hash == '3c2eaa260ee29dfb464a0321aa9c7dc74e343894b663fac4fdd11d40fab0bacc'
    pe = pefile.PE(str(game))
    imports = {entry.address: entry.name.decode() for module in pe.DIRECTORY_ENTRY_IMPORT
               for entry in module.imports if entry.name}
    assert imports[0x10e111c] == 'CreateSemaphoreA'
    assert imports[0x10e11c4] == 'WaitForSingleObject'
    assert imports[0x10e10fc] == 'CloseHandle'
    cs = Cs(CS_ARCH_X86, CS_MODE_32)
    def disasm(start, size):
        return [dict(address=hex(i.address), instruction=i.mnemonic + ' ' + i.op_str)
                for i in cs.disasm(pe.get_data(start-pe.OPTIONAL_HEADER.ImageBase, size), start)]
    wait_wrapper = disasm(0xbb6f30, 12)
    assert wait_wrapper[0]['instruction'] == 'mov eax, dword ptr [ecx]'
    assert wait_wrapper[-1]['instruction'].strip() == 'ret'
    assert len(wait_wrapper) == 5
    result = dict(input_sha256=expected, input_bytes=saved.stat().st_size,
        build='sleepingdogs-fextendo-0.1.0-low-window-v3-load-watch',
        profile='fastest', scalar_tso=0, vector_tso=0, memcpy_tso=0,
        present_plateau=dict(first=plateau[0], last=plateau[-1], samples=len(plateau)),
        invalid_wait=dict(handle='0x6d4ffff0', status='0xc0000008', status_name='STATUS_INVALID_HANDLE',
                          alertable=False, timeout='infinite', threads=threads),
        last_resource=resources[-1], last_heap_available_mib=resources[-1]['heap_available']/1048576,
        last_vkmem=next(line for line in reversed(lines) if line.startswith('[SD-VKMEM-STATS]')),
        completed_driver_calls_after_130_seconds=0,
        native_runtime_base=hex(runtime_base), elf_sha256=sha(elf_path),
        representative_stacks=[next(s for s in stacks if f'tid={tid}w ' in s['text']) for tid in (4, 72)],
        game_sha256=game_hash, game_modified=False,
        semaphore_constructor=disasm(0xbb6f00, 30), wait_wrapper=wait_wrapper,
        diagnosis='Two game job-queue threads repeatedly retry an invalid semaphore handle while Present stops. The origin of the invalid value is unproven.',
        limits=['Available native heap is not a proof of sufficient space inside every game suballocator.',
                'Completed driver-call counters alone do not rule out all GPU problems.',
                'Relaxed memory ordering, stale/freed storage and other guest/runtime corruption are hypotheses, not established causes.'],
        next_experiment='Same v3 runtime and assets; launcher/fex-mode.txt changes from fastest to fast, enabling scalar/vector/memcpy TSO. No game or binary changes.',
        hardware_fix_confirmed=False)
    write_json(ROOT / 'reports/low-window-invalid-semaphore-analysis.json', result)
    print(json.dumps({k: result[k] for k in ('input_sha256', 'present_plateau', 'invalid_wait', 'last_heap_available_mib', 'diagnosis')}, indent=2))


if __name__ == '__main__':
    main()
