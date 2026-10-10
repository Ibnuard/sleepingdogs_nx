"""Snapshot the reported New Game crash and record evidence separately from inference."""
from pathlib import Path
import re
from port_common import ROOT, sha, write_json


def main():
    source = Path('C:/Users/Administrator/Pictures/pesnx/SS/08')
    expected = {'crash.log': '5391270b6f01fbac2779ecfdba480c865a26617bf0b39ecac5f9de8300c1fd85',
        'fex-runtime.log': '90300dc32f458b2c867f1ce0bb7a7468b9a0b5aa5027773411b80722b24f9af4'}
    dest = ROOT / 'reports/streaming-memory-input'; dest.mkdir(exist_ok=True)
    for name, digest in expected.items():
        assert sha(source / name) == digest, 'Input changed: ' + name
        if (dest / name).exists(): assert sha(dest / name) == digest
        else: (dest / name).write_bytes((source / name).read_bytes())
    runtime = (dest / 'fex-runtime.log').read_text(errors='replace'); lines = runtime.splitlines()
    evidence = []
    for i, line in enumerate(lines, 1):
        if any(token in line for token in ('[SD-GPU-BUDGET]', '[SD-FEX-MODE]', '[SD-COMPILER-MEM]',
            '[SD-DXVK-MAP]', 'largest_examined=720952', 'used=262799360',
            '[SD-FIRSTFAULT] eip=00e5897a', '[SD-FIRSTFAULT] access=1 target=40',
            '[SD-FIRSTFAULT] eip=0071d2ab')):
            evidence.append({'line': i, 'text': line})
    assert 'paired_loader=1' in runtime and 'reserved_mib=256' in runtime
    assert 'eip=00e5897a' in runtime and 'target=40 ' in runtime
    assert 'deferred buffer allocation failed: bytes=5242880' in runtime
    pools = re.findall(r'\[SD-GPU-ARENA\] capacity=(\d+) used=(\d+) free=(\d+) largest=(\d+)', runtime)
    final_pool = dict(zip(('capacity', 'used', 'free', 'largest'), map(int, pools[-1])))
    assert final_pool == {'capacity':268435456, 'used':262799360, 'free':5636096, 'largest':2097152}
    write_json(ROOT / 'reports/streaming-memory-analysis.json', {
        'input_sha256': expected, 'original_log_directory': str(source),
        'user_progress': 'Main menu and New Game loading reached; crash approaching the 3D scene',
        'mode': 'gui', 'paired_256_mib_gpu_pool_active': True, 'fex_fastest': True,
        'gpu_oom_bytes': 5242880, 'final_gpu_pool': final_pool,
        'normal_heap_largest_examined_bytes': 720952,
        'dxvk_allocated_mib': 256, 'dxvk_used_mib': 241,
        'process_total_bytes': 2147483648, 'process_used_bytes': 2110832640,
        'last_periodic_render_snapshot': {'heap_free_bytes': 59251680, 'unclaimed_bytes': 44412928,
            'timing_caveat': 'Before the New Game failure; GUI has no contemporaneous full heap snapshot at OOM.'},
        'first_fault': {'module': 'HKShip.exe', 'eip': '0x00e5897a', 'instruction': 'rep movsd',
            'access': 'write', 'target': '0x40', 'ecx': '0x10', 'esi': '0x9f4f0040',
            'edi': '0x40', 'caller': '0x00a5a6fe'},
        'secondary_fault': {'eip': '0x0071d2ab', 'target': '0x10005'},
        'inference': 'The game copies to NULL+0x40 after a failed deferred Map. Native GPU backing is fragmented and nearly full.',
        'source_observation': 'sdmem1 tries shared suballocation even for large mapped buffers. A small live allocation can retain a retiring large buffer backing.',
        'hypothesis': 'Dedicated large mapped allocations plus size segregation reduce small-allocation interference during scene loading. The log does not record every resource lifetime.',
        'change': {'mapped_dedicated_threshold_bytes':2097152, 'total_gpu_pool_bytes':268435456,
            'large_preferred_region_bytes':67108864, 'small_borrow_contiguous_guard_bytes':16777216,
            'forwarder_unchanged':True, 'compiler_buffers_unchanged':True},
        'evidence': evidence, 'candidate_hardware_tested': False})
    print('Recorded New Game OOM evidence and immutable log hashes.')


if __name__ == '__main__': main()
