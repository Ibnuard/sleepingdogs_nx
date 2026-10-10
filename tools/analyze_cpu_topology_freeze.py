"""Link the preserved v5 device evidence to the original-code CPU/queue replay."""
import json
import re
import struct
from port_common import ROOT, sha, write_json


def main():
    path = ROOT / 'local/loading-freeze-v5-fxtmem/fex-runtime.log'
    digest = 'a824b17585f2b3b001a0665116b87041f277c4da92d6ed359aae92b8f4317a49'
    assert sha(path) == digest
    lines = path.read_text(encoding='utf-8').splitlines()
    progress = []
    for number, line in enumerate(lines, 1):
        match = re.match(r'\[SD-LOAD\] v1 t=(\d+)s presents=(\d+) delta=(\d+) present_seen=(\d+) age_ms=(\d+) present_errors=(\d+)', line)
        if match:
            sec, count, delta, seen, age, errors = map(int, match.groups())
            progress.append(dict(line=number, seconds=sec, presents=count, age_ms=age, present_errors=errors))
    captures = []
    for seq, tid in ((30, 4), (31, 72)):
        obj = next(line for line in lines if line.startswith(f'[SD-SYNC-OBJECT] seq={seq} '))
        base = int(re.search(r'queue=([a-f0-9]+)', obj).group(1), 16)
        data = bytearray(352)
        filled = 0
        for line in lines:
            match = re.match(rf'\[SD-SYNC-MEM\] seq={seq} queue address=([a-f0-9]+) words= (.*)', line)
            if not match: continue
            offset = int(match[1], 16) - base
            payload = b''.join(struct.pack('<I', int(word, 16)) for word in match[2].split())
            data[offset:offset+len(payload)] = payload
            filled += len(payload)
        assert filled == 352
        count, default = (struct.unpack_from('<I', data, offset)[0] for offset in (0x64, 0x54))
        slot = int(re.search(r' index=(\d+)', obj).group(1))
        assert count == 0 and default == slot == 0xffffffde and data[0x121] == 0xde
        captures.append(dict(seq=seq, tid=tid, queue=hex(base), worker_count=count,
                             default_index_signed=-34, used_index_signed=-34,
                             index_table=data[0x121:0x12d].hex(),
                             pointer_array_address_for_bad_index=hex(base+0x78-34*4),
                             invalid_wait=next(line for line in lines if line.startswith(f'[SD-SYNC] v1 seq={seq} '))))
    heap_line = next(line for line in reversed(lines) if line.startswith('[SD-RESOURCE]'))
    available = int(re.search(r'heap_available=(\d+)', heap_line).group(1))
    vkmem = next(line for line in reversed(lines) if line.startswith('[SD-VKMEM-STATS]'))
    assert available == 1060842912 and re.search(r'\boom=0\b', vkmem)
    plateau = [p for p in progress if p['presents'] == progress[-1]['presents']]
    assert len(plateau) >= 3 and progress[-1]['presents'] == 2442
    binary = json.loads((ROOT/'reports/low-window-v6-cpu-topology.json').read_text())
    assert binary['status'] == 'PASS'
    assert binary['old_game']['indices'] == [0xffffffde]
    assert binary['new_game']['indices'] == [1, 0, 0, 0]
    result = dict(status='PASS', log_sha256=digest, log_bytes=path.stat().st_size,
        profile=next(line for line in lines if line.startswith('[SD-FEX-MODE]')),
        low_window=next(line for line in lines if line.startswith('[SD-LOWVA] v1 host=')),
        plateau=plateau, last_heap_available_bytes=available,
        last_heap_available_mib=round(available/1048576, 2), vkmem=vkmem,
        invalid_captures=captures, original_code_replay={
            'report_sha256':sha(ROOT/'reports/low-window-v6-cpu-topology.json'),
            'old':binary['old_game'], 'new':binary['new_game']},
        diagnosis='Horizon logical-processor API has no backend in v5; HKShip replaces its GetSystemInfo count with zero after the failed topology query. The queue initializer skips the worker map and later sign-extends untouched 0xde to -34, indexing before the semaphore array.',
        qualification='Device queue snapshots are non-atomic. The API/initialization chain is reproduced from original ARM64 Wine and x86 game/kernelbase code with modeled platform boundaries, not a full hardware gameplay test.',
        hardware_freeze_fixed=False,
        sources={'tools/analyze_cpu_topology_freeze.py':sha(ROOT/'tools/analyze_cpu_topology_freeze.py')})
    write_json(ROOT/'reports/loading-freeze-v5-cpu-topology-analysis.json', result)
    print(json.dumps({k:result[k] for k in ('status','plateau','last_heap_available_mib','diagnosis')}, indent=2))


if __name__ == '__main__':main()
